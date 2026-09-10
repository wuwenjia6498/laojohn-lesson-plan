# CLAUDE.md · 老约翰深度阅读课案生产工作台

本文件是给 AI agent 看的**跨技能硬约束**。完整目录结构、数据流图、各 SKILL 输出目录对照、生产流程，见 `README.md`——本文件不重复，只固化"改任何 SKILL/脚本都必须守住"的不变量。

---
# 语言偏好设置
请务必始终使用简体中文（Simplified Chinese）进行思考和回复。
严禁在对话、步骤解释或代码注释中混入日语或其他语言。

## 1. 移动硬盘 · 路径约定（单一声明）

本项目存放在移动硬盘，盘符随挂载变动（`e:\`、`h:\` 等）。所有 SKILL 与脚本以 `<项目根目录>` 表示项目路径：**执行前用 `(Get-Location).Path` 确认实际盘符，禁止硬编码盘符。** 各 SKILL.md 里重复的这段警告以本条为准。

**本机渲染/脚本环境（跑任何 python 物料脚本都适用，踩中会静默失败或乱码）：**
- **用 `python`，不要 `python3`**——`python3` 是 Microsoft Store 占位别名，会以 exit 49 直接退出。
- **Playwright 浏览器路径一般无需手动 export**：各渲染脚本已在脚本内用 `Path.home()`／`expanduser("~")` 回退到 `%LOCALAPPDATA%\ms-playwright`（PowerShell 写法 `$env:LOCALAPPDATA\ms-playwright`）——**用户名无关，换机器自动跟随当前用户，不要往文档或脚本里写死具体用户名**。路径异常时再 `export PLAYWRIGHT_BROWSERS_PATH=…` 覆盖（环境变量优先于脚本缺省值）。
- **python 命令一律加 `PYTHONUTF8=1`**，避免脚本里 ✓ 等字符触发 GBK `UnicodeEncodeError`、中文路径乱码。

**密钥承载约定（全仓首例，仅 `laojohn-picture-writing` 自动生图闭环用）：** 文生图/视觉验收的 AiHubMix 密钥经 **环境变量 `AIHUBMIX_API_KEY`（优先）** 或 **gitignored 的 `scripts/imggen.config.json`** 注入；base_url 默认 `https://aihubmix.com/v1`、模型 id 配置化、不写死。`imggen.config.json` 已入 `.gitignore`，**禁止提交密钥**；除此技能外全仓仍保持零网络调用。

## 2. 数据流主链

```
laojohn-book-profile（建档 · 下游唯一事实来源）
        ├─→ laojohn-lesson-plan（整本书课案详案）
        │       └─→ ppt-draft→ppt / book-card / course-poster /
        │           reading-guide / reading-sheet / lesson-mindmap /
        │           teaching-mindmap / course-feedback
        └─→ laojohn-reading-assessment（整本书阅读测评卷 · 直接读档案、不读详案）
```

- **书籍档案是事实源头**：lesson-plan 生成详案时不再翻原书，只依赖 `读书会书籍档案\<书名>书籍档案.md`。档案错一处、详案跟着错一处，且下游无从发现。
- **书目/出版类基本信息（出版社/字数/页数/ISBN/出版年/译者/作者/类型/主题/获奖）的唯一固定源 = 书籍档案的 `## 海报/指南元数据` 机读块**。课案是教学文档、不收录这些字段，所以书目卡/海报/阅读指南/抢先看导图/反馈话术要这类信息时一律从该机读块取（book-card、course-poster 脚本正则解析，其余物料由 AI 读取）；绝不从课案正文猜或凭记忆补。
- **缺失字段的呈现：「待补充」只存在于书籍档案机读块（人工回填提示），绝不进入对外物料**。生成的成品里某项基本信息没有就**留空白**——信息表/信息栏保留栏位、值空白（不写"待补充/请回填"、不画占位框）；获奖块、思维导图节点这类列表项缺失则**整条隐藏**；反馈话术等正文缺页数就不提，不写「【请补充…】」。
- **`laojohn-reading-assessment`（阅读测评卷）直接消费书籍档案、与 lesson-plan 平行**：整本书阅读理解选择题（题量/五维配比等命题规则见该 skill）。两条跨技能硬线：① **事实源唯一锁定书籍档案**——题干·选项·解析的情节·人物·章节·数字只来自档案（真实性红线不豁免，无页码档案禁写"第X页"），详案与档案冲突以档案为准；② **课案详案是默认必读的深度蓝本但不充当事实源**——系统性提取其思辨题/讨论题做高阶考点与干扰项来源，详案缺失时退回纯档案模式、不阻断出题。复用 lesson-plan 的 docx 引擎，但 H1 不带《》以免触发课案封面页。
- **`laojohn-writing-lesson`（写作/习作课）是独立平行分支**：吃「习作主题 + 年级」+ `references/archive/` 习作档案，**不进**上面这条以书籍档案为源头的链路。

## 3. 共享资产 · 单一事实源（禁副本）

