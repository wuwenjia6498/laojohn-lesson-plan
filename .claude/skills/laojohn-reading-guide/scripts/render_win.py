#!/usr/bin/env python3
"""Windows 包装渲染器 —— 绕过 /opt/pw-browsers 路径问题"""
import os, sys, json, pathlib

# 设置 Windows 下 Playwright 浏览器路径
pw_path = str(pathlib.Path.home() / "AppData" / "Local" / "ms-playwright")
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = pw_path

HERE = pathlib.Path(__file__).parent
ASSETS = HERE.parent / "assets"

def render(data_path, out_base, template_path=None):
    if template_path is None:
        template_path = ASSETS / "template.html"

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()

    payload = json.dumps(data, ensure_ascii=False)
    html = tpl.replace("/*__DATA__*/ null", payload)

    html_out = out_base + ".html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)
    print("HTML:", html_out)

    from playwright.sync_api import sync_playwright
    pdf_out = out_base + ".pdf"
    file_url = "file:///" + html_out.replace("\\", "/")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        A4_W, A4_H = 794, 1123
        content_h = page.evaluate("() => document.getElementById('page').scrollHeight")
        page_h = max(A4_H, content_h) + 40  # 额外缓冲，防止内容被截断或意外分页
        page.pdf(
            path=pdf_out,
            width=f"{A4_W}px",
            height=f"{page_h}px",
            print_background=True,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        browser.close()

    print("PDF:", pdf_out)
    return pdf_out, html_out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_base")
    ap.add_argument("--template", default=None)
    args = ap.parse_args()
    render(args.data, args.out_base, args.template)
