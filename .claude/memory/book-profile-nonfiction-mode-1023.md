---
name: book-profile-nonfiction-mode-1023
description: "非虚构书建档走同一个 book-profile skill 加 NONFICTION 模板,不另起 skill;节号与纯事实版对齐"
metadata:
  node_type: memory
  type: project
  originSessionId: a36e6b92-9f0a-417e-bffd-465f6ffc4f24
  modified: 2026-10-23T07:02:16.734Z
---

2026-10-23 用户问「一批非虚构书要优化 skill 还是新写一个」,定为:**在 laojohn-book-profile 里加 `assets/book-profile-NONFICTION.md` + SKILL「非虚构类建档适配」节,不另起 skill**。起因是《万物成长的故事》(稻垣荣洋,科普随笔)建档时撞上旧第3步「非叙事先停下问」。

**Why:** 产物同名同机读块(profile_meta.py 共用);通读/逐字/书内外/插图红线与体裁无关,另起 skill 必漂移;两个 skill 会抢「建档」触发;lesson-plan 早有「非虚构」判型列,缺的只是档案字段。

**How to apply:**
- 分流:叙事→FACTS-ONLY;**人物传记/纪实仍走 FACTS-ONLY**(变化线索=人生阶段);科普/知识/说明性→NONFICTION。
- **节号刻意不变**:四=关键片段(detail-review 按「档案第四节」核引文)、八主题词、九拓展、十插图;只换三(分节要点表+例证清单)、五(核心概念·数据·说明方法实例)、七(作者观点句与开放问题)。改模板勿动节号。
- 非虚构专属红线「照书不纠错」:书中科学说法不许用模型知识改、补、更新,可疑只标(待核实)。
- 下游已同步对应关系:lesson-plan SKILL/checklist/style-and-format、reading-assessment SKILL/dimension-rubric。

关联 [[book-profile-full-read-redline]]、[[low-grade-collection-profile-formalized]]。
