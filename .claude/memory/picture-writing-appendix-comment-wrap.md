---
name: picture-writing-appendix-comment-wrap
description: "看图写话详案「生图工单」「真实性自检」两附录区整体包<!-- -->不进docx,支架小提醒保留可见(2026-07-22拍板)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a6406374-f79d-471e-91f5-799ed6d90018
  modified: 2026-07-22T04:27:30.749Z
---

看图写话详案文末三附录的处置口径(2026-07-22 用户拍板):「附：生图工单」「附：真实性自检」两区各自从 `## 附：` 标题行起整体包 `<!-- ... -->`(`<!--`/`-->` 独立成行、区内禁 `-->` 字样),只留 md 源、不渲进老师拿到的 docx;「附：本期支架与说写格式小提醒」是唯一可见附录(老师发卡/撤架依据+冷审维五查验对象)。正文校内基线句**不再写「官方原文详录见文末真实性自检」转引括注**(docx 里该节不存在会悬空)。

**Why:** 工单是图位规格唯一源(正文只有占位)、生图/验收/冷审判型硬依赖,md 里删不得;但 docx 共享引擎没有代码围栏跳过逻辑,整页生图英文提示词和审稿自检口径全渲进了交付稿。引擎唯一跳过机制=多行 `<!-- -->` 块(md_to_laojohn_docx.py:818-827);imgspec_parser 用 re.S 全文正则抓 ```imgspec 围栏、冷审读 md 原文,注释对两者透明——已实测回归(一上5块/二上3块解析不变,4份docx目检过)。

**How to apply:** 新详案按 SKILL.md 骨架条直接包注释产出;规则已固化五处:picture-writing SKILL.md(骨架+包注释条+校内基线措辞)、image-spec.md(工单格式示例)、lesson-structure.md §12、checklist.md 门禁类新增自检项、review-rubric.md(注释包裹属正常形态防冷审误报)。存量两期(一上/二上第1次)已包好并重渲全部 docx。[[picture-writing-opening-simplified]] [[picture-writing-cold-review-wired]]
