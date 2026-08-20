---
name: downstream-shared-layer-and-token-facts
description: "读书会六件下游物料已抽三条共享层(2026-07-28);并实测「合并skill省token」不成立——skill只占常驻19%,MEMORY.md已无压缩空间"
metadata: 
  node_type: memory
  type: project
  originSessionId: 7a266031-4b44-4bfb-b757-1b84a64ac7e0
  modified: 2026-07-28T11:37:32.415Z
---

2026-07-28 用户问「20多个SKILL费token,能不能把读书会下游物料合成一个」。实测后**否决合并、改抽共享层**。

## 一、token 账（别再重算一遍）

常驻上下文只有三块：`MEMORY.md` ~10.3k 字符 + `CLAUDE.md` ~10k + **21 个 skill 的 description 合计 4,754**（skill 只占 19%）。
**SKILL.md 正文与 references 按需加载、不常驻**——所以「skill 多＝费 token」只在 description 那一层成立。

六件下游物料 description 合计仅 889 字符，合并后仍需一条 ~250 的，**净省约 640 字符≈600 token＝常驻的 2.5%**；代价却是：正文合计 33.5k 一次读进（出一张书目卡原本只加载 2.3k）、6 条精准触发词表挤成一条、约 60 处按名引用要改、**6 套模板脚本一份都省不掉**。「一个入口」的需求 `laojohn-pipeline` 早已满足。

**同理 `MEMORY.md` 也压不动**：117 条压在 10.3k 里、平均每条 88 字符，本次试着合并 4 条已废止/已覆盖的索引行，结果**净增 43 字符**（因为要保留「哪些内容仍有效」的提示）。想减字符就必须丢信息，别再尝试。

## 二、真正做了的：三条共享层（真源＋importlib 薄壳）

六件物料此前**脚本零共享、全是 fork**（项目其余线早已按 CLAUDE.md §3 做了单一源，只剩这一片）。已抽：

| 真源 | 用它的 |
|---|---|
| `book-profile\scripts\profile_meta.py` | book-card、course-poster 的 `extract_fields.py`（机读块格式归 book-profile 定义，故解析器也归它） |
| `book-card\scripts\_jpg_render.py` | book-card、course-poster 的渲染 |
| `reading-guide\scripts\_a4_render.py` | reading-guide、两种 mindmap 的 `render_pdf.py` |

**口径差异一律参数化、不要为了「统一」改默认值**：`strip_parens`（卡 True／海报 False）、`fallback`（卡留空／海报占位图）、`recenter_on_overflow`（**两种导图都传 True**，阅读指南 False）。
薄壳按 `parents[2]` 相对定位真源，**改 skill 目录名会静默断链**。

SKILL.md 侧另建 `pipeline\references\downstream-common.md` 承载六家通用纪律（此前各存一份、共约 7.3k 重复），六份 SKILL.md 只留独有部分。

## 三、回归方法（下次改这三件真源照做）

基准数据＝`读书会配套输出\俗世奇人\` 下五份 json（真实生产数据，比 skill 里的 evals 样张更好）。

- **PDF 的 md5 不可比**——Chromium 写入时间戳，同一脚本连跑两次 md5 都不同；**比字节数**（俗世奇人：阅读指南 186205 / 抢先看 131628 / 教学导图 189747）。
- **HTML 与 JPG 可比 md5**，应 bit-identical。
- 用 `git show HEAD:<path>` 取改动前脚本跑一遍做 A/B，比自己肉眼 diff 可靠（本次 8 本书×2 脚本＝16 份 json 全 identical）。
- 跑之前**不要**设 `PLAYWRIGHT_BROWSERS_PATH`，正好验证脚本内 setdefault 回退。

## 四、顺带修掉的既有缺陷

`course-feedback` 整块缺 YAML frontmatter（description 一直是文件名兜底句，触发力弱）；`lesson-mindmap` 的 `render_pdf.py` 是 0727「三渲染脚本根治」的**漏网**（仍留 `/opt/pw-browsers` 分支）；`lesson-mindmap\SKILL.md` 悬空引用 teaching 侧的 `evals/sushiqiren_extracted.json`；`reading-guide` 有硬编码盘符的一次性脚本与重复实现的 `render_win.py`（均已删）；`render_poster.py` 的占位二维码写死 `/tmp`（Windows 必崩）；`teaching-mindmap` 要求缺失填「待补」，与 CLAUDE.md §2「待补充绝不进对外物料」冲突（已改为整条不列）。

> 另注：`.pyc` **并未**入库（`.gitignore` 早有 `__pycache__/`），子 agent 报告的「已入库」是误判——**子 agent 的结论要抽样核实**。
