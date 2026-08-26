# -*- coding: utf-8 -*-
r"""render_promo_html.py —— 写作课对外宣传件 HTML → PDF 渲染（单一入口）

    PYTHONUTF8=1 python render_promo_html.py             # 渲全部
    PYTHONUTF8=1 python render_promo_html.py 家长端海报   # 只渲一份

服务对象＝`写作课相关宣传文件\` 下那两份自包含海报 html（logo 内嵌 base64、零外链）。
它们不属于任何 laojohn-* skill 线，各自的输出模型又不同，故收敛成本脚本一个入口，
差异全部写进下面的 PROFILES 表。

**为什么不复用 `laojohn-reading-guide\scripts\_a4_render.py`**：那件是 data.json ＋
`/*__DATA__*/ null` 模板注入驱动、宽度硬编码 794px，且 CLAUDE.md §3 已登记它是读书会
下游三家（阅读指南/两种导图）的单一源。宣传件不在那条线上，往里加宽度分支等于把
「A4 单页动态高」和「A4 横版固定尺寸」两种输出模型塞进同一个引擎。

两个模型：
    tall  —— 视口宽 width_px，量 #page（回退 body）的 scrollHeight，按该高度出单页、不分页。
             家长端海报是手机阅读的窄长图：480 css px ＝ 360 pt，与原件 MediaBox 精确相等。
    fixed —— 给定纸张尺寸 + scale。馆内海报是 A4 横版，**scale 必须 0.98**：
             1.0 与 0.99 都会把页脚那行「让孩子从『怕写』到『会写』」挤到第 2 页（实测）。

⚠ 三条会咬人的：
  1. **CLI 覆盖参数默认值一律 None**（照 CLAUDE.md §3 对 insert_images_docx.py 立的红线）：
     给硬默认会永久盖住 PROFILES 里的值，且完全静默、渲出来的东西看不出哪里不对。
  2. **改文案只改 html，不要去改 pdf**。2026-08-26 曾因误判「家长端海报无源」而用 PyMuPDF
     原位手改过一次 pdf，代价是体积 391 KB → 12.8 MB（TextWriter 嵌了整套微软雅黑而非子集）、
     文字层阅读顺序错乱（新写的行落到内容流末尾）。源一直都在，只是当时叫「招生海报.html」。
  3. 同目录的 `招生海报.pdf` 是 0817 的孤儿件（浏览器手工打印、正文残留 "or browse files"），
     **与现存任何 html 都不对应，本脚本不管它**，也不要试图用哪个 html 去覆盖它。
"""
import argparse
import os
import sys
from pathlib import Path

# Playwright 浏览器路径（未设环境变量时回退到本机默认 ms-playwright；环境变量优先于此缺省值）
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"),
)

ROOT = Path(__file__).resolve().parent

PROFILES = {
    "家长端海报": {
        "src": "写作课相关宣传文件/家长端海报.html",
        "out": "写作课相关宣传文件/家长端海报.pdf",
        "mode": "tall",
        "width_px": 480,          # ＝360 pt，与原件 MediaBox 精确相等
        "scale": None,
        "expect_pages": 1,
    },
    "馆内海报": {
        "src": "写作课相关宣传文件/馆内张贴海报.html",
        "out": "写作课相关宣传文件/馆内海报.pdf",
        "mode": "fixed",
        "width": "11.706in",      # 842.88 pt · A4 横版
        "height": "8.277in",      # 595.92 pt
        "scale": 0.98,            # 1.0/0.99 会溢出到第 2 页，实测
        "expect_pages": 1,
    },
}

NO_MARGIN = {"top": "0", "bottom": "0", "left": "0", "right": "0"}


def render(name, prof, width_px=None, scale=None):
    """渲一份。width_px / scale 为 None 时用 profile 里的值——不要给它们硬默认。"""
    from playwright.sync_api import sync_playwright

    src = ROOT / prof["src"]
    out = ROOT / prof["out"]
    if not src.exists():
        raise SystemExit("源 html 不存在：%s" % src)

    mode = prof["mode"]
    eff_scale = prof.get("scale") if scale is None else scale

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto(src.as_uri())
        page.wait_for_timeout(800)          # 等 base64 图与字体落位
        page.emulate_media(media="print")

        kw = {"path": str(out), "print_background": True, "margin": NO_MARGIN}
        if eff_scale is not None:
            kw["scale"] = eff_scale

        if mode == "tall":
            w = prof.get("width_px") if width_px is None else width_px
            page.set_viewport_size({"width": w, "height": 1200})
            h = page.evaluate(
                "() => {const e = document.querySelector('#page') || document.body;"
                " return Math.ceil(Math.max(e.scrollHeight, document.body.scrollHeight));}"
            )
            kw["width"] = "%dpx" % w
            kw["height"] = "%dpx" % h
        elif mode == "fixed":
            kw["width"] = prof["width"]
            kw["height"] = prof["height"]
        else:
            raise SystemExit("未知 mode：%s" % mode)

        page.pdf(**kw)
        browser.close()

    return out


def selfcheck(name, prof, out):
    import fitz

    doc = fitz.open(out)
    n = len(doc)
    rect = doc[0].rect
    size_kb = out.stat().st_size / 1024
    print("  %s → %d 页 · %.2f×%.2f pt · %.0f KB"
          % (out.name, n, rect.width, rect.height, size_kb))

    exp = prof.get("expect_pages")
    ok = True
    if exp is not None and n != exp:
        print("  !! 页数核验：%d 页，预期 %d 页——内容溢出，调 scale 或压数据层" % (n, exp))
        ok = False
    if size_kb > 2048:
        print("  !! 体积 %.1f MB 偏大：多半是字体没做子集，检查是不是又去手改 pdf 了" % (size_kb / 1024))
        ok = False
    doc.close()
    return ok


def main():
    ap = argparse.ArgumentParser(description="宣传件 HTML → PDF")
    ap.add_argument("names", nargs="*", help="要渲的 profile 名，省略＝全渲")
    # 覆盖参数默认值一律 None，见文件头注释坑 1
    ap.add_argument("--width-px", type=int, default=None, help="仅 tall 模式：覆盖视口宽")
    ap.add_argument("--scale", type=float, default=None, help="覆盖缩放")
    args = ap.parse_args()

    names = args.names or list(PROFILES)
    bad = [n for n in names if n not in PROFILES]
    if bad:
        raise SystemExit("未知 profile：%s（可选：%s）" % ("、".join(bad), "、".join(PROFILES)))

    all_ok = True
    for name in names:
        prof = PROFILES[name]
        print("[%s]" % name)
        out = render(name, prof, width_px=args.width_px, scale=args.scale)
        all_ok &= selfcheck(name, prof, out)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
