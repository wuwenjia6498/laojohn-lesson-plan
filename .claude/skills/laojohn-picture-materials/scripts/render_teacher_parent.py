#!/usr/bin/env python
"""看图写话配套 · 教师家长页渲染入口（2 页 A4：P1 教师速览 / P2 家长一页纸）。
用法：PYTHONUTF8=1 python scripts/render_teacher_parent.py <data.json> <out_dir> [--template <path>]"""
import sys
import pathlib
import argparse

HERE = pathlib.Path(__file__).parent
sys.path.insert(0, str(HERE))
from _shared import render  # noqa: E402

DEFAULT_TEMPLATE = HERE.parent / "assets" / "template_teacher_parent.html"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data")
    ap.add_argument("out_dir")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE))
    a = ap.parse_args()
    render(a.data, a.out_dir, a.template, expected_pages=2)


if __name__ == "__main__":
    main()
