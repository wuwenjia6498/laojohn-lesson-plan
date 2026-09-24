---
name: imgtool-handdraw-gptimage-0924
description: 课件配图工具接入手绘风格库＋缺省通道改 gpt-image（0924）：风格解析抽成与海报共用的单一源；通道钉在项目上，老项目不漂移
metadata:
  type: project
---

2026-09-24 用户要求：手绘风格编号接入课件配图工具，ChatGPT（gpt-image）作默认出图模型。

**落地形态**
- 风格解析从海报 `gen_illustration.py` 抽到 `课件配图工具/scripts/handdraw_style.py`，资产 `git mv` 到 `课件配图工具/手绘风格库/`（原 `laojohn-writing-poster/assets/handdraw/`）。海报 importlib 载入；抽离前后 53 条 build_prompt 快照逐字相等。
- 课件配图：风格卡新字段 `手绘编号`（网页新建表单／风格卡一栏／`build_specs.py --handdraw`）。所有出图入口统一走 `run_lesson.compose()`：有编号 ⇒ 特征放最前、`前缀基底` 弃用、人物条目后补「服从风格」句、风格参考图挂在所有挂载图**之后**并用文字指派分工（依据 T5）；无编号 ⇒ 与旧 `prefix_for` 逐字一致（七个项目全量比对 0 差异）。编辑通道不拼画风不挂风格图。
- 缺省通道 gemini→gpt-image（imgclient、run_lesson、`.env`/`.env.example`）。**通道钉在 `project.通道`**：新建项目写入；老项目无此字段时按 `课件产出/<项目>/` 下哪个通道目录有图来认——七个老项目全认作 gemini。生成时 client 一律 `make_client(outdir.name)`，此前 web 端读 env 缺省、与目录可能不一致。

**Why:** 换缺省值若不钉通道，老项目会去读空的 gpt-image 目录，界面上图全「消失」、验收记录对不上。

**How to apply:**
- ⚠ 规则库 T1–T5 在 gpt-image 上**尚未重验**，用户拍板先用；出图须人工逐张看。首个 gpt-image 项目跑完后值得回头看 T2（数量）/T5（多参考图）是否还成立。
- 改 `handdraw_style.py` 须两家回归（见 CLAUDE.md §3「手绘风格库」行）。
- 老项目想改走 gpt-image：改 JSON 的 `project.通道`，换目录、旧验收不继承。
- 相关：[[writing-poster-tool-0920]]（编号选择经验、参考图服装去不干净就换号、subject 别写反风格的词）
