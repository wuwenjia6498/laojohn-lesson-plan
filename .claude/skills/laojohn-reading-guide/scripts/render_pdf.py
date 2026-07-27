#!/usr/bin/env python3
"""
laojohn-reading-guide 渲染器
用法:
    python3 render_pdf.py <data.json> <output_basename> [--template path]

输入:
    data.json          —— 萃取得到的阅读指南结构化数据
    output_basename    —— 输出文件名(不含扩展名),会生成 .pdf 与 .html

输出(同时产出,满足"PDF + 可编辑源文件"):
    <basename>.pdf     —— 最终交付,竖向 A4,中文字体已嵌入
    <basename>.html    —— 可编辑源文件(数据已内联,改完可直接重渲染)
"""
import json
import os
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")

# Playwright 浏览器路径（未设环境变量时回退到本机默认 ms-playwright）
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"),
)


def build_html(data, template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    payload = json.dumps(data, ensure_ascii=False)
    # 把 /*__DATA__*/ null 替换成真实数据,得到自包含、可独立打开的 HTML
    return tpl.replace("/*__DATA__*/ null", payload)


def render(data_path, out_base, template_path):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    html = build_html(data, template_path)
    html_out = out_base + ".html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)

    from playwright.sync_api import sync_playwright
    pdf_out = out_base + ".pdf"
    file_url = "file://" + os.path.abspath(html_out)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        # 等版式渲染完成(脚本填完内容会打上 data-rendered=1)
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        # 竖向 A4 基准;内容超高时页面自适应增高,避免截断
        A4_W, A4_H = 794, 1123
        content_h = page.evaluate(
            "() => document.getElementById('page').scrollHeight"
        )
        page_h = max(A4_H, content_h)
        page.pdf(
            path=pdf_out,
            width=f"{A4_W}px",
            height=f"{page_h}px",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    print("PDF :", pdf_out)
    print("HTML:", html_out)
    return pdf_out, html_out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_base")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    args = ap.parse_args()
    render(args.data, args.out_base, args.template)
