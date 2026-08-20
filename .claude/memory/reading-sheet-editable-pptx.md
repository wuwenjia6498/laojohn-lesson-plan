---
name: reading-sheet-editable-pptx
description: 阅读单新增「原生可编辑 PPTX」输出引擎 render_pptx.py（与 render.py 平行）
metadata: 
  node_type: memory
  type: project
  originSessionId: 2e788ccf-7b5f-4683-b790-0f77f8b851df
---

reading-sheet 在 PDF/HTML 之外新增第三种成品：**老师可编辑的 PPTX**。新引擎
`scripts/render_pptx.py`，与 `render.py` 平行——读**同一份 manifest（零 data 改动）**，
把每张单重建成 PPT 原生表格/文本框/线条/形状（非整页图片，可直接改字/加行/挪元素）。
CLI：`PYTHONUTF8=1 python scripts/render_pptx.py <manifest.json> <输出目录>` →
`<书名>-阅读单.pptx`（一份多页、按 manifest=教学序、`-示范` 自动跳过、不出 zip）。

设计要点（2026-06-30 落地，13 模板全部目检通过）：
- **保真移植**：直接搬各 `template_<键>.html` render() 的像素坐标常量，按
  `SCALE=Mm(210)/794px` 做 px→EMU、字号 `pt=px*0.75`。
- **自包含**：绘制原语就地实现，**不跨技能 import** laojohn-ppt 的 helpers/theme；只依赖
  python-pptx。含中文字体 latin-在-ea-前 修复（见 [[ppt-font-ea-latin-order]]）。
- **仿射 TF 类**：竖版恒等；timeline/story_mountain 原横版→缩放横铺进竖版页（唯一近似点，
  交付要提示「精确横版以 PDF 为准」）；流式单子超一页→纵向压缩 `sx=1,sy=vk` 入页(字号不变)。
- **加模板要同步**：新模板除 HTML 外，须在 render_pptx.py 的 `RENDERERS` 注册
  `render_<键>(slide,d)`，否则该模板 PPTX 缺页（渲成占位提示）；PDF 路径不受影响。
- 与已删除的旧 `ppt_export.py`（阅读单塞进 laojohn-ppt 投屏页型，已下线）**无关**，别混淆。

验证法：PowerPoint COM 导 PNG（`POWERPNT.EXE` 在
`C:\Program Files\Microsoft Office\root\Office16\`）：`$ppt.Presentations.Open(f,$true,...)`
→ `Slide.Export(png,"PNG",850,1202)`。相关：[[reading-sheet-skill]]、[[reading-sheet-no-auto-zip]]。
