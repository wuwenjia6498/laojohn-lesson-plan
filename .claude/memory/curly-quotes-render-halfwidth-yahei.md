---
name: curly-quotes-render-halfwidth-yahei
description: 微软雅黑把弯引号“”‘’画成半角窄字形，HTML 物料要全角引号须用 @font-face unicode-range 让引号码位落宋体
metadata: 
  node_type: memory
  type: project
  originSessionId: 4d0df761-4da7-4476-94fb-11a4fb3b1faa
  modified: 2026-07-27T04:42:31.316Z
---

用户要求物料成品里的中文引号是**全角字形**。字符层面 U+201C/201D 已是标准中文弯引号（无单独全角码位），显示成半角是**微软雅黑的字形问题**。

**How to apply:** 在模板 CSS 加 `@font-face{font-family:"CJK Quotes";src:local("SimSun"),local("宋体");unicode-range:U+2018-2019,U+201C-201D;}` 并把 `"CJK Quotes"` 放字体栈首位——只有引号落宋体，其余文字不变。已修：course-poster `assets/template.html`（2026-07-27，提交 c5da4ee）。其他 HTML 渲染物料（reading-guide / book-card / 两导图 / writing-materials / picture-materials / reading-sheet）用雅黑字体栈的**大概率同病**，用户再提引号半角时照此修，别去改 JSON 字符。相关：[[json-materials-curly-quotes]]（字符层统一弯引号禁「」）。
