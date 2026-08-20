---
name: docx-engine-redundancy-audit
description: md_to_laojohn_docx.py 冗余审计结论——大=固有复杂度非臃肿，唯一死代码(PIL旧封面残骸)已清
metadata: 
  node_type: memory
  type: project
  originSessionId: b77feab6-3161-4a85-897e-60ef5f367f57
---

`md_to_laojohn_docx.py`（lesson-plan/writing-lesson/reading-assessment 三技能共用的 docx 排版引擎，单一事实源见 CLAUDE.md §3）2026-06-23 做过一次冗余审计。

**结论：文件「大」是固有复杂度，不是臃肿。** 880 行里绝大部分都在用且必要——原生可编辑封面页的 wps DrawingML XML 注入(~170 行)、引号跨行状态机 `smart_quotes`、行内标记安全网 `add_md_text`、页眉双栏表格、各块渲染器与 markdown 分派。逐符号 grep 核对后，真正的冗余只有一处。

**已清理的唯一死代码**：一套被废弃的「PIL 绘制封面」旧方案残骸（现封面改用 wps XML + 局部 hex 字符串，完全不碰 PIL）——删了 `from PIL import Image,ImageDraw,ImageFont`+`_PIL_OK`、`FONT_MSYH_BOLD/REG`、`COVER_INK/NAVY/CORAL`，以及未用 import `WD_TAB_ALIGNMENT`/`WD_BREAK`/`nsdecls`。共 ~15 行，零行为影响。回归：《洞》烘焙 2 section + 2 media + 14 表全部如旧。

**故意保留的 legacy（别再当冗余删）**：`PPT_RE`+`render_ppt`（`【PPT换页-Pxx】` 橙色渲染）是 CLAUDE.md §5 明文的向后兼容旧 docx 死代码，用户拍板保留。

**别再重复的评估**：曾评估「是否按文档类型把引擎拆成三份独立脚本」→ 结论=不拆。差异都是数据驱动且互不碰撞的小分支(封面靠 H1 有无《》、题号 `QNUM_RE`、师话特征)，共享的是最复杂易错的 90%，拆分会让 bug 修 3 遍且违反 §3 禁副本。若只想消掉测评卷「H1 不写《》以避封面」的绕路，可加显式 `--type` 档位(仍单脚本不复制)，而非拆分。
