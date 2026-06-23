#!/usr/bin/env python3
"""
laojohn-course-poster 渲染器
用法:
    python3 render_poster.py <data.json> <output_basename>

输出(满足"JPG 长图 + 可编辑 HTML"):
    <basename>.jpg     —— 朋友圈/社群传播用长图(待人工补全占位框后对外)
    <basename>.html    —— 可编辑源文件(数据已内联,改字/补占位/删获奖块后可重渲染)

封面匹配:按 data.json 的 title 去 assets/covers/ 找 <书名>.jpg(去书名号/空格容错),
匹配不到则用 assets/covers/_placeholder.jpg,并在 stderr 明确提示用户补图。
"""
import json
import os
import sys
import re
import base64
import argparse

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
DEFAULT_TEMPLATE = os.path.join(ASSETS, "template.html")
# 默认封面目录(兼容旧行为)；可通过 --covers 指定项目级共用封面目录
DEFAULT_COVERS_DIR = os.path.join(ASSETS, "covers")
PLACEHOLDER_COVER = os.path.join(DEFAULT_COVERS_DIR, "_placeholder.jpg")
HEADER = os.path.join(ASSETS, "header.jpg")    # 固定头部图(整宽页眉)
LOGO = os.path.join(ASSETS, "logo.png")        # 可选,目前用文字 logo
DEFAULT_QR = os.path.join(ASSETS, "qrcode.png")  # 默认二维码;可通过 --qr 指定项目级共用资产

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "/opt/pw-browsers")


def norm(name):
    """书名归一化:去书名号、空格、标点,便于容错匹配。"""
    return re.sub(r"[《》\s「」·、,，。.\-_]", "", name).lower()


def find_cover(title, covers_dir=None):
    """按书名在 covers_dir 里找封面。返回(路径, 是否匹配成功)。
    covers_dir 优先使用 --covers 参数传入的路径，兼容项目级共用封面目录。
    """
    if covers_dir is None:
        covers_dir = DEFAULT_COVERS_DIR
    if not os.path.isdir(covers_dir):
        return PLACEHOLDER_COVER, False
    target = norm(title)
    for fn in os.listdir(covers_dir):
        if fn.startswith("_"):
            continue
        stem, ext = os.path.splitext(fn)
        if ext.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        if norm(stem) == target:
            return os.path.join(covers_dir, fn), True
    return PLACEHOLDER_COVER, False


def data_uri(path):
    """把图片转 data URI,使 HTML 自包含(可独立打开,不依赖本地路径)。"""
    if not path or not os.path.exists(path):
        return ""
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:image/{mime};base64,{b64}"


def make_placeholder_qr():
    """二维码资产缺失时,生成一张占位二维码图,提示替换。"""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (160, 160), "#ffffff")
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 159, 159], outline="#cccccc", width=2)
    try:
        f = ImageFont.truetype("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", 18)
    except Exception:
        f = ImageFont.load_default()
    d.text((34, 58), "二维码", font=f, fill="#999999")
    d.text((20, 86), "待替换", font=f, fill="#999999")
    tmp = "/tmp/_qr_placeholder.png"
    img.save(tmp)
    return tmp


def render(data_path, out_base, template_path, covers_dir=None, qr_path_override=None):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "")
    cover_path, cover_ok = find_cover(title, covers_dir)
    if not cover_ok:
        hint_dir = covers_dir or DEFAULT_COVERS_DIR
        sys.stderr.write(
            f"⚠ 封面未匹配:封面目录里没有找到《{title}》对应的封面图,已用占位封面。\n"
            f"  请把书封图放入 {hint_dir}/,命名为「{title}.jpg」后重渲染。\n"
        )

    # 二维码：优先用 --qr 指定的路径，否则用 assets/ 内置默认路径
    qr_resolved = qr_path_override or DEFAULT_QR
    qr_path = qr_resolved if os.path.exists(qr_resolved) else make_placeholder_qr()
    if not os.path.exists(qr_resolved):
        sys.stderr.write(f"⚠ 二维码资产缺失({qr_resolved}),已用占位二维码,请补充正式二维码。\n")

    with open(template_path, "r", encoding="utf-8") as f:
        tpl = f.read()
    html = (tpl
            .replace("/*__DATA__*/ null", json.dumps(data, ensure_ascii=False))
            .replace("/*__HEADER__*/", data_uri(HEADER))
            .replace("/*__COVER__*/", data_uri(cover_path))
            .replace("/*__QR__*/", data_uri(qr_path))
    )

    html_out = out_base + ".html"
    with open(html_out, "w", encoding="utf-8") as f:
        f.write(html)

    from playwright.sync_api import sync_playwright
    jpg_out = out_base + ".jpg"
    file_url = "file://" + os.path.abspath(html_out)

    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--no-sandbox"], channel="chromium")
        # 固定宽 1242,高度由内容撑开(full_page 截图)
        page = browser.new_page(viewport={"width": 1242, "height": 1000},
                                device_scale_factor=2)
        page.goto(file_url, wait_until="networkidle")
        page.wait_for_selector("body[data-rendered='1']", timeout=15000)
        page.wait_for_timeout(150)
        # 截 #page 元素的完整范围,避免 viewport 外留白
        el = page.query_selector("#page")
        el.screenshot(path=jpg_out, type="jpeg", quality=92)
        browser.close()

    print("JPG :", jpg_out)
    print("HTML:", html_out)
    return jpg_out, html_out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_base")
    ap.add_argument("--template", default=DEFAULT_TEMPLATE)
    ap.add_argument(
        "--covers",
        default=None,
        help="封面图目录路径(默认: assets/covers/)。项目级共用封面目录传入 <项目根目录>\\书籍封面",
    )
    ap.add_argument(
        "--qr",
        default=None,
        help="二维码图片路径(默认: assets/qrcode.png)。项目级共用二维码传入 <项目根目录>\\品牌资产\\qrcode.png",
    )
    args = ap.parse_args()
    render(args.data, args.out_base, args.template, covers_dir=args.covers, qr_path_override=args.qr)
