---
name: reading-sheet-venn-ellipse-rewrite
description: 维恩图模板由正圆改双长椭圆、书写空间大扩；改几何须同步 template_venn.html 与 render_pptx.py
metadata: 
  node_type: memory
  type: project
  originSessionId: c3f822bc-12f9-49dd-b7a3-3697c78fc9ff
  modified: 2026-07-28T03:02:06.575Z
---

2026-07-28 重做 `laojohn-reading-sheet` 的 venn 模板：由两枚正圆（R=212、每区 2–3 条 120–158px 短线）改为**两枚竖向长椭圆**（CX1=266/CX2=528/CY=466/RX=244/RY=400），左右独有区每个维度 3 条 234px 书写线、交叠区 2 条 126–201px；新增可选 `row_marks`，三区行首挂 ①②③ 维度序号且同一 y 齐平。

**Why：** 用户实测发现原维恩图填写空间太小——同一张单子的参考内容（三维度对照表，左右每格 30–45 字）根本写不下，且页面下方 40% 全是空白。

**How to apply：**
- 关键几何性质：**两椭圆等大 ⇒ 左/右独有区在任一高度上水平宽度恒为 CX2−CX1**，所以书写线随椭圆边缘平移即可始终满宽。旧版固定 x 只能取最窄处，这是空间小的根因——别改回固定 x。
- 交叠区是透镜形、上下两端骤窄（约 100px），**共同点只写短句**；维度行不能像左右区那样往上下铺开。
- 数组的一个元素 = 一个「对比维度」（自带多条线），不是一行字。
- **同一张图画两遍**：`templates/template_venn.html` 与 `scripts/render_pptx.py` 的 `render_venn()` 常量必须同步改，否则 PDF 与可编辑 PPTX 打架。
- 改完记得重渲用到 venn 的全部书目（当时为 小飞侠彼得·潘／洞／格列佛游记／俗世奇人）。

相关：[[reading-sheet-skill]]、[[reading-sheet-always-pptx]]、[[reading-sheet-fishbone-landscape]]
