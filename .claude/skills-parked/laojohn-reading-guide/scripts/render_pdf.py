#!/usr/bin/env python
"""laojohn-reading-guide 渲染器 —— 薄壳,零逻辑。

实现在同目录 `_a4_render.py`(三物料共享单一源,见 CLAUDE.md §3)。

用法:
    python render_pdf.py <data.json> <output_basename> [--template path]

输出(同时产出,满足"PDF + 可编辑源文件"):
    <basename>.pdf     —— 最终交付,竖向 A4(内容超高时整页增高不分页),中文字体已嵌入
    <basename>.html    —— 可编辑源文件(数据已内联,改完可直接重渲染)
"""
import os

from _a4_render import build_html, main, render  # noqa: F401  (转出供外部 import)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TEMPLATE = os.path.join(HERE, "..", "assets", "template.html")

if __name__ == "__main__":
    # 阅读指南是文档流版式,不做超页居中重设(recenter_on_overflow 保持默认 False)
    main(DEFAULT_TEMPLATE)
