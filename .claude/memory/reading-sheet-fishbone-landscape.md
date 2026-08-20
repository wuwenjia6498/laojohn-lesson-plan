---
name: reading-sheet-fishbone-landscape
description: 鱼骨图阅读单模板内容改横排放大，但纸仍是竖版 A4——整页旋转 90° 印上去
metadata: 
  node_type: memory
  type: project
  originSessionId: 8c2cbf03-980c-4352-bfa2-28133e84f4ea
  modified: 2026-07-28T02:16:57.457Z
---

2026-07-28 把 `template_fishbone.html` 的内容改成横排 1123×794（主干贯穿整页宽、事件框由 150×80 放大到约 226×206、6 支骨时每框 5 条书写线），**但纸面仍是竖版 A4 794×1123**——内容装在 `#canvas` 里整页 `rotate(-90deg)` 铺满页面，学生把纸顺时针转 90° 即为正常视图。

**Why:** 竖版排下鱼骨主干只有 446px、框 150×80 两行，学生几乎没有书写空间；横排把主干拉到 ~700px，框面积增至约 4 倍。用户明确要求这张要与其余阅读单**同叠竖版打印**，所以不能真出横向纸（第一版做成横向纸后被否），改用「竖纸 + 内容旋转」。

**How to apply:**
- **纸向口径别混**：`timeline` 是全套唯一真横向纸（`#page` 自报 1123×794，`render.py` 量宽自动出横向 PDF）；`fishbone` 的 `#page` 仍是 794×1123、PDF 与其余单子一样 596×855。PPTX 侧 `timeline`/`fishbone`/`story_mountain` 都是横排内容缩放横铺进竖版页、**不旋转**的近似还原。
- 改鱼骨几何**只动 `#canvas` 内的坐标**，旋转层（`#canvas` 的 top/left/transform）不必动；容器居中值 `top:164.5px; left:-164.5px` 是 (1123−794)/2 推出来的，换尺寸才需重算。
- **框宽是自适应的**：`BOX_W = clamp(2×根点步长 − 24, 120, 300)`，支骨越少框越宽。所以支骨建议 4–8，别为了填满硬加骨。
- **主干两端按标签宽度让位**：HTML 侧用 `getComputedTextLength()` 实测 `head_label`/`tail_label` 宽度反推 `X_TAIL`/`X_HEAD`（曾把「刚进老胡家」切掉半个字）；PPTX 侧没法实测，按 18px/字估算——**改 endlab 字号必须同步改这个估算常量**，否则 PPTX 两端错位。
- 改 `template_fishbone.html` 的几何常量后，**必须同步 `scripts/render_pptx.py` 的 `render_fishbone`**（它是独立重绘、不读 HTML），否则 PDF 与 PPTX 视觉分叉。

相关：[[reading-sheet-skill]]、[[reading-sheet-template-expansion-18]]、[[reading-sheet-editable-pptx]]
