---
name: skills-parked-0910
description: 2026-09-10 起读书会 11 个＋看图写话 3 个 skill 停用归档到 .claude/skills-parked/，lesson-plan 与 ppt-draft 因写作线硬依赖留下；恢复=整目录移回
metadata:
  type: project
---

**事实**：2026-09-10 用户拍板，写作线专注期把读书会线 11 个（book-profile / book-card / course-poster / course-feedback / course-package / lesson-mindmap / teaching-mindmap / reading-guide / reading-sheet / reading-assessment / pipeline）＋看图写话线 3 个（picture-writing / picture-materials / picture-package）skill 整目录移到 `.claude/skills-parked/`，已提交进 git 同步给协作者。加载中的 skill 从 22 降到 8。

**两个读书会线 skill 没停、也不许停**：`laojohn-lesson-plan`（`assets/` docx 引擎三件套，写作课出 docx 与 PPT 链第 5 步全靠它）、`laojohn-ppt-draft`（`pageback_annotate.py` 是 PPT 链第 4 步执行体，`writing-mode.md` 是写作页型唯一源）。

**Why**：14 条不相干的 skill 描述每次会话都占上下文，且加剧与官方 pptx/docx skill 的触发词撞车；两线产物自 08-18 起没动。

**How to apply**：
- 用户要做读书会/看图写话任务时，先按 `.claude/skills-parked/README.md` 口令把对应 skill 移回 `.claude/skills/` 并提交，再干活；停用件目录内部一字未改。
- 停用件 `SKILL.md` 里的 `.claude/skills/...` 命令路径停用期间全部陈旧，别照抄跑。
- 活线侧四处引用已改「两处都找」（`tone_gate.py` 的 `_skill_path`、`imgclient.py` 密钥回退、`detail-review/SKILL.md` 判型表下注、本地 `_build_notice_jpg.py`），恢复时不需改回。
- `.gitignore` 里 `laojohn-picture-writing/assets/` 五条规则已改 `.claude/skills*/...`；再给两处任一新增 ignore 目录，同样用 `skills*` 写法。
- picture-materials 与 picture-writing 两个薄壳指向仍在 `skills/` 的真源，停用期间断链属预期、移回即复原。
- 关联：[[two-person-sync-0820]]、[[downstream-shared-layer-and-token-facts]]
