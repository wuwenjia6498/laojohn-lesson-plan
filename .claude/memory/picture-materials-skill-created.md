---
name: picture-materials-skill-created
description: 看图写话配套物料 skill(laojohn-picture-materials)落地——四类课堂印刷件+首本二上第1次验证闭环
metadata: 
  node_type: memory
  type: project
  originSessionId: 754323ec-f6c8-4e0a-a2e7-5a33f9a4f3df
  modified: 2026-07-24T04:42:12.377Z
---

看图写话线原来只有详案+生图、无配套；2026-07-24 新建 `laojohn-picture-materials`（对齐 [[writing-materials-skill-student-bundle]] 的架构与品牌壳），把看图写话详案转成四类**扁平单件 A4 打印件**：

1. **支架小卡**（`render_cards.py`）：8 张/页 2×4 裁切；卡型数据驱动 `chips`(三素句结构条 谁→在哪里→做什么) / `quad`(细节四问 2×2 盒)。
2. **兜底纸条**（`render_slips.py`）：7 条/页竖排裁切；填空句式 `＿＿＿`(全角下划线≥2)→填空线；只发写不动的孩子。
3. **看图写话稿纸**（`render_sheet.py`）：本课锚图内联(`看图写话详案输出\<stem>\图位\锚-01.png`)+格子稿纸(复用 writing buildGrid 18列动态行)+写话格式提醒。
4. **教师家长页**（`render_teacher_parent.py`）：2页=P1教师速览(时间轴/过关判定/评价三级/下水例文/物料清单)+P2家长一页纸(一句话说清/好坏对照/好句本亲子任务/避开两件)。**家长页禁虚构学生作品**，只讲能力与怎么陪(区别于同步写作家长侧的成长反馈结构件)。

**关键架构**：渲染引擎单一源复用 writing-materials `scripts/_shared.py`——picture 的 `_shared.py` 是**薄 shim**(importlib 按路径以 `_shared_real` 之名载入，避同名 `_shared` 撞车循环导入；直接 `from _shared import *` 会自引用报错)。给单一源 `inject/render` 加了向后兼容可选参 `extra_images={token:图路径}`(稿纸锚图注入用)，已 CLAUDE §3 登记、回归 writing 三侧无差异。

**输出**：`看图写话配套输出\<详案stem>\`；命名 `<stem>-<物料名>_data.json`→`.html/.pdf`(json源入库、html/pdf已gitignore)。纯口头课(如一上会看)无当堂写作→只出卡+教师家长页，不出纸条/稿纸。

**状态**：首本 `二上（秋）第 1 次 · 方法课`《细节四问》四件全渲染闭环、目检品牌壳一致、锚图咬合(2026-07-24)。兜底纸条初渲溢出2页已压间距回单页。事实源锁详案(下水例文/兜底句式/过关判定逐字取)。其余存量课(一上第1次/二上第2次)未出配套。README/CLAUDE §3/gitignore 已改。
