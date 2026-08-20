---
name: terminology-unified-image-and-model-essay
description: 2026-07-26 全仓两项术语统一——「下水例文/下水文」→「示范例文/示范文」；图片人读文字→「主图/备选图」（⚠当日晚编号前缀亦改主-/练-/备-，见 picture-writing-three-image-slots）
metadata: 
  node_type: memory
  type: project
  originSessionId: 30be76e1-5b88-4db2-962a-375d1001e4a0
  modified: 2026-07-26T06:16:12.340Z
---

2026-07-26 用户拍板的两项全仓改名，已执行完毕（改动 50 个文件，产物已重渲）。

**① 教师范文用词去「下水」**
- 看图写话线标记：`【教师下水例文 · 示范】` → **`【教师示范例文】`**（尾部重复的「· 示范」一并去掉）
- 写作课配套：「教师下水文」→ **「教师示范文」**，与写作课详案侧本来就有的 `【教师示范文】` 合流
- 全仓「下水」字样归零（唯一命中是 L4 十万个为什么范例里的「水会沸腾」，非术语）

**② 图片概念统一（双轨制的人读侧收敛）**
- 人读文字一律 **主图／备选图／格式图**：SKILL、references、详案正文（含「教学准备」栏与生图工单的 `角色:` 值）、配套物料、验收报告、CLAUDE.md、README.md
- **机器标识刻意不动**（⚠ **当日晚被用户推翻**：编号前缀已改 `主-/练-/备-`、常量已改 `ROLE_MAIN`／`MAIN_STYLE_TOKEN`，详见 [[picture-writing-three-image-slots]]；下面这段留作决策史）：编号前缀 `锚-0N`／`例-0N`、图片文件名 `锚-01.png`、正文占位标记 `【图位:锚-01】`、脚本常量名 `ROLE_ANCHOR`／`ANCHOR_STYLE_TOKEN`。改它们要连带重命名存量图片资产、断解析链，收益为零。
- `imgspec_parser.py` 加了 `_ROLE_ALIASES = {'锚图':…, '例库图':…}`，`role` 属性走别名映射——**旧稿写 `角色: 锚图` 仍能解析**，不会静默失配。
- 规则固化进 `picture-writing/references/terminology.md` 硬替换表（锚图→主图、例库图/例图→备选图），并注明机器标识例外，防回潮。

**Why:** 同一张图在总地图叫「主图」、在图位规格叫「锚图」、在详案「教学准备」栏写「（锚-01 主图）」两词并列，对外文档要用内部黑话，教研看着混乱。

**How to apply:** 以后写看图写话任何人读文字只说主图/练笔图/备选图；写规格块 `角色:` 同口径；**编号前缀以 [[picture-writing-three-image-slots]] 的新口径（主-/练-/备-/格-）为准，本条的「锚/例 照旧」已作废**。改画风令牌仍须 `style-tokens.md` 与 `imgspec_parser.py` 两处一字一致（本次已复验通过，并顺带把文档侧的「本期主图」统一成脚本侧的「本课主图」）。相关：[[picture-writing-course-map-v4-0723]]、[[picture-writing-global-style-tokens]]、[[outline-row-names-teaching-terms]]
