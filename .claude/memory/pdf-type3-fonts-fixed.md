---
name: pdf-type3-fonts-fixed
description: "配套PDF的Type3字体病=雅黑字表外字符触发系统回退;已修写作+看图写话两线并装机检,阅读单线18份遗留未修"
metadata: 
  node_type: memory
  type: project
  originSessionId: c0e8a850-0a20-401d-9a70-ef388388ab03
  modified: 2026-08-17T03:16:42.416Z
---

2026-08-17：用户报「同步写作配套 PDF 在 WPS/福昕里提示 TYPE3 字体不支持编辑」。已修完写作线 + 看图写话线（用户拍板两线一起 + 存量全部重渲）。

**根因**（实测，非推测）：模板/data.json 里用了**微软雅黑字表外的字符**——🏠 U+1F3E0、✍ U+270D、✕ U+2715、∨ U+2228——Chromium 打印时走系统回退字体（SimSun / Segoe UI Symbol / Segoe UI Emoji），**为每个字形现造一个 Type3 字体**（无 FontDescriptor、Differences 里几十个位置全填 /g0 只有一个真字形）。PDF 编辑器一律拒编 Type3。**正文中文没问题**——雅黑走 Type0+FontFile2 子集嵌入，可编。

**修法（已落地，勿回退）**：
- 装饰图标（🏠 ✍）→ **纯 CSS 图形**（`content:""` + width/height/background），不是换个 emoji——彩色 emoji 换哪个都走 Segoe UI Emoji 的 COLR 路径再变 Type3。样板：模板里既有的 `.sech::before`、`.legend .dot`。
- 功能符号 → 换雅黑覆盖内的等价字符：`✕`→`×`（U+00D7）。
- `.mark .sym` 字体栈中间插一档 `"Microsoft YaHei"`（`"Courier New","Microsoft YaHei",monospace`）：逐字符回退，Courier New 缺的（∨、data 层塞进来的汉字「改」）兜到雅黑而非系统回退。**勿删中间那档**。
- **机检 `_shared.check_type3`**：每次 render 自动扫 PDF、按 /ToUnicode 反查并报出具体字符。这是长期防线——data.json 随时可能再带进新符号，人眼看 PDF 发现不了。

**遗留未修**：`读书会阅读单输出\` 18 份含 Type3（`↔` 从详案文本流入标题、`✏` 在 `reading-sheet\templates\template_writing.html`）。属读书会线、另一套引擎（`reading-sheet\scripts\render.py`），本次用户未圈进范围。同法可修。

**可复用诊断手法**：`pikepdf` 遍历页 `/Resources /Font` 挑 `/Subtype == /Type3`，`/ToUnicode` 的 bfchar 反查字符；**FontMatrix 就是 1/upem 指纹**——`1/256`→SimSun 系，`1/2048`→Segoe 系；Type3 里出现 `PatternType 2` 渐变 XObject＝彩色 emoji 的 COLRv1 被展平。全仓对照很有用：`读书会配套输出\`（reading-guide/两导图）历来 0 个 Type3，证明这不是 Chromium 通病而是模板选字的问题。

相关：[[curly-quotes-render-halfwidth-yahei]]、[[downstream-shared-layer-and-token-facts]]
