#!/usr/bin/env python3
"""
laojohn-book-card 渲染器
用法:
    python3 render_card.py <data.json> <output_basename>
                           [--covers <封面图目录>]

输出:
    <basename>.jpg   —— 书目卡图片（900px 宽，高度随内容自适应，2× 高清）
    <basename>.html  —— 可编辑源文件（数据已内联，可独立打开）

封面匹配:
    按 data.json 的 title 去 covers_dir 找 <书名>.jpg（去书名号/空格容错）。
    匹配不到则用占位文字，并在 stderr 提示用户补图。
"""
import json
import os
import sys
import re
import base64
import argparse

HERE        = os.path.dirname(os.path.abspath(__file__))
ASSETS      = os.path.join(HERE, "..", "assets")
TEMPLATE    = os.path.join(ASSETS, "template.html")
# 脚本自身目录内的封面目录（兼容旧路径），通常被 --covers 覆盖
DEFAULT_COVERS = os.path.join(ASSETS, "covers")

# 不强制覆盖 PLAYWRIGHT_BROWSERS_PATH，让 playwright 使用系统默认安装路径


def norm(name):
    """书名归一化：去书名号、空格、标点，便于容错匹配。"""
    return re.sub(r"[《》\s「」·、,，。.\-_（）()]", "", name).lower()


def find_cover(title, covers_dir):
    """
    在 covers_dir 里按书名匹配封面图（jpg/png/webp）。
    返回 (路径, 是否匹配成功)。
    """
    if not os.path.isdir(covers_dir):
        return None, False
    target = norm(title)
    for fn in sorted(os.listdir(covers_dir)):
        if fn.startswith("_"):
            continue
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        if norm(stem) == target:
            return os.path.join(covers_dir, fn), True
    return None, False


def data_uri(path):
    """把图片转成 data URI，使 HTML 自包含（不依赖本地路径）。"""
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{b64}"


def render(data_path, out_base, covers_dir=None, logo_path=None):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "")

    # ── 封面 ──────────────────────────────────────────────────────────────────
    effective_covers = covers_dir or DEFAULT_COVERS
    cover_path, cover_ok = find_cover(title, effective_covers)
    if not cover_ok:
        sys.stderr.write(
            f"[WARN] Cover not found for '{title}' in {effective_covers}\n"
            f"       Add <{title}.jpg> to that folder and re-render.\n"
        )
    cover_data_uri = data_uri(cover_path) if cover_ok else ""

    # ── Logo ──────────────────────────────────────────────────────────────────
    # 优先用 --logo 传入的路径；未传则尝试从 JSON 所在目录向上推断品牌资产目录
    if not logo_path:
        json_dir = os.path.dirname(os.path.abspath(data_path))
        # 典型路径：<root>/书目卡输出/xxx.json → <root>/品牌资产/logo.png
        candidate = os.path.join(json_dir, "..", "品牌资产", "logo.png")
        logo_path = os.path.normpath(candidate)

    logo_data_uri = data_uri(logo_path)
    if not logo_data_uri:
        sys.stderr.write(
            f"[WARN] Logo not found at {logo_path}. Logo area will be hidden.\n"
            f"       Pass --logo <path> to specify the logo file.\n"
        )

    with open(TEMPLATE, "r", encoding="utf-8") as f:
        tpl = f.read()

    # 模板里有两处 /*__LOGO__*/（img src 和 JS 判断），需同时替换
    html = (tpl
            .replace("/*__DATA__*/ null",  json.dumps(data, ensure_ascii=False))
            .replace("/*__COVER__*/",      cover_data_uri)
            .replace("/*__LOGO__*/",       logo_data_uri)
    )

    html_out = out_base + ".html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)

    # ── Playwright 截图 ──────────────────────────────────────────────────────
    from playwright.sync_api import sync_playwright

    jpg_out  = out_base + ".jpg"
    file_url = "file://" + os.path.abspath(html_out)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"], channel="chromium")
        # 宽 900px，高度由内容撑开（full_page / element 截图）
        page = browser.new_page(
            viewport={"width": 900, "height": 800},
            device_scale_factor=2,
        )
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        page.wait_for_timeout(200)
        el = page.query_selector("#page")
        el.screenshot(path=jpg_out, type="jpeg", quality=93)
        browser.close()

    print(f"JPG : {jpg_out}")
    print(f"HTML: {html_out}")
    return jpg_out, html_out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(
        description="把 data.json 渲染成「本期深度阅读书目」书目卡 JPG + HTML"
    )
    ap.add_argument("data",     help="data.json 路径")
    ap.add_argument("out_base", help="输出文件基础名（不含扩展名）")
    ap.add_argument(
        "--covers",
        default=None,
        help="封面图目录（默认：assets/covers/）。\n"
             "项目级共用封面目录：<项目根目录>\\书籍封面",
    )
    ap.add_argument(
        "--logo",
        default=None,
        help="品牌 logo 图片路径（默认自动查找 <项目根目录>\\品牌资产\\logo.png）",
    )
    args = ap.parse_args()
    render(args.data, args.out_base, covers_dir=args.covers, logo_path=args.logo)
