---
name: picture-writing-cold-review-wired
description: 看图写话已接入 detail-review 冷审（补了第三份 review-rubric）；附生图验收链两个长期缺陷的修复
metadata: 
  node_type: memory
  type: project
  originSessionId: aeca672b-5266-41b7-99d0-08bb0f7d5717
  modified: 2026-07-19T16:22:49.075Z
---

2026-07-20 补齐。起因：用户问"现在走的冷审是哪套代码"——查出我上一轮**根本没走 `laojohn-detail-review`**，而是派通用 agent + 临场手写 prompt。原因是结构上接不上：detail-review 自身不含判据，全靠"判型 → 加载对应 skill 的 `review-rubric.md`"，而 picture-writing **没有 rubric**，判型表也只有两类。

**已接通**：新建 `laojohn-picture-writing/references/review-rubric.md`（150 行，与另两份 137/144 同量级）。五维＝① 时间安排与装载量（双向）② 逐字稿可执行性 ③ **图位与正文的咬合**（本技能特有、优先级最高）④ 阶位与训练点兑现 ⑤ 支架分层与评价的真实性。每维带强制算式/清单，并内嵌上一轮的真实命中做范例。detail-review 判型表加第三行（**辨识信号＝正文有 `【图位:` 或文末有 imgspec 块**，另两类都不含）；picture-writing SKILL 补第 7 步冷审；CLAUDE.md 同步为三份 rubric。

**事实核对源与另两类结构性不同**：看图写话不是书籍档案，而是「图位规格的必须可见元素清单＋curriculum-archive＋course-map」三处。

**分流特例（血的教训）**：**改图位规格不算无争议项**——规格是已生成真图的验收依据，改了就可能让「真图＝规格＝正文」失配。要么进 B 块，要么改完立即回验真图。

**端到端验证通过**：fresh agent 只给路径就自行判型、加载新 rubric、**自发做出师话计数表与图位对照表**，并逮到我漏掉的：文末支架说明"到期2 加什么时候"（实为期4）、例-04 参考句"大声读书"越清单、**例-02 真图与正文彻底失配**（规格写"操场上拍皮球"，真图是公园里两人合抱带兔耳把手的大跳跳球＋滑梯）——我上轮只核了 3 张图，它逐张核。已按"改文字就图"修正。

**顺带修掉生图验收链两个长期缺陷**：
1. `generate_images.py` **无条件重生并覆盖已有图**，没有"图已存在则跳过"。用户要"重跑验收"若照跑就会毁掉已核准的图 → 新增 **`--verify-only`**（复用 `verify_image`，attempts=0、绝不覆盖）。
2. `imgspec_parser` 解析了例库图的 `验收:` 字段却**从未进入验收项**（items 只取支持句式/一句话画面）——规格里收紧的条款一直只是给人看的，**例-02 的失配正是这样漏过去的**。已加 `accept` property 并纳入 items（`process_library` 与 `verify_only` 两处）。修后回验 5/5 过，"妈妈须可见""须能指认单独一个孩子""须能一眼数清两个人"三条才第一次被机器验到。

另修 `course-map.md` 期2 锚点与 `curriculum-archive.md` 1A-8 打架（《小兔运南瓜》主锚在期1，期2 加注只承其口头讲述形态）。期1 现为方法课 15/10/5/15＋15/15/15，师话 65；course-map 的"期1 练习课"仍待另排（已在详案自检注明）。

相关 [[picture-writing-legacy-extraction]]、[[detail-review-cold-start]]、[[review-rubric-single-source-dedup]]、[[picture-writing-24-stages-v6]]。
