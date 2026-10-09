---
name: pptx-text-edit-three-silent-traps-0916
description: 用 python-pptx 改外部课件时，三种改法会让 PowerPoint 拒绝打开文件，而 python-pptx 自己读得出、zip 与 XML 校验也全过
metadata: 
  node_type: memory
  type: project
  originSessionId: 04aa0ce8-b2dd-49b1-ab34-eb9cb77f4d87
  modified: 2026-09-16T15:42:32.409Z
---

用 python-pptx 对外部 .pptx 做文本级改稿（2026-09-16 按改页清单改五上二《“漫画”老师》桌面终稿时踩全），三种改法产出的文件 **python-pptx 能打开、zip 完整性过、每个 XML 都能 parse，但 PowerPoint 一律拒绝打开**，报错只有一句 `PowerPoint could not open the file`，不指出是哪一条：

1. **复制形状没换 shape id**——`copy.deepcopy(shape._element)` 会把 `cNvPr` 的 id 一起复制，同页出现重复 id。
2. **删形状后时间轴留了空容器**——摘掉引用该形状的 clickEffect 之后，`<p:childTnLst>`／`<p:bldLst>` 变成空元素，schema 要求非空。
3. **`<a:endParaRPr>` 不在段落末尾**——往 `<a:p>` 里 append run 会把它挤到 run 前面；`<a:pPr>` 同理必须在首位。

**Why：** 三项都不在 python-pptx 的校验面内，所以「脚本跑通了、文件存下来了」完全不能说明 PowerPoint 认。当时的表现极具误导性——第一次导出恰好成功过一次，之后连同一份逻辑的产物都失败，一度以为是 WPS 占用或 COM 环境脏（本机 WPS 抢注 .pptx 关联，确实也会让 COM 导出失败，见 `shot_assets.py` 头注释），白绕了三轮。

**How to apply：** 改外部 pptx 一律用 `.claude/skills/laojohn-ppt/tools/pptx_text_edit.py`（本次固化，头注释里有完整排查表）：复制形状走 `clone_shape()`，收尾**必须**调 `prune_timing(prs)` + `normalize_paragraphs(prs)` 再 save。文件打不开时按 **1→2→3 顺序排查**（查重复 shape id → 查 timing 空容器 → 查段落子元素顺序），三项都干净才去怀疑 COM 环境；用「原件副本导得出、改后件导不出」这一对照来区分是文件问题还是环境问题。另两处小坑：`set_rich` 的 `{b}…{/b}` 跨行不闭合会静默吃掉四个字符（已加拦截）；手工 `\n` 断行位置靠估算必出孤字行，交给 PowerPoint 自动折行更稳，但别在文本里留缩进空格。

**⚠ 0925 反例：`normalize_paragraphs` 自己也会把文件改坏。** 六上五外部 pptx 有 26 个 slide 的段落是「pPr, r, pPr, r…」多个 `pPr` 交错的写法（PowerPoint 认）。`normalize_paragraphs` 会把每个 `pPr` 都挪到段首，挤成一串，结果原件只跑这一个函数就打不开。**所以「收尾必调」要改成「往段落里 append 过 run 才调」**；只换图或只挪几何的改动不要调它。工具本身还没修（应当只处理单个 `pPr` 的段落），修之前照此执行。排查法：拿原件分别只跑 `prune_timing`、只跑 `normalize_paragraphs`，各自用 COM 打开，看是哪一个导致打不开。

与 [[manhua-laoshi-5a-lesson-state]]、[[revise-finalized-lesson-plan-pitfalls-0915]] 同族。

**0929 补·整页复制的第四坑**（改宣讲件 0904→1008 踩中）：WPS 改过的 pptx 每个形状带 `p:custDataLst` 指向 `/tags` 部件。整页复制时若不带 tags 关系，r:id 悬空；若让新页与原页共用同一 tag 部件，PowerPoint 照样拒开。可行做法＝复制时删掉 custDataLst、不复制 tags 关系。另：`set_text` 也会 append run，改完同样要 `normalize_paragraphs`，否则 PowerPoint 能打开但**整框文字不显示**（不报错）。
