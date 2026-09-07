---
name: writing-materials-richtext-field-scope
description: 配套三侧 data.json 里 {b}/{hl} 富文本标记只有部分字段解析，写错的字段会把标记原样印进 PDF，且三道机检全部抓不到、只有目检能发现
metadata:
  type: project
---

2026-09-07（五上四《二十年后的家乡》三侧配套实做时踩到）。

`laojohn-writing-materials` 三侧模板里，**不是每个字段都走 `rich()`**——有些字段用 `textContent` 直接塞，
写进去的 `{b}…{/b}` 会被当普通文字，**在 PDF 里印成 `(b)…(/b)`**（尖括号被 esc 掉了，所以是圆括号形态）。

本次踩到两处：**教师侧 `overview.materials[]`**、**家长侧 `onepager.oneline`**。
判断方法只有一条：**动手前 grep 模板里的 `rich(` 与 `textContent`**，看目标字段落在哪一边；
`references/data_schema*.md` 的字段注释里标了 `{b}` 的才支持，没标的就是纯文本，注释是准的、我没照着看才写错。

⚠ **三道自检全部抓不到这个错**：`_shared.py` 的溢出检查、pypdf 页数核验、`check_type3` 字体机检——
标记泄漏既不改变页数也不换字体，全绿照样错。**只有目检 / 从 PDF 提文本正则扫 `\(/?b\)` 才发现**。
渲染完顺手扫一遍，成本极低：

    from pypdf import PdfReader; import re
    t = "".join(p.extract_text() for p in PdfReader(f).pages)
    re.findall(r"\(/?b\)|\{/?b\}|\{/?hl\}", t)   # 非空即泄漏

同族：[[json-materials-curly-quotes]]（弯引号纪律）、[[pdf-type3-fonts-fixed]]（字体机检）。
