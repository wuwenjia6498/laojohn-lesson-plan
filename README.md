# 老约翰深度阅读 · 课案生产工作台

本项目是「老约翰」系列课程的内容生产工作台，包含 AI 辅助生产三条课线全套教学物料所需的 SKILL 与脚本：

- **读书会线（整本书阅读）**：电子书 → 书籍档案 → 课案详案 → 投屏 PPT/讲稿 → 书目卡·海报·阅读指南·阅读单·测评·两种导图·反馈话术
- **同步习作线（写作课）**：习作主题+年级 → 写作课详案 → 外部 PPT 后处理 → 学生/教师/家长三侧配套
- **看图写话线（低年级）**：图位规格 → 详案 → 自动生图闭环 → 支架小卡·稿纸等课堂印刷件

> ⚠ **移动硬盘注意**：盘符随挂载变动。路径与本机环境约定（`<项目根目录>` 占位、`(Get-Location).Path` 确认盘符、python/Playwright 环境、生图密钥承载）见 `CLAUDE.md` §1，此处不重复。
>
> 📖 **跨技能硬约束**（数据流事实源、共享脚本单一源、详案两核心不变量、命名口径、提交纪律）见 `CLAUDE.md`。本文件只管**目录结构、SKILL↔输出目录对照、生产流程**，不重复硬约束。

---

## 项目目录结构

