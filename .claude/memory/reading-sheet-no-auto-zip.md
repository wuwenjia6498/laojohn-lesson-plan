---
name: reading-sheet-no-auto-zip
description: 阅读单交付以后不要自动打包成 ZIP
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a38a763a-29b8-4052-8fac-26b482e3e003
---

阅读单(laojohn-reading-sheet)交付：**不要 ZIP，但要那份合订 PDF**。

- **ZIP**：以后不要再打 `<书名>阅读单.zip`——它从来不是 SKILL/render.py 的产出，是我自发加的，用户不用（2026-06-29）。
- **合订 PDF**：用户要的「阅读单合成文件」= render.py 默认产出的 `<书名>-阅读单-全套.pdf`（按 manifest 次序把各空版顺次合订）。**所以跑 render.py 不要加 `--no-bundle`**。

**How to apply:** 正常 `python render.py <manifest> <出目录>`（默认即出单张 PDF/HTML + 合订全套 PDF）；交付这三样 + manifest。不再用 zipfile 打包，旧 zip 不主动刷新。相关 skill 状态见 [[reading-sheet-skill]]。
