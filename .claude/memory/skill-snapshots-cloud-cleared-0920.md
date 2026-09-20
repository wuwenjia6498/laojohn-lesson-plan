---
name: skill-snapshots-cloud-cleared-0920
description: claude.ai 旧 skill 快照已于 2026-09-20 手动删净，重名冲突根除；CLAUDE.md §5 那段警告已作废并压缩
metadata:
  type: project
---

2026-09-20 用户在 claude.ai 的 Skills 页手动删除，**问题永久解决**，CLAUDE.md §5 那约 3,800 字节的警告块同日压成一条（只留 polish 那条现行约束）。

## 曾经是什么问题（留作复发时的判据）

2026-06 上传到 claude.ai 的三份 skill 快照（`laojohn-writing-lesson` 06-12／`laojohn-lesson-plan` 06-08／`laojohn-lesson-mindmap` 06-06），经账号级同步落回本机 `C:\Users\<用户>\.claude\skills\synced\<同步 id>\`，在会话里带 `anthropic-skills:` 前缀出现，与项目版**并存而非覆盖**，选哪个全凭模型读 description 自选，**而旧快照的触发面反而更宽**。

内容冻结在 06 月、此后从未跟着项目演进：写作课那份项目版 32,902 字节／16 份 references，旧快照仅 7,277 字节／4 份 references；且**冲突是方向性的**——旧快照带「先导红线」明令禁止引单元课文，而现行规则要求「匹配则引」（见 [[writing-lesson-cite-unit-text-0821]]）。

⚠ **误用自查点（若日后再往 claude.ai 传 skill，这条仍然管用）**：产物落到 `写作课输出\` 而非 `写作课详案输出\`，或文件名缺 `-第N单元-` 段——**命中即停手重做**。旧快照产出的详案结构上看着完全正常（同样两节连排 45 分钟、同样有作前作中作后与教师示范文），不盯路径不会当场发现，往往要到出配套或打包才炸。

## 现状（2026-09-20 核实）

云端「Created by you」只剩 `laojohn-lesson-polish`（网页端常用，有意保留）；本机 `synced\` 同步清单＝docs／docx／import-memory／laojohn-lesson-polish／morning／pdf／pptx／skill-creator／xlsx。
`laojohn-daily-post`、`picture-book-recommend` 用户一并手动删除（**有意为之，不是误删**）——CLAUDE.md 旧文里「务必保留这两个」的叮嘱随之作废。

## 仍然有效的防线（与删不删云端无关）

新窗口用斜杠命令 `/laojohn-writing-lesson` 显式点名，不靠自然语言让模型自选。官方 `docx`/`pptx`/`xlsx`/`pdf` skill 的作用域限制（只许读改外部文件、禁止新建本仓产物）是**另一条独立规则**，仍在 CLAUDE.md §5，未受本次影响。
