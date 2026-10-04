---
name: materials-template-optional-fields-0922
description: 配套学生模板新增可选字段 plan_label_width；兼记品牌 logo 0921 换新导致 42 份存量配套 PDF 的 logo 已过期
metadata:
  type: project
---

**新增可选字段 `worksheet.plan_label_width`**（2026-09-22，`laojohn-writing-materials/assets/template_student.html`）。
多列构思表的首列缺省压到 **10%、居中**，那是为 ①②③ 序号列设计的；《介绍一种事物》的首列是「方面一：」这类 **要学生当场写上方面名**的行名，10% 既读着折行、也无处下笔。传了它同时改成左对齐（`.widelabel`）；**不传＝渲染结果一字不变**。本课传 `22%`。

**Why**：模板是 45 份课次共用的共享件，改它要么全线受影响、要么不改。跟 [[manhua-laoshi-5a-lesson-state]] 里 `plan_name`（0916）、`plan_hint`（0922）同一个套路：**加可选字段、不传则沿用旧行为**，别直接改默认值。

**How to apply**：改共享模板后必跑零影响回归。**判据＝重渲存量课次，PDF 页数与逐页提取文本逐字相等**（不比 md5、也不比字节）。本次抽三上四课次，页数 4→4、文本全等。

⚠ **同一次回归照出另一件事：品牌 logo 已于 2026-09-21 换新**（commit d08e699，写作课海报线顺带换的）：`品牌资产\logo.png` 由 **292×110 RGB（55KB）→ 1200×414 RGBA（147KB）**。所以每份重渲的配套 PDF 会突然涨约 **137KB**——**这是 logo 换新，不是模板改坏了**，回归时别被字节数吓到。
由此引出的待办：**写作配套输出里 42 份 09-21 之前渲的 PDF 还印着老的低分辨率 logo**（三侧都有），重渲即可；于 0922 回归时顺手重渲了其中三上四份学生用。共用该 logo 的其余渲染线（书目卡、海报、阅读指南、导图、学习单）同理待核。

**0923 又加三个可选字段（三上五《我们眼中的缤纷世界》首用）**：`worksheet.practice`（第 1 页练笔横线空白）、`worksheet.selfcheck`（第 1 页分档自检表）、`worksheet.plan_ref`（稿纸页小字整句覆盖——`plan_name` 自动拼的「一样一样写」与「只选一两处写」的教法相反）。有 practice/selfcheck 时第 1 页加 `.dense`（构思表行高 36px）；8 行卡＋3 行练笔＋三档表同页已贴着 1123px 上限，**练笔 3 行是上限**。契约已写进 data_schema.md。回归：五上四、三上四逐页文本相等；四上五的现存 PDF 是外部工具处理过的（康熙部首码位＋html 里有「一项一项写」手改），与本次改动无关，**它的 html 手改未回写 json，重渲会冲掉**（同 [[writing-materials-handedits-lost-on-rerender]]）。

**连带：PPT 稿纸页＝学生用第 2 页截图**（1004 自 MEMORY.md 索引行下沉）。外部件 PPT 里的稿纸页是截图，配套一改就过期，须重截；仓内直出件用 `grab_worksheet.py` 现截，不会过期。
