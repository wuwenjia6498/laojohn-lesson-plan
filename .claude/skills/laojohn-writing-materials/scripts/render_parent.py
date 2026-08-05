#!/usr/bin/env python
"""同步习作 · 家长合订渲染器
data.json -> 家长一页纸 HTML（1 个 A4 sheet）-> A4 PDF

用法:
    PYTHONUTF8=1 python render_parent.py <data.json> <输出目录> [--template <模板路径>]

产出（落在输出目录）:
    <基名>.html   可编辑源件（基名 = data 文件名去掉 "_data" 尾缀）
    <基名>.pdf    打印件（预期 1 页：家长一页纸）

家长侧只出「家长一页纸」；习作成长反馈页已于 2026-08-03 撤销，勿再加回。
自检由 _shared.render 内置（sheet 溢出 + pypdf 页数核验）。
"""
import argparse
from _shared import ASSETS, render

EXPECTED_PAGES = 1  # 家长一页纸

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="家长合订 data.json 路径")
    ap.add_argument("out_dir", help="输出目录（写作配套输出\\<年级册>-第N单元-<题目>\\）")
    ap.add_argument("--template", default=None)
    args = ap.parse_args()
    template = args.template or ASSETS / "template_parent.html"
    render(args.data, args.out_dir, template, EXPECTED_PAGES)