**停用归档（2026-09-10 立）**：读书会线 11 个＋看图写话线 3 个 skill 已整目录移到 **`.claude\skills-parked\`**（Claude Code 只加载 `.claude\skills\` 一级子目录，停用件不进上下文、不触发），清单与恢复口令见该目录 `README.md`，恢复＝整目录移回。**`laojohn-lesson-plan` 与 `laojohn-ppt-draft` 虽属读书会线但没有停用、也禁止移进去**——前者 `assets\` 是 docx 引擎三件套，后者 `pageback_annotate.py` 与 `writing-mode.md` 是写作课 PPT 链的执行体与唯一源。下表里宿主为 `book-profile`／`book-card`／`reading-guide`／`reading-sheet` 的四行，停用期间路径一律读作 `skills-parked`。活线侧指向停用件的引用（根 `tone_gate.py`、`课件配图工具\scripts\imgclient.py`、`laojohn-detail-review\SKILL.md`）已改成两处都找，恢复时不必改回；`.gitignore` 针对 `laojohn-picture-writing/assets/` 的规则已改 `skills*` 通配，两处同时生效。

新增/换图一律改这里，不要在 skill 内另存副本：

| 资产 | 唯一源 | 谁在用 |
|------|--------|--------|
| 品牌 logo / 二维码 | `品牌资产\logo.png`、`品牌资产\qrcode.png` | book-card、course-poster |
| 书籍封面 | `读书会书籍封面\<书名>.jpg/png`（书名不带书名号） | poster、book-card、reading-guide |
| 原书插图 | `读书会原书插图\<书名>\插-01.png`（书名不带书名号，编号全书连号、半角连字符）+ 同目录 `_图单.md` | lesson-plan 配图版详案（后续可接 PPT 上屏/阅读单）。**扫描件＝版权材料，2026-08-20 起已入库**（私有仓库，见 §8；旧口径「永不入库」已作废）；`_图单.md` 同样入库，是取图与追溯的凭据。**书籍封面绝不挪进此目录**——引擎找不到封面是静默跳过，一挪就丢封面页且不报错 |
| 书籍档案 | `读书会书籍档案\<书名>书籍档案.md` | lesson-plan 及所有消费档案的下游 |
| docx 排版引擎 | `.claude\skills\laojohn-lesson-plan\assets\md_to_laojohn_docx.py` | lesson-plan、writing-lesson、reading-assessment（跨技能复用同一条流水线；assessment 用法见 §2 末条）。**页眉经课型无关的可选参数 `--header-left/--header-right` 传入**：读书会缺省「老约翰深度阅读／阅读·思辨·表达」，看图写话「老约翰·看图写话／从看懂一幅图，到写成一个故事」，同步习作「老约翰·同步习作／写清楚·写生动·有章法」——各 SKILL 导出时必带，漏传即回落读书会页眉 |
| docx 首页版式化 | `.claude\skills\laojohn-lesson-plan\assets\style_front_page.py` | picture-writing、writing-lesson 两线共用（把朴素首页重排为提纲页定稿版式）。**课型差异全收敛在脚本顶部 `PROFILES` 表，禁 fork、禁往渲染原语里塞课型分支**；改它须同时回归两条线。版式/配色/行名细则见**脚本头注释**与两线各自 `lesson-structure.md` |
| docx 正文图回插 | `.claude\skills\laojohn-lesson-plan\assets\insert_images_docx.py` | picture-writing（`scripts\insert_images_docx.py` 是薄 shim）、lesson-plan（读书会配图版）、writing-lesson（`writing` 档）三家。**二段式后处理**（引擎先出基础 docx、再换真图），**故引擎侧不新增 `![](…)` 解析分支**。三条红线：① **课型差异全收敛在顶部 `PROFILES` 表，禁 fork**，改它须同时回归看图写话三课次与读书会配图版；② ⚠ **凡 `PROFILES` 里有的字段（含取图目录名 `name_from`），CLI 与上游脚本默认值一律 `None`**——给硬默认会永久盖住课型档且完全静默；③ 共享件**绝不 import `imgspec_parser`**（picture-writing 私有模块，反向依赖会让读书会线故障依赖看图写话文件树）。段内处理规则与回归法见**脚本头注释** |
| PPT 渲染原语 | `.claude\skills\laojohn-ppt\scripts\helpers.py` + `parser.py` | 读书会 / 写作课 / 宣讲**三个 profile** 共用的底层横切层（有 bug 史，修一处即重烘焙全部）。**永不 fork、禁 `doc_kind`/课型分支**——课型差异在各自的 layouts_* 与 theme_* 里表达；分派点是 `build_ppt.py` 的 `PROFILES` 表，新增课型只加一行 |
| 学习单渲染引擎 | `.claude\skills\laojohn-reading-sheet\` 下：`scripts\render.py`（PDF/HTML）+ `scripts\render_pptx.py`（可编辑 PPTX）+ `templates\`（模板库，**在 skill 根目录、不在 `scripts\` 下**） | reading-sheet（整本书阅读单）专用；`render.py` 的 `--templates-dir`/`--bundle-label` 是课型无关的可选参数（reading-sheet 自用，`--bundle-label` 默认「阅读单」），保留不删 |
| 配套物料 HTML→PDF 渲染引擎 | `.claude\skills\laojohn-writing-materials\scripts\_shared.py` | writing-materials（同步习作配套）与 picture-materials（看图写话配套）两线共享单一源；后者的 `scripts\_shared.py` 是薄 shim，**禁复制**。**两线模板与 data.json 禁 emoji/生僻符号字符**——不在微软雅黑字表内的字会被现造成 Type3 字体、PDF 编辑器一律拒编；装饰图标一律纯 CSS 图形，`check_type3` 每次渲染自动报警。**完整红线口径见 writing-materials `SKILL.md`**。⚠ 与下面三件**不是同一个引擎**：本件出固定 A4 多页，下游物料出单页动态高，两种输出模型不可互相塞分支 |
| 书籍档案机读块解析 | `.claude\skills\laojohn-book-profile\scripts\profile_meta.py` | book-card、course-poster 的 `extract_fields.py`（各以 importlib 载入，**禁复制正则**）。归 book-profile 是因为机读块格式由它定义（键名见其 `assets\book-profile-template.md`）——谁定义格式谁给解析器。`BLANK_MARKERS` 是两线并集，改它同时影响两个物料的"缺失留空"判定。函数清单见**脚本头注释** |
| 读书会 JPG 长图渲染引擎 | `.claude\skills\laojohn-book-card\scripts\_jpg_render.py` | book-card（书目卡）与 course-poster（海报）两家。**两家历史口径差异全部参数化**（`strip_parens`／`fallback`）——**不要为了"统一"而改默认值，会改变既有产物**。尺寸/质量/输出模型见**脚本头注释** |
| 读书会 A4 单页 PDF 渲染引擎 | `.claude\skills\laojohn-reading-guide\scripts\_a4_render.py` | reading-guide、lesson-mindmap、teaching-mindmap 三家（后两家 `render_pdf.py` 是薄壳）。**`recenter_on_overflow`：两种导图传 True**（居中放射版式，超页需重设 min-height），**阅读指南保持 False**（文档流版式，打开会推开版式）。输出模型见**脚本头注释** |

> 现存物理副本（`laojohn-ppt\assets\logo\`、`laojohn-course-poster\assets\qrcode.png` / `assets\covers\`）属历史遗留；以根目录单一源为准，勿据副本做新决策。

**PPT 引擎按课型分 profile（接缝原则）**：`laojohn-ppt` 分两层——共享层 `helpers.py`/`parser.py`/`build_ppt.py` 课型无关、单一源；呈现层按 profile 分模块，按中间稿元信息 `文体：写作` 选（缺省=读书会）。**新增写作课视觉/页型时只动 writing 模块 + theme_writing，绝不往 reading renderer 或 helpers 里塞课型分支**——否则共享引擎退化成条件分支堆。两层结构、页型按 `RENDERERS_<profile>` 裁决、写作专属页型、v8 版式选择器等全部细则的唯一源＝`laojohn-ppt/references/architecture.md`；写作页型字段写法的唯一源＝`laojohn-ppt-draft/references/writing-mode.md`。

**写作课 PPT 已改「外部生成 + 本仓动画后处理」（2026-08-03 立 · 仅写作课线）**：写作课 .pptx **不再由本仓 `build_ppt.py` 烘焙**，改由外部平台生成后复制进 `写作课件PPT输出\<年级册>-第N单元-<题目>\`。完整后处理链＝**归位 → 读详案审查 PPT → 动画 → 详案页标回注**；四步操作、命令、闸门用法、连带口径（两节合一命名／讲稿停产／直引号须核）的唯一源＝`laojohn-ppt/SKILL.md`「外部 PPT 后处理链」节。三条属于跨技能层、不随手册下沉的硬序：① **审查是 2026-08-06 用户拍板加的硬序，详案没读完就不许动动画脚本**——外部件漏环节、改归类、剧透结论，本仓一概不知情，且分组顺序本就以详案为准；这道序已装机器闸门（`plan_link.py`＋`audit_against_plan.py`，`animate_pptx.py` 校验不过拒绝注入，`--no-lesson-plan` 是唯一逃生口），**不再只是文档约束**。② **闸门守的是「做过」不是「全绿」**——机检 issues 非空照样放行；反过来**机检全过也不等于审查完成**，教学顺序与归类判断机器给不出，人仍须整篇读详案。③ 审查常反过来照出**详案自身的错**——这类**是 PPT 对、详案错，报用户去改详案，不许倒过来改 PPT 迁就**。**读书会线不适用**——`读书会课件PPT输出\` 仍由 `build_ppt.py` 烘焙，两套口径不得混用。

## 4. 详案类两核心共用的不变量（lesson-plan / writing-lesson）

两个核心 SKILL 先后独立开发，以下骨架两边必须一致，改一处要想到另一处：

- **中文弯引号铁律**：正文一律全角 `""` / `''`，**严禁** ASCII 直引号 `"` `'`（Markdown 语法/代码/英文路径除外）。源 `.md` 阶段就要正确，不依赖引擎安全网兜底；旧文件批修用根 `fix_quotes_md.py`，校验用 `check_quotes.py`。
- **行内强调克制**：正文流水句里不做行内强调；**尤其禁用单星/单下划线斜体 `*…*`、`_…_`——引擎不解析这两者，会把星号/下划线原样印进 docx**。成对的 `**…**`／`__…__` 引擎会转成真实加粗、未配对的残余标记自动剥除（不会泄漏星号）。整行的 `**小标题**` 引擎会识别成加粗小标题，但**两 skill 的写法政策不同**：**lesson-plan 用它**（如 `**本节三维目标**`）；**writing-lesson 更严、连整行 `**` 也不用**，教学目标（核心素养四维）等小标题改用 `【】` 标签与固定话术骨架承载，详案检索 `*` 应为零（两类豁免——提纲表节内成对 `**` 与 `> **可压缩预案**：` 引块批注，见 writing checklist E 组机检门条）。两 skill 共用同一引擎，差异是各自的写法政策、非引擎能力——单星斜体两边都禁，是唯一对两 skill 完全一致的硬线。**同理禁用任何 HTML 样式/高亮标签承载强调**（`<mark>`／`<b>`／`<u>`／`<span>` 等）：引擎不解析这些标签，会把 `<mark>…</mark>` 之类原样印进 docx（曾在《格列佛》详案泄漏两处）；行内强调一律只用 `**`，需要「下节课再议」这类伏笔用文字直说、不靠视觉高亮。唯一放行的 HTML 是引擎明确支持的表格换行 `<br>` 与整块跳过的注释 `<!-- -->`。此禁对两 skill 同样是硬线。
- **固定话术骨架**：`师：`（师话）/ `参考：`（参考答案）/ 整行 `学生互动分享`·`学生自由分享` / `（教师总结）`。
- **教学目标标签（⚠ 三条线已各走各路）**：lesson-plan（读书会）仍用三维 `【知识技能】`/`【过程方法】`/`【情感价值】`；**writing-lesson 与 picture-writing 均已取消独立教学目标节**——writing-lesson 改由首页提纲表「核心技法」＋「学习目标」两行承载（唯一源：`writing-lesson/references/lesson-structure.md` §四），picture-writing 由「教学内容」「学习目标」＋各课时「本课目标」承载。**两写作线详案检索四维标签应为零。** `【】` 标签承载机制、及"标签为既定符号、不进语言风格红线"的处理仍三线共用。
- **首页形态（writing-lesson / picture-writing 两线已分形态，勿互抄）**：两线书级头部都在 `## 教案提纲表` 下写两列表，docx 侧由共享的 `style_front_page.py` 重排（见 §3）——**picture-writing＝三区**（各区以整行加粗区头 `**N、区名**` 起头，只写区名、不带 `—— 副题`）；**writing-lesson＝无区头单表 6 行**（2026-07-29 用户定稿，区头与「怎么落地」行一并删除，课时信息回到「课题·课时」行末段）。行名口径＝教研通用词。三条不可推断的硬线：① **行名是 `style_front_page.py` `PROFILES[*]["rules"]` 的键，改 md 必同步改脚本**，否则该行掉回 `plain` 样式；② 线名行在本课名后打「（本课）」标记；要点区值内可用成对 `**…**` 强调（writing 全文 `*` 禁令在提纲表节内放行）；③ **行名与事实源各自不同、不得互抄**——picture-writing 取 `picture-writing/references/course-map.md`（24 方法·四学期 64 课次），writing-lesson 取 `writing-lesson/references/course-map.md`（六阶轴 + 63 任务全表）。具体区划与行名清单以脚本 `PROFILES` 表＋两线各自 `lesson-structure.md` 为准。lesson-plan（读书会）不适用此形态。
- **收尾**：每课时末 `本课完。`，全文末 `全课完。`。
- **交付双道工序**：先逐项 `checklist.md` 自检（合规），再独立复盘 `review-rubric.md`（质量）。**第二道复盘已独立为冷启动执行**：由 `laojohn-detail-review` 承载，正常**派一个全新（fresh，非 fork）子 agent**或在新会话里跑，**不在生成会话里自审**（顺接自审会为自己的设计辩护，沦为走过场；无法另起时才降级为同会话「显式封存生成过程后自审」）。各 skill 的 `review-rubric.md` 是各自五维与审稿人协议的唯一源——detail-review 按文档类型加载、不复制内容，改 rubric 即同时改了冷审依据；现有三份 rubric（lesson-plan/writing-lesson/picture-writing）与 detail-review 判型表一一对应，**新增课型须同时补 rubric 与判型行**，否则冷审加载不到判据、空转。
- **上课场景现实约束（三条详案线通用 · 2026-07-31 立）**：老约翰是**校外机构课**，不是校内课堂。哪怕课型定位写着「校内同步习作」，那指的也只是**跟着校内教材进度走**，上课场景仍在机构——**学生手边没有课本/教科书，也没有校内作息**。故详案禁写「翻开课本」「书上第 X 页」「照课本上说的做」「找个晨读的时间」「课间」「班主任」这类假设；教材图、教材题面一律**投屏出示**，凡要学生看图看字的地方须确认投屏清晰。同族既有约束：教室无黑板白板、禁写板书，学生动手一律走学习单。**「校内同步」四个字最容易诱发这类误设，写作课线尤其要防。**⚠ **但要分辨落点（2026-08-21 补）**：禁的是**指向动作**（翻开课本／书上第 X 页／照课本上说的做）；**指代教材进度不禁**——“这个单元的《海滨小城》”、“这幅画就印在你们语文书上” 照写不误，那是说“课本上有这么一篇”、不要求学生手边有书，且正是写作课 ③ 引本单元课文佐证与 ① 单元交代所必需（见 `laojohn-writing-lesson/references/workflow-engine.md` 环节①③）。
- **真实性红线**：伪摘录禁令——无可逐字核对的真实原文，禁止输出带引号的"原文"或"——节选自…"，一律占位；事实/页码/情节只来自档案，不得凭模型记忆补写（越是名作越易记错）。

