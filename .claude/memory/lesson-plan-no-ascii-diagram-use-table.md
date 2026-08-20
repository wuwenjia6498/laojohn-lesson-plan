---
name: lesson-plan-no-ascii-diagram-use-table
description: 读书会详案里可视化工具禁用代码块 ASCII 画图、一律用 Markdown 表格（用户 2026-07-03 反馈）
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 339baf21-88da-411b-8c20-b6632de28713
---

用户看格列佛详案，指出维恩图那种「```代码块里用制表符 ┌─│ 画的 ASCII 示意图」读起来奇怪，「需替换为表格」。

根因：生成时随手用 ASCII 画了维恩图/思维导图/阶梯图/讽刺逻辑图（格列佛详案共 4 处），在 docx 里渲染成等宽错位难读。**其实 visualization-tools.md 本就规定「工具用 Markdown 空白表格/节点清单，不画图、不出图形代码」——ASCII 画图是违反现有规则**，只是规则没把「ASCII 制表符画图」显性点名、没被自检抓到。

**Why:** ASCII 图靠等宽对齐，docx/普通渲染下必然错位乱码；且详案定位是「文字骨架」，图形交给下游 PPT/物料线。

**How to apply:** 可视化工具在详案里一律用 Markdown 表格承载——空白版（给学生填，空单元格）与参考版（填答案）**同一套表头/行列**，图形形态（圈叠/台阶/树枝）用一句话文字说明，不用 ASCII 还原。已固化：visualization-tools.md 输出边界加「⚠不用代码块画 ASCII 图」硬规则 + checklist「可视化落地」加自检项。**已执行**：格列佛详案 4 处 ASCII（维恩/思维导/讽刺逻辑/阶梯）转成与各自下方参考表同构的表格、docx 已重渲染；洞/俗世奇人详案经 box-char 全扫无此问题。注意 Edit 插入的全角引号会被写成 ASCII，事后必跑 [[write-tool-normalizes-curly-quotes]] 的 fix_quotes_md。看图写话详案里的代码块是板书/imgspec 生图工单，非表格、不要动。
