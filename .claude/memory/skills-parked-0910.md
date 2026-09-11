---
name: skills-parked-0910
description: 2026-09-10 曾把读书会 11 个＋看图写话 3 个 skill 停用归档到 skills-parked，09-11 评估后全部移回并删目录——省 token 微乎其微且误触发方向反，别再重做
metadata:
  type: project
---

**⚠ 2026-09-11 已撤回**：用户问「有必要吗」，按账评估——14 条 description 合计 2,782 字符 ≈ 2k token，占常驻约 8%、占 1M 窗口 0.2%；代价是 CLAUDE.md 多一条特殊路径口径、恢复要移目录＋提交＋双机拉取，且误触发方向反了（说「做个书目卡」时没有 laojohn skill 可接，易落到官方 docx/pptx skill 或即兴凑）；0727 那轮压 description 后 22 个并存一个半月无撞车记录。故 14 个整目录 `git mv` 回 `.claude/skills/`，`skills-parked/` 连 README 一并删除。**别再为省 token 停用 skill**——SKILL 正文与 references 本就触发才加载，停用只动 description 那一层。三处遗留保留不改（无害）：`tone_gate.py`／`imgclient.py`／`detail-review/SKILL.md` 的两处查找，`.gitignore` 的 `skills*` 通配。以下为 0910 立时的原记录。

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