## 5. 其它跨技能红线

- **「绝不联网」红线的作用域 + 看图写话生图例外口**：全仓「绝不联网、绝不凭记忆」红线**专指"事实不许凭网络或记忆补"**——书目/书封/页码/情节/人物只来自书籍档案（下游唯一事实源），不因网络搜到或模型记忆而混入。**`laojohn-picture-writing` 的自动生图闭环（按 imgspec 规格调 AiHubMix 文生图 + 多模态视觉验收）不属此禁**：方向与"从网络捞事实"相反——**规格是事实源、生成图必须服从规格**，并经「真图 vs 必须可见清单」自动验收 + 人工抽查双重把关（守门禁 4）。**铁律：生成插画不是"事实"，绝不可反过来用图去改写规格/正文的情节·数字**。**第二个例外口＝写作课核实教材单元课文（2026-08-21 立 · 仅 `laojohn-writing-lesson`）**：同步习作详案 ③ 环节默认要引本单元课文佐证本课技法，而仓内没有单元篇目事实源（`archive/` 的输入文档是《习作要求…》、`course-map.md` 是课程序列表，两者设计范围都不含课文），课文因此长期落在「规则鼓励引用、却无据可核」的真空里——2026-08-21 实测存量三处课文断言全部来自模型记忆。**故允许联网核实教材课文与单元语文要素**：方向同样与"从网络捞事实"相反——**核的是已有断言对不对，对象是教材这一公开权威文本**，且结论必须落进 `laojohn-writing-lesson/references/unit-texts.md` 留痕、带来源与日期、可回溯。**铁律：核实结果只进那张表，不得绕过它直接写进详案**；只点篇名 + 概括写法，不输出带引号的课文"原文"（伪摘录禁令不豁免）。**读书会线（书籍档案）的红线完全不受影响**——书目/书封/页码/情节/人物仍只来自书籍档案，不因网上搜得到而混入。此二例外之外，其余技能维持零网络调用。