```
<项目根目录>\
│
├── ── 输入资产（人工放置，多 SKILL 共用）─────────────────────
│
├── 读书会书籍档案\                # ← laojohn-book-profile 产物（下游课案的唯一事实来源）
│   └── <书名>书籍档案.md
│
├── 读书会书籍封面\                # 📌 封面图统一维护在这里（poster / book-card / reading-guide 共用）
│   ├── 俗世奇人.png
│   └── <书名>.jpg / .png          # 新增书时在此放封面图，无需改任何代码
│
├── 读书会原书插图\                # 📌 原书插图（按书分夹；配图版详案取图）
│   └── <书名>\
│       ├── 插-01.png              # 编号全书连号、半角连字符；也认 .jpg/.jpeg
│       └── _图单.md               # 每张图的出处/画面描述/拟用环节（图本身不入 git，此表入库）
│
├── 写作课教材插图\                # 📌 统编教材习作页扫描/翻拍（按课次分夹；配图版写作课详案取图）
│   └── <年级册>-第N单元-<题目>\
│       ├── _教材页.jpg            # 整页翻拍（存档用）
│       ├── 插-01.jpg              # 从教材页裁出的单图，编号连号
│       └── _图单.md               # 同上：图不入 git，此表入库
│
├── 品牌资产\                      # 📌 品牌固定素材（所有海报共用，非按书变化）
│   ├── logo.png                   # 品牌 Logo（书目卡/海报右上角）
│   └── qrcode.png                 # 报名/关注二维码，更换时直接替换此文件
│
├── ── 读书会线 · 产物 ────────────────────────────────────────
│
├── 读书会详案输出\                # ← laojohn-lesson-plan
│   ├── <书名>-课案详案.md / .docx
│   └── <书名>-课案详案-配图.docx  # 回插原书插图版（无图版不被覆盖）
│
├── 读书会课件中间稿输出\          # ← laojohn-ppt-draft（PPT 中间稿 .md）
│   └── <书名>\<书名>-<课型>-中间稿.md
│
├── 读书会课件讲稿输出\            # ← laojohn-ppt-draft（逐页讲稿，与中间稿页序 1:1）
│   └── <书名>\<书名>-<课型>-逐页讲稿.md / .docx
│
├── 读书会课件PPT输出\             # ← laojohn-ppt（投屏课件 .pptx 成品，由 build_ppt.py 烘焙）
│   └── <书名>\<书名>-<课型>.pptx
│
├── 读书会配套输出\                # ← 读书会下游配套物料统一目录（按书分夹，各物料 skill 共写一夹）
│   └── <书名>\
│       ├── <书名>_书目卡.jpg/.html/.json        # ← laojohn-book-card
│       ├── <书名>_海报.jpg/.html/.json          # ← laojohn-course-poster
│       ├── <书名>_阅读指南.pdf/.html/.json      # ← laojohn-reading-guide
│       ├── <书名>_抢先看.pdf/.html/.json        # ← laojohn-lesson-mindmap（书籍概况图）
│       ├── <书名>_教学导图.pdf/.html/.json      # ← laojohn-teaching-mindmap（教学设计图）
│       ├── 《书名》_课程反馈话术.docx/.md + <书名>_content.json   # ← laojohn-course-feedback
│       └── <书名>_阅读测评.md/.docx             # ← laojohn-reading-assessment
│
├── 读书会阅读单输出\              # ← laojohn-reading-sheet（学生动手填的学习单，按书分夹）
│   └── <书名>\
│       ├── <阅读单名>-空.pdf/.html/.pptx  # 只出学生空白版（示范版已停产）
│       └── <书名>-manifest.json           # 内容源头，改字段重渲
│
├── 读书会整套文件打包输出\        # ← laojohn-course-package（把全部成品归集成一个交付文件夹）
│
├── ── 同步习作线（写作课）· 产物 ─────────────────────────────
│
├── 写作课详案输出\                # ← laojohn-writing-lesson
│   ├── <年级册>-第N单元-<题目>-写作课详案.md / .docx
│   └── …-写作课详案-配图.docx     # 回插教材插图版（有教材图的课次才出）
│
├── 写作课件中间稿输出\            # ← laojohn-ppt-draft（写作档；PPT 改外部生成后降级为生成依据）
│   └── <年级册>-第N单元-<题目>\
│
├── 写作课件PPT输出\               # 📌 外部平台生成的 .pptx 复制进来，本仓只做动画后处理
│   └── <年级册>-第N单元-<题目>\<题目>.pptx（两节合一时为 <题目>-全课.pptx）
│
├── 写作配套输出\                  # ← laojohn-writing-materials（学生/教师/家长三侧合订）
│   └── <年级册>-第N单元-<题目>\…-<侧名>合订.html/.pdf + …_data.json
│
├── 写作课整套文件打包输出\        # ← laojohn-writing-package
│
├── ── 看图写话线 · 产物 ──────────────────────────────────────
│
├── 看图写话详案输出\              # ← laojohn-picture-writing（一课次一目录）
│   └── <年级册>（<季>）第 N 次 · <课型>\
│       ├── <同名>.md / .docx      # 目录名＝文件 stem
│       ├── <同名>-配图.docx       # 回插图位真图版
│       ├── <同名>-生图提示词.txt  # imgspec_parser --export 重导，不入库
│       └── 图位\*.png             # 按图位规格生成并验收后回插的真图
│
├── 看图写话配套输出\              # ← laojohn-picture-materials（A4 课堂印刷件）
│   └── <详案stem>\<详案stem>-<物料名>.html/.pdf + …_data.json
│
├── 看图写话整套文件打包输出\      # ← laojohn-picture-package
│
├── ── 工程件 ─────────────────────────────────────────────────
│
├── tests\                         # tone_gate.py 机检回归夹具（故意保留缺陷的改前原稿，
│                                  #   绝不可复制进详案输出目录；用法见 tests\README.md）
├── docs\handoff\                  # 判据存档：被 skill 规则文件显式挂链的「为什么」
│                                  #   （image-spec / style-tokens / measurement-ledger 指向这里，
│                                  #   详案正文也写「依据《小试结论》§三」），**勿当残留清理**；
│                                  #   已完结的一次性交接件已于 2026-08-18 清空
├── docs\协作同步说明.md           # 双人协作操作规程（给同事看的一页：两条命令 / 交球 /
│                                  #   记忆与大件的目录联接 / 出岔子怎么办）
├── sync_assets.ps1                # 大件资产与网盘双向同步（见文末表）
├── fix_quotes_md.py               # 辅助脚本（见文末表）
├── check_quotes.py
├── tone_gate.py
│
├── CLAUDE.md                      # 跨技能硬约束（AI agent 必读）
├── README.md                      # 本文件
├── 协作看板.md                     # 双人接力状态表：条目 / 状态 / 球在谁手上
│                                  #   （唯一需两人共同维护的文件，交球前顺手改一行）
│
└── .claude\
    ├── memory\                    # 项目记忆 182 份（踩坑笔记与跨课次通则）。原在 Claude Code
    │                              #   用户目录、不随 git 走，2026-08-20 迁入仓库；各机器把用户目录
    │                              #   那份换成指向此处的目录联接，此后随 git 自动双向同步
    └── skills\                    # AI Agent SKILL 定义
        ├── ── 上游建档 ──
        ├── laojohn-book-profile\       # 电子书 → 书籍档案（下游唯一事实来源）
        ├── ── 三条详案生成线 ──
        ├── laojohn-lesson-plan\        # 整本书阅读课案详案（并承载共享 docx 引擎/回插件）
        ├── laojohn-writing-lesson\     # 同步习作（写作课）逐字稿详案
        ├── laojohn-picture-writing\    # 低年级看图写话详案（图位规格驱动 + 自动生图闭环）
        ├── ── 课件链 ──
        ├── laojohn-ppt-draft\          # 详案 → PPT 中间稿 + 逐页讲稿
        ├── laojohn-ppt\                # 读书会：中间稿 → .pptx；写作课：外部 PPT 后处理链
        ├── ── 配套物料 ──
        ├── laojohn-book-card\          # 本期深度阅读书目卡（社群传播）
        ├── laojohn-course-poster\      # 课程招生海报
        ├── laojohn-reading-guide\      # 阅读指南（给学生/家长看的导读卡）
        ├── laojohn-reading-sheet\      # 学生阅读单（课堂动手填，只出学生空白版）
        ├── laojohn-reading-assessment\ # 整本书阅读测评（一二年级15题/三至六年级20题，五维命题）
        ├── laojohn-course-feedback\    # 家长社群课后反馈话术
        ├── laojohn-lesson-mindmap\     # 精彩抢先看思维导图（书是什么）
        ├── laojohn-teaching-mindmap\   # 教学思维导图（怎么教这本书）
        ├── laojohn-writing-materials\  # 同步习作三侧配套（并承载共享 HTML→PDF 渲染引擎）
        ├── laojohn-picture-materials\  # 看图写话课堂印刷件
        ├── ── 复盘 / 编排 / 归集 ──
        ├── laojohn-detail-review\      # 详案独立·冷启动复盘（三类详案自动判型，只审稿不生成）
        ├── laojohn-pipeline\           # 编排：一键按序生成读书会全套下游物料
        ├── laojohn-course-package\     # 读书会：全部成品归集进一个交付文件夹
        ├── laojohn-writing-package\    # 写作课：全部成品归集进一个交付文件夹
        └── laojohn-picture-package\    # 看图写话：全部成品归集进一个交付文件夹
```

