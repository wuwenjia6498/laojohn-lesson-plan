---
name: reading-sheet-low-grade-lively-1008
description: 阅读单别一律表格(1008低年级→1011扩到L3)；详案点名的图形工具用专用模板，树形图用1014新开的tree；radial/profile color/note、timeline fields 由此而来
metadata:
  type: feedback
---

给二年级《大头儿子和小头爸爸》出阅读单时，四张全用 table/voyage，用户反馈「二年级的阅读单可以设计得活泼点，不要都这样表格样式」。

**Why:** 表格/棕色调是给中高年级的版式，低年级学生面对整页格子没兴趣，也不适合他们边写边画。

**How to apply:** L1–L2 的书出阅读单时，先挑非表格版式——中心+分支导图用 `radial`（1008 新增，亮色卡片+中心圆）、逐日记录用 `facets` 逐卡给亮色 `color`、需要写一写画一画的用 `profile`（可选 `color` 上彩）；table 只作兜底。

**1011 扩到 L3（稻草人）**：用户反馈「阅读单太单一，基本以表格为主，流程图，维恩图，思辨阅读单调整下形式」。详案就算写了「阅读单上我们用表格来填」，**名为流程图/维恩图/思辨单的照样用专用模板**（timeline／venn／stance），那句话只说上屏形式。流程图每站要写多样东西时用 timeline 的可选 `nodes[].fields`（1011 新增，零影响已回归）；stance 的 `verdict.lines: 0` 此前 HTML 侧不认（`||`→`??` 已修）。只有纯清单类（逐日记录、十二篇各说一句）才留 table。
附带修了 profile 模板静默丢弃 `note` 的老问题——神笔马良心愿卡的 note 以前从没印出来，manifest 已把画框高 760→700 以便 note 放得下，但其存量 PDF 未重渲。相关：[[downstream-shared-layer-and-token-facts]]

**1014 树形图新开 `tree` 模板（克雷洛夫寓言）**：先用 voyage（竖叠框）再用 radial（放射），用户都判「不像树形图」。树形图要的是**顶部根节点 → 横向总线 → N 支并排垂下**的样子，现已开 `template_tree.html` + `render_pptx.render_tree()`，登记表/决策树/schema 三处已补。以后详案点名「树形图」直接用 tree，别拿 voyage/radial 凑。
