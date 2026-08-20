---
name: context-engineering-slimdown-0727
description: 2026-07-27 上下文工程瘦身收官——CLAUDE.md/两SKILL/description/记忆索引全线收窄+坏记忆修复；新增三处下沉文件的落点与「单一位置」指针约定
metadata: 
  node_type: memory
  type: project
  originSessionId: bc7b5695-c8f2-4cba-8549-db99241ebecd
  modified: 2026-07-27T08:41:28.377Z
---

2026-07-27 按 Anthropic《context engineering for Claude 5》思路做了全仓上下文优化（用户逐项拍板）。**改动落点（后续别把内容抄回上级文件）**：

- **CLAUDE.md 12,047→10,070 字符**：PPT profile 实现细节下沉 `laojohn-ppt/references/architecture.md`（§3 只留接缝原则）；首页形态/命名体例/交付双道工序压成硬线+指针；游离条目编为 §5；与 README 六处双写收敛（README 规则段一律指针化）。
- **laojohn-picture-writing/SKILL.md 17,767→9,489**：详案骨架与三区提纲表细则下沉 `references/lesson-structure.md` **§16**（新增节，细则唯一源）；自动生图闭环下沉新建 `references/imggen-pipeline.md`；衔接课 6 条生成规则**留在 SKILL.md**（course-map.md 明文指它为唯一源）；语言风格（去游戏化）块也留 SKILL.md（lesson-structure 文首指它为源）。
- **laojohn-ppt/SKILL.md 8,512→3,031**：新建 `references/` 三件——`page-contract.md`（中间稿契约唯一源）、`visual-variants.md`（视觉/动画/故障排查唯一源）、`architecture.md`。
- **盘符/环境警告全仓指针化**：各 SKILL 的「Cursor 工作区路径」变体全部改为一句「见根 CLAUDE.md §1」；命令示例 `python3`→`python` 清零；references/rendering.md 三处「/opt/pw-browsers」旧口径改本机路径。
- **PLAYWRIGHT_BROWSERS_PATH 已根治（2026-07-27 收尾）**：poster/teaching-mindmap/reading-guide 三个 render_pdf 的 `setdefault("/opt/pw-browsers")` 已改为 Windows 本机回退（`~/AppData/Local/ms-playwright`，与 reading-sheet render.py 同款），三线均在**不设环境变量**下用「洞」的存量 JSON 回归通过。现行口径＝**一般无需 export**，环境变量仍可覆盖脚本缺省值；CLAUDE.md §1 与 pipeline SKILL 已同步简化。
- **description 合计 5,375→3,753 字符**（13 个 >250 的压到 150~200，保留触发短语+边界区分句）。
- **MEMORY.md 索引 11,660→9,847**：钩子压到一句触发提示；结构性下限约 7k（113 个链接文本本身的开销），别再追求 6k。
- **坏记忆已修**：writing-materials-tools-removed 标废止导流；reading-sheet-skill 13→18 模板+目录名；antihomogenization 12/11→指向 14 字段；24-stages-v6 指针改指 course-map-v4；core-literacy-goals「学生带走」→「学习目标」。

- **深度档已收口（2026-07-27 第二轮，用户拍板只做三切口、其余明确关闭不再提）**：① ppt-draft「输出契约」§3~§6 与 `laojohn-ppt/references/page-contract.md` 的双写已收敛（契约细节指针化，生成端口径留 field-extraction）；② reading-sheet「如何加第N种模板」下沉新建 `references/template-extension.md`；③ writing-lesson「批次横审」下沉 `references/variation-ledger.md` §四（pools/archetype-decision 的旧指向已同步改）。**明确不做**：弯引号/真实性 30+ 文件全面指针化（重复都在审校期加载的 checklist/rubric，本就符合渐进披露）；writing-lesson 工作流/核心约束压缩（其 references 全部每次必读，挪动零 token 收益，摘要有防违规回潮作用）；每次必用的内容（ppt-draft 自检清单、reading-sheet 模板登记表）不挪——**判据：挪进 references 只对「非每次必读」的内容省 token**。

**Why:** 每会话固定成本约 1.6 万 token 且存在互相矛盾的口径；病灶是「坏」不是「大」。

**How to apply:** ① 新增/改 skill 时，路径与环境警告只写一句指向 CLAUDE.md §1 的指针，禁再抄出变体；② 改上述下沉文件（architecture/page-contract/visual-variants/imggen-pipeline/lesson-structure §16）时直接改它们，别回填 SKILL.md 或 CLAUDE.md；③ 两个残留 zip 已经用户确认删除（2026-07-27）。相关 [[bookclub-materials-dir-consolidation]] [[ppt-profile-seam-architecture]]
