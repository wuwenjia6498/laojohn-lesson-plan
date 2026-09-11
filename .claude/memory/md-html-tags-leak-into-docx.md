---
name: md-html-tags-leak-into-docx
description: 详案 md 里的 HTML 样式标签（mark/b/u/span）与单星斜体会被 docx 引擎原样印进成品；《格列佛》详案曾泄漏两处；行内强调只用成对 **
metadata:
  type: feedback
---

docx 引擎 `md_to_laojohn_docx.py` 不解析 HTML 样式标签，`<mark>…</mark>`、`<b>`、`<u>`、`<span>` 会一字不差印进 docx；单星/单下划线斜体 `*…*`、`_…_` 同样不解析、星号原样泄漏。《格列佛游记》详案曾用 `<mark>` 做「下节课再议」高亮，成品泄漏两处才发现。

**Why：** 引擎只认成对 `**…**`（转真实加粗，未配对残余自动剥除）、表格换行 `<br>`、整块跳过的注释 `<!-- -->`；此外一律透传。

**How to apply：** 行内强调只用成对 `**`；伏笔、提醒用文字直说，不靠视觉高亮。交付前检索 `<mark>`／`<b>`／`<u>`／`<span>` 与单星应零命中（writing-lesson 连整行 `**` 也不用，见 CLAUDE.md §4）。规则本体在 CLAUDE.md §4「行内强调克制」。
