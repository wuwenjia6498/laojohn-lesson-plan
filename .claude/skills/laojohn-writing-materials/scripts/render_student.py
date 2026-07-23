#!/usr/bin/env python
"""同步习作 · 学生合订渲染器
data.json -> 合订 HTML（4 个 A4 sheet）-> 多页 A4 PDF

用法:
    PYTHONUTF8=1 python render_student.py <data.json> <输出目录> [--template <模板路径>]

产出（落在输出目录）:
    <基名>.html   可编辑源件（基名 = data 文件名去掉 "_data" 尾缀）
    <基名>.pdf    合订打印件（预期 4 页：学习单2 + 范文1 + 练笔1）

自检（_shared.render 内置溢出/页数核验，此处附加格子稿纸检查）:
    - 第2页格子数须为 18 的倍数且 >=5 行；练笔小稿纸须为 18×6
"""
import argparse
from _shared import ASSETS, render

EXPECTED_PAGES = 4  # 学习单2 + 范文1 + 课后练笔1


def grid_checks(page):
    ws_cells = page.evaluate("() => document.querySelectorAll('.sheet.page2 .grid .cell').length")
    hw_cells = page.evaluate("() => document.querySelectorAll('#hw-grid .cell').length")
    ok_ws = ws_cells % 18 == 0 and ws_cells // 18 >= 5
    ok_hw = hw_cells == 18 * 6
    print(f"格子自检: 稿纸 {ws_cells} 格({ws_cells // 18} 行) {'OK' if ok_ws else '!! 异常'};"
          f" 练笔 {hw_cells} 格 {'OK' if ok_hw else '!! 异常(应 108)'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data", help="学生合订 data.json 路径")
    ap.add_argument("out_dir", help="输出目录（写作配套输出\\<年级册>-<题目>\\）")
    ap.add_argument("--template", default=None)
    args = ap.parse_args()
    template = args.template or ASSETS / "template_student.html"
    render(args.data, args.out_dir, template, EXPECTED_PAGES, page_checks=grid_checks)