---

## SKILL 与输出目录对照

| SKILL | 用途 | 固定输出目录 | 文件命名规则 |
|-------|------|-------------|-------------|
| `laojohn-book-profile` | 从电子书/PDF/全文提取书籍档案（**下游唯一事实来源**，须全文通读、基于原文，禁止凭记忆编造；建档时同步逐张目视原书插图并产 `_图单.md`） | `读书会书籍档案\` | `<书名>书籍档案.md`（**无连字符、不带书名号**） |
| `laojohn-lesson-plan` | 生成整本书阅读逐字稿课案详案（L1/L2 两节、L3–L6 四节，每节 60 分钟） | `读书会详案输出\` | `<书名>-课案详案.md` / `.docx`；回插了原书插图的另出 `<书名>-课案详案-配图.docx`（图取自 `读书会原书插图\<书名>\`，见下文「原书插图管理」） |
| `laojohn-writing-lesson` | 生成同步习作（写作课）逐字稿详案（两节连排 × 45 分钟，含作前/作中指导+当堂写作+作后评改，正面讲技法、配教师示范文） | `写作课详案输出\` | `<年级册>-第N单元-<题目>-写作课详案.md` / `.docx`（如 `三上-第一单元-猜猜他是谁-写作课详案.md`；单元号用**中文数字**、取 `writing-lesson/references/course-map.md` §三「单元」列，年级册与单元、单元与题目之间均用半角连字符；**不在教材单元序列的自拟主题省略单元段**，如 `三年级-写秋天的公园-写作课详案.md`。该课次标识段贯穿写作课线全部下游产物）；有教材配图的另出 `…-配图.docx` |
| `laojohn-picture-writing` | 生成低年级看图写话逐字稿详案（图位规格驱动，24 方法·四学期 64 课次；AI 先出《图位规格书》再写图文自洽详案，含自动生图 + 视觉验收闭环） | `看图写话详案输出\<课次>\` | 一课次一目录（目录名＝文件 stem）：`<年级册>（<季>）第 N 次 · <课型>.md` / `.docx`（如 `二上（秋）第 1 次 · 方法课.md`，课次/课型按其 `course-map.md` §四 64 课次表取）+ 配图版 `…-配图.docx` + 生图提示词 `…-生图提示词.txt` + 图位 `图位\*.png` |
| `laojohn-ppt-draft` | 详案 → PPT 中间稿 **+ 逐页讲稿**（每课时双产出，页序 1:1；自带教学节拍分页引擎，详案无需换页点）。另承载页标回注脚本 `pageback_annotate.py`（两线共用） | 中间稿 `读书会课件中间稿输出\<书名>\` / `写作课件中间稿输出\<课次>\`；讲稿 `读书会课件讲稿输出\<书名>\`（**写作课讲稿已于 2026-08-03 停产**） | `<书名>-<课型>-中间稿.md`；`<书名>-<课型>-逐页讲稿.md` / `.docx` |
| `laojohn-ppt` | **读书会**：中间稿 → 投屏课件 PPT 成品（`build_ppt.py` 烘焙）。**写作课**：承载「外部 PPT 后处理链」= 归位 → 读详案审查 PPT → 注入点击动画 → 详案页标回注（`build_ppt.py` 对写作课已停用） | `读书会课件PPT输出\<书名>\`；写作课为 `写作课件PPT输出\<课次>\`（外部件复制进来） | `<书名>-<课型>.pptx`；写作课 `<题目>.pptx`（两节合一为 `<题目>-全课.pptx`，文件名内不带年级单元段） |
| `laojohn-writing-materials` | 生成同步习作配套物料（学生合订：学习单+范文页 3 页；教师合订：速览页+怎么讲活三色旁注 2 页；家长件：家长一页纸 1 页）。承载两线共享的 HTML→PDF 渲染引擎 `_shared.py` | `写作配套输出\<年级册>-第N单元-<题目>\` | `<年级册>-第N单元-<题目>-<侧名>合订.html/.pdf` + `…-<侧名>合订_data.json`（源；侧名=学生/教师/家长） |
| `laojohn-picture-materials` | 生成看图写话配套课堂印刷件（支架小卡 8 张/页裁切 · 兜底纸条 7 条/页裁切 · 看图写话稿纸=主图+格子+格式提醒 · 教师家长页 2 页=教师速览+家长一页纸；纯口头课只出卡与教师家长页）。渲染引擎单向复用 writing-materials `_shared.py` | `看图写话配套输出\<详案stem>\` | `<详案stem>-<物料名>.html/.pdf` + `…-<物料名>_data.json`（源；物料名=支架小卡/兜底纸条/看图写话稿纸/教师家长页） |
| `laojohn-book-card` | 生成「本期深度阅读书目」书目卡（书封+信息格+内容简介，社群传播用）。承载两家共享的 JPG 长图渲染引擎 `_jpg_render.py` | `读书会配套输出\<书名>\` | `<书名>_书目卡.jpg/.html/.json` |
| `laojohn-course-poster` | 生成课程招生海报（读书会详案 → 对外招生宣传图） | `读书会配套输出\<书名>\` | `<书名>_海报.*` |
| `laojohn-reading-guide` | 生成阅读指南（给学生/家长**看**的导读卡）。承载三家共享的 A4 单页 PDF 渲染引擎 `_a4_render.py` | `读书会配套输出\<书名>\` | `<书名>_阅读指南.*` |
| `laojohn-reading-sheet` | 生成学生阅读单（课堂**动手填**的学习单：18 模板=表格/维恩/阶梯/逻辑/导图/故事山/鱼骨/时间轴/气泡等图形类 + 写作/绘画/图文并排/人物名片等版式原语（全清单见该 skill 模板登记表），只出学生空白版；默认同出可编辑 PPTX） | `读书会阅读单输出\<书名>\` | `<阅读单名>-空.pdf/.html/.pptx` + `<书名>-manifest.json` |
| `laojohn-reading-assessment` | 生成整本书阅读测评（单项选择题，**一二年级 15 题 / 三至六年级 20 题**，参照 PIRLS 五维=提取信息/整体感知/解释推断/评价鉴赏/转化运用，按年级 L1–L6 调配题量，附答案+维度+解析）。**直接读书籍档案、与 lesson-plan 平行**，详案作深度蓝本但不充当事实源 | `读书会配套输出\<书名>\` | `<书名>_阅读测评.md/.docx` |
| `laojohn-course-feedback` | 生成发给家长社群的课后反馈话术（恒三段：导读课后/交流课后/思辨课后） | `读书会配套输出\<书名>\` | `《书名》_课程反馈话术.docx/.md` |
| `laojohn-lesson-mindmap` | 生成精彩抢先看思维导图（**讲书本身**：精彩抢先看 / 书籍概况，面向学生） | `读书会配套输出\<书名>\` | `<书名>_抢先看.pdf/.html/.json` |
| `laojohn-teaching-mindmap` | 生成教学思维导图（**讲教学设计**：备课/教研用） | `读书会配套输出\<书名>\` | `<书名>_教学导图.*` |
| `laojohn-detail-review` | **复盘层**：对已成稿详案做独立·冷启动通读复盘，**三类详案（课案/写作课/看图写话）自动判型**并加载对应五维 review-rubric，查 checklist 查不出的质量/节奏/衔接问题，出「已自动改的无争议项 + 待定夺的教学判断项」报告（只审稿，不生成详案、不出 docx、不碰下游物料、不生图不回插；**须派 fresh 子 agent 或在新会话里跑**，不在生成会话里自审） | （审稿报告，无固定产物目录） | —— |
| `laojohn-pipeline` | **编排层**：课案+档案就绪后，一键按序生成全套下游物料（书目卡/海报/阅读指南/两种导图/反馈话术，可选含 PPT 链） | （委托各下游 skill，无独立输出） | —— |
| `laojohn-course-package` | **归集层（读书会）**：把一本书散落在各输出目录的全部成品复制进一个交付文件夹（复制不移动） | `读书会整套文件打包输出\<书名>\` | 子文件夹见左 + 根目录详案/测评 docx |
| `laojohn-writing-package` | **归集层（写作课）**：把一节写作课的全部成品（详案+PPT+三侧合订配套）复制进一个交付文件夹（复制不移动） | `写作课整套文件打包输出\<年级册>-第N单元-<题目>\` | 课件PPT / 配套物料 两子文件夹 + 根目录写作课详案 docx |
| `laojohn-picture-package` | **归集层（看图写话）**：把一次看图写话课的全部成品（详案+图位图+四件印刷件）复制进一个交付文件夹（复制不移动；详案择优只收 `-配图.docx`，回落无图版则警告；本线无 PPT/讲稿） | `看图写话整套文件打包输出\<详案stem>\` | 课堂用图 / 配套物料 两子文件夹 + 根目录看图写话详案 docx |

---

## 输入资产管理

### 封面图（`读书会书籍封面\`，所有 SKILL 共用）

新增一本书时，只需把书封图放入该目录，按书名命名（不含书名号）：

```
读书会书籍封面\俗世奇人.png
读书会书籍封面\<书名>.jpg
```

- `laojohn-book-card` / `laojohn-course-poster`：渲染脚本通过 `--covers <项目根目录>\读书会书籍封面` 参数取封面
- `laojohn-reading-guide`：AI 直接从此目录读图并转 base64 内联进 HTML

**一次放图，多个 SKILL 都能用，无需重复操作。**

### 原书插图（`读书会原书插图\`）

给某本书的详案配原书插图时，图按书分夹放这里（**与封面目录分开，别混放**——引擎按 `读书会书籍封面\<书名>.png` 精确匹配封面，找不到会静默跳过封面页）：

```
读书会原书插图\神笔马良\插-01.png     # 两位编号、全书连号、半角连字符；也认 .jpg/.jpeg
读书会原书插图\神笔马良\_图单.md      # 出处/画面描述/拟用环节
```

- **建档阶段就要做**：`laojohn-book-profile` 通读原书时同步逐张目视插图、产出 `_图单.md`，并在档案里加 `## 十、原书插图` 指针节。
- 详案 `.md` 里写占位 `【图位:插-01｜图注文字】`（单独成行，紧跟触发出图的师话），**禁写图片 Markdown 语法**——引擎不解析，会把源码原样印进 Word。写法细则见 `laojohn-lesson-plan\assets\课案Markdown约定规范.md` §10。
- 出配图版（跑完得 `<书名>-课案详案-配图.docx`，**无图版不被覆盖**）：

