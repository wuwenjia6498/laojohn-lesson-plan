#!/usr/bin/env python
"""读书会下游物料 · A4 单页动态高 PDF 渲染引擎(单一源,禁复制逻辑)

使用者三家(CLAUDE.md §3 已登记):
    laojohn-reading-guide    —— 本 skill,阅读指南(文档流版式)
    laojohn-lesson-mindmap   —— 抢先看导图(居中放射,传 recenter_on_overflow=True)
    laojohn-teaching-mindmap —— 教学导图(居中放射,传 recenter_on_overflow=True)
三者的 `render_pdf.py` 均为本引擎的薄壳,改本文件等于同时改三条线,须三线一并回归。

输出模型:宽固定 794px(竖向 A4 @96dpi),高 = max(1123, #page.scrollHeight)——
内容不超一页按整页出,超页则整页增高而不分页,避免跨页截断。
"""
import json
import os
import argparse

# Playwright 浏览器路径(未设环境变量时回退到本机默认 ms-playwright;环境变量优先于此缺省值)
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"),
)

A4_W, A4_H = 794, 1123


def build_html(data, template_path):
    """把 /*__DATA__*/ null 替换成真实数据,得到自包含、可独立打开的 HTML。"""
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    payload = json.dumps(data, ensure_ascii=False)
    return tpl.replace("/*__DATA__*/ null", payload)


def render(data_path, out_base, template_path, recenter_on_overflow=False):
    """渲染 PDF + 可编辑 HTML 两件套。

    recenter_on_overflow: 内容超一页时是否重设 #page 的 min-height 以保持整体垂直居中。
        两种导图(lesson-mindmap / teaching-mindmap)是居中放射版式,均需 True;
        阅读指南是文档流版式、原本就无这段逻辑,保持 False(打开会把版式推开)。
        默认 False——新接入方除非确认版式需要,不要打开。
    """
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
                "    python -m playwright install chromium\n"
                f"(原始错误:{e})"
            )
        page = browser.new_page()
        page.goto(file_url, wait_until="networkidle")
        # 等版式/连线绘制完成(模板画完会给 body 打上 data-rendered=1)
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        content_h = page.evaluate("() => document.getElementById('page').scrollHeight")
        page_h = max(A4_H, content_h)
        if recenter_on_overflow and page_h > A4_H:
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


def main(default_template, recenter_on_overflow=False):
    """三家薄壳共用的命令行入口。"""
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_base")
    ap.add_argument("--template", default=default_template)
    args = ap.parse_args()
    render(args.data, args.out_base, args.template,
           recenter_on_overflow=recenter_on_overflow)
