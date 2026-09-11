#!/usr/bin/env python
"""
laojohn-book-card 渲染器 —— 只解析本物料的资产,渲染骨架在同目录 `_jpg_render.py`
(书目卡/海报两家共享单一源,见 CLAUDE.md §3,禁在此复制渲染逻辑)。

用法:
    python render_card.py <data.json> <output_basename>
                          [--covers <封面图目录>] [--logo <logo 路径>]

输出:
    <basename>.jpg   —— 书目卡图片（900px 宽，高度随内容自适应，2× 高清）
    <basename>.html  —— 可编辑源文件（数据已内联，可独立打开）

封面匹配:
    按 data.json 的 title 去 covers_dir 找 <书名>.jpg（去书名号/空格/括号容错）。
    匹配不到则封面区留空，并在 stderr 提示用户补图。
"""
import argparse
import json
import os
import sys

from _jpg_render import data_uri, find_cover, shoot

HERE        = os.path.dirname(os.path.abspath(__file__))
ASSETS      = os.path.join(HERE, "..", "assets")
TEMPLATE    = os.path.join(ASSETS, "template.html")
# 脚本自身目录内的封面目录（兼容旧路径），通常被 --covers 覆盖
DEFAULT_COVERS = os.path.join(ASSETS, "covers")

# 书目卡口径：900px 宽、quality 93、书名归一化连圆括号一并去掉
WIDTH, QUALITY, VIEWPORT_H, SETTLE_MS = 900, 93, 800, 200


def find_logo(data_path):
    """未传 --logo 时，从 JSON 所在目录逐级向上找品牌资产目录。

    典型路径：<root>/读书会配套输出/<书名>/xxx.json → <root>/品牌资产/logo.png，
    层级不定故向上搜。找不到时返回兜底值用于报错提示。
    """
    cur = os.path.dirname(os.path.abspath(data_path))
    fallback = os.path.join(cur, "品牌资产", "logo.png")
    for _ in range(6):
        candidate = os.path.join(cur, "品牌资产", "logo.png")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return fallback


def render(data_path, out_base, covers_dir=None, logo_path=None):
    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    title = data.get("title", "")

    # ── 封面 ──────────────────────────────────────────────────────────────────
    effective_covers = covers_dir or DEFAULT_COVERS
    cover_path, cover_ok = find_cover(
        title, effective_covers, fallback=None, strip_parens=True
    )
    if not cover_ok:
        sys.stderr.write(
            f"[WARN] Cover not found for '{title}' in {effective_covers}\n"
            f"       Add <{title}.jpg> to that folder and re-render.\n"
        )
    cover_data_uri = data_uri(cover_path) if cover_ok else ""

    # ── Logo ──────────────────────────────────────────────────────────────────
    logo_path = logo_path or find_logo(data_path)
    logo_data_uri = data_uri(logo_path)
    if not logo_data_uri:
        sys.stderr.write(
            f"[WARN] Logo not found at {logo_path}. Logo area will be hidden.\n"
            f"       Pass --logo <path> to specify the logo file.\n"
        )

    # 模板里有两处 /*__LOGO__*/（img src 和 JS 判断），shoot 会全部替换
    jpg_out, html_out = shoot(
        TEMPLATE, out_base, data,
        {"/*__COVER__*/": cover_data_uri, "/*__LOGO__*/": logo_data_uri},
        width=WIDTH, quality=QUALITY,
        viewport_height=VIEWPORT_H, settle_ms=SETTLE_MS,
    )

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
             "项目级共用封面目录：<项目根目录>\\读书会书籍封面",
    )
    ap.add_argument(
        "--logo",
        default=None,
        help="品牌 logo 图片路径（默认自动查找 <项目根目录>\\品牌资产\\logo.png）",
    )
    args = ap.parse_args()
    render(args.data, args.out_base, covers_dir=args.covers, logo_path=args.logo)