```
PYTHONUTF8=1 python .claude/skills/laojohn-lesson-plan/assets/insert_images_docx.py "读书会详案输出/<书名>-课案详案.md" --profile lesson
```

  加 `--check-only` 可先核对「正文占位／目录真图／`_图单.md` 登记」三方缺口。
- **扫描件是版权材料，已 gitignore、不入库**；`_图单.md` 入库，是换机器时唯一的补图凭据。新克隆后配图版必然报「缺图待补」，这是预期行为、不是链路坏了。

### 教材插图（`写作课教材插图\`）

写作课详案要引统编教材的习作页配图（如三上《续写故事》的四格图）时，按课次分夹放这里，口径与原书插图一致：

```
写作课教材插图\三上-第三单元-续写故事\_教材页.jpg   # 整页翻拍，存档用
写作课教材插图\三上-第三单元-续写故事\插-01.jpg     # 从教材页裁出的单图，编号连号
写作课教材插图\三上-第三单元-续写故事\_图单.md      # 元数据，入库
```

- 详案里同样写 `【图位:插-01｜图注】` 占位，出配图版走同一个共享回插件 `insert_images_docx.py`（`--profile writing`）。
- **教材扫描/翻拍同属版权材料，按扩展名逐条 gitignore、不入库**；`_图单.md` 入库。
- ⚠ 教学场景是校外机构课，学生手边没有课本——教材图一律**投屏出示**，详案禁写「翻开课本／书上第 X 页」（见 `CLAUDE.md` §4）。

