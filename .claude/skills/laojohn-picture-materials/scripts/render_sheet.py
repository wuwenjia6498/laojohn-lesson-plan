#!/usr/bin/env python
"""看图写话配套 · 看图写话稿纸渲染入口。
用法：PYTHONUTF8=1 python scripts/render_sheet.py <data.json> <out_dir> [--anchor <主图png>] [--template <path>]
本课图位框 + 写话格子稿纸（18 列动态行）+ 写话格式小提醒。
主图：优先 --anchor；否则取 data.json 的 sheet.anchor_img（相对路径按 CWD 解析）；缺则留占位框。"""
import sys
import json
import pathlib
import argparse

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from _shared import render  # noqa: E402

DEFAULT_TEMPLATE = HERE.parent / "assets" / "template_sheet.html"


def grid_checks(page):
    n = page.evaluate("() => document.querySelectorAll('#grid .cell').length")
    if n % 18 or n < 18 * 5:
        print(f"!! 稿纸格子数 {n} 异常（应为 18 的倍数且 ≥5 行）")
    else:
        print(f"格子核验：{n} 格（{n // 18} 行 × 18）OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_dir")
    ap.add_argument("--anchor", default=None,
                    help="稿纸该印的图 png 路径（应为本课练笔图 练-01.png；回落 主-01/旧稿 锚-01）；"
                         "覆盖 data.json 的 sheet.anchor_img")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    a = ap.parse_args()

    anchor = a.anchor
    if not anchor:
        d = json.loads(pathlib.Path(a.data).read_text(encoding="utf-8"))
        anchor = (d.get("sheet") or {}).get("anchor_img")
    extra = {"__ANCHOR_SRC__": anchor} if anchor else {"__ANCHOR_SRC__": ""}

    render(a.data, a.out_dir, a.template, expected_pages=1,
           page_checks=grid_checks, extra_images=extra)


if __name__ == "__main__":
    main()
