#!/usr/bin/env python
"""laojohn-teaching-mindmap 渲染器 —— 薄壳,零逻辑。

实现＝`laojohn-reading-guide/scripts/_a4_render.py`(三物料共享单一源,见 CLAUDE.md §3,禁复制逻辑)。
用 importlib 按显式路径以 `_a4_render_real` 之名载入,避免与其它同名模块撞车。

用法:
    python render_pdf.py <data.json> <output_basename> [--template path]

输出(同时产出,满足"PDF + 可编辑源文件"):
    <basename>.pdf     —— 最终交付,竖向 A4(内容超高时整页增高不分页),中文字体已嵌入
    <basename>.html    —— 可编辑源文件(数据已内联,改完可直接重渲染)
"""
import importlib.util
import os
import pathlib

# scripts -> laojohn-teaching-mindmap -> skills;到同级 reading-guide/scripts 取单一源
_REAL_PATH = (
    pathlib.Path(__file__).parents[2]
    / "laojohn-reading-guide" / "scripts" / "_a4_render.py"
)
_spec = importlib.util.spec_from_file_location("_a4_render_real", _REAL_PATH)
_real = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_real)

# 单一源整体转出(勿在此处写任何渲染逻辑)
render = _real.render
build_html = _real.build_html
main = _real.main

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")

if __name__ == "__main__":
    # 放射状导图:内容超一页时需重设 min-height 保持导图区垂直居中
    main(DEFAULT_TEMPLATE, recenter_on_overflow=True)
