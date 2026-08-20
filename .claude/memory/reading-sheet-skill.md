---
name: reading-sheet-skill
description: laojohn-reading-sheet skill 已固化——详案→学生阅读单(学习单)批量出 PDF/HTML
metadata: 
  node_type: memory
  type: project
  originSessionId: 24170b6e-39ff-472f-893c-fa7b0b7f2b04
  modified: 2026-07-27T05:02:04.382Z
---

> **(2026-06-29 更新 · 两条恒久规则，覆盖下文一切"空+示范双版""盖角标"旧描述)**
> ① **只出学生能填的版本**：阅读单不再出示范版(教师参考)。引擎渲染时**自动跳过** manifest 里任何 `-示范` sheet；合册从两本(空白版/示范版)缩成一本 `<书名>-阅读单-全套.pdf`(`plan_bundle` 单册)。新写 manifest 别再加 `-示范`。
> ② **学生版左上不盖"空白版/派发版"角标**：引擎 `clean_variant()` 中央 gate——纯"空白版"/"派发版"整条隐藏，复合标签(如"空白版 · 换你来：xxx")只剥前缀留后半。manifest 里 `variant` 照写不影响。
> 已同步：render.py + SKILL.md + data-schema.md + generation-rules.md + archetype-decision.md + course-package SKILL。例 manifest(洞/格列佛/_新模板自检)仍含 `-示范` sheet 但被引擎跳过、未手动清理。

`laojohn-reading-sheet`（2026-06-22 固化）：把课案详案里**学生动手填**的阅读单批量做成 A4 竖版可打印学习单（PDF+HTML），**只出学生能填的版本(空白版/无后缀单版)，示范版已停产(见顶部 2026-06-29 更新)**。区别于 `laojohn-reading-guide`（给学生/家长**看**的导读卡）。

> ⚠ **两处口径已更新**：① 模板数已扩到 **18 个**（2026-07-18，13→18 扩容见 [[reading-sheet-template-expansion-18]]，下文"13 个"及 9+4 分列是当时快照）；② 输出目录 2026-07-23 大改名后为 `读书会阅读单输出\`（见 [[bookclub-materials-dir-consolidation]]），下文旧目录名照此换算。

**架构 = 固定模板 + 规则化数据 + 通用引擎**：
- 模板层 `templates/`：**18 个**参数化模板 + `template_base.html`(骨架/契约)。换书不动。
  - 表格/图形类(9)：`table`(万能兜底)/`venn`/`ladder`/`logic`/`voyage`/`story_mountain`(故事山形·**高潮单峰**，峰顶认 header 含「高潮」或 `peak` 索引)/`fishbone`(鱼骨)/`timeline`(横排时间轴·**全套唯一横向 A4 1123×794**)/`bubble`(气泡放射)。
  - 版式原语类(4，跨书高频、多单版)：`writing`(写作/写诗页)/`draw`(整页绘画框)/`comic`(左写右画小漫画)/`profile`(人物名片/档案)。
- 数据层 `manifest.json`：从该书详案抽出，逐张 `{file, template, data}`。是内容源头，改字段重渲。
- 引擎层 `scripts/render.py`：读 manifest 逐张渲染，logo 统一注入(根 `品牌资产\logo.png`)，**渲染后量 `#page` 实际宽高出 PDF**(竖版 794×自适应；横版模板自报 1123×794，如 timeline)——尺寸模板驱动、引擎不认模板名；文件锁旁路写 `.new.pdf`。加模板**不改引擎**。

**模板契约**(新模板四条)：注入点 `/*__DATA__*/ null`、根 `#page` 宽794、渲完置 `body[data-rendered='1']`、白底+右上logo+标题下移+左上版本角标。加第6种模板=照 base 抄一个 html + 登记表加一行 + decision/schema 各加一段，详见 SKILL.md「如何加第N种模板」。

