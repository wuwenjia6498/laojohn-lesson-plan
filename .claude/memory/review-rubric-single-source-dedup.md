---
name: review-rubric-single-source-dedup
description: 复盘相关三文件去冗余——review-rubric 是唯一源，detail-review 与两 SKILL 只指向不复述
metadata: 
  node_type: memory
  type: feedback
  originSessionId: b574a459-e3b1-45bf-96bb-0e0fce1b06e5
---

成稿复盘的「审稿人协议五条 / 五维查项 / 分流处理 / 报告三件套」**唯一源 = 各自的 `references/review-rubric.md`**（阅读、写作各一份，五维不同）。下游一律**只指向、不复述**：

- `laojohn-detail-review/SKILL.md`：只写冷审**流程骨架**（判型表 / 冷启动理由 / 形态A·B·降级 / 分流动作），协议五条·五维名·报告格式改为"以 rubric 为准，本技能不复述"。
- `laojohn-lesson-plan/SKILL.md`(第8步) 与 `laojohn-writing-lesson/SKILL.md`(第6步)：只管"派活"——停手→派 fresh 子 agent 调 detail-review（带 .md 绝对路径）/ 兜底新会话；形态细则·协议·五维·分流·报告格式全部下沉，一句"以 detail-review 及其加载的 review-rubric 为准，此处不复述"。
- 两个 `review-rubric.md` 把 `review-rubric.md` 从生成方「每次必读」移到新行「生成方不读·复盘方读」——复盘已冷启动独立化，生成会话自己不读 rubric，由冷审 agent 读。

**Why:** 2026-06-25 盘点发现这三文件把协议/五维/分流/报告格式各重复 3 遍，且 detail-review 第1步白纸黑字写"不重抄五维"却在 2–5 步全文抄了，自我违约；生成方也不再自审 rubric 却仍挂"每次必读"。重复=改一处忘改它处的漂移源。

**How to apply:** 改复盘五维/协议/报告格式只改对应 `review-rubric.md`；**严禁**把这些内容回填进 detail-review 或两 SKILL 的复盘步骤——那两处只能放"派活动作 + 指向"。唯一允许在多处重申的是**真实性红线**（CLAUDE.md §4 有意强调）。详见 [[detail-review-cold-start]]。
