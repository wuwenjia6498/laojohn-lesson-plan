#!/usr/bin/env python
"""看图写话配套 · 兜底纸条（裁切版）渲染入口。
用法：PYTHONUTF8=1 python scripts/render_slips.py <data.json> <out_dir> [--template <path>]
只发给写不动的孩子的填空句式条，竖排 N 条铺满 A4，沿虚线裁开。"""
import sys
import pathlib
import argparse

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from _shared import render  # noqa: E402

DEFAULT_TEMPLATE = HERE.parent / "assets" / "template_slips.html"


def slip_checks(page):
    n = page.evaluate("() => document.querySelectorAll('.slip').length")
    if n < 1:
        print(f"!! 兜底纸条：纸条数 {n}，应至少 1 条")
    else:
        print(f"纸条核验：{n} 条 OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_dir")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    a = ap.parse_args()
    render(a.data, a.out_dir, a.template, expected_pages=1, page_checks=slip_checks)


if __name__ == "__main__":
    main()
