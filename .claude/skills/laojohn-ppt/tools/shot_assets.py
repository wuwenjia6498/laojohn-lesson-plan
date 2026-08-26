# -*- coding: utf-8 -*-
"""shot_assets.py - 把已有成品（PDF / docx / pptx / html）按工单截成 PNG，供宣讲件贴图。

只服务「宣讲 profile」这条线：宣讲件要展示"老师实际拿到的材料长什么样"，
素材全部是仓内已有的成品，不新造内容。放 tools/ 不放 scripts/——scripts/ 是产线
脚本（每次烘焙都跑），本件是出素材的一次性工具。

用法：
    PYTHONUTF8=1 python .claude/skills/laojohn-ppt/tools/shot_assets.py \
        --shots "写作课相关宣传文件/同步写作课上线宣讲/shots.json" [--force] [--dry-run]

工单 JSON：
    {
      "out_dir": "写作课相关宣传文件/同步写作课上线宣讲/imgs",
      "shots": [
        {"src": "写作配套输出/…/…-学生用.pdf", "page": 1, "out": "学生单-构思表.png"},
        {"src": "写作课详案输出/…-写作课详案.docx", "page": 1, "out": "详案-首页.png"},
        {"src": "写作课件PPT输出/…/…-课件PPT.pptx", "slide": 6, "out": "课件-示范文页.png"}
      ]
    }
    page/slide 均 1 基。dpi 缺省 170（够清晰，又不至于把 pptx 撑爆）。

四条链与本机依赖（2026-08-24 实测）：
    .pdf  → PyMuPDF(fitz) 直接光栅化                      【已装 1.25.3】
    .docx → Word COM 导 PDF → PyMuPDF                     【pywin32 + MS Office 已装】
    .pptx → PowerPoint COM 逐页 Export PNG                【同上】
    .html → Playwright 截图                               【已装】
    本机没有 LibreOffice / pandoc，所以 docx/pptx 只有 COM 这一条路。

COM 的三个坑（踩中的表现都不像"文件打不开"，别往错方向查）：
  1. 目标文件正被 Word/WPS/PowerPoint 打开时，COM 可能拿到只读句柄或整个卡住。
     脚本开跑前先提示，卡住就去关掉那个窗口。
  2. Quit() 必须放 finally——异常时不退会留一个后台 WINWORD/POWERPNT 进程，
     下次运行行为诡异（拿到上次的脏实例）。
  3. WPS 抢注了 .docx/.pptx 关联时，Dispatch("Word.Application") 可能落到 WPS 的
     COM 实现上，ExportAsFixedFormat 的参数名不同 → 这里用位置参数并 try/except，
     失败就明确报错让用户手动"另存为 PDF"，不要静默出一张空图。

版权红线：截图一律避开含教材插图 / 原书扫描页的版面（尤其 `-配图.docx` 那一版详案），
只截自制内容。仓内那些扫描件仅限内部备课使用，不得随宣讲件对外转发。
"""
import argparse
import json
import os
import sys

NEWLINE = chr(10)
MAX_EDGE = 1600          # 长边上限（像素）：控 pptx 体积，40 页十几张全页图很容易上百 MB
DEFAULT_DPI = 170


def _log(msg):
    print(msg, flush=True)


# ---------------------------------------------------------------- PDF
def pdf_to_png(src, page_no, out, dpi):
    import fitz
    doc = fitz.open(src)
    try:
        if not (1 <= page_no <= doc.page_count):
            raise ValueError(f"{src} 只有 {doc.page_count} 页，要不到第 {page_no} 页")
        pix = doc[page_no - 1].get_pixmap(dpi=dpi)
        pix.save(out)
    finally:
        doc.close()


# ---------------------------------------------------------------- docx
_WORD_TMP = "_shot_tmp_word.pdf"


def docx_to_png(src, page_no, out, dpi):
    """Word COM 先整篇导 PDF（缓存复用），再由 PyMuPDF 取那一页。"""
    cache = os.path.join(os.path.dirname(os.path.abspath(out)),
                         os.path.splitext(os.path.basename(src))[0] + ".__cache.pdf")
    if not os.path.isfile(cache) or os.path.getmtime(cache) < os.path.getmtime(src):
        _docx_export_pdf(src, cache)
    pdf_to_png(cache, page_no, out, dpi)


