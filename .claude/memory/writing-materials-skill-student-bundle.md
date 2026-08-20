---
name: writing-materials-skill-student-bundle
description: laojohn-writing-materials三侧全落地(建设史)；⚠页数已过时(4/2/2)，现行形态见writing-materials-pages-trimmed-0803；工程踩点与_shared.py共享管线仍有效
metadata: 
  node_type: memory
  type: project
  originSessionId: 8ad48bc3-b9ce-4919-bb60-6fd4ca56de17
  modified: 2026-08-03T10:08:28.204Z
---

2026-07-23 新建 `laojohn-writing-materials`（同步习作配套物料）并跑通首例《这儿真美》。

- **形态（用户拍板）**：学生侧三件（学习单 01 / 范文页 02 / 课后练笔 03）**合成一个 HTML 源件 → 一份 4 页 A4 合订 PDF**（学习单2+范文1+练笔1）；输出 `写作配套输出\<年级册>-<题目>\<…>-学生合订.html/.pdf` + `_data.json`（源，唯一进 git；html/pdf 已补 gitignore）。README 对照表已加行。
- **模板来源**：桌面 `C:\Users\69491\Desktop\同步习作配套-CLAUDE\婧愪欢鍖卂en\` 的三份人工模板（含 `README_skill-build-guide.md` 构建说明——教师侧/家长侧/机构侧模板都在那里，后续扩展要回去取）。02 范文页 7-23 当天已被人工改版删掉学生例文占位区，合订按新版 4 页。
- **架构**：照仓库四 skill 同构范式（data.json → `/*__DATA__*/ null` 注入 → playwright 等 `body[data-rendered='1']`），但 PDF 用 `page.pdf(width=210mm,height=297mm)` 出**真多页 A4**（区别于既有单长页 px 模式）；页数核验用 **pypdf**（构建说明里写的 pdfplumber 未采纳，仓库无先例）。富文本标记 `{hl}`/`{b}`（JSON 禁塞原始 HTML）。
- **踩点**：01 原版 `buildGrid()` 的 `document.querySelector('.mod .modhead')` 在合订多页文档里会误抓第 1 页元素，已改为 sheet 作用域查询；`used+=110` 余量与 `@media print` 里 `.sheet.page2{min-height:calc(297mm - 2px)!important}` 是格子稿纸不烂版的关键，勿动。
- **页眉 logo（用户拍板改真图）**：桌面模板的手工仿制 CSS logo 已弃用，改 `品牌资产\logo.png` 单一源、渲染脚本 base64 内联注入（`__LOGO_SRC__` 占位，`.logo-img{height:46px}`）；后续扩教师侧/家长侧从桌面模板取骨架时**同样要换掉手工 logo**，勿照抄。PDF 被预览器锁时脚本旁路写 `.new.pdf`（照 reading-sheet safe_pdf 惯例）。
- **首例真抽取（猜猜他是谁，2026-07-23）踩出两处通用改进**：① 修改符号表改为可覆盖——`worksheet.marks` 可选字段，缺省仍四条通用符号；**详案教了具体修改符号的课（如首次引入课）必须覆盖**，否则与课堂教法冲突（横线在该课=删除号、缺省表里=画好句）；② buildGrid 加收敛环——估算余量后建格，实测 `sheet.offsetHeight>1123` 就减行重排（导语/起笔提示行数因课而异，纯估算会差 1 行导致 PDF 裂页），这儿真美回归 20 行不变。教师侧旁注文案要压短（每行 ≤50 字左右，一行放不下第 2 页会超高）。
- **派生内容口径**：课后练笔任务卡详案无直接锚点，场景候选优先取详案「选材菜单」（首例把桌面版“外婆家的院子”改回详案的“奶奶家屋后”）；绝不虚构学生作品。
- **教师合订（同日追加）**：速览页（一句话目标+两节时间轴+易错点+下水文+物料清单）+ 怎么讲活三色旁注（必守绿/可放开黄/为什么蓝 + 最不能念稿N处）合成 2 页 A4；`template_teacher.html` + `render_teacher.py` + `data_schema_teacher.md`。渲染管线已重构抽 `scripts/_shared.py`（logo/数据注入、safe_pdf、溢出+页数自检），后续家长侧直接复用、**勿再复制管线逻辑**；学生侧重构后已回归（4页/360格不变）。教师侧纪律：时间轴分钟数逐字取详案不自调；旁注/易错点每条须指向详案真实环节动作。
- **家长合订（同日收官，三侧全齐）**：成长反馈（**结构件**：信息条+作品区留白+能力勾选项+评语/关注/寄语线全留白，数据层只供 `feedback.abilities`，给老师的填写提示固化在骨架）+ 家长一页纸（一句话说清/好坏对照教学示意句/亲子小游戏/避坑两条，全大白话禁术语）；`template_parent.html` + `render_parent.py` + `data_schema_parent.md`。对照例是教学示意句、不冒充学生作品或课文；桌面版任务名「」与半角逗号已按引号纪律修正。三侧 CLI 同形态：`render_<side>.py <data.json> <输出目录>`。见 [[writing-lesson-front-page-zones]]。