- **Anthropic 官方 `docx`/`pptx`/`xlsx`/`pdf` skill：只许读改外部文件，禁止用来新建本仓产物（2026-08-18 装 · user 级 `anthropic-agent-skills` 市场）**。作用域**仅限「读取或修改一份已经存在的外部文件」**——体检外部平台生成的 pptx、拆解第三方 docx、合并 pdf 之类。**本仓一切交付产物的生成一律走 laojohn-* 流水线**：docx 走 `md_to_laojohn_docx.py`（且必带 `--header-left/--header-right`），读书会 pptx 走 `build_ppt.py`，写作课 pptx 走「归位 → 读详案审查 → 动画 → 页标回注」四步链（含 `plan_link.py` 闸门）。用官方 skill 新建，产出既不带品牌版式、也绕过页眉参数与闸门。
  - **须防触发词撞车**：官方 pptx 的 description 明写「凡用户提到 deck／slides／presentation 或点到 .pptx 文件名就触发，不问他接下来要干什么」，docx 亦覆盖 report／memo／letter／template；而本仓天天说 PPT、课件、docx。**凡涉及本仓产出，一律以 laojohn-* skill 为准**，官方件不得抢活。
  - **环境事实（2026-08-24 实测复核 · 已推翻 0818 的记载）**：本机**现已装 node v22.14.0 / npm 10.9.2**（还有 Vercel CLI，作文批改工具部署用），**openpyxl 3.1.5 / pandas 2.2.3 / python-docx 0.8.11 / python-pptx 1.0.2 也都在**。仍然没有的只剩 **LibreOffice、pandoc、markitdown**。故官方 skill 的实际可用面比 0818 记的宽得多：docx/pptx 的「新建」路径（docx-js／pptxgenjs）**现在跑得通**，xlsx **整体可用**，pdf 各项操作可用（pypdf 6.7.1），`scripts/office/validate.py` 可用（defusedxml 0.7.1）；只有「读取」路径（pandoc／markitdown）仍跑不通。**另有 0824 复核时漏记的两样：`pywin32` 与 Microsoft Office 本体（Word/PowerPoint/Excel）都在**——这条很要紧，因为本机没有 LibreOffice，**docx/pptx 要转成 PDF 或 PNG 就只剩 Office COM 这一条路**（`win32com.client.Dispatch("Word.Application")` → `ExportAsFixedFormat`；PowerPoint 则是 `Slides(i).Export(png, "PNG", w, h)`）。已在 `laojohn-ppt\tools\shot_assets.py` 跑通并封装，取图直接用它、不必重写。⚠ 用 COM 有三个坑，脚本头注释里写了：目标文件被 Word/WPS 打开会拿只读句柄或卡住；`Quit()` 必须放 finally，否则留后台进程；**同一份文件要导多页必须一次会话导完——`Quit()` 后 PowerPoint 要几秒才真退出，期间再 Dispatch 会让下一次 `Presentations.Open` 失败，报错却写成「发生意外」，指向完全错的方向**（实测踩过）。
  - **⚠ 由此风险性质变了，禁令必须当真**：0818 那条禁令背后其实有环境天然挡着——**想违反也违反不了**；现在 node 装上了，**违反禁令随时能成功**，挡住它的只剩纪律这一层。上面那条「禁止用官方 skill 新建本仓产物」的理由从来不是「跑不通」，而是**产出不带品牌版式、绕过 `--header-left/--header-right` 页眉参数与 `plan_link.py` 闸门**——这个理由与装没装 node 完全无关，一个字都不因环境变化而松动。**别因为「现在能跑了」就去用**。仍然不要为跑通 pandoc／markitdown 路径去装 LibreOffice／pandoc——那与本仓已成熟的产出链重复造轮子。