def _docx_export_pdf(src, pdf_out):
    import win32com.client
    word = None
    doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        try:
            word.DisplayAlerts = 0
        except Exception:
            pass                      # WPS 的实现可能没有这个属性
        doc = word.Documents.Open(os.path.abspath(src), ReadOnly=True)
        # 17 = wdExportFormatPDF；用位置参数，兼容 WPS 的参数命名差异
        doc.ExportAsFixedFormat(os.path.abspath(pdf_out), 17)
    except Exception as e:
        raise RuntimeError(
            f"Word COM 导出失败：{src}\n  {e}\n"
            f"  排查：① 该文件是否正被 Word/WPS 打开（关掉再跑）；"
            f"② 若本机是 WPS 接管 .docx，请手动『另存为 PDF』到 {pdf_out} 后重跑。") from e
    finally:
        try:
            if doc is not None:
                doc.Close(0)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass


# ---------------------------------------------------------------- pptx
def pptx_to_png_batch(src, jobs):
    """PowerPoint COM 一次会话导出多页。jobs = [(slide_no, out_path), ...]

    必须批量、不能一张一开一关：Quit() 之后 PowerPoint 要几秒才真正退出，期间
    再 Dispatch 会拿到正在退出的实例，下一次 Presentations.Open 直接失败，报
    「发生意外 / Presentations.Open : Failed」——这条报错读起来像"文件被占用"，
    与真实原因（上次会话没退干净）完全无关，极易查错方向。实测踩过一次。
    """
    import win32com.client
    app = None
    prs = None
    results = []
    try:
        try:
            # 早期绑定：命名参数与返回类型都靠类型库解析，最稳
            from win32com.client import gencache
            app = gencache.EnsureDispatch("PowerPoint.Application")
        except Exception:
            app = win32com.client.Dispatch("PowerPoint.Application")
        # 位置参数 (FileName, ReadOnly, Untitled, WithWindow)；-1=msoTrue, 0=msoFalse。
        # 动态绑定下命名参数会让 Open 返回非 Presentation 对象，取 .Slides 就报
        # 「Open.Slides」——那条报错读起来像文件被占用，与真实原因毫无关系。
        prs = app.Presentations.Open(os.path.abspath(src), -1, 0, 0)
        total = prs.Slides.Count
        w = MAX_EDGE
        h = int(MAX_EDGE * 9 / 16)          # 16:9 按长边导出
        for slide_no, out in jobs:
            if not (1 <= slide_no <= total):
                results.append((out, "%s 只有 %d 页，要不到第 %d 页"
                                % (os.path.basename(src), total, slide_no)))
                continue
            prs.Slides(slide_no).Export(os.path.abspath(out), "PNG", w, h)
            results.append((out, None))
    except Exception as e:
        raise RuntimeError(
            "PowerPoint COM 导出失败：%s%s  %s%s"
            "  排查：该文件是否正被 PowerPoint/WPS 打开（关掉再跑）。"
            % (src, NEWLINE, e, NEWLINE)) from e
    finally:
        try:
            if prs is not None:
                prs.Close()
        except Exception:
            pass
        try:
            if app is not None:
                app.Quit()
        except Exception:
            pass
    return results


# ---------------------------------------------------------------- html
def html_to_png(src, out, width=1200):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": width, "height": 900},
                        device_scale_factor=2)
        pg.goto("file:///" + os.path.abspath(src).replace("\\", "/"))
        pg.wait_for_timeout(600)
        pg.screenshot(path=out, full_page=True)
        b.close()


# ---------------------------------------------------------------- 后处理
def shrink(path):
    """长边压到 MAX_EDGE 以内并 optimize 重存，控 pptx 体积。"""
    try:
        from PIL import Image
    except ImportError:
        return
    with Image.open(path) as im:
        im = im.convert("RGB") if im.mode in ("RGBA", "P") else im
        w, h = im.size
        if max(w, h) > MAX_EDGE:
            s = MAX_EDGE / max(w, h)
            im = im.resize((int(w * s), int(h * s)), Image.LANCZOS)
        im.save(path, "PNG", optimize=True)