### 品牌资产（`品牌资产\`）

存放所有物料共用的固定品牌素材，不随书目变化：

| 文件 | 用途 | 更换方式 |
|------|------|---------|
| `logo.png` | 书目卡/海报右上角品牌 Logo | 直接替换此文件，重跑渲染即可 |
| `qrcode.png` | 海报上的报名/关注二维码 | 直接替换此文件，重跑渲染即可 |

渲染命令通过 `--logo <项目根目录>\品牌资产\logo.png` 和 `--qr <项目根目录>\品牌资产\qrcode.png` 传入脚本。

---

## 典型生产流程

### A · 读书会线（整本书阅读）

一本书从零到全套物料，按顺序执行：

```
0.  放入封面图     → 读书会书籍封面\<书名>.jpg
1.  准备电子书     → PDF / 全文文本（建档硬闸，无原文不开写）
2.  生成书籍档案   → [laojohn-book-profile]        → 读书会书籍档案\<书名>书籍档案.md
                     （通读时同步读图，产 读书会原书插图\<书名>\_图单.md）
3.  生成课案详案   → [laojohn-lesson-plan]         → 读书会详案输出\<书名>-课案详案.md
3b. 详案冷启动复盘 → [laojohn-detail-review]       → 派 fresh 子 agent / 新会话，出审稿报告
3c. 出配图版详案   → insert_images_docx.py         → <书名>-课案详案-配图.docx（有插图时）
4.  生成书目卡     → [laojohn-book-card]           → 读书会配套输出\<书名>\<书名>_书目卡.*
5.  提炼中间稿+讲稿 → [laojohn-ppt-draft]          → 读书会课件中间稿输出\ ＋ 读书会课件讲稿输出\
6.  编译课件PPT    → [laojohn-ppt]                 → 读书会课件PPT输出\<书名>\*.pptx
6b. 页标回注详案   → pageback_annotate.py          → 详案写入〖PPT第N页〗并重渲 docx
7.  制作招生海报   → [laojohn-course-poster]       → 读书会配套输出\<书名>\<书名>_海报.*
8.  生成阅读指南   → [laojohn-reading-guide]       → 读书会配套输出\<书名>\<书名>_阅读指南.*
8b. 生成阅读单     → [laojohn-reading-sheet]       → 读书会阅读单输出\<书名>\<阅读单名>-空.*
8c. 生成阅读测评   → [laojohn-reading-assessment]  → 读书会配套输出\<书名>\<书名>_阅读测评.*
9.  生成抢先看导图 → [laojohn-lesson-mindmap]      → 读书会配套输出\<书名>\<书名>_抢先看.*
10. 生成教学导图   → [laojohn-teaching-mindmap]    → 读书会配套输出\<书名>\<书名>_教学导图.*
11. 生成反馈话术   → [laojohn-course-feedback]     → 读书会配套输出\<书名>\《书名》_课程反馈话术.*
12. 打包交付       → [laojohn-course-package]      → 读书会整套文件打包输出\<书名>\
```

