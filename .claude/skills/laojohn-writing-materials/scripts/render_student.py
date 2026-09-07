#!/usr/bin/env python
"""同步习作 · 学生用渲染器
data.json -> HTML（3 个 A4 sheet）-> 多页 A4 PDF

用法:
    PYTHONUTF8=1 python render_student.py <data.json> <输出目录> [--template <模板路径>]

产出（落在输出目录）:
    <基名>.html   可编辑源件（基名 = data 文件名去掉 "_data" 尾缀）
    <基名>.pdf    打印件（预期 4 页：构思表1 + 稿纸2（含备用续页）+ 范文1）

自检（_shared.render 内置溢出/页数核验，此处附加格子稿纸检查）:
    - 两页稿纸格子数均须为 15 的倍数且 >=5 行；续页不带起笔提示与符号表，行数应不少于第 1 页
"""
import argparse
from _shared import ASSETS, render

EXPECTED_PAGES = 4  # 构思表1 + 稿纸2（第2张为备用续页）+ 范文1


def grid_checks(page):
    def cells(sel):
        return page.evaluate(f"() => document.querySelectorAll('{sel} .grid .cell').length")

    p1 = cells(".sheet.page2")
    p2 = cells(".sheet.page2b")
    for name, n in (("稿纸", p1), ("续页", p2)):
        ok = n % 15 == 0 and n // 15 >= 5
        print(f"格子自检: {name} {n} 格({n // 15} 行) {'OK' if ok else '!! 异常'}")
    # 续页无起笔提示、无修改符号表，可用高度更大；若反而更少，说明 usedSels 漏列或版式塌了
    if p2 < p1:
        print(f"!! 格子自检: 续页 {p2} 格少于第1页 {p1} 格——检查 buildGridOn 的 usedSels")
    print(f"格子自检: 两页合计 {p1 + p2} 格")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="学生用 data.json 路径")
    ap.add_argument("out_dir", help="输出目录（写作配套输出\\<年级册>-第N单元-<题目>\\）")
    ap.add_argument("--template", default=None)
    args = ap.parse_args()
    template = args.template or ASSETS / "template_student.html"
    render(args.data, args.out_dir, template, EXPECTED_PAGES, page_checks=grid_checks)
