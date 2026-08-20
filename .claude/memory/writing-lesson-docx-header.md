---
name: writing-lesson-docx-header
description: 写作课docx页眉定版「老约翰·同步习作／写清楚·写生动·有章法」，导出必带参数否则回落读书会页眉
metadata: 
  node_type: memory
  type: project
  originSessionId: 0df2ac86-709d-47f4-a675-2760a3f8bb7f
  modified: 2026-08-03T04:22:57.839Z
---

2026-07-21 用户定版：同步习作 docx 页眉 = 左「老约翰·同步习作」／右「写清楚·写生动·有章法」。

经共享 docx 引擎的**课型无关可选参数** `--header-left/--header-right` 传入（引擎本就支持，无需改引擎）：

```
PYTHONUTF8=1 python ../laojohn-lesson-plan/assets/md_to_laojohn_docx.py 详案.md \
  --header-left "老约翰·同步习作" --header-right "写清楚·写生动·有章法"
```

**漏传即静默回落成读书会页眉「老约翰深度阅读／阅读·思辨·表达」**——这是写作课导出最易犯的错，已写进 SKILL 第 8 步与 CLAUDE.md §3 引擎行。三条线的页眉口径：读书会（缺省）／看图写话「老约翰·看图写话／从看懂一幅图，到写成一个故事」／同步习作（本条）。

**How to apply**：存量 5 篇已按新页眉重渲。同批顺手回改了两篇源 md 的中文语境半角标点（续写故事 12 处、漫画的启示 28 处）——引擎只是渲染时兜底转全角，源 md 仍是半角，`fullwidth_punct` 可直接 import 来批修。

**⚠ 但半角标点警告要先看落点再动手（2026-08-03 实测）**：导出时若警告数恰好≈指纹块字段行数（如动物园 17 处），八成全落在文末 `<!-- VARIATION-FINGERPRINT -->` 里的 `册级: 四上` 这类**字段名半角冒号**上——那是 variation-ledger 台账重建的机读契约，且注释块根本不进 docx，**属误报，改了反而弄坏台账**。判断法：`re.compile(r'[一-龥][,:?!;()]|[,:?!;()][一-龥]')` 扫一遍看行号，落在指纹块（文件末尾注释区）的一律不改，只改正文里的。同族误报见 [[picture-writing-1a-lesson3-state]]（imgspec 字段）。

另：**PowerShell 里带弯引号的文件名不能直接写进命令行**——`“动物园”` 会被 PS 当成字符串定界符，路径在 `小小` 处截断报 FileNotFoundError；用 `$md = (Get-ChildItem 目录 -Filter '四上-*动物园*.md').FullName` 取到再传变量。

相关 [[writing-lesson-front-page-two-zones]]
