---
name: picture-writing-opening-simplified
description: "看图写话详案开篇简化(历史:两区表版式已被2026-07-22三区提纲页取代,删四维目标节仍有效)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9a5952c6-3f2c-4d8f-a37a-4916ad450630
  modified: 2026-07-22T13:45:13.026Z
---

2026-07-21 用户两轮拍板：①删「核心素养教学目标」整节（四维是客套，目标由提纲表+各课时「本课目标」承载，**与 writing-lesson 开篇形态分叉**）；②首页按用户提供《详案首页示例.docx》定版——md 源=「教案提纲表」4行表(课次·课型兼表头/教什么/学生带走/用什么)＋加粗组头「这一课在整个课程里的位置」4行表(这一期/本学期主题/能力线/对齐统编，事实只来自course-map，增量用平实说法 同步/加深/先导 对应档案 同步/超深/超前)＋`>`校内基线注；docx 出完后**必跑 `scripts/style_front_page.py <md> <无图.docx> <配图.docx>`** 重排首页（居中三行标题+副题/品牌行下细分隔线/节标题左竖条/10×2分组表·标签列居中垂直居中/左色条基线框，样式常量单一源=该脚本，首页独占一页——脚本给「第N课时」锚段补 pageBreakBefore）。**关键词自动标红**（`_render_value`，md 无标红标记）：课次·课型第2段课型／能力线中的本期期名（H1《》内，含冒号时退化取后半段）／「增量：」后的词；「这一期」括号注灰色小字。样式历经三稿：示例docx→截图定稿（2026-07-21晚），以截图版为准。

**Why**：老师翻开第一页要一眼见课＋这课在整个课程里的位置，不是读审稿口径和素养话术。

**How to apply**：已固化 SKILL.md 骨架节 + checklist（"课次·课型"行）+ review-rubric（"教什么"行）；期6/期1 已回改并重渲 4 份 docx（Word COM 转 PDF 目检过）。新出期次检索「【语言运用】」等四维标签应为零。中间态"三行极简表"当天即被首页示例版取代，勿再采用。相关 [[picture-writing-stage6-state]]

**⚠ 版式已再度换代（2026-07-22 晚）**：本条的「两区表＋`>`校内基线注＋标红」版式已被《新_课案提纲页.docx》**三区提纲页**取代（见 [[picture-writing-front-page-3zones]]）；「删四维目标节」「必跑 style_front_page」「首页独占一页」仍有效。

**⚠ 两处已变更（2026-07-22）**：① **「与 writing-lesson 分叉」作废**——写作课同日也取消四维目标节、也改首页两区表，两线开篇形态重新对齐（各自的行名与事实源仍不同：看图写话 24 期七模块 vs 写作课六阶 63 任务，不得互抄）；② **脚本已迁走**——`style_front_page.py` 从 `picture-writing/scripts/` 迁入 `laojohn-lesson-plan/assets/` 作两线共享单一源，课型差异收在脚本顶部 `PROFILES` 表（本技能＝`picture` 档，H1 自动判型）。看图写话调用改为 `python ../laojohn-lesson-plan/assets/style_front_page.py …`，其余用法不变。详见 [[writing-lesson-front-page-two-zones]]
