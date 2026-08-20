---
name: writing-lesson-front-page-zones
description: 写作课首页定版分区提纲页(新－同步习作_课案提纲页.docx 2026-07-22)——两区/行名重组(课题·课时/核心能力点/怎么落地)/与picture同构;脚本旧两区路径已删
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b90a1462-9ca1-4691-85f7-ac01ab31e8f9
  modified: 2026-07-22T14:39:56.268Z
---

> ⚠ **分区结构已于 2026-07-29 作废**（写作线改无区头单表 6 行）——以 [[writing-lesson-front-page-single-table]] 为准；本条只剩视觉（标题区/语义灰阶/无红）与脚本清理史仍有效。

> ⚠ **行名已于 2026-07-25 全部换成教研通用词**（对应教材／教学内容／学习目标／教学准备／校内学情起点／本课提升点／教学边界；写作线 `学生带走`→`学习目标`）。本条的版式结论仍有效，**行名一律以 [[outline-row-names-teaching-terms]] 为准**。


2026-07-22 用户提供《新－同步习作_课案提纲页.docx》定版写作课首页，取代同日上午的两区表（[[writing-lesson-front-page-two-zones]] 版式部分作废）。与看图写话三区版（[[picture-writing-front-page-3zones]]）**同构**：居中两行标题区（《题目》20pt ─ 分隔线 9A9A9A ─ 副题 13pt 灰，无品牌行）＋一张两列表按 `**N、区名 —— 副题**` 灰底区头分区，语义灰阶＋纯黑强调无红。

**writing 两区行名**：一、本课定位——**课题·课时**（`三上·第一单元《猜猜他是谁》　│　写人·校内同步`，课时 2×45 不再进表）／能力阶段／**文体线**（本课题目后打「（本课）」标记→渲纯黑）／**核心能力点**（`对齐统编<册>·第N单元习作——<能力点>。`，——前弱化灰）；二、本课要点——核心技法（原主线+辅助收纳）／**怎么落地**（原「落地:」独立成行）／学生带走。原「基本信息」行拆解、「辅助」技法条括注收纳。**「怎么落地」「学生带走」值内成对 `**…**` 强调＝写作课全文 `*` 禁令的唯一放行处**（连同两区头行，已改 lesson-structure §三禁令例外口＋checklist）。

**脚本**：`style_front_page.py` 大清理——旧两区路径（NAVY/RED 深蓝红标体系、节标题左竖条、底部提示框、head_note/highlight_current 等规则）**整体删除**，两 profile 统一走分区渲染（PROFILES 只剩 h1/subtitle/zones_anchor/tbl 表宽/rules）；writing 表宽 9572/1877、picture 9072/1636，新增 `_tbl_grid` 显式写 tblGrid（此前只设 tcW、grid 均分）。新增规则 p_ink/p_src_dash。**picture 线回归零差异已验**（重构前后 XML 逐成员一致）。

**Why**：两线首页视觉统一成一套设计语言，老师拿到的两类详案第一页同构。

**How to apply**：已固化 writing-lesson lesson-structure §四（唯一源）/SKILL/checklist、CLAUDE.md §3/§4；存量 5 篇写作课 md 已改分区结构并重渲 docx。新详案 md 直接按两区写；改脚本仍须两线回归。
