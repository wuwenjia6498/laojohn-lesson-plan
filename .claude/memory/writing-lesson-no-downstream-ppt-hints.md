---
name: writing-lesson-no-downstream-ppt-hints
description: writing-lesson 详案正文不写面向下游 ppt-draft 的提示标签(可视化建议/素材提示),同换页点已废弃
metadata:
  type: feedback
  originSessionId: 956fa1e5-53a5-4214-852b-638e1ac051fe
---

用户要求(2026-06-27):writing-lesson 详案正文里**不写面向下游 `laojohn-ppt-draft` 的提示标签**——如 `[可视化建议:…供 ppt-draft 出图]`、`[此表…可作 ppt「原文→批注」可视化页素材]`。生成 PPT 时由 ppt-draft 环节自行判断哪些适合做可视化,详案不必夹这种衔接元信息。

**Why**:详案是给老师上课的教学文档,这类「告诉下游怎么做 PPT」的话属 AI/下游提示,不该进面向师生的正文——与已废弃的逐环节括号自注 `(此处落实…)`、`【PPT换页-PXX】` 换页点同理。

**How to apply**:① 旁批表、示范文、构思表等教学内容**本身保留**(它们是给师生的课堂呈现),只去掉「这也是 ppt 素材/供出图」这类话;② 规则里「示范文旁批对照也能作 ppt-draft 素材」这层用途**只写给生成器、不落进详案正文**。已固化:`checklist.md` E 组(换页点条之后新增一条)、`workflow-engine.md` 环节④旁批 bullet、`model-essay.md` §五、`SKILL.md` 换页点条。《这儿真美》已删两处(原 line129 可视化建议、line255 旁批 ppt 素材提示)。相关:[[style-redline-covers-edits]]。
