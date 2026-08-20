---
name: ppt-click-reveal-animation
description: laojohn-ppt v7 逐条点击淡入动画——要点小结/引导问题追问注入 PPT 原生 timing，--no-anim 可关默认开
metadata: 
  node_type: memory
  type: project
  originSessionId: ba73de40-bf2d-4336-a03b-a2d427ccbc6e
---

laojohn-ppt 渲染引擎已加 **逐条点击呈现动画（v7，2026-06-23 用户确认线上系统能播后固化进 SKILL）**。

**范围**：只对 `要点小结`、`引导问题`的追问两类页型生效；封面/环节标题/原文齐读/填空表格/END 不加（直出）。标题/眉标/引文/问号水印首屏即在，不参与点击。仅 ≥2 条才启用，单条直出。动画固定 fade 0.5s + 点击推进。

**机制**：往 slide 注入 PowerPoint 原生 `<p:timing>` mainSeq。
- 要点小结：每条"红方块+数字+文字"3 形状成组，一次点击同出（1 clickEffect + 2 withEffect）。
- 引导问题追问：单文本框按段落构建 `bldP build="byParagraph"`，点一次出一段。

**实现**：`helpers.add_click_reveal(slide, groups)`（groups 元素=一次点击的一组 target，target=int shape_id 或 (spid, 段落号)）；`add_numbered_bullets` 改为返回每条形状分组。每个 `<p:cTn>` id 全树唯一。`build_ppt.py` 加 `--no-anim`（默认开），ctx["anim"] 路由。改了 helpers/layouts/build_ppt 三文件 + SKILL.md。

**开关与退化**：`--no-anim` 关闭则 0 个 timing 节点。会拍平成图片/PDF 的线上系统会丢动画，多数退化为"整页直出"（非损坏）。

**重要**：用户拍板**只固化进引擎+文档、不重烘焙已有 8 份洞/格列佛 PPT**（"PPT 还有其他地方要调整"）。后续若批量重烘焙，默认就会带动画。相关 [[docx-engine-redundancy-audit]] 不受影响（那是 docx 引擎，本改动在 ppt 引擎）。
