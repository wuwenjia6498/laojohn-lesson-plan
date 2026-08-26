---
name: writing-line-filename-unit-segment
description: 2026-08-02 起写作课线全部产物的文件名/目录名在年级册后加「第N单元」段（中文数字），存量7篇已改名
metadata: 
  node_type: memory
  type: project
  originSessionId: 6756bef2-cb1f-40b4-a50f-7e7f6a3f58fa
  modified: 2026-08-02T02:14:14.383Z
---

写作课线（laojohn-writing-lesson 及其全部下游）的课次标识由 `<年级册>-<题目>` 改为 **`<年级册>-第N单元-<题目>`**，2026-08-02 用户拍板。单元号用**中文数字**、取 `writing-lesson/references/course-map.md` §三全表的「单元」列；不在教材单元序列的自拟主题省略该段（`三年级-写秋天的公园-写作课详案.md`）。

**Why:** 同一年级册下多篇习作并列时，只看年级+题目排不出教学顺序，也对不上教材单元。

**How to apply:**
- 详案 `写作课详案输出\三上-第一单元-猜猜他是谁-写作课详案.md`；配套/PPT/讲稿/中间稿/打包/教材插图的**子目录名与文件名前缀**同此口径；~~**PPT、讲稿的文件名内仍是纯题目**~~ **⚠ 这半条 2026-08-26 已被推翻**：PPT 文件名内也带课次标识段，现行 `<年级册>-第N单元-<题目>-课件PPT.pptx`（如 `三上-第六单元-这儿真美-课件PPT.pptx`），存量 12 份已迁移；讲稿已于 0803 停产。详见 [[writing-line-naming-flattened-0826]]。
- 口径已写进 CLAUDE.md §7、README 对照表、writing-lesson SKILL「输出形态」、course-map §三表头注；package_writing.py / render_*.py / insert_images_docx.py 均是文件名驱动，**无逻辑改动**（教材图 `name_from='stem'` 自动跟随新目录名，已用 `--check-only` 回归通过）。
- 存量 7 篇（三上一/二/三/四/六单元、三下第六单元、五下第八单元）连同 2 套配套/PPT/讲稿/中间稿/打包目录已全部改名（源文件走 git mv）。
- `variation-ledger.md` 里的篇目简称**有意未改**——指纹块按「册级+题目」字段记，不含文件名，改了无收益。
- 相关：[[writing-lesson-title-naming]]（文内标题与环节命名体例，与文件名口径是两件事）。
