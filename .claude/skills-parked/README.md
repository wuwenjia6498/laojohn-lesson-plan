# skills-parked · 停用归档的 skill（2026-09-10 立）

本目录存放**暂时停用**的 skill。Claude Code 只加载 `.claude/skills/` 一级子目录，放在这里的不会进上下文、也不会被触发。**目录内部一律未改动**，恢复＝整目录移回。

## 为什么停用

近一个月两位协作者全在同步习作（写作课）线上工作，读书会/看图写话两线产物自 2026-08-18 起未动。22 个 skill 全部装进每次会话，14 条不相干的描述只增噪音、且加剧与官方 pptx/docx skill 的触发词撞车。

## 停用清单（14）

读书会线 11：`laojohn-book-profile` `laojohn-book-card` `laojohn-course-poster` `laojohn-course-feedback` `laojohn-course-package` `laojohn-lesson-mindmap` `laojohn-teaching-mindmap` `laojohn-reading-guide` `laojohn-reading-sheet` `laojohn-reading-assessment` `laojohn-pipeline`

看图写话线 3：`laojohn-picture-writing` `laojohn-picture-materials` `laojohn-picture-package`

## 两个读书会线 skill **没有**停用（写作线硬依赖，禁止移进来）

- `laojohn-lesson-plan`：`assets\` 是 docx 引擎三件套（`md_to_laojohn_docx.py` / `style_front_page.py` / `insert_images_docx.py` / `docx_backfill.py`），写作课出 docx 与 laojohn-ppt 后处理链第 5 步全靠它。
- `laojohn-ppt-draft`：`scripts\pageback_annotate.py` 是 PPT 后处理链第 4 步执行体；`references\writing-mode.md` 是写作页型唯一源。

## 停用期间的注意事项

- 这里各 skill 的 `SKILL.md` / `references\` 里写的 `.claude/skills/laojohn-xxx/...` 命令路径**全部陈旧**，恢复前不要照抄跑。
- 读书会线内部的 importlib 链（book-card→book-profile、course-poster→book-card、两导图→reading-guide）走 `parents[2]/<同级 skill 名>`，整组同在本目录下相对关系不变、不断；`laojohn-picture-materials` 的 `_shared.py` 与 `laojohn-picture-writing` 的 `insert_images_docx.py` 两个薄壳指向仍在 `skills/` 的真源，**停用期间断链、移回即复原**，故不改。
- 活线侧四处指向本目录 skill 的引用已改成「`skills/` 与 `skills-parked/` 两处都找」，恢复时不需改回：根 `tone_gate.py`（`_skill_path`）、`课件配图工具\scripts\imgclient.py`（密钥回退路径）、`laojohn-detail-review\SKILL.md`（判型表下注）、本地 `Z日常工作文件\_build_notice_jpg.py`。
- `.gitignore` 里针对 `laojohn-picture-writing/assets/` 的 5 条规则已改为 `.claude/skills*/...`，两处同时生效。**在这里新增会被 ignore 的目录时，同样用 `skills*` 写法。**

## 恢复口令（单个或整批）

```powershell
Move-Item .claude\skills-parked\laojohn-book-profile .claude\skills\laojohn-book-profile
git add -A .claude/skills .claude/skills-parked
git commit -m "[定] 恢复 laojohn-book-profile 到 .claude/skills"
```

整批恢复就对 14 个各跑一遍 `Move-Item`。移回后本 README 若清空即可整目录删除。