> 步骤 4–11 可用 `laojohn-pipeline` 一键按序跑完（失败隔离，单件失败不中断后续）。

### B · 同步习作线（写作课）

**不进以书籍档案为源头的链路**，吃「习作主题 + 年级」+ `writing-lesson/references/archive/` 习作档案：

```
1.  生成写作课详案 → [laojohn-writing-lesson]      → 写作课详案输出\<年级册>-第N单元-<题目>-写作课详案.md
1b. 机检语言肌理   → tone_gate.py --profile writing    → [FAIL] 项须清零
1c. 批次横审       → batch_ngram_scan.py               → 反同质化：与既有篇目查重
2.  详案冷启动复盘 → [laojohn-detail-review]       → 派 fresh 子 agent / 新会话
3.  出配图版详案   → insert_images_docx.py --profile writing（引教材图的课次）
4.  外部平台做 PPT → 复制进 写作课件PPT输出\<年级册>-第N单元-<题目>\
5.  PPT 后处理链   → [laojohn-ppt] 四步硬序：
      ① 归位（place_pptx.py）
      ② 读详案审查 PPT（硬序：详案没读完不许动动画脚本；已装机器闸门 plan_link.py +
         audit_against_plan.py，校验不过 animate_pptx.py 拒绝注入）
      ③ 注入逐条点击动画（inspect_pptx.py 出工作单 → 人工校正 → animate_pptx.py）
      ④ 详案页标回注（pageback_annotate.py）并重渲 docx
6.  生成三侧配套   → [laojohn-writing-materials]   → 写作配套输出\<课次>\…-学生/教师/家长合订.pdf
7.  打包交付       → [laojohn-writing-package]     → 写作课整套文件打包输出\<课次>\
```

