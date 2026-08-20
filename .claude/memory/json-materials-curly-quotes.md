---
name: json-materials-curly-quotes
description: "下游物料 JSON 内容字符串引号统一弯引号“”禁「」(2026-07-22口径,已覆盖阅读指南+教学导图+抢先看导图三线)"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: a6406374-f79d-471e-91f5-799ed6d90018
  modified: 2026-07-22T06:28:42.376Z
---

下游物料 data.json 内容字符串里引用词语/短句一律全角弯引号“”(嵌套内层‘’),**禁直角引号「」、禁英文直引号**(2026-07-22 统一口径,弯引号在 JSON 无需转义、与详案正文一致)。已覆盖三条线:reading-guide(先行拍板,存量 3 本已改)、teaching-mindmap、lesson-mindmap(用户点名伊凡教学导图后扩展,两线各 4 本存量——伊凡/呼兰河/汉修/俗世奇人——已批改重渲 pdf+html、打包副本已覆盖;teaching-mindmap evals 范例 json 也清了 6 处,那是生成时的模仿源)。

**Why:** 范例/规则里的「」会被生成时模仿,一本一本冒出来;引号口径三线不一致会反复被用户抓。

**How to apply:** 三 SKILL 各已固化「引号纪律」段(reading-guide SKILL 萃取节、两 mindmap SKILL「第一步:萃取」节)。书名仍用《》不受影响。其余产 JSON 的下游(book-card/course-poster 的 json)若再被抓同病,按同口径处理并固化。批量改用 python 成对映射「→“ 」→”(先 grep `「[^」]*「` 查嵌套),改后 json.load 校验 + 重渲。
