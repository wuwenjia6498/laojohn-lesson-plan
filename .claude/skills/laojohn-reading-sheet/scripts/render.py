# -*- coding: utf-8 -*-
"""老约翰 · 阅读单渲染引擎（通用，加模板不用改这里）。

输入：一份 manifest.json，描述某本书要出的所有阅读单。
输出：每张阅读单一个 .pdf + .html（HTML 自包含，可独立打开/再编辑）。

用法（Windows，先确认盘符）：
    set PYTHONUTF8=1
    set PLAYWRIGHT_BROWSERS_PATH=C:/Users/<你>/AppData/Local/ms-playwright
    python render.py <manifest.json> <输出目录> [--png] [--no-bundle]

渲染完默认再合出两份「全套」PDF（按 manifest 次序排，= 教学先后次序）：
    <书名>-阅读单-空白版-全套.pdf   ← 各单子的空白/派发版（学生打印用）
    <书名>-阅读单-示范版-全套.pdf   ← 各单子的示范版（无示范的用其唯一版兜底）
归类规则：<名>-空 进空白册、<名>-示范 进示范册、无后缀单版两册都收；同一基名
两册各取对应版、无对应版则兜底，保证两册都覆盖全部单子、不缺页。可在某 sheet
上加 "packet": "both|blank|demo|none" 覆盖默认归属。--no-bundle 关掉合册。

manifest.json 结构：
{
  "book": "格列佛游记",
  "sheets": [
    {"file": "预测阅读单-空", "template": "table", "data": { ...见 data-schema.md... }},
    {"file": "维恩图-空",     "template": "venn",  "data": { ... }}
  ]
}
- file：输出文件名（不含扩展名），约定 <阅读单名>-空 / -示范。
- template：模板键，对应 templates/template_<键>.html（table/venn/ladder/logic/voyage…）。
- data：注入模板的字段；logo 由本脚本统一注入，data 里不用写。

页面尺寸由模板自报：渲染后量 #page 实际宽高出 PDF——
竖版 794×(≥1123 自适应)，横版模板(如 timeline)自带 1123×794。
"""
import os, sys, json, base64, pathlib

# 移动硬盘：盘符可能变动，全部用相对本文件的路径解析，不硬编码盘符。
HERE = pathlib.Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
TEMPLATES = SKILL_ROOT / "templates"
PROJECT_ROOT = SKILL_ROOT.parents[2]   # .../.claude/skills/<skill> → 上溯到项目根

# Playwright 浏览器路径（未设环境变量时回退到本机默认）
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    str(pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"),
)

A4_W, A4_H = 794, 1123          # 竖版 A4（默认）
VIEW_W = 1280                   # 渲染视口宽（容得下横版模板，竖版固定宽不受影响）

# 直角引号 → 规范弯引号：「」→“”（双）、『』→‘’（嵌套单）。
# 阅读单成品统一用弯引号，data 里若残留「」一律就地归一，杜绝漏改。
_QUOTE_MAP = str.maketrans({"「": "“", "」": "”", "『": "‘", "』": "’"})


def normalize_quotes(obj):
    """递归把 data 里所有字符串的直角引号换成规范弯引号。"""
    if isinstance(obj, str):
        return obj.translate(_QUOTE_MAP)
    if isinstance(obj, list):
        return [normalize_quotes(x) for x in obj]
    if isinstance(obj, dict):
        return {k: normalize_quotes(v) for k, v in obj.items()}
    return obj


def load_logo():
    p = PROJECT_ROOT / "品牌资产" / "logo.png"
    if not p.exists():
        sys.stderr.write(f"[warn] 找不到 logo：{p}\n")
        return ""
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


def template_text(key):
    f = TEMPLATES / f"template_{key}.html"
    if not f.exists():
        raise SystemExit(f"[error] 未知模板 '{key}'：缺少 {f.name}。"
                         f"（新增模板见 SKILL.md「如何加第 N 种模板」）")
    return f.read_text(encoding="utf-8")