> **写作课 PPT 自 2026-08-03 起改「外部生成 + 本仓动画后处理」**（读书会线不变，仍走 `build_ppt.py` 烘焙，两套口径不得混用）。**写作课线的逐页讲稿同日停产**（`写作课件讲稿输出\` 目录已撤），中间稿降级为外部平台的生成依据、不再定页序。外部件若两节合一，pptx 命名用 `<题目>-全课.pptx`。
>
> 第 5 步的审查常反过来照出**详案自身的错**——这类是 PPT 对、详案错，**报用户去改详案，不许倒过来改 PPT 迁就**。闸门守的是「审查做过」不是「机检全绿」：机检有 issues 照样放行，反过来机检全过也不等于审查完成。

### C · 看图写话线（低年级）

**图位规格驱动**：AI 先为每个用图位出《图位规格书》，再据「必须可见元素清单」写图文自洽详案，用户事后生图验收回插：

```
1.  生成详案+图位规格 → [laojohn-picture-writing]  → 看图写话详案输出\<课次>\<课次>.md
1b. 机检语言肌理      → tone_gate.py --profile picture
2.  导出生图提示词    → imgspec_parser.py --export  → …-生图提示词.txt
3.  自动生图闭环      → generate_images.py（AiHubMix 文生图 + 多模态视觉验收）
                        → 看图写话详案输出\<课次>\图位\*.png
                        ⚠ 生成插画不是「事实」，绝不可用图反过来改写规格/正文的情节·数字
