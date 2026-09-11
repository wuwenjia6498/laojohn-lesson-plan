#!/usr/bin/env python
"""
laojohn-course-poster 渲染器 —— 只解析本物料的资产,渲染骨架＝单一源
`laojohn-book-card/scripts/_jpg_render.py`(书目卡/海报两家共享,见 CLAUDE.md §3,禁复制逻辑)。

用法:
    python render_poster.py <data.json> <output_basename>
                            [--template path] [--covers 目录] [--qr 路径]

输出(满足"JPG 长图 + 可编辑 HTML"):
    <basename>.jpg     —— 朋友圈/社群传播用长图(待人工补全占位框后对外)
    <basename>.html    —— 可编辑源文件(数据已内联,改字/补占位/删获奖块后可重渲染)

封面匹配:按 data.json 的 title 去 --covers 目录找 <书名>.jpg(去书名号/空格容错),
匹配不到则用 assets/covers/_placeholder.jpg,并在 stderr 明确提示用户补图。
"""
import argparse
import importlib.util
import json
import os
import pathlib
import sys

# 渲染骨架＝单一源(scripts -> laojohn-course-poster -> skills)
_REAL = (
    pathlib.Path(__file__).parents[2]
    / "laojohn-book-card" / "scripts" / "_jpg_render.py"
)
_spec = importlib.util.spec_from_file_location("_jpg_render_real", _REAL)
_jr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_jr)

data_uri = _jr.data_uri
find_cover = _jr.find_cover
shoot = _jr.shoot

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "..", "assets")
DEFAULT_TEMPLATE = os.path.join(ASSETS, "template.html")
# 默认封面目录(兼容旧行为)；可通过 --covers 指定项目级共用封面目录
DEFAULT_COVERS_DIR = os.path.join(ASSETS, "covers")
PLACEHOLDER_COVER = os.path.join(DEFAULT_COVERS_DIR, "_placeholder.jpg")
HEADER = os.path.join(ASSETS, "header.jpg")    # 固定头部图(整宽页眉)
DEFAULT_QR = os.path.join(ASSETS, "qrcode.png")  # 默认二维码;可通过 --qr 指定项目级共用资产

# 海报口径：1242px 宽、quality 92、书名归一化保留圆括号
WIDTH, QUALITY, VIEWPORT_H, SETTLE_MS = 1242, 92, 1000, 150


def make_placeholder_qr():
    """二维码资产缺失时,生成一张占位二维码图,提示替换。"""
    import tempfile

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
    # 写系统临时目录（勿硬编码 /tmp：Windows 上不存在，会直接抛错）
    tmp = os.path.join(tempfile.gettempdir(), "_qr_placeholder.png")
    img.save(tmp)
    return tmp


def render(data_path, out_base, template_path, covers_dir=None, qr_path_override=None):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "")
    cover_path, cover_ok = find_cover(
        title, covers_dir or DEFAULT_COVERS_DIR,
        fallback=PLACEHOLDER_COVER, strip_parens=False,
    )
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

    jpg_out, html_out = shoot(
        template_path, out_base, data,
        {
            "/*__HEADER__*/": data_uri(HEADER),
            "/*__COVER__*/": data_uri(cover_path),
            "/*__QR__*/": data_uri(qr_path),
        },
        width=WIDTH, quality=QUALITY,
        viewport_height=VIEWPORT_H, settle_ms=SETTLE_MS,
    )

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
        help="封面图目录路径(默认: assets/covers/)。项目级共用封面目录传入 <项目根目录>\\读书会书籍封面",
    )
    ap.add_argument(
        "--qr",
        default=None,
        help="二维码图片路径(默认: assets/qrcode.png)。项目级共用二维码传入 <项目根目录>\\品牌资产\\qrcode.png",
    )
    args = ap.parse_args()
    render(args.data, args.out_base, args.template, covers_dir=args.covers, qr_path_override=args.qr)
