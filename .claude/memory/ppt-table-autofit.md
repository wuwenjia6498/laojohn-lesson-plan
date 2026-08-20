---
name: ppt-table-autofit
description: laojohn-ppt 表格渲染自适应改造——<br>真换行 + 自适应字号/行高/列宽，杜绝表格溢出页面
metadata: 
  node_type: memory
  type: project
  originSessionId: 8fe89af1-0860-4f02-9f28-a18e360131c3
---

**表格自适应改造（2026-06-22，laojohn-ppt/scripts/helpers.py 的 add_table）**

起因：用户反映"七天阅读计划表基本都在页面外面"。根因两叠加：① `<br>` 被当字面量渲染（单元格挤成一长行）；② 固定行高 44pt×行数 + 四列等宽——8 行表最小高度就到 1.05H、掉出页面（slide_h=540pt）。

**改了什么**（add_table 重写，单一调用方 layouts.render_table）：
- `<br>` 与 `\n` → 单元格内真实换行（多段落 add_paragraph，line_spacing 1.1），不再印字面量。
- 列宽内容自适应：`_content_col_widths()` 按各列"最长一行字符数"的 len^0.7 加权分配（短列如日期/章节量窄、长列如圈画提示宽）。
- 字号自适应：`_fit_table_font()` 从 16pt 往下试到 10pt 下限，按列宽估算每格换行数→每行行高→全表高，取"全表 ≤ 区域高"的最大字号；连 10pt 都放不下则等比压缩行高（宁挤不出界）。行高逐行写入。
- 密集表（≥7 行）收紧单元格边距。
- render_table 不再传死 head_size/body_size（改自动定档）；theme `TABLE_AREA` 上移加高 → Y=0.385/H=0.555（底边 ~0.94H）。

**效果**：全 8 份（4 洞 + 4 格列佛）重烘焙，所有表格底边 ≤ 0.921H（原最坏 1.05H 出界）。最密的洞交1 P08 主线大事记（16 事件 <br> 表）降到 10pt、5 段落正常换行、0.921H 贴边但在内。已同步到 `洞相关文件/课件PPT/` 与 `格列佛游记相关文件/课件PPT/` 交付包。与 [[ppt-four-image-grid]] 同批改动。
