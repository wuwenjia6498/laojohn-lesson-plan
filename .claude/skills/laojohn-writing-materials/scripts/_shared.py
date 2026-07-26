#!/usr/bin/env python
"""同步习作配套物料 · 渲染共享件（学生/教师/家长各入口共用，勿在入口脚本里复制这些逻辑）"""
import os
import json
import base64
import pathlib

# Windows 下 Playwright 浏览器路径（勿删：默认会去找不存在的 /opt/pw-browsers）
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
    pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"
)

HERE = pathlib.Path(__file__).parent
ASSETS = HERE.parent / "assets"
PROJECT_ROOT = HERE.parents[3]  # scripts -> skill -> skills -> .claude -> 项目根
LOGO_PATH = PROJECT_ROOT / "品牌资产" / "logo.png"  # 单一源，禁在 skill 内存副本

A4_H_PX = 1123  # 297mm @96dpi，溢出判定基准


def out_base(data_path):
    """data 文件名去掉 _data 尾缀 = 产物基名"""
    base = pathlib.Path(data_path).stem
    return base[: -len("_data")] if base.endswith("_data") else base


def _img_data_uri(path):
    """本地图片转 data: URI（按扩展名定 MIME），供 base64 内联；失败返回空串"""
    p = pathlib.Path(path)
    if not p.exists():
        return ""
    ext = p.suffix.lower().lstrip(".")
    mime = "jpeg" if ext in ("jpg", "jpeg") else ext or "png"
    return f"data:image/{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def inject(template_path, data_path, extra_images=None):
    """data.json + 品牌 logo 注入模板，返回完整 HTML 字符串。
    extra_images: 可选 {占位符token: 图片路径}——logo 之外再内联命名图（如稿纸主图）；
    路径缺失则该 token 置空串（不伪造），由模板 onerror 兜底。"""
    data = json.loads(pathlib.Path(data_path).read_text(encoding="utf-8"))
    tpl = pathlib.Path(template_path).read_text(encoding="utf-8")
    html = tpl.replace("/*__DATA__*/ null", json.dumps(data, ensure_ascii=False))
    # 品牌 logo：读根目录单一源转 base64 内联，HTML 保持自包含
    if LOGO_PATH.exists():
        uri = "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()
        html = html.replace("__LOGO_SRC__", uri)
    else:
        print(f"!! 未找到品牌 logo: {LOGO_PATH}，页眉将留空（不伪造）")
        html = html.replace("__LOGO_SRC__", "")
    # 额外命名图（可选，向后兼容）：如稿纸主图 __ANCHOR_SRC__
    for token, img_path in (extra_images or {}).items():
        uri = _img_data_uri(img_path)
        if not uri:
            print(f"!! 未找到图 {img_path}，占位符 {token} 留空（模板 onerror 兜底）")
        html = html.replace(token, uri)
    return html


def safe_pdf(page, pdf_out):
    """写多页 A4 PDF；目标被预览器锁住时旁路写 .new.pdf，不中断。返回实际写出的路径。"""
    kw = dict(width="210mm", height="297mm", print_background=True,
              margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
    try:
        page.pdf(path=str(pdf_out), **kw)
        return pdf_out
    except Exception:
        alt = pdf_out.with_suffix(".new.pdf")
        page.pdf(path=str(alt), **kw)
        print(f"!! {pdf_out.name} 被占用（预览器未关？），已旁路写 {alt.name}")
        return alt


def check_sheet_overflow(page):
    """屏幕布局下各 sheet 是否已超一页高（超了 PDF 就会裂页）"""
    sheets = page.evaluate(
        "() => [...document.querySelectorAll('.sheet')].map((s,i) =>"
        " ({i: i+1, h: Math.round(s.offsetHeight)}))"
    )
    for s in sheets:
        if s["h"] > A4_H_PX + 12:  # 12px 容差
            print(f"!! 第 {s['i']} 个 sheet 高 {s['h']}px 超一页({A4_H_PX}px)，PDF 可能多页")


def check_pages(pdf_out, expected):
    """pypdf 页数核验"""
    try:
        from pypdf import PdfReader
        n = len(PdfReader(str(pdf_out)).pages)
        if n == expected:
            print(f"页数核验: {n} 页 OK")
        else:
            print(f"!! 页数核验: {n} 页，预期 {expected} 页——某页内容溢出，"
                  "请压缩数据层文本或模板间距后重渲")
    except ImportError:
        print("(未装 pypdf，跳过页数核验；pip install pypdf)")


def render(data_path, out_dir, template_path, expected_pages, page_checks=None, extra_images=None):
    """通用渲染流程：注入 -> 写 HTML -> Playwright 渲 PDF -> 自检。
    page_checks: 可选回调 fn(page)，在出 PDF 前跑物料特有的自检（如格子数）。
    extra_images: 可选 {token: 图片路径}，透传给 inject（如稿纸主图内联）。"""
    data_path = pathlib.Path(data_path)
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    html = inject(template_path, data_path, extra_images=extra_images)
    base = out_base(data_path)
    html_out = out_dir / f"{base}.html"
    html_out.write_text(html, encoding="utf-8")
    print("HTML:", html_out)

    from playwright.sync_api import sync_playwright

    pdf_out = out_dir / f"{base}.pdf"
    file_url = "file:///" + str(html_out).replace("\\", "/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        if page_checks:
            page_checks(page)
        check_sheet_overflow(page)
        pdf_out = safe_pdf(page, pdf_out)
        browser.close()

    print("PDF:", pdf_out)
    check_pages(pdf_out, expected_pages)
    return pdf_out, html_out
