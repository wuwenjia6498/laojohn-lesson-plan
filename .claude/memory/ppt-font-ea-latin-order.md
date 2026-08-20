---
name: ppt-font-ea-latin-order
description: PPT 中文显示成 Calibri 的根因——OOXML 字体槽 latin 必须在 ea 之前
metadata: 
  node_type: memory
  type: project
  originSessionId: 4acc5a7a-8e3e-46f2-b719-101450c6b4e6
---

PPT 在本地打开「所有字体显示 Calibri」的根因：`laojohn-ppt/scripts/helpers.py` 注入字体 XML 时把 `<a:ea>`(东亚字体)写到了 `<a:latin>` 之前。OOXML 的 `CT_TextCharacterProperties` 规定 `rPr` 子元素顺序须 **latin 在前、ea 在后**；顺序写反会被 PowerPoint 判为非法而忽略 `ea`，中文于是套用 latin 槽的 Calibri。字体名本身是正确的 UTF-8(微软雅黑/宋体)，不是缺字体或编码问题。

**两处都会犯，改字体注入务必两处一起守**：
- `_set_east_asia_font`(~104 行)：必须先 append latin、再 append ea。
- `set_ascii_font`(~661 行，给章节序号换 Bahnschrift)：删掉 latin 重建时若已有 ea，要用 `ea.addprevious(latin)` 插到 ea 前，不能直接 append 到末尾（否则又把 latin 挤到 ea 后）。

诊断手段：解压 pptx 看 `ppt/slides/*.xml`，正则抓每个 `<a:rPr>` 里 `a:latin`/`a:ea` 的出现次序，ea 在前即错。参考 PPT(`assets/reference-ppt/`)是 latin→ea 正例。

2026-06-25 已修两处并重烘洞/格列佛全 8 份(+课程打包输出洞副本)，全页 0 错误。相关：[[docx-engine-redundancy-audit]]
