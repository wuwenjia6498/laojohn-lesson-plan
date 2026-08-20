---
name: docx-engine-title-heading-layout
description: docx 引擎标题/标题层版式改动——软回车副标题 + 头部
metadata: 
  node_type: memory
  type: project
  originSessionId: 84c65f81-ec04-4e33-9b5e-69434d22a8fc
---

`md_to_laojohn_docx.py`（共用排版引擎）2026-06-25 改了标题与 `##` 标题层处理，为写作课教学设计的版式服务，**对阅读课案/测评等价不变**（已回归《洞》验证：4 课时分页、标题居中、书级 `###` 靠左均不变）：

1. **主+副标题软回车同段**：H1 后若紧跟一行非标记文本，引擎把它当副标题、与主标题**同一段落**用 `<w:br/>`（软回车）分行 + 单倍行距，主副标题不再隔一个段距。`render_doc_title(doc, text, subtitle=None)` 新增 subtitle 参；无副标题（阅读课案 H1 后是空行）走原样。

2. **头部 `##` 靠左不分页**：引擎原把**所有 `##` 都当课时级**（居中、第二个起分页）。改为——`##` 非「第N课时」且在首个课时之前（写作课的"教案提纲表/核心素养教学目标"）→ `render_lesson_title(..., align_left=True, page_break=False)`：靠左、不分页、保留课时同款 14pt 字号与标题色。课时（第…）仍居中+分页;课时之后的"附:…"附录块仍居中+分页。判定标志由 `seen_lesson`→`seen_lesson_title`（仅遇课时置位）。

阅读课案不受影响的根因：其 `##` 全是"第N课时"、H1 后是空行（无副标题）。相关：[[writing-lesson-core-literacy-goals]]（标题用词"教学设计"+副标题"校内同步写作"）、[[docx-engine-redundancy-audit]]。