**输出**：`阅读单输出\<书名>\`，命名 `<阅读单名>-空/-示范.pdf/.html` + `<书名>-manifest.json`。已注册进 README。

**硬规则**(references/generation-rules.md，踩坑拍下来的，换书必套)：空白格要够大(写整段行 row_min_h≥130、思辨理由~180；短词≥90；书写线间距≥56)、书写重的列给宽、固定维度列作 label_first_col、空+示范双版(计划表类单版、预测单示范只示意)、真实性红线(章节/情节只来自详案档案、禁伪造带引号原文、缺则留白)。

**产物**：①格列佛游记 17 文件 `阅读单输出\格列佛游记\`；②洞 16 文件 `阅读单输出\洞\`。canonical 例 `examples/格列佛游记-manifest.json` + `examples/洞-manifest.json`。

**洞 泛化验证(2026-06-22)通过**，引擎零改动跑通另一本书，并暴露+修掉两点：
- **ladder 阶数自适应**：原写死 4 阶坐标 → 改为按 steps 数量在版面均分(2–6+ 阶，配色 6 色循环)。洞阶梯=6 阶、格列佛=4 阶共用同模板(格列佛 4 阶因此更舒展、铺满 A4)。
- **决策树落地**：洞"维恩图"实为 5 维度×左/右/共同 → 按"多维对照→table"归 table(详案本就是表格)；"故事山形图"5 模板没有 → table 兜底(候选专用模板)；预测/思辨/故事山详案无参考 → 按真实性红线只出单版/空版、不伪造。

**模板扩充(2026-06-22，5→13)**：起因——洞实跑太多退化成 table(维恩多维、山形图)，用户给参考扩模板。参考源两处：`桌面\阅读单示例\`(魔法师/十岁那年/长袜子 真实阅读单 PDF) + `lesson-plan\references\source-docs\可视化工具官方案例图\`(故事山/鱼骨/时间轴/故事地图/维恩/思维导图 官方案例 png)。新增 8 个：故事山形图/鱼骨/横排时间轴/气泡放射 + 写作/绘画/图文并排/人物名片。**最大收获=版式原语**(写/画/名片)比图形工具更高频跨书。引擎/老模板零改动、洞16+格列佛17 回归通过。坑：鱼骨头标签易被右边缘截断(已缩鱼身+缩框防重叠)；图形模板"A4 用满"靠提高振幅/书写区；story_mountain **框宽随阶数自适应**(`BOX_W=min(132, 跨度/(n-1)-12)`)——6 阶时峰顶相邻两框(上升②/高潮)会贴连成表格状，自适应后分开。全模板自检样例 `examples\_新模板自检-manifest.json`(13 张 demo)。暂缓：环形故事地图、多级括号导图(小众)。

**table 新增 `highlight_col`(2026-06-22)**：整数列索引，把某列高亮成绿色(深绿表头+浅绿加粗格)，呼应维恩"共同"绿。用途——详案本想用维恩图、但内容是**多维度对照**(圆圈几何上装不下 5 维度长句)只能退化成 table 时，用它高亮"相同点"列补回视觉落点。**判断**：维恩(圆圈)只适合"无维度、左独有/共同/右独有的条目袋"；一旦是"N 维度×各自值+相同点"且文字长，table 才是合适容器(洞「两次上山对照」5 维度即此情形，highlight_col=3 高亮相同点)。不影响未设该字段的表格。

**洞已应用新模板(2026-06-22)**：洞 manifest 两处从 table 兜底改专用模板——①「故事山形图-空」→ `story_mountain`(6 阶：起始/上升①/上升②/高潮/下降/结局；长 header 压成短词放进框内色条；原 note→footer；**仍只空版无示范**，详案无参考守真实性红线)；②「黄斑蜥蜴时间线」空+示范 → `timeline`(6 章节点 第1/8/28/33/45–47/49 章；示范"场景/作用"两段做**忠实压缩**适配窄列、未加新信息；横排显「先立后破」时间推进感强于表格)。examples + 交付 `阅读单输出\洞\` 两处 manifest 同步、整本 16 张重渲，只留 pdf/html/manifest。**注意 safe_pdf 锁旁路**：用户开着 PDF 预览器时 .pdf 写不进、旁路成 .new.pdf 致主 pdf 滞留旧版——需用户关预览器后重渲落位。

原型搓制目录 `E:\laojohn-lesson-plan\_阅读单原型\`(make_sheets/make_graphics/build_manifest/build_dong + _newtpl_demo.json/_demo_out，留作回归)。关联 [[ppt-four-image-grid]]。
