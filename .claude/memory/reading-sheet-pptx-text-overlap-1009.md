---
name: reading-sheet-pptx-text-overlap-1009
description: 阅读单可编辑PPTX文字挤压/被遮挡的根因与已修位置；PDF正常不代表PPTX正常
metadata:
  node_type: memory
  type: project
  originSessionId: 5b9eb105-d4f0-4548-a21d-44424bdeae59
  modified: 2026-10-09T11:52:29.961Z
---

2026-10-09 用户反馈神笔马良阅读单2“小字重叠、有重影”（称《大头儿子》也有）。PDF/HTML 均正常，问题在 `render_pptx.py` 出的可编辑 PPTX：定高文本框按「字号×1.2」估行高，微软雅黑实际≈字号×1.33×行距，两行文字会溢出被下方形状盖住。

已修两处：voyage 顶部棕框（书名/副题间距 28→42px、框高 64→84）、deduce matrix 卡头（按 `_wrap_lines` 实算行数撑高 HEAD_H）。用户随后指出真正的“重影”是雅黑粗体在小字号上笔画糊在一起（放大即不重叠），voyage 栏目字已改常规体（HTML+PPTX）；《大头儿子》那张用户已自行删掉。

**How to apply:** 查阅读单排版问题要用 PowerPoint/WPS COM 按 A4 比例导出 PPTX 看（`shot_assets.py` 导 pptx 会被拉成 16:9，不能用来判版式）；同类病多半在其他写死高度的 add_text 上。

同日：抢先看模板 `.leaf` 由 nowrap 改 `white-space: pre`（不自动折行、认手写换行），超长叶在 json 里手动断行；《洞》抢先看也贴右边距，未处理。
