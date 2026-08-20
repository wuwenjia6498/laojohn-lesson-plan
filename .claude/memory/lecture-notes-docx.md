---
name: lecture-notes-docx
description: 逐页讲稿新增 docx 输出能力，永久接入 ppt-draft 与 course-package
metadata: 
  node_type: memory
  type: project
  originSessionId: 749effa7-43bc-49d0-b183-a9908433f0ba
---

2026-06-25：逐页讲稿（课件讲稿）从「只出 .md」升级为「.md + .docx 同时出」。

- 转换脚本：`.claude/skills/laojohn-ppt-draft/scripts/lecture_notes_to_docx.py`（用 python-docx，**讲稿专用干净版式**，非详案品牌引擎——不触发课案封面页）。用法 `PYTHONUTF8=1 python lecture_notes_to_docx.py 讲稿.md [输出.docx]`，默认同名 .docx。
- 版式：文档标题居中 + 用法说明灰字；每页一条顶部横线 + 「第N页·页型」深蓝灰色标 + 加粗标题；口播=青绿标签+可念正文(11.5pt)、回溯/节奏=灰色元信息合并一行、兜底参考=橙棕(仅老师看)；行内 `**加粗**` 渲染真加粗、残余 `**` 自动剥除。
- **md 是事实源、docx 是渲染产物**：改讲稿改 md 后须重跑脚本重转 docx。
- ppt-draft SKILL 已加 step 5b（讲稿写完即转 docx）、自检清单、文件树、输出契约；不再是「纯 Prompt 无脚本」(末端转换走脚本)。
- course-package 逐页讲稿 primary = `{.docx}`：**打包只收 docx 打印件，md 视为源默认不收**（--with-sources 才带 md）。洞打包目录逐页讲稿\ = 4 份 docx。
- 《洞》4 份讲稿 docx 已补出（导读21/交流1=17/交流2=17/思辨18 页，与 PPT 张数同）。

关联 [[detail-review-cold-start]] 之外的下游产物口径；详案↔中间稿↔讲稿↔PPT 四方页号一致仍成立。
