---
name: two-person-sync-three-channels-0820
description: 双人协作同步改三层通道（git/网盘/不同步），记忆迁入仓库靠目录联接；配一次后自动，联接断了不报错
metadata:
  type: project
---

2026-08-20 立。项目已交接给另一位同事（她的硬盘拷贝**带 `.git`**，两边本就是同一 GitHub 仓库 `wuwenjia6498/laojohn-lesson-plan` 的两份克隆——不必新建同步机制，缺的只是权限与纪律）。分工是**接力**：一人写粗稿、另一人审核优化，不同时改同一文件。

**三层通道**：① 源文件（md/json/py/skill/封面/图位 png）走 git；② 项目记忆走 git；③ 版权插图两个目录 + 外部生成的 `写作课件PPT输出\` 走网盘。渲染产物**哪层都不走，两边各自重渲**。

**关键手法＝Windows 目录联接（`mklink /J`，不需管理员权限）**——把仓库内的 memory、网盘上的大件「挂」回原本的位置，**项目内所有路径一个字都没改**，脚本与 `.gitignore` 规则照常生效（联接对 git 透明）。别因为「东西现在在网盘上」就去改脚本路径。

**记忆迁入仓库是本次最实质的改动**：原在 `C:\Users\<用户>\.claude\projects\<路径编码>\memory\`，完全在 git 之外，双机必然分叉——而记忆正是跨课次通则的载体，分叉＝两人各自把同一个坑重踩一遍。现事实源＝仓库 `.claude\memory\`，用户目录那份是联接。**`<路径编码>` 随盘符变**（D 盘＝`D--laojohn-lesson-plan`），同事那边要先 `robocopy /XC /XN /XO` 把她新增的记忆并进来再建联接，否则覆盖。

**三个不可推断的点**：
- **联接断了不报错**，表现只是 Claude Code「什么都不记得」；自检话术＝问「这个项目有哪些跨技能硬约束」。
- **`MEMORY.md` 与 `协作看板.md` 是仅有的高频冲突点**（两人都往里追加行）——冲突时两边新增的行都保留，不选边。
- **产物不同步会被误读成「同步坏了」**：对方审改后推上来的只有 `.md`，最新 docx 得自己重渲（必带 `--header-left/--header-right`）。

规则落点：`CLAUDE.md` §9（跨技能硬约束）、`docs\协作同步说明.md`（给人看的操作规程）、根 `协作看板.md`（接力状态表，commit 前缀 `[稿]`/`[审]`/`[定]`）。相关：[[bash-heredoc-file-writing-pitfalls]]、[[memory-index-structure-over-size-0818]]。