- **`【PPT换页-PXX】` 已废弃**（lesson-plan、writing-lesson 详案均不再写）。分页权归 `laojohn-ppt-draft`，由它按"教学节拍"自行切页；详案只需 `## 第N课时 · 课型` 划课时、`### 一、xx` 划环节。
- docx 引擎仍把残留换页点渲染成橙色，**仅为向后兼容旧 docx**，新稿一律不产出。

## 6. 两核心 SKILL 的边界（防混用）

| | laojohn-lesson-plan | laojohn-writing-lesson |
|---|---|---|
| 对象 | 整本书阅读读书会 | 校内同步习作（写作）课 |
| 技法 | **默认不主动讲写作技法**；仅当用户在需求里明确要求「读写结合／讲写法／带写作技法」时**解锁**，且只挂在**读后写作应用任务**上正面讲解（详见下方「写作技法解锁口」） | **正面讲技法是本分**（不需用户点名，逐字稿默认就讲） |
| 课时 | L1/L2 两节、L3–L6 四节，每节 60 分钟 | 固定两节连排，每节 45 分钟 |
| 吃什么 | 书籍档案 | 习作主题 + 年级 + `archive/` 习作档案 |

**写作技法解锁口（lesson-plan 专属 · 防滥用）**：读书会详案对写作的基线态度仍是「用而不教」——写作只作读后迁移/应用活动出现（见 §2 数据流外的教学定位）。但当**用户明确提出要结合写作技法**时，允许在详案里正面讲解，受三条边界约束：① **触发须显式**——用户没点名就不主动讲，默认稿与解锁前完全一致（向后兼容，存量详案不受影响）；② **落点唯一**——技法只能挂在**已有的读后写作应用任务**上（L3–L6 第4课时的创编/续编/专题写作，或 L1–L2 收尾的创意写作环节），即「要动笔写之前先点拨写法」，**不得侵入导读课/交流课的文本分析主体**，更不得把读书会改写成写作课的两节连排结构；③ **真实性红线不豁免**——技法范例若要引书中原文做示范，仍走 §4 占位规则，禁止用仿写句冒充原文。需要系统化、独立成课地教写作，仍走 `laojohn-writing-lesson`，不在本技能膨胀。

