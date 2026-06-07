#!/usr/bin/env python3
"""
laojohn-lesson-mindmap 渲染器
用法:
    python3 render_pdf.py <data.json> <output_basename> [--template path]

输入:
    data.json          —— 萃取得到的思维导图结构化数据
    output_basename    —— 输出文件名(不含扩展名),会生成 .pdf 与 .html

输出(同时产出,满足"PDF + 可编辑源文件"):
    <basename>.pdf     —— 最终交付,竖向 A4,中文字体已嵌入
    <basename>.html    —— 可编辑源文件(数据已内联,改完可直接重渲染)
"""
import json
import sys
import os
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")

# Chromium 浏览器目录自动适配:
# - 云端环境若把浏览器装在 /opt/pw-browsers,则指向它;
# - 本地环境(未设置且该目录不存在)则保持不动,
#   交给 Playwright 使用其默认安装路径(~/.cache/ms-playwright 等)。
# 这样同一份脚本在本地与云端都能直接运行,无需手动改动。
if "PLAYWRIGHT_BROWSERS_PATH" not in os.environ and os.path.isdir("/opt/pw-browsers"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"


def build_html(data, template_path):
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    payload = json.dumps(data, ensure_ascii=False)
    # 把 /*__DATA__*/ null 替换成真实数据,得到自包含、可独立打开的 HTML
    html = tpl.replace("/*__DATA__*/ null", payload)
    return html


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
        try:
            browser = p.chromium.launch(args=["--no-sandbox"])
        except Exception as e:
            raise RuntimeError(
                "无法启动 Chromium。若是首次在本机运行,请先安装浏览器:\n"
                "    pip install playwright\n"
                "    python3 -m playwright install chromium\n"
                f"(原始错误:{e})"
            )
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        # 等连线绘制完成(模板画完弧线会打上 data-rendered=1)
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        # 竖向 A4 基准高度;内容超高时才扩展,否则固定整页以实现垂直居中
        A4_W, A4_H = 794, 1123
        content_h = page.evaluate(
            "() => document.getElementById('page').scrollHeight"
        )
        page_h = max(A4_H, content_h)
        if page_h > A4_H:
            # 内容超过一页:重设 min-height 让导图区在更高的页面里仍居中
            page.evaluate(
                "(h) => { document.getElementById('page').style.minHeight = h + 'px'; }",
                page_h,
            )
            page.wait_for_timeout(150)
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
