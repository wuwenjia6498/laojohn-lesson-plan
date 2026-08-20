---
name: writing-materials-tools-removed
description: 【已废止】写作课配套曾于2026-07-06/08两轮清空(历史记录)；后已按新方案重建，现状见 writing-materials-skill-student-bundle
metadata: 
  node_type: memory
  type: project
  originSessionId: 5f4cb6ec-6aba-493b-b009-a412d6ff6764
  modified: 2026-07-27T05:01:39.373Z
---

> ⚠ **已被推翻（2026-07 下旬重建完成），本文件仅存清空史实。** 写作课配套已按新方案独立重建：`laojohn-writing-materials`（学生/教师/家长三侧合订，见 [[writing-materials-skill-student-bundle]]）与 `laojohn-writing-package`（写作课整套打包）现均存在且可用，产物目录为 `写作课整套文件打包输出\`。**下文「How to apply」的"先说明已删除"话术不再适用**；仍然有效的仅两点——教学导图/招生图/学习指南至今未为写作课重建（要做需新设计），及「写作配套独立于读书会」的设计原则。

写作课下游配套曾分两轮清空（当时只剩详案 + 课件PPT链），其余配套待重新独立设计（独立于读书会）——**该状态已成历史，见顶部导流**。

**第一轮 2026-07-06：** 删除写作课三个配套物料生成工具——① `laojohn-writing-sheet` 整技能（写作学习单）；② `laojohn-course-poster` 写作模式（习作招生图）；③ `laojohn-reading-guide` 写作模式（写作学习指南）。

**第二轮 2026-07-08：** 按用户「除详案和课件外配套全删、后续重新独立设计」，把最后剩的教学导图及其编排/归集也拆了：
- `laojohn-teaching-mindmap`：删 `references/writing-mode.md` 整文件 + SKILL.md/data_schema.md 里的写作判型段落，教学导图**不再支持写作详案**（共用渲染引擎 render_pdf.py/template.html 课型无关、未动）。
- `laojohn-pipeline`：删「第 4b 步 · 写作课模式」整节 + description/边界的写作子句。
- `laojohn-course-package`：删 `package_course.py` 的 `WRITING_CATEGORIES` + `--mode` 参数（传 `--mode writing` 现直接 argparse 报错）+ SKILL.md 写作节；只剩读书会单模式。
- 存量产物 `教学思维导图\这儿真美_教学导图.{html,json,pdf}` 已删（读书会各书导图不动）。README 同步（删写作打包目录树、改 teaching-mindmap/pipeline/course-package 三行）。

**Why:** 用户要把写作课配套推倒重来、独立于读书会重设计；先清干净腾空。

**How to apply:**
- 用户再要写作课的教学导图/招生图/学习单/学习指南/一键全套/打包时，先说明这些写作配套已全部删除、需确认按新方案重建，别走旧 skill 的写作路径。
- **保留未动**：[[ppt-profile-seam-architecture]]（写作课 PPT 链，ppt-draft/ppt 写作 profile）、`laojohn-writing-lesson`（详案）、`laojohn-detail-review` 的写作判型/复盘（详案的审稿关口，非对外配套，用户明确保留）。
- 产物目录 `习作招生图输出\``写作学习单输出\``写作学习指南输出\``写作课打包输出\` 均已删/不再生成；CLAUDE.md 经确认无写作配套触点、未改。
