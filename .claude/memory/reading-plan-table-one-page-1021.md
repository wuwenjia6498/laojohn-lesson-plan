---
name: reading-plan-table-one-page-1021
description: 读书会 PPT 的阅读计划/七天阅读记录表永远只放一页，不按「表格超 6 行拆两页」拆；规则已写进 ppt-draft 两处与 ppt 故障排查表
metadata:
  type: feedback
---

读书会 PPT 的**阅读计划表（七天阅读记录表，按天一行）一律只放一页 PPT，不拆成两页**（2026-10-21 用户定）。

**Why:** 《和大人一起读（一）》导读课按「同一张工具表超 6 行拆两页」把记录表拆成「前三天／后四天」两页（P34–35），用户回改时要求合并，并明确「以后的阅读计划表都只放在一页 PPT 上」。表头＋7 天＝8 行，引擎 `add_table` 按行数自适应放得下（实测 22pt 字、行高约 0.49M EMU，版面正常）。

**How to apply:**
- 写中间稿时阅读计划表直接写成一页 `填空表格`：标题不带「（前三天）」这类后缀，两页的副标题合成一句。例外已写进 `laojohn-ppt-draft/references/field-extraction.md`（表格禁忌）、`page-type-decision.md`，以及 `laojohn-ppt/references/visual-variants.md` 的故障排查表。
- 其它超 6 行的工具表照旧拆两页，例外只管阅读计划表。
- 合并后后续页号前移一位：中间稿 P 号、讲稿 `## 第N页`、详案〖PPT第N页〗三处要一起改。
- 存量里《孤独的小螃蟹》《小狗的小房子》导读课中间稿仍是拆开的（用户说的是「以后」，没回改）。

相关：[[reading-ppt-general-feedback-1008]] · [[ppt-draft-pageback-mandatory]]
