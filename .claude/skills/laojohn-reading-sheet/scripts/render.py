# -*- coding: utf-8 -*-
"""老约翰 · 阅读单渲染引擎（通用，加模板不用改这里）。

输入：一份 manifest.json，描述某本书要出的所有阅读单。
输出：每张阅读单一个 .pdf + .html（HTML 自包含，可独立打开/再编辑）。

用法（Windows，先确认盘符）：
    set PYTHONUTF8=1
    set PLAYWRIGHT_BROWSERS_PATH=C:/Users/<你>/AppData/Local/ms-playwright
    python render.py <manifest.json> <输出目录> [--png]

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


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    manifest_path = pathlib.Path(sys.argv[1]).resolve()
    out_dir = pathlib.Path(sys.argv[2]).resolve()
    want_png = "--png" in sys.argv[3:]
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sheets = manifest.get("sheets", [])
    logo = load_logo()

    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for s in sheets:
            key = s["template"]
            data = dict(s["data"])
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
            safe_pdf(page, out_dir / (s["file"] + ".pdf"), pw, ph)
            if want_png:
                page.screenshot(path=str(out_dir / (s["file"] + ".png")),
                                full_page=True)
            page.close()
            print("OK:", s["file"])
        browser.close()
    print(f"\n完成 {len(sheets)} 张 → {out_dir}")


if __name__ == "__main__":
    main()
