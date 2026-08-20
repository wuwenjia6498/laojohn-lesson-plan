---
name: picture-writing-detail-dir-per-lesson
description: 看图写话详案输出改「一课次一目录」（2026-08-03）：四件收进课次夹、图位路径未变、image_dir 带旧布局回落
metadata: 
  node_type: memory
  type: project
  originSessionId: 9152d4c1-a113-40b2-80a6-fc43dae1440c
  modified: 2026-08-03T08:19:31.843Z
---

2026-08-03 起，`看图写话详案输出\` 从「四件平铺顶层 + 同名子夹只装图」的混合布局，改为**一课次一目录**：`看图写话详案输出\<课次>\` 里同住 md、docx、`-配图.docx`、`-生图提示词.txt` 与 `图位\`，目录名＝文件 stem，顶层不再有任何散文件。存量 4 个课次已迁完（md 走 git mv）。

三件不看代码想不到的事：

1. **`图位\` 的完整路径一个字没变**——迁移前后都是 `看图写话详案输出\<课次>\图位\`，因为课次夹本来就在。所以存量配套稿纸 `_data.json` 的 `anchor_img`、`package_picture.py` 的课堂用图 glob、冷审 rubric 的核图路径**全部没动过**。判断这次改动的影响面时别把它们算进去。

2. **代码只改了一处**：`picture-writing/scripts/imgspec_parser.py` 的 `image_dir()`（全链唯一图位路径真源，generate_images 与 insert_images_docx 都调它）。`-生图提示词.txt` 与 `-配图.docx` 是「与 md 并排」派生的，**自动跟着进目录、无需改**。

3. **`image_dir()` 里的旧布局回落分支不可删**——`.claude/skills/laojohn-picture-writing/_临时_角色定妆\` 仍是旧平铺布局（md 与同名子夹并排），去掉回落它会静默找不到图、不报错。判定顺序是「同名子夹里的 `图位\` 存在就用它，否则用 md 同级 `图位\`」。

`package_picture.py` 侧同步改了四条详案模板（各加一层 `{unit}/`）与 `list_available()`（从 glob `*.md` 改成枚举「装着同名 md 的子目录」，`_评估\` 这类非课次目录因此自动排除）。

相关：[[picture-writing-title-naming]]（课次 stem 的命名口径）、[[bookclub-materials-dir-consolidation]]（上一轮目录口径大改名）、[[picture-writing-1a-lesson3-state]]（本次回归样本，docx「半角标点 62 处」警告仍是误报勿改）。
