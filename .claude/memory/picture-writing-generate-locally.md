---
name: picture-writing-generate-locally
description: 看图写话教案生成侧收归本地 CC，不再走 web 端生成+打包合并
metadata: 
  node_type: memory
  type: project
  originSessionId: 3b2a1d4b-0859-4f2c-bd86-97658f155dd9
  modified: 2026-07-19T09:53:41.509Z
---

2026-07-19 用户拍板：**看图写话（及各类教案）以后一律在本地 CC 这边生成，不再在 web 端生成后打包合并过来。**

**影响**：
- `laojohn-picture-writing` 的 SKILL/references 从此**只有本地一个源**，不再存在「web 版 vs 本地版」的分叉与逐段合并工序。改规则直接改本地文件即可，不必再考虑"web 侧要同步"。
- 上一轮 v6 合并中标注为「web 生成侧仍需同步」的两条（`【图位:编号】` 机读占位契约、教室无黑板禁令）已写进本地 SKILL 工作流第6步 + checklist，**由我生成时直接遵守，无需再向 web 侧传达**。
- 期2/3/4/18/19 及后续期次都在本地按「ability-ladder 期记录 + curriculum-archive 锚点 → 图位规格 → 正文 → imgspec_parser 机检 → build_picture_lesson 生图闭环」一条龙产出。

**背景**：v6 那次是 web 端做内容层升级、打包 zip 过来逐段合并（见 [[picture-writing-24-stages-v6]]），合并中踩了占位契约缺失、黑板残留、游戏化说法回潮等多处分叉成本——收归本地即为消除这类成本。
