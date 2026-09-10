#!/usr/bin/env python
"""读书会下游物料 · JPG 长图渲染引擎(单一源,禁复制逻辑)

使用者两家(CLAUDE.md §3 已登记):
    laojohn-book-card     —— 书目卡  (900px 宽,quality 93,注入 DATA/COVER/LOGO)
    laojohn-course-poster —— 招生海报(1242px 宽,quality 92,注入 DATA/HEADER/COVER/QR)
两家的 `render_*.py` 只负责解析各自的资产与注入 token,渲染骨架全在本文件。
改本文件等于同时改两条线,须两线一并回归。

输出模型:固定宽度 viewport + device_scale_factor=2,截 #page 元素(高度由内容撑开),
不用 full_page 以免 viewport 外留白。

两家的历史口径差异全部参数化(默认值＝海报口径),不要改成"统一"而改变既有产物:
    strip_parens   书名归一化时是否连圆括号一并去掉  书目卡 True / 海报 False
    fallback       封面匹配不到时的回退              书目卡 None(留空) / 海报占位图
"""
import base64
import json
import os
import re

# Playwright 浏览器路径(未设环境变量时回退到本机默认 ms-playwright;环境变量优先于此缺省值)
os.environ.setdefault(
    "PLAYWRIGHT_BROWSERS_PATH",
    os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"),
)

COVER_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def norm(name, strip_parens=False):
    """书名归一化:去书名号、空格、常见标点,便于容错匹配。

    strip_parens: 是否连圆括号一并去掉(书目卡口径;海报口径保留括号)。
    """
    chars = r"《》\s「」·、,，。.\-_"
    if strip_parens:
        chars += r"（）()"
    return re.sub("[" + chars + "]", "", name).lower()


def find_cover(title, covers_dir, fallback=None, strip_parens=False):
    """在 covers_dir 里按书名匹配封面图。返回 (路径, 是否匹配成功)。

    匹配不到时返回 (fallback, False)——书目卡传 None(封面区留空),海报传占位图路径。
    以 `_` 开头的文件(如 _placeholder.jpg)不参与匹配。
    """
    if not covers_dir or not os.path.isdir(covers_dir):
        return fallback, False
    target = norm(title, strip_parens)
    for fn in sorted(os.listdir(covers_dir)):
        if fn.startswith("_"):
            continue
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in COVER_EXTS:
            continue
        if norm(stem, strip_parens) == target:
            return os.path.join(covers_dir, fn), True
    return fallback, False


def data_uri(path):
    """把图片转 data URI,使 HTML 自包含(可独立打开,不依赖本地路径)。缺失返回空串。"""
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{b64}"


def shoot(template_path, out_base, data, tokens,
          width, quality, viewport_height, settle_ms):
    """注入 -> 写 HTML -> Playwright 截 #page -> 出 JPG。返回 (jpg_out, html_out)。

    tokens: {模板占位符: 已解析好的值},如 {"/*__COVER__*/": "data:image/jpeg;base64,…"}。
            `/*__DATA__*/ null` 的数据注入由本函数统一处理,不必放进 tokens。
            同一 token 在模板里出现多次会全部替换(书目卡的 LOGO 即有两处)。
    """
    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    html = tpl.replace("/*__DATA__*/ null", json.dumps(data, ensure_ascii=False))
    for token, value in tokens.items():
        html = html.replace(token, value)

    html_out = out_base + ".html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)

    from playwright.sync_api import sync_playwright

    jpg_out = out_base + ".jpg"
    file_url = "file://" + os.path.abspath(html_out)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"], channel="chromium")
        page = browser.new_page(
            viewport={"width": width, "height": viewport_height},
            device_scale_factor=2,
        )
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        page.wait_for_timeout(settle_ms)
        el = page.query_selector("#page")
        el.screenshot(path=jpg_out, type="jpeg", quality=quality)
        browser.close()

    return jpg_out, html_out
