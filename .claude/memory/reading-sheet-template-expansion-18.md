---
name: reading-sheet-template-expansion-18
description: 阅读单模板库 13→18（relation/facets/lanes/stance/deduce），五类工具不再退化成表格；共用标签必须只印一次
metadata: 
  node_type: memory
  type: project
  originSessionId: 70c0d0df-f2b2-4c96-b686-9a3a5d06205a
  modified: 2026-07-18T11:19:55.963Z
---

2026-07-18 一轮「表格太多」整改：用户逐本指出阅读单里 `table` 兜底过多，按「先问选项、再改模板」的节奏扩了 5 个模板，模板库 **13 → 18**。

**新增模板（HTML + `render_pptx.py` 的 RENDERERS 均已注册）**

| 键 | 形态 | 典型用法 |
|---|---|---|
| `relation` | N 户/组围栏并排 + 组内人物槽 + 关系书写线 + 底部共同节点 | 人物关系图（呼兰河三户、彼得潘四方阵营） |
| `facets` | N 面卡片墙（面名彩条 + 该面问题 + 书写线） | 六面体讨论图；`columns:1` 时也用作「竖排阶段卡」（汉修三段梳理） |
| `lanes` | 共同起点 → N 阶段并排推进 → 末端向外分岔各接结局框 | 双角色故事地图（彼得潘：温迪↔彼得，落点是详案那句「分岔」） |
| `stance` | claim 横幅 + 左右两栏对峙 + 底部裁决行 | 立场表、正反对照（玛丽阿姨立场表、汉修两副笔墨、伊凡笼子↔动物园） |
| `deduce` | N 条线索 × ①线索 ↓ ②追问 ↓ ③裁决，带箭头 + 底部收口条 | 物证推断表（玛丽阿姨） |

**决策树已改**：`archetype-decision.md` 第三刀里「人物关系图 / 六面体讨论图 / 故事地图·英雄之旅 / 立场表 / 物证推断表」五项从「退化成 table」改为指向专用模板（单角色单线的情节起伏仍走 `story_mountain`）。

**头号坑：共用标签只能印一次。** `deduce` 初版每张卡各印一遍步骤文字、`stance` 初版每栏各印一遍字段标签——用户两次都指出「文字重复」。两者现在都按**是否共用**自动选版式：
- `deduce`：各卡共用 `steps` → `matrix`（步骤在左侧竖排一次，箭头也在左列），否则 `cards`
- `stance`：两栏共用 `fields` → `matrix`（标签在中间比较轴排一次，VS 圆标做轴头），否则 `columns`
可用 `"layout"` 显式覆盖。**新做单子时别手动指定 columns/cards 版式**，除非每卡/每栏的字段真的不同。

**一页 A4 的行数上限**（超了会溢出成更高的单页，打印被缩放；正常一页 = 854.9pt，与全套一致）：
facets 6 面 × 3 行；deduce 3 卡 × (3+3 行 + 裁决) + 收口 3 行；stance 4 字段 × 2 行 + 裁决 2 行。
`lanes` **别手写 `lines`**——不给就按格高自动铺满（先按 56px 下限算容量、再把间距均分）。

**顺手修的模板缺陷**：`relation` 长标签在窄列溢出到相邻组（已按列宽折行、最多 2 行）；`timeline` 时段标签不折行会被 chip 切掉（已折行 + chip 高度自适应，短标签行为不变）。

**写模板/引擎代码时的教训**：用 heredoc + python 脚本批量改 `.html`/`.py` 时，`\n` 会被解成真换行、把字符串打断（`render_pptx.py` 和两个模板都中过，表现为 SyntaxError 或渲染卡在 `data-rendered`）。改完必须 `ast.parse` 校验 py、并实渲一次 html。

相关：[[reading-sheet-skill]]（架构与硬规则，其中「13 个模板」已过时）、[[reading-sheet-editable-pptx]]（加模板要同步加 RENDERERS）、[[reading-sheet-always-pptx]]。
