---
name: reading-sheet-always-pptx
description: 阅读单交付默认同时出可编辑 PPTX（render_pptx.py 与 PDF 同批跑）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: f0e24186-1d20-485f-ab54-8539d6c0da3d
---

用户拍板（2026-07-14，玛丽阿姨阅读单）：跑 laojohn-reading-sheet 时，生成全套 PDF 的**同时**默认跑 `render_pptx.py` 出 `<书名>-阅读单.pptx`，不必等用户另行索要。

**Why：** SKILL.md 把 PPTX 标为"可选、用户要时才跑"，但用户希望它是标配交付物（老师要能在 PowerPoint/WPS 里直接改）。

**How to apply：** 同一份 manifest 两个引擎各跑一遍（render.py → PDF/HTML/合册；render_pptx.py → 单份多页 pptx）；交付时仍照 SKILL 提示几何类模板（venn/ladder/voyage/timeline/story_mountain 等）在 PPTX 里是近似还原、timeline/story_mountain 精确横版以 PDF 为准。相关：[[reading-sheet-editable-pptx]]、[[reading-sheet-no-auto-zip]]