**依赖声明**：`writing-lesson` 单向复用 `lesson-plan` 的资源——docx 引擎、`assets\课案Markdown约定规范.md`、`references\visualization-tools.md`、`references\grade-structure.md`（L1–L6 人设）。**改动这些文件的路径或契约前，必须同步检查 writing-lesson 是否受影响**（它没有自己的副本，会静默失效）。

**读书会下游物料的跨 skill 依赖（2026-07-28 抽共享层后新增）**：六个下游物料不再各自 fork 脚本，三条链路都是「真源 + importlib 薄壳」（三件真源见 §3 表）——
- `book-card\scripts\extract_fields.py`、`course-poster\scripts\extract_fields.py` → `book-profile\scripts\profile_meta.py`
- `course-poster\scripts\render_poster.py` → `book-card\scripts\_jpg_render.py`
- `lesson-mindmap`、`teaching-mindmap` 的 `render_pdf.py` → `reading-guide\scripts\_a4_render.py`

薄壳按**相对路径**（`pathlib.Path(__file__).parents[2]`）定位真源，所以**改 skill 目录名或挪 scripts 目录会静默断链**；改三件真源中任何一件，必须把其"谁在用"栏里的物料全部重渲回归（回归基准数据：`读书会配套输出\俗世奇人\` 下五份 json）。

## 7. 命名口径

| 产物 | 命名 |
|------|------|
| 书籍档案 | `<书名>书籍档案.md`（**无连字符、不带书名号**——下游脚本按此路径查档案，带横杠会查不到） |
| 课案详案 | `<书名>-课案详案.md` / `.docx` |
| 写作课详案 | `<年级册>-第N单元-<题目>-写作课详案.md` / `.docx`。**「第N单元」是写作课线全部产物的统一课次标识段**（2026-08-02 立）：配套物料/PPT/中间稿/打包的**子目录名与文件名前缀**一律同此口径，**PPT 文件名内也带课次标识段**（`<年级册>-第N单元-<题目>-课件PPT.pptx`，2026-08-26 改；旧口径「PPT 文件名内仍是纯题目、不带年级单元」已作废，存量 12 份已迁移，命名生成点在 `laojohn-ppt/scripts/place_pptx.py`）。**配套三侧的文件名后缀为 `-学生用/-教师用/-家长用`**（同日由 `-X合订` 改）；**打包目录单层平铺、无子文件夹**（同日撤掉 `课件PPT\`、`配套物料\` 两层，仅写作课线）。**文内标题与环节命名体例的唯一源＝`writing-lesson/references/title-naming.md`**；改体例须同时改其 `lesson-structure.md` §三与 `checklist.md`——三处曾自相矛盾 |
| 看图写话详案 | `<年级册>（<季>）第 N 次 · <课型>.md` / `.docx`（**不带主题、不带「看图写话详案」尾缀**）。**一课次一目录**（2026-08-03 立）：四件与 `图位\` 同住 `看图写话详案输出\<课次>\`，目录名＝文件 stem；**`图位\` 的完整路径未变**，故存量取图口径（配套稿纸 `anchor_img`、打包 glob、冷审核图）不受影响。标题体例＝三行（唯一源 `picture-writing/references/title-naming.md`），其中 `######` 期次副标**承载文件名口径、`style_front_page.py` 靠它判型，不可省**；期号仅为内部方法编号，禁入对外产物 |

