---
name: ppt-four-image-grid
description: "laojohn-ppt 四图网格能力——引导问题页多条配图建议自动排2×2，用于\"看N幅画面\"页"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8fe89af1-0860-4f02-9f28-a18e360131c3
---

**四图网格能力（2026-06-22 新增，跨 laojohn-ppt + laojohn-ppt-draft）**

起因：格列佛导读课详案 P3"奇在哪儿？给你们看四幅画面，你自己感受"本质要展示四国各一图，但旧中间稿把四幕压成 4 条文字要点 + 1 条合并配图建议（还漏了慧骃国），PPT 只渲染单个占位框。用户拍板"新增 2×2 四图网格能力"（而非拆四页/改文案）。

**契约**：引导问题页写 **≥2 条** `配图建议：`（每幅一条，2–4 条）即触发；laojohn-ppt 在标题下整幅排 2×2 占位网格，每格一图、题面取各条「篇目·场景」段。此模式**不画问号水印、不渲染要点**；该页 `要点` 改为豁免必填。单条配图建议行为完全不变（向后兼容）。

**改了哪些**（laojohn-ppt/scripts/）：
- parser.py：Page 加 `image_suggestions: List[str]`（收全部），`image_suggestion` 留首条兼容旧单图路径。
- theme.py：加 `IMAGE_GRID_REGION=(0.07,0.42,0.86,0.50)` + `IMAGE_GRID_GAP=0.018`。
- helpers.py：加 `add_image_grid()`（2 列网格，过滤"无"，末行不足两个时居中，复用 add_image_placeholder 逐格渲染）。
- layouts.py：render_guide 加 `_real_suggestions()` 判定 grid_mode（≥2 条），网格模式跳过 Q 水印/要点/单图占位、直接铺网格 return。
- build_ppt.py：占位清单报告 grid 页显示 `[四图网格×N]`。

**ppt-draft 侧**：_smoke_check.py 对"引导问题+≥2配图建议"豁免 `要点` 必填；image-suggestion.md 加「四图网格」节；field-extraction.md 矩阵加脚注ⁱ；SKILL.md 字段表/工作流 step4/自检清单各加一条。两 SKILL.md 同步。

**已应用**：格列佛导读课 P03 中间稿改 4 条配图建议（小人国/大人国/飞岛/慧骃国各一），重烘焙 `课件PPT输出/格列佛游记/格列佛游记-导读课.pptx`（仍 20 页，结构验证 4 占位框 2×2 无水印无散落要点），并同步到 `格列佛游记相关文件/课件PPT/` 交付包副本。讲稿 P03 节奏本就是"看一幅说一幅"、详案页标仍单页〖PPT 第3页〗，均无需改。详见 [[ppt-draft-skill-state]] 体系。