def safe_pdf(page, path, width, height):
    """写 PDF；目标被预览器锁住时改写 .new.pdf 旁路，不中断整批。"""
    kw = dict(width=f"{width}px", height=f"{height}px", print_background=True,
              margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    try:
        page.pdf(path=str(path), **kw)
        return str(path.name)
    except Exception:
        alt = path.with_suffix(".new.pdf")
        page.pdf(path=str(alt), **kw)
        sys.stderr.write(f"[warn] {path.name} 被占用，已改写 {alt.name}\n")
        return str(alt.name)


# ── 全套合册：把单张按 manifest 次序拼成「空白版」「示范版」两本 ──
def _split_name(fname):
    """<名>-空 / <名>-示范 / <名>(单版) → (basename, version)。"""
    if fname.endswith("-空"):
        return fname[:-2], "空"
    if fname.endswith("-示范"):
        return fname[:-3], "示范"
    return fname, "单"


def plan_bundles(sheets):
    """按出现次序分组，定每本收哪些文件。返回 (空白册文件名表, 示范册文件名表)。

    同一基名的多版归一组：空白册取「空 > 单 > 示范」、示范册取「示范 > 空 > 单」，
    故无示范版的单子(如故事山形图/两难思辨/纯主观单)也会以兜底版进两册、不缺页。
    sheet 上的 "packet"(both|blank|demo|none) 覆盖该组默认归属。
    """
    import collections
    groups = collections.OrderedDict()
    for s in sheets:
        base, ver = _split_name(s["file"])
        g = groups.setdefault(base, {})
        g[ver] = s["file"]
        if s.get("packet"):
            g["packet"] = s["packet"]
    blank, demo = [], []
    for g in groups.values():
        blank_pick = g.get("空") or g.get("单") or g.get("示范")
        demo_pick = g.get("示范") or g.get("空") or g.get("单")
        packet = g.get("packet", "both")
        if packet in ("both", "blank") and blank_pick:
            blank.append(blank_pick)
        if packet in ("both", "demo") and demo_pick:
            demo.append(demo_pick)
    return blank, demo


def write_bundle(out_path, pdf_paths):
    """把若干单张 PDF 顺次合并成一本；目标被锁时旁路到 .new.pdf。"""
    from pypdf import PdfWriter
    w = PdfWriter()
    for p in pdf_paths:
        w.append(str(p))
    try:
        with open(out_path, "wb") as fh:
            w.write(fh)
        return out_path.name
    except OSError:
        alt = out_path.with_suffix(".new.pdf")
        with open(alt, "wb") as fh:
            w.write(fh)
        sys.stderr.write(f"[warn] {out_path.name} 被占用，已改写 {alt.name}\n")
        return alt.name


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    manifest_path = pathlib.Path(sys.argv[1]).resolve()
    out_dir = pathlib.Path(sys.argv[2]).resolve()
    want_png = "--png" in sys.argv[3:]
    want_bundle = "--no-bundle" not in sys.argv[3:]
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sheets = manifest.get("sheets", [])
    logo = load_logo()
    rendered_pdf = {}            # file 名 → 实际写出的 PDF 路径（供合册）

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for s in sheets:
            key = s["template"]
            data = normalize_quotes(dict(s["data"]))  # 直角引号「」→ 弯引号“”
            data["logo"] = logo                      # 统一注入 logo
            html = template_text(key).replace(
                "/*__DATA__*/ null", json.dumps(data, ensure_ascii=False))
            html_path = out_dir / (s["file"] + ".html")
            html_path.write_text(html, encoding="utf-8")

            page = browser.new_page(
                viewport={"width": VIEW_W, "height": A4_H},
                device_scale_factor=2)
            page.goto("file:///" + str(html_path).replace("\\", "/"),
                      wait_until="networkidle")
            page.wait_for_selector("body[data-rendered='1']", timeout=15000)
            # 量 #page 的实际宽高决定纸张：竖版宽=794、横版模板自报更宽（如 timeline 1123）
            box = page.evaluate(
                "() => {const p=document.getElementById('page');"
                "return {w: Math.ceil(p.getBoundingClientRect().width),"
                " h: Math.ceil(p.scrollHeight)};}")
            if box["w"] <= A4_W + 1:                 # 竖版 A4
                pw, ph = A4_W, max(A4_H, box["h"] + 16)
            else:                                     # 横版（模板自带更宽 #page）
                pw, ph = box["w"], box["h"]
            written = safe_pdf(page, out_dir / (s["file"] + ".pdf"), pw, ph)
            rendered_pdf[s["file"]] = out_dir / written
            if want_png:
                page.screenshot(path=str(out_dir / (s["file"] + ".png")),
                                full_page=True)
            page.close()
            print("OK:", s["file"])
        browser.close()
    print(f"\n完成 {len(sheets)} 张 → {out_dir}")

    if want_bundle:
        try:
            import pypdf  # noqa: F401  仅探测可用性
        except ImportError:
            sys.stderr.write("[warn] 未装 pypdf，跳过合册（pip install pypdf）。\n")
        else:
            book = manifest.get("book", "阅读单")
            blank, demo = plan_bundles(sheets)
            for tag, files in (("空白版", blank), ("示范版", demo)):
                paths = [rendered_pdf[f] for f in files if f in rendered_pdf]
                if not paths:
                    continue
                name = write_bundle(
                    out_dir / f"{book}-阅读单-{tag}-全套.pdf", paths)
                print(f"合册 {name}：{len(paths)} 张")


if __name__ == "__main__":
    main()