> **与 README 的分工（勿再互指）**：完整的「SKILL → 输出目录 → 文件命名规则」对照表在 `README.md`「SKILL 与输出目录对照」；本节只留**命名错了下游会静默失效**的跨技能硬约束（路径查找、标识段贯穿全线、脚本靠副标判型），不重列格式细则。

## 8. 产物不进 git（提交纪律）

各输出目录的**渲染产物**（docx/pptx/pdf/jpg/渲染 html/png，及 `读书会整套文件打包输出\`、`读书会课件PPT输出\` 整目录）已 gitignore——它们都能从 md/json 源 + 引擎脚本重渲，只存本地不进仓库。**只提交 md/json 源与输入资产**（书籍档案、中间稿/讲稿 md、各 `_content.json`/`-manifest.json`、书籍封面、品牌资产、skill 参考件、看图写话图位 png）。提交前 `git status` 里不该出现产物文件；若出现，说明有人改了 `.gitignore` 或新增了未纳规则的输出目录——新输出目录要同步补 ignore 规则，**严禁用 `git add -f` 把产物强加回来**。

**「重渲不出来」的三类资产已于 2026-08-20 改为入库**（`读书会原书插图\`、`写作课教材插图\`、`写作课件PPT输出\`）。它们不是产物——前两者是版权扫描件、后者是外部平台生成的 pptx，共同点是**引擎重渲不出来**，所以 gitignore 掉就等于双人协作时 git 覆盖不到，两台机器静默分叉。先后试过 OneDrive（账号六年未登录成功、静默不同步）与坚果云（需另装客户端），最终判断：仓库本就私有、仅两人可访问，三者合计 79.5 MB（最大单文件 13.6 MB，远低于 GitHub 100 MB 硬限制），git 是唯一已跑通的通道。⚠ **这个体积数字已过时，且外部件必须压缩后才入库（2026-09-02 立）**：外部平台重做的 pptx 每份 13~22MB（本仓 `build_ppt.py` 烘焙的才约 1MB），一轮 7 份即 125.5MB，远超当初三类大件的总和；`.git` 已达 689MB、远程 549MB，GitHub 软建议 1GB，两三轮就触线，而 git 只进不出。**同日（09-02）用户拍板了根本解法：本仓工序止于动画注入，人工嵌图后的终稿不回本仓**——`写作课件PPT输出\` 存的是「审核过＋注入动画」的版本（约 1.5MB/份），终稿归档在外部平台/固定目录；连带 `laojohn-writing-package` 不再收 PPT（否则交付包混进无插图的半成品），页标仍以本仓这一版页码为准。详见 `laojohn-ppt/SKILL.md`「交付边界」。故压缩工序 `laojohn-ppt\scripts\shrink_pptx_media.py` **已从「入库前必跑」降级为「仅当单份 >5MB 时跑」**，常态下用不上；**只压新入库的件**——已在远程历史里的旧件压了也收不回，反而再叠一版。

⚠ **这推翻了此前「原书扫描件永不入库」的规定**，是明确决策、不是有人手滑 `git add -f`。三条连带口径同时变更：
- **「换机器后配图版详案报『缺图待补』是预期行为」这条已作废**——新克隆现在自带全部插图，**再报缺图就是真出问题了，必须排查**（多半是文件名与 `_图单.md` 对不上，或 `【图位:插-NN】`占位写错）。旧稿里凡见到「缺图属预期」的说法一律以本条为准。
- **git 只进不出**：入库即永久留在历史里，日后要撤须 `git filter-repo` 重写全部历史并 force push、两台机器重新 clone。故**不要往这三个目录里放与备课无关的东西**。
- **版权材料仅限内部备课使用，不得再行转发**；`_图单.md` 仍是取图与追溯的凭据，照常入库。

## 9. 双人协作 · 同步口径（2026-08-20 立）

项目由两人在两台机器上接力生产（一人写粗稿、另一人审核优化）。**判据只有一条：这东西引擎重渲得出来吗？**

| 内容 | 通道 |
|---|---|
| 源文件（md / json / py / skill / 封面 / 图位 png）、项目记忆 `.claude\memory\`、**三类重渲不出来的大件**（`读书会原书插图\`、`写作课教材插图\`、`写作课件PPT输出\`） | **全部走 git**（`github.com/wuwenjia6498/laojohn-lesson-plan`，私有） |
| 渲染产物（docx / pdf / pptx / jpg / 渲染 html） | **不同步**，两边各自本地重渲 |

> 曾设计过「源文件 / 记忆 / 大件」三层通道，大件走网盘。2026-08-20 大件并入 git 后该设计作废，**根 `sync_assets.ps1` 已删除**——见下第二条。

五条不可推断的硬线：

- **项目记忆已迁入仓库**（原在 Claude Code 用户目录 `C:\Users\<用户>\.claude\projects\<路径编码>\memory\`，在 git 之外、双机必然分叉）。现在事实源＝`.claude\memory\`，用户目录那份是**指向它的目录联接**（`mklink /J`，不需管理员权限）。**联接断了不报错**——表现只是「什么都不记得」，此后踩过的坑全部重踩；自检话术＝问一句「这个项目有哪些跨技能硬约束」。改动记忆目录位置或写记忆的路径前，必须想到这条联接。
- **大件已并入 git，网盘方案整条作废**（2026-08-20）。三类重渲不出来的资产直接入库，理由与连带口径见 §8。曾依次尝试并否掉两条路，**记下来是为了别再走一遍**：① **目录联接挂网盘**——`mklink /J` **只能建在 NTFS 卷上**，本项目常驻 exFAT 移动硬盘，在项目内建直接报 `Local NTFS volumes are required`；**记忆那条联接之所以成立，是因为它建在 C 盘、只是指向项目，方向不可颠倒**（这一条仍然有效，改动记忆联接时必须记得）。② **网盘 + 同步脚本**——本机 OneDrive 六年前就掉线（`LastSignInTime` 停在 2020-02-13），进程照跑、目录照在、文件照放，**全程零报错**，放进去的 80MB 一个字节都没上云。由此得到一条通用判据：**任何网盘通道都必须以「网页端看得到」验收，「本地有文件」永远不能证明「云端有文件」**。
- **产物不同步是有意的**（§8 已立不入库，这里补协作侧的后果）：对方审改后推上来的只有详案 `.md`，**最新 docx 必须自己重渲**，且渲染必带 `--header-left/--header-right`（漏传静默回落读书会页眉）。别把「我这边 docx 是旧的」当成同步坏了。
- **交球靠 commit 前缀 `[稿]`/`[审]`/`[定]` ＋ 根目录 `协作看板.md`**。`MEMORY.md` 与 `协作看板.md` 是仅有的两个高频冲突点（两人都会往里追加行）——**冲突时两边新增的行都保留，不选边**。给人看的完整操作规程在 `docs\协作同步说明.md`，本节只留跨技能硬约束。
- **仓库是私有的，且提交身份禁止照抄历史作者**（2026-08-20 补）。私有意味着**未受邀者 `pull` 同样不可用**，不只是推不上去——新机器接入前拿不到任何更新，这是权限问题、不是链路坏了。而新机器上没有 git 身份配置时提交会失败，此时**照着 `git log` 里的作者补是错的**：仓库历史长期只有一个作者，照抄的结果是两人的提交全署同一个名，`git log` 里彻底分不清谁写的稿、谁审的——而接力分工恰恰只有作者字段是无争议的归属证据。身份一律配**仓库局部**（`git config --local`）、用本人的 GitHub 邮箱。**趁未推送时订正是一条 `--amend --reset-author`，推上去之后就是改写已发布历史**，代价完全不同。
