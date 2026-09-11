#!/usr/bin/env python
"""看图写话配套物料 · 渲染引擎薄 shim（零逻辑）。

唯一实现＝同步写作配套的 `_shared.py`（CLAUDE.md §3 声明的两线共享单一源，禁复制逻辑）。
用 importlib 按显式路径以 `_shared_real` 之名载入真实实现（避免与本文件同名 `_shared` 撞车），
再把 render/inject/safe_pdf/check_pages/out_base 等整体转出。
真实 _shared.py 的 PROJECT_ROOT / LOGO_PATH 由它自己的 __file__ 解析，指向项目根 品牌资产\\logo.png。
"""
import importlib.util
import pathlib

# scripts -> laojohn-picture-materials -> skills；到同级 writing-materials/scripts 取单一源
_REAL_PATH = (
    pathlib.Path(__file__).parents[2]
    / "laojohn-writing-materials" / "scripts" / "_shared.py"
)
_spec = importlib.util.spec_from_file_location("_shared_real", _REAL_PATH)
_real = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_real)

# 单一源整体转出（勿在此处写任何渲染逻辑）
render = _real.render
inject = _real.inject
safe_pdf = _real.safe_pdf
check_pages = _real.check_pages
check_type3 = _real.check_type3
check_sheet_overflow = _real.check_sheet_overflow
out_base = _real.out_base
A4_H_PX = _real.A4_H_PX
PROJECT_ROOT = _real.PROJECT_ROOT
LOGO_PATH = _real.LOGO_PATH
