# -*- coding: utf-8 -*-
"""Vercel 入口。

Vercel 的 Python 预设认「部署根下的 index.py 里的顶层 app」，认出来之后
**把所有请求都路由给它**（API 与前端静态都走这里，和本机 python server/main.py
的行为完全一致）。

⚠ 别把这个文件挪进 api/：那个目录名在 Vercel 上是「一个文件一个端点」的旧式
文件路由，所有 /api/* 会塌缩成同一个路径，FastAPI 一个路由都匹配不上、全 404。
这是 2026-08-24 部署时踩过的坑。

真正的服务在 server/main.py —— 这里只是把它导进来，**不要往这个文件里写逻辑**，
否则本地跑和线上跑成了两套代码，而且只有线上会坏。

配套：部署前必须先跑 build_deploy.py。
"""
import importlib.util
from pathlib import Path

_main = Path(__file__).resolve().parent / "server" / "main.py"
_spec = importlib.util.spec_from_file_location("lj_grade_server", _main)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

app = _mod.app
