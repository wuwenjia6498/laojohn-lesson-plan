#!/usr/bin/env python
"""看图写话配套 · 支架小卡（裁切版）渲染入口。
用法：PYTHONUTF8=1 python scripts/render_cards.py <data.json> <out_dir> [--template <path>]
每人一张随身支架卡，2 列 × N 行铺满 A4，沿虚线裁开。卡数须为偶数（成对裁切）。"""
import sys
import pathlib
import argparse

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from _shared import render  # noqa: E402

DEFAULT_TEMPLATE = HERE.parent / "assets" / "template_cards.html"


def card_checks(page):
    """卡片总数须为偶数（2 列成对裁切）且 ≥ 1；卡内内容不得溢出虚线裁切框"""
    n = page.evaluate("() => document.querySelectorAll('.grid .card').length")
    if n < 1:
        print(f"!! 支架小卡：卡片数 {n}，应至少 1 张")
    elif n % 2:
        print(f"!! 支架小卡：卡片数 {n} 为奇数，2 列裁切建议用偶数张")
    else:
        print(f"卡片核验：{n} 张 OK")
    # 卡是固定高度的裁切框：内容一超高就会压出虚线（曾在四问卡实发），机检兜住
    overflow = page.evaluate(
        "() => [...document.querySelectorAll('.grid .card')]"
        ".filter(c => c.scrollHeight > c.clientHeight + 1).length"
    )
    if overflow:
        print(f"!! 支架小卡：{overflow} 张卡内容超出虚线框（会印到裁切线外），"
              "请压缩卡内文本或模板间距后重渲")
    else:
        print("卡内溢出核验：0 张超框 OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_dir")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    a = ap.parse_args()
    # 支架小卡默认 1 页（8 张）；多卡型时详案侧自行加页，页数核验放宽为 >=1
    render(a.data, a.out_dir, a.template, expected_pages=1, page_checks=card_checks)


if __name__ == "__main__":
    main()
