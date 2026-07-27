---
name: laojohn-ppt
description: 把"老约翰深度阅读读书会"风格的课件中间稿 (.md) 编译为老师投屏用 .pptx。当用户要求"把课件中间稿做成 PPT""根据中间稿生成幻灯片""烘焙投屏课件"或基于 laojohn-ppt-draft 的产物制作 PPT 时使用本技能。需要先有一份符合契约的中间稿 .md 才能调用。
---

# laojohn-ppt — 中间稿 → 投屏 PPT 编译器

把一份"课件中间稿 markdown"编译为投屏专用 `.pptx`（16:9，微软雅黑 + 宋体，零依赖）。
本技能只做"渲染"，不做内容生成；上游中间稿由 `laojohn-ppt-draft` 或人工撰写产生。

## 何时使用

- 用户说"把中间稿做成 PPT""根据中间稿生成投屏 PPT""把这份 md 烘焙成 pptx"
- 用户上传一份带 `## P\d+ | 页型:xx` 分页的 md 并希望产出 pptx
- 上游 `laojohn-ppt-draft` 已输出中间稿，需要继续编译

## 文件加载策略（先读这里）

| 文件 | 何时读 |
|---|---|
| 本 SKILL.md | 每次 |
| `references/page-contract.md`（中间稿契约唯一源：元信息/分页头/页型枚举/7 字段/`{{}}` 填空答案/`参考：` 答案上屏/v8 版式选择器/实景观察/自动封面与 END/完整示例） | 编译前核对输入、或诊断"页型未识别"时 |
| `references/visual-variants.md`（视觉规范与差异化渲染唯一源：v6.1 关键词高亮与环节标题自适应/v7 逐条点击动画规则/故障排查表） | 关心视觉行为、调动画、排查渲染问题时 |
| `references/architecture.md`（profile 分层架构：共享层/呈现层、页型×profile 归属、写作专属页型清单） | 改代码、加页型、判断某页型归哪个 profile 时 |
| `laojohn-ppt-draft/references/writing-mode.md` §2/§2.5/§2.6/§2.7 | 写作页型**字段写法**唯一源（本 skill 不复制） |

## 契约速览（细则见 page-contract.md）

- 一份中间稿 = 一节课的 PPT。分页头 `## P14 | 页型:原文齐读`；**P01 固定封面、正文从 P02 起**，每课时独立编号；**PPT 页面上不标页码**。
- 页型**按 profile 裁决**：读书会（缺省）6 种（封面/环节标题/引导问题/原文齐读/要点小结/填空表格）；写作课（元信息 `文体：写作` 触发）自成一套（共用 3 种 + 情境任务/写法讲解/活动指令/示范文/双栏对照/写作任务/实景观察）。写错 profile 会因查不到 renderer 报错。
- 字段 7 个：眉标（**不写课型**）/标题/副标题/正文/要点/表格/配图建议。要点行下 `参考：答案` → 红字点击上屏；填空表格 `{{答案}}` → 底表留空、逐格点击揭示；引导问题页 2–4 条配图建议 → 2×2 四图网格。
- 封面与 END 页自动注入；逐条点击动画默认开启（`--no-anim` 关闭）。

## 调用方式

### 固定输出目录

> ⚠ 路径与本机环境约定见根 `CLAUDE.md` §1：执行前用 `(Get-Location).Path` 确认实际项目根目录，下文 `<项目根目录>` 代表该路径，禁止硬编码盘符。

**所有投屏课件 PPT 按课型线保存到（与中间稿目录同线对应）：**

```
读书会（文体缺省） → <项目根目录>\读书会课件PPT输出\<书名>\
写作课（文体：写作） → <项目根目录>\写作课件PPT输出\<年级册>-<题目>\
```

例：`<项目根目录>\读书会课件PPT输出\俗世奇人\俗世奇人-导读课.pptx`、`<项目根目录>\写作课件PPT输出\三上-这儿真美\这儿真美-写作指导课.pptx`

```bash
cd .claude/skills/laojohn-ppt/scripts
python build_ppt.py --input "<项目根目录>\读书会课件中间稿输出\<书名>\<书名>-<课型>-中间稿.md" --output "<项目根目录>\读书会课件PPT输出\<书名>\<书名>-<课型>.pptx"
```

可选参数：`--course` 覆盖课时／`--book` 覆盖书名／`--logo`、`--banner` 自定义素材（默认 `../assets/logo/logo-red.png`、`../assets/decorations/cover-banner.jpg`）／`--no-anim` 关闭点击动画（默认开启）。

执行后终端输出"配图占位清单"——交给老师即知哪些页需手动贴图。

## 不做的事

- 不生成内容，不改写文案
- 不内嵌字体（保证 .pptx 体积小、跨平台兼容）
- 不自动配图（始终给老师占位框）
- 不导出 PDF（让 PowerPoint/WPS 自行导出）

## 文件结构

```
.claude/skills/laojohn-ppt/
├── SKILL.md
├── references/
│   ├── page-contract.md    中间稿契约唯一源
│   ├── visual-variants.md  视觉规范/动画/故障排查唯一源
│   └── architecture.md     profile 分层架构（CLAUDE.md §3 接缝原则的细则）
├── scripts/
│   ├── build_ppt.py        入口 CLI（按元信息 文体 选 profile）
│   ├── parser.py           中间稿解析（共享·课型无关）
│   ├── layouts_common.py   公共元素 + 参数化封面基函数 + END（两 profile 共用）
│   ├── layouts_reading.py  读书会 6 页型渲染 RENDERERS_READING
│   ├── layouts_writing.py  写作课页型渲染 RENDERERS_WRITING
│   ├── theme.py            字号/颜色/坐标常量（读书会默认）
│   ├── theme_writing.py    写作课视觉变体常量
│   └── helpers.py          文本框/占位框/表格工具 + 点击动画注入（共享·课型无关）
├── assets/    logo/ · reference-ppt/ · decorations/
├── examples/  mini-test.md（最小端到端样例）+ mini-test.pptx
└── tools/     parse_slide.py（开发期 XML 侦察）
```