def main():
    ap = argparse.ArgumentParser(description="宣讲件实物截图取图器")
    ap.add_argument("--shots", required=True, help="工单 JSON 路径")
    ap.add_argument("--force", action="store_true", help="忽略幂等，全部重出")
    ap.add_argument("--dry-run", action="store_true", help="只列计划，不真出图")
    args = ap.parse_args()

    with open(args.shots, encoding="utf-8") as f:
        job = json.load(f)

    root = os.path.dirname(os.path.abspath(args.shots))
    out_dir = job.get("out_dir") or os.path.join(root, "imgs")
    if not os.path.isabs(out_dir):
        out_dir = os.path.normpath(os.path.join(os.getcwd(), out_dir))
    os.makedirs(out_dir, exist_ok=True)

    manifest = []
    pptx_pending = {}      # {pptx 源: [(slide_no, out), ...]} 同一份只开一次会话
    done = skipped = failed = 0
    for s in job["shots"]:
        src = s["src"]
        if not os.path.isabs(src):
            src = os.path.normpath(os.path.join(os.getcwd(), src))
        out = os.path.join(out_dir, s["out"])
        dpi = int(s.get("dpi", DEFAULT_DPI))
        page = int(s.get("page") or s.get("slide") or 1)
        ext = os.path.splitext(src)[1].lower()

        if not os.path.isfile(src):
            _log(f"[缺源] {s['out']}  <- {src}")
            failed += 1
            continue
        # 幂等：产物比源新就跳过（省掉反复起 Word/PowerPoint 的时间）
        if (not args.force and os.path.isfile(out)
                and os.path.getmtime(out) >= os.path.getmtime(src)):
            _log(f"[跳过] {s['out']}（已是最新）")
            skipped += 1
            manifest.append((s["out"], src, page))
            continue
        if args.dry_run:
            _log(f"[计划] {s['out']}  <- {os.path.basename(src)} 第 {page} 页")
            continue

        try:
            if ext == ".pdf":
                pdf_to_png(src, page, out, dpi)
            elif ext == ".docx":
                docx_to_png(src, page, out, dpi)
            elif ext == ".pptx":
                pptx_pending.setdefault(src, []).append((page, out))
                manifest.append((s["out"], src, page))
                continue          # 同一份 pptx 攒到一起，见下方批处理
            elif ext in (".html", ".htm"):
                html_to_png(src, out)
            else:
                raise ValueError(f"不支持的源格式：{ext}")
            shrink(out)
            kb = os.path.getsize(out) // 1024
            _log(f"[出图] {s['out']}  ({kb} KB)")
            done += 1
            manifest.append((s["out"], src, page))
        except Exception as e:
            _log(f"[失败] {s['out']}  {e}")
            failed += 1

    # pptx 批处理：每份源只开一次 PowerPoint
    for psrc, jobs in pptx_pending.items():
        try:
            for out, err in pptx_to_png_batch(psrc, jobs):
                if err:
                    _log("[失败] %s  %s" % (os.path.basename(out), err))
                    failed += 1
                else:
                    shrink(out)
                    _log("[出图] %s  (%d KB)"
                         % (os.path.basename(out), os.path.getsize(out) // 1024))
                    done += 1
        except Exception as e:
            _log("[失败] %s 的 %d 张  %s" % (os.path.basename(psrc), len(jobs), e))
            failed += len(jobs)

    # 清掉 docx 链的中间 PDF 缓存
    for fn in os.listdir(out_dir):
        if fn.endswith(".__cache.pdf"):
            try:
                os.remove(os.path.join(out_dir, fn))
            except OSError:
                pass

    if manifest and not args.dry_run:
        lines = ["# 宣讲件实物截图 · 图单", "",
                 "> 由 `tools/shot_assets.py` 按 `shots.json` 自动生成，可重跑覆盖。",
                 "> 图与本表都在已 gitignore 的宣传件目录内、不入库；追溯信息同时抄进中间稿文件头。",
                 "",
                 "| 图 | 来源文件 | 页 |", "| --- | --- | --- |"]
        for name, src, page in manifest:
            lines.append(f"| {name} | {os.path.relpath(src, os.getcwd())} | {page} |")
        with open(os.path.join(out_dir, "_图单.md"), "w",
                  encoding="utf-8", newline="") as f:
            f.write("\n".join(lines) + "\n")

    _log(f"\n出图 {done} 张，跳过 {skipped} 张，失败 {failed} 张 -> {out_dir}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