4.  人工抽查验收      → 按「必须可见清单」逐项核；五官类返工回生成端改规格重出
5.  回插出配图版      → insert_images_docx.py --profile picture → <课次>-配图.docx
6.  详案冷启动复盘    → [laojohn-detail-review]
7.  生成课堂印刷件    → [laojohn-picture-materials] → 看图写话配套输出\<详案stem>\
8.  打包交付          → [laojohn-picture-package]   → 看图写话整套文件打包输出\<详案stem>\
```

> 生图密钥经环境变量 `AIHUBMIX_API_KEY`（优先）或 gitignored 的 `scripts/imggen.config.json` 注入。**这是全仓唯一的网络调用例外**，其余技能维持零网络调用（详见 `CLAUDE.md` §5）。

---

## 注意事项

- **书籍档案是课案的事实源头**：数据流与真实性红线的完整规则见 `CLAUDE.md` §2/§4——建档必须**全文通读**电子书/PDF 原文，严禁框架式/选读式建档，禁止凭模型记忆填写。
- **共享脚本禁 fork**：docx 排版引擎、首页版式化、正文图回插、PPT 渲染原语、HTML→PDF 渲染、JPG 长图渲染、A4 单页 PDF 渲染、档案机读块解析——八件共享真源与「谁在用」对照表见 `CLAUDE.md` §3。**课型差异一律收敛在脚本顶部 `PROFILES` 表**，改真源须把其「谁在用」栏里的物料全部重渲回归。
- **JSON 是内容源头**：各配套输出目录下的 `.json` / `-manifest.json` / `_data.json` 是产物的内容数据，修改字段后重跑渲染脚本即可更新图片/HTML/PDF，请妥善保存。
- **两种思维导图别搞混**：`laojohn-lesson-mindmap` 出的是**书的概况**（精彩抢先看，面向学生），`laojohn-teaching-mindmap` 出的是**教学设计骨架**（面向备课老师）。拿不准时先问用户要哪种。
- **书目卡内容简介**：由 AI 按课案「内容简介」段提炼，提炼完成后保存在 `<书名>_书目卡.json` 的 `summary` 字段，如需修改直接编辑 JSON 后重渲染。
- **引号规范**：中文弯引号铁律见 `CLAUDE.md` §4；批量修复用根 `fix_quotes_md.py`、校验用 `check_quotes.py`（用法见下表）。⚠ `fix_quotes_md.py` 无差别替换、不认代码围栏，含命令示例的 md 跑完须回扫代码块把命令里的引号还原半角。
- **产物不进 git**：各输出目录的渲染产物（docx/pptx/pdf/jpg/html/png）与三个打包目录已 gitignore，只提交 md/json 源与输入资产。提交前 `git status` 里不该出现产物；新增输出目录要同步补 ignore 规则，**严禁 `git add -f` 强加回来**。详见 `CLAUDE.md` §8。
- **双人协作靠三层通道**：源文件（md/json/脚本/skill）与项目记忆走 **git**；版权插图与外部生成的 PPT 走**网盘 + 目录联接**；渲染产物**哪边都不走、各自本地重渲**——所以对方审改后你 pull 到的只有 md，最新 docx 要自己再渲一次。交球靠 commit 前缀（`[稿]`/`[审]`/`[定]`）+ 根目录 `协作看板.md`。完整操作规程见 `docs\协作同步说明.md`。
- **`tests\` 是机检回归夹具，不是详案**：里面的 md 往往是**故意保留缺陷的改前原稿**，绝不可复制进 `写作课详案输出\`，也不要拿它当写作参考。说明见 `tests\README.md`。

---

## 辅助工具脚本

### 仓根脚本

| 脚本 | 用途 | 用法 |
|------|------|------|
| `tone_gate.py` | 详案「AI 腔／语言肌理」机检门（写作课 + 看图写话两线共用）。`[FAIL]` 命中即不合规、exit 1；`[INFO]` 只报数不判（破折号计数、参考行长度、词池频次等软规则）。判据从各 skill 规则文件运行时解析，改判据须同步本脚本 | `PYTHONUTF8=1 python tone_gate.py <详案.md> --profile writing` 或 `--profile picture` |
| `fix_quotes_md.py` | 批量把 `.md` 里的 ASCII 直引号转为中文弯引号 | `python fix_quotes_md.py`（处理内置列表）或 `python fix_quotes_md.py 某文件.md` |
| `check_quotes.py` | 统计 `.md` 里各类引号字符数量，用于校验 | `python check_quotes.py`（处理内置列表） |
| `sync_assets.ps1` | 大件资产（两个版权插图目录 + 外部 PPT 目录）与网盘双向合并。两向都只覆盖更旧的、**不做删除同步**。⚠ 项目在 exFAT 盘上无法用目录联接（只能建在 NTFS 卷），故用脚本；NTFS 盘可改用联接 | `.\sync_assets.ps1`／`-WhatIf` 试运行／`-CloudRoot <路径>` 指定网盘 |

### 常用 SKILL 内脚本

| 脚本 | 归属 | 用途 |
|------|------|------|
| `assets\md_to_laojohn_docx.py` | lesson-plan | 详案 md → 品牌 docx（三条详案线共用；**导出必带 `--header-left/--header-right`**，漏传静默回落读书会页眉） |
| `assets\style_front_page.py` | lesson-plan | 把朴素首页重排为提纲页定稿版式（写作课 / 看图写话两线共用，课型差异在顶部 `PROFILES` 表） |
| `assets\insert_images_docx.py` | lesson-plan | 正文图回插（读书会配图版 / 写作课教材图 / 看图写话图位三家共用，二段式后处理） |
| `assets\batch_ngram_scan.py` | writing-lesson | 写作课批次横审：与既有篇目做 n-gram 查重、反同质化（`--focus/--against` 可做单篇邻篇机检） |
| `scripts\imgspec_parser.py` | picture-writing | 解析详案里的图位规格书，`--export` 导出生图提示词 |
| `scripts\generate_images.py` | picture-writing | 自动生图闭环：按规格调 AiHubMix 文生图 + 多模态视觉验收 |
| `scripts\inspect_pptx.py` / `animate_pptx.py` / `regroup_anim.py` | ppt | 外部 PPT 后处理链：勘查出分组工作单 → 注入逐条点击动画（工作单填的是 **shape_id 不是位置索引**，改分组一律走 `regroup_anim.py`） |
| `scripts\plan_link.py` / `audit_against_plan.py` | ppt | 「先读详案再做动画」的机器闸门；`animate_pptx.py` 校验不过拒绝注入，`--no-lesson-plan` 是唯一逃生口 |
| `scripts\pageback_annotate.py` | ppt-draft | PPT 定稿后把 `〖PPT第N页〗` 页标回注进详案（两线共用，回注后须重渲 docx） |
| `scripts\render.py` / `render_pptx.py` | reading-sheet | 阅读单渲染：PDF/HTML + 可编辑 PPTX（模板库在 skill 根 `templates\`，不在 `scripts\` 下） |
