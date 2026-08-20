---
name: ppt-reading-sheet-page
description: 「阅读单」页型已下线，回退为「填空表格」承载阅读单+答案 {{}} 标记逐格点击
metadata: 
  node_type: memory
  type: project
  originSessionId: ba73de40-bf2d-4336-a03b-a2d427ccbc6e
---

**「阅读单」页型已彻底下线（2026-06-24 用户拍板回退）**。原 v8 方案（把 reading-sheet 真实渲染图——维恩/阶梯/逻辑/远航/山形/时间线/表格 7 版式——整图搬进 PPT、逐格点击填示范答案；ppt_export.py 桥接 + manifest 匹配）实际应用发现**版式类型太多、破坏 PPT 整体排版一致性**。现一律改回统一的 **`填空表格`** 页型呈现阅读单。

**回退后的新能力：填空表格答案 `{{}}` 标记 + 逐格点击**（替代原阅读单逐格点击）
- 痛点：填空表格只渲空白格，答案只在详案、PPT 端无从呈现。现在 ppt-draft 从详案抽答案填进单元格、用 `{{答案}}` 包裹。
- 技术：OOXML 表格是单 graphicFrame、无法对单元格做动画目标 → 答案必须用独立叠层。`render_table` 用 `add_table` 返回的几何，对每个含 `{{}}` 的单元格叠「不透明底色矩形 + 完整答案文本框」盖住底格占位 `＿＿`，按阅读顺序（行优先、列内左→右）每格成一组，复用 [[ppt-click-reveal-animation]] 的 `add_click_reveal` 逐格点击淡入。
- 两类空格：整格留白→整格包 `{{第1—28章}}`；行内挖空→只包答案片段 `【第{{3}}章】`（提示留框里当脚手架）。一格多 `{{}}` 仍算一格、一击整格揭示。
- 对齐铁律：几何/行高用**完整答案版**算（叠层放得下），底表渲**空白版**；叠层文本框镜像单元格样式（同字号/字体/边距/列宽）。实测 5 格叠层 EMU 级精确对齐。
- 退化安全：`--no-anim`/系统拍平丢动画 → 叠层无入场动画默认全可见 = 答案静态全显（非损坏）。无 `{{}}` 的表格行为不变（纯空白表，向后兼容）。

**改了什么（2026-06-24）**：
- laojohn-ppt 引擎：`parser.py`（PAGE_TYPES 删阅读单、删 sheet_ref、`Page.table_reveals`、`parse_table` 扫 `{{}}` 产 full/blank）；`helpers.py`（`add_table` 加 `reveal_cells` 入参=底表渲 blank、返回 `(table, geom)`；新 `cell_bg_color`）；`layouts.py`（删 `render_sheet`/RENDERERS阅读单/SHEET_AREA import；`render_table` 叠层+点击）；`build_ppt.py`（删 `resolve_sheet_assets`/SHEET_*/阅读单分支）；`theme.py`（删 SHEET_AREA_*）；SKILL.md（6 页型、填空表格答案契约、点击动画三类页型）。
- laojohn-ppt-draft 契约：`field-extraction.md`（7 字段；§6 表格**反转**——从"不填答案"改为"必须填答案+`{{}}`标记，真实性红线不豁免详案没给留空"；删 §8 阅读单+冲突矩阵阅读单行/禁用列）；`page-type-decision.md`（6 页型，删 manifest 预读+序0阅读单+示例5b，可视化工具统一判填空表格）；`pagination-engine.md`（节拍表阅读单→填空表格）；`SKILL.md`（枚举7→6、字段8→7、删步3.5、核心约束/自检改答案标记）；`_smoke_check.py`（VALID/FIELD_MATRIX 删阅读单 + 加 `{{}}` 配对校验）。
- 删 `laojohn-reading-sheet/scripts/ppt_export.py`（桥接脚本）；reading-sheet SKILL.md 改历史说明。模板里残留的 `data-answer/data-content` 标注**保留**（无害、不影响打印），新模板无需再加。

**验证**：5 格 `{{}}` 测试 deck——5 reveal、底表 `＿＿`、叠层 EMU 精确、5 click 组、`--no-anim`=0 timing 静态全显；smoke 好/坏样本各捕获正确；俗世奇人例(全 6 页型,含无标记填空表格)20 页正常烘焙(向后兼容)；scripts 0 阅读单残留。

**范围**：只改 skill/引擎 + 1 测试 deck，**存量 PPT 不重烘焙**（用户拍板）。已交付的 `洞-交流课2.pptx`（含旧阅读单页）原样保留；其旧中间稿 .md 因含阅读单页不再可重建，后续按需重跑 ppt-draft（产出填空表格）即可。其余存量(洞/格列佛各课)按需各自重跑。相关 [[ppt-table-autofit]]（add_table 自适应）不受影响、被复用。

**格列佛游记 阅读单答案补全（2026-07-01）**：格列佛 4 份中间稿的填空表格全是空白（早于 `{{}}` 规则、洞已带答案而它漏）。回详案 `参考：` 逐张核对后，给**有定论答案的 5 张梳理表**补 `{{}}`：交流课1 P05(四次远航归并·12格)/P09(小人国↔大人国对比·4格)/P14(讽刺三层中层内核·2格)、交流课2 P05(慧骃↔野胡维恩·6格)/P11(态度阶梯四阶·4格)；**开放/个人单保持空白**——导读 P16 预测阅读单、导读 P19 阅读计划(教师给定)、思辨 P08 两难思辨单(我的判断/理由)。答案全部压缩自详案参考、真实性红线未豁免。仅交流课1/2 两份 PPT 重烘（导读/思辨未变）。**固化**：ppt-draft `field-extraction.md` §6 + SKILL 自检 加「正向义务：详案给了 `参考：` 定论的梳理表必须包 `{{}}` 别漏」＋「豁免：预测单/纯思辨判断单保持空白」，判据同 [[ppt-reference-answer-on-slide]] 的"纯思辨不强加"。
