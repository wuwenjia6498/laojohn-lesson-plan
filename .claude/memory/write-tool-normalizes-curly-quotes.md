---
name: write-tool-normalizes-curly-quotes
description: 生成详案 .md 后必跑 fix_quotes，因 Write 工具会把弯引号规范化成 ASCII 直引号
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 4a78c8ad-d538-4f6c-b69f-de7a6aaeed84
  modified: 2026-08-07T14:18:44.274Z
---

用 Write 工具新建/覆盖详案 .md 时，输入的全角弯引号 “”/‘’ 会被规范化（吞）成 ASCII 直引号 `"`/`'`——即便我本意写的是弯引号，落盘后仍是 0x22/0x27（实测一份新稿 150 个双引号全是 ASCII、且弯直混排）。

**Why:** lesson-plan / writing-lesson 详案有「正文一律弯引号、ASCII 直引号为零」的硬规则；若以为 Write 已写对而跳过校验，docx 引擎的交替式安全网对跨行/奇数/弯直混排会判错方向，不可托底。

**How to apply:** 生成或编辑详案 .md 后，不要假设弯引号已正确——立刻用根目录 `fix_quotes_md.py` 的 `smart_quotes_line` 逐行转换（先把残留弯引号归一为 ASCII，再逐行交替转回），然后 Python 精确核验 ASCII 残留为 0、弯引号左右成对。这一步对「初稿生成」和「后续局部增改」都要做，不只在导出 docx 前。同理，对含引号的段落做 Edit 时，old_string 用弯引号会因规范化匹配失败——改用无引号锚点，或先把全文弯引号归一为 ASCII 再用 ASCII 引号匹配、改完统一转回。参见 CLAUDE.md §4 弯引号铁律与 [[style-redline-covers-edits]]。

**⚠ 嵌套引号是 fix_quotes 的盲区（2026-08-07 建档克雷洛夫寓言时实测）：** `smart_quotes_line` 是**逐行按奇偶交替**转换的，所以凡「引用一段本身就带引号的原文」——外层引用引号 + 原文自带引号——转出来必然错位（实测图单三行出现左3右2、左3右4、左7右8）。**别用 『』 替换内层引号去回避**，那违反建档 SKILL 的「保留原书弯引号原样照录、不得为避免嵌套改写内层引号」逐字红线。**正解：这类段落不加外层引用引号**，改用「原文照录：」「（原文照录·内含一处原书引号）」之类的文字引导，让原文自带的引号成为该行唯一的一层。跑完 fix_quotes 后再逐行核 `line.count('“') != line.count('”')`——跨行长引文（首行开、次行闭）会正常报一处不配对，属预期，其余都得查。
