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
- **Playwright 浏览器路径一般无需手动 export**：各渲染脚本已在脚本内回退到本机默认 `C:/Users/69491/AppData/Local/ms-playwright`（2026-07-27 根治并回归三线；此前 poster/两导图曾把缺省值写死成 Linux 路径 `/opt/pw-browsers`）。换机器或路径异常时再 `export PLAYWRIGHT_BROWSERS_PATH=…` 覆盖（环境变量优先于脚本缺省值）。
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

新增/换图一律改这里，不要在 skill 内另存副本：

| 资产 | 唯一源 | 谁在用 |
|------|--------|--------|
| 品牌 logo / 二维码 | `品牌资产\logo.png`、`品牌资产\qrcode.png` | book-card、course-poster |
| 书籍封面 | `读书会书籍封面\<书名>.jpg/png`（书名不带书名号） | poster、book-card、reading-guide |
| 原书插图 | `读书会原书插图\<书名>\插-01.png`（书名不带书名号，编号全书连号、半角连字符）+ 同目录 `_图单.md` | lesson-plan 配图版详案（后续可接 PPT 上屏/阅读单）。**扫描件＝版权材料，已 gitignore、永不入库**；`_图单.md` 入库，是唯一可追溯凭据。**书籍封面绝不挪进此目录**——引擎找不到封面是静默跳过，一挪就丢封面页且不报错 |
| 书籍档案 | `读书会书籍档案\<书名>书籍档案.md` | lesson-plan 及所有消费档案的下游 |
| docx 排版引擎 | `.claude\skills\laojohn-lesson-plan\assets\md_to_laojohn_docx.py` | lesson-plan、writing-lesson、reading-assessment（跨技能复用同一条流水线；assessment 用法见 §2 末条）。**页眉经课型无关的可选参数 `--header-left/--header-right` 传入**：读书会缺省「老约翰深度阅读／阅读·思辨·表达」，看图写话「老约翰·看图写话／从看懂一幅图，到写成一个故事」，同步习作「老约翰·同步习作／写清楚·写生动·有章法」——各 SKILL 导出时必带，漏传即回落读书会页眉 |
| docx 首页版式化 | `.claude\skills\laojohn-lesson-plan\assets\style_front_page.py` | picture-writing、writing-lesson 两线共用。把共享引擎产的朴素首页重排为**提纲页定稿版式**（picture＝三区分区表、writing＝无区头单表 6 行，版式细节见脚本头注释与两线各自 `lesson-structure.md`）；**课型差异全收敛在脚本顶部 `PROFILES` 表，禁 fork、禁往渲染原语里塞课型分支**；改它须同时回归两条线 |
| docx 正文图回插 | `.claude\skills\laojohn-lesson-plan\assets\insert_images_docx.py` | picture-writing（`scripts\insert_images_docx.py` 是 importlib 薄 shim，只注入 `imgspec_parser.image_dir` 取图口径）、lesson-plan（读书会原书插图配图版）、writing-lesson（`writing` 档 · 统编教材习作页原图，2026-07-31 接通）。**二段式后处理**：先调共享引擎出基础 docx（占位原样印为文字），再用 python-docx 把 `【图位:编号】` 换真图——**故引擎侧不新增 `![](…)` 解析分支**（那会牵动全部 5 个消费者回归）。**课型差异全收敛在顶部 `PROFILES` 表，禁 fork、禁往渲染原语塞课型分支**；改它须同时回归看图写话三课次与读书会配图版。**取图目录名的取法也是 `PROFILES` 数据（`name_from`）**：读书会取 H1 里的《书名》，写作课取文件名去尾缀（写作课 H1 是《题目》、不含年级册，而目录名是 `<年级册>-第N单元-<题目>`，取标题必错）。⚠ **凡 `PROFILES` 里有的字段，CLI 与上游脚本默认值一律 `None`**——给硬默认会永久盖住课型档且完全静默（docx 打开只是图偏大，无任何报错）。共享件**绝不 import `imgspec_parser`**（那是 picture-writing 私有模块，反向依赖会让读书会线故障依赖看图写话文件树） |
| PPT 渲染原语 | `.claude\skills\laojohn-ppt\scripts\helpers.py`（文本框/表格/字体/点击动画/渐变/占位等底层件）+ `parser.py`（中间稿解析） | laojohn-ppt 读书会与写作课两 profile 共用；有 bug 史的横切层（字体槽顺序、表格自适应等修一处即重烘焙全部），**永不 fork、禁 `doc_kind`/课型分支** |
| 学习单渲染引擎 | `.claude\skills\laojohn-reading-sheet\scripts\render.py`（PDF/HTML）+ `render_pptx.py`（可编辑 PPTX）+ `templates\`（模板库） | reading-sheet（整本书阅读单）专用；`render.py` 的 `--templates-dir`/`--bundle-label` 是课型无关的可选参数（reading-sheet 自用，`--bundle-label` 默认「阅读单」），保留不删 |
| 配套物料 HTML→PDF 渲染引擎 | `.claude\skills\laojohn-writing-materials\scripts\_shared.py`（`inject`/`render`/`safe_pdf`/`check_pages`/`out_base`，Playwright 出 A4 PDF + logo base64 内联 + pypdf 页数核验） | writing-materials（同步习作配套）与 picture-materials（看图写话配套）两线共享单一源。picture-materials 的 `scripts\_shared.py` 是薄 shim（importlib 按路径载入本引擎，零逻辑），**禁复制**；`inject`/`render` 的可选 `extra_images={token:图路径}`（稿纸主图注入用）是课型无关参数，改签名/删该参数须同时回归两线。⚠ 与下面三件**不是同一个引擎**：本件出固定 A4 多页（210mm×297mm），下游物料出单页动态高，两种输出模型不可互相塞分支 |
| 书籍档案机读块解析 | `.claude\skills\laojohn-book-profile\scripts\profile_meta.py`（`read`/`is_blank`/`meta_section`/`simple_field`/`award_list`） | book-card、course-poster 的 `extract_fields.py`（各以 importlib 载入，**禁复制正则**）。归 book-profile 是因为机读块格式由它定义（键名见其 `assets\book-profile-template.md`）——谁定义格式谁给解析器。`BLANK_MARKERS` 是两线并集，改它同时影响两个物料的"缺失留空"判定 |
| 读书会 JPG 长图渲染引擎 | `.claude\skills\laojohn-book-card\scripts\_jpg_render.py`（`norm`/`find_cover`/`data_uri`/`shoot`，定宽 viewport + 2× 截 `#page`） | book-card（书目卡 900px/q93）与 course-poster（海报 1242px/q92）。**两家历史口径差异全部参数化**：`strip_parens`（书名归一化是否去圆括号，卡 True／海报 False）、`fallback`（封面匹配不到时，卡留空／海报占位图）——**不要为了"统一"而改默认值，会改变既有产物** |
| 读书会 A4 单页 PDF 渲染引擎 | `.claude\skills\laojohn-reading-guide\scripts\_a4_render.py`（`build_html`/`render`/`main`，宽 794px、高 `max(1123, #page.scrollHeight)` 单页动态高不分页） | reading-guide、lesson-mindmap、teaching-mindmap 三家，后两家 `render_pdf.py` 是 importlib 薄壳。**`recenter_on_overflow`：两种导图传 True**（居中放射版式，超页需重设 min-height），**阅读指南保持 False**（文档流版式，打开会推开版式） |

> 现存物理副本（`laojohn-ppt\assets\logo\`、`laojohn-course-poster\assets\qrcode.png` / `assets\covers\`）属历史遗留；以根目录单一源为准，勿据副本做新决策。

**PPT 引擎按课型分 profile（接缝原则）**：`laojohn-ppt` 分两层——共享层 `helpers.py`/`parser.py`/`build_ppt.py` 课型无关、单一源；呈现层按 profile 分模块（`layouts_common.py`/`layouts_reading.py`/`layouts_writing.py`/`theme_writing.py`），按中间稿元信息 `文体：写作` 选 profile（缺省=读书会）。**新增写作课视觉/页型时只动 writing 模块 + theme_writing，绝不往 reading renderer 或 helpers 里塞课型分支**——否则共享引擎退化成条件分支堆。页型在某 profile 下是否有效按其 `RENDERERS_<profile>` 字典裁决（读书会 6 种；写作课自成一套，弃用 引导问题/要点小结）。页型清单、写作专属页型视觉、v8 版式选择器等实现细节见 `laojohn-ppt/references/architecture.md`；写作页型字段写法的唯一源 = `laojohn-ppt-draft/references/writing-mode.md` §2/§2.5/§2.6/§2.7。

**写作课 PPT 已改「外部生成 + 本仓动画后处理」（2026-08-03 立 · 仅写作课线）**：写作课的 .pptx **不再由本仓 `build_ppt.py` 烘焙**，改由外部平台生成后复制进 `写作课件PPT输出\<年级册>-第N单元-<题目>\`，本仓只做动画处理。两段式工具（均在 `laojohn-ppt/scripts/`）：`inspect_pptx.py` 勘查形状、按卡片聚簇出**建议**分组工作单 JSON → 人工校正顺序与取舍 → `animate_pptx.py` 注入逐条点击淡入。**分组是教学判断，几何启发式只给构成、给不出教学顺序**（实测样本里页面最底部那句结论是第 3 次点击而非最后一次），故必须人工过一遍。动画 XML 一律走 `helpers.add_click_reveal`，**禁在新脚本里复制那段时间树**。完整后处理链＝**归位 → 动画 → 详案页标回注**（一句话入口「<题目> 的 PPT 放好了，处理一下」，手册在 `laojohn-ppt/SKILL.md`）。三条连带口径：① 外部件可能**两节合一**，此时 pptx 命名用 `<题目>-全课.pptx`，「每节课独立 PPT 不合并」对写作课线不再是硬线；② **写作课线的逐页讲稿已停产**（2026-08-03，`写作课件讲稿输出\` 目录已撤、存量已删、打包档已撤；读书会线照旧），中间稿降级为外部平台的生成依据（详见 `laojohn-ppt-draft/SKILL.md`）；③ 外部平台产的文本常带 ASCII 直引号，与全仓弯引号铁律冲突，**投屏前须核**。**读书会线不适用**——`读书会课件PPT输出\` 仍由 `build_ppt.py` 正式烘焙，两套口径不得混用。

## 4. 详案类两核心共用的不变量（lesson-plan / writing-lesson）

两个核心 SKILL 先后独立开发，以下骨架两边必须一致，改一处要想到另一处：

- **中文弯引号铁律**：正文一律全角 `""` / `''`，**严禁** ASCII 直引号 `"` `'`（Markdown 语法/代码/英文路径除外）。源 `.md` 阶段就要正确，不依赖引擎安全网兜底；旧文件批修用根 `fix_quotes_md.py`，校验用 `check_quotes.py`。
- **行内强调克制**：正文流水句里不做行内强调；**尤其禁用单星/单下划线斜体 `*…*`、`_…_`——引擎不解析这两者，会把星号/下划线原样印进 docx**。成对的 `**…**`／`__…__` 引擎会转成真实加粗、未配对的残余标记自动剥除（不会泄漏星号）。整行的 `**小标题**` 引擎会识别成加粗小标题，但**两 skill 的写法政策不同**：**lesson-plan 用它**（如 `**本节三维目标**`）；**writing-lesson 更严、连整行 `**` 也不用**，教学目标（核心素养四维）等小标题改用 `【】` 标签与固定话术骨架承载，详案检索 `*` 应为零。两 skill 共用同一引擎，差异是各自的写法政策、非引擎能力——单星斜体两边都禁，是唯一对两 skill 完全一致的硬线。**同理禁用任何 HTML 样式/高亮标签承载强调**（`<mark>`／`<b>`／`<u>`／`<span>` 等）：引擎不解析这些标签，会把 `<mark>…</mark>` 之类原样印进 docx（曾在《格列佛》详案泄漏两处）；行内强调一律只用 `**`，需要「下节课再议」这类伏笔用文字直说、不靠视觉高亮。唯一放行的 HTML 是引擎明确支持的表格换行 `<br>` 与整块跳过的注释 `<!-- -->`。此禁对两 skill 同样是硬线。
- **固定话术骨架**：`师：`（师话）/ `参考：`（参考答案）/ 整行 `学生互动分享`·`学生自由分享` / `（教师总结）`。
- **教学目标标签（⚠ 三条线已各走各路）**：lesson-plan（读书会）仍用三维 `【知识技能】`/`【过程方法】`/`【情感价值】`；**writing-lesson 与 picture-writing 均已取消独立教学目标节**——writing-lesson 的核心素养四维 `【语言运用】` 等于 2026-07-22 停用（此前 2026-06 的四维改制作废），目标改由首页提纲表「核心技法」＋「学习目标」两行承载（唯一源：`writing-lesson/references/lesson-structure.md` §四）；picture-writing 于 2026-07-21 同样取消，由「教学内容」「学习目标」＋各课时「本课目标」承载。两写作线详案检索四维标签应为零。`【】` 标签承载机制、及"标签为既定符号、不进语言风格红线"的处理仍三线共用。
- **首页形态（writing-lesson / picture-writing 两线已分形态，勿互抄）**：两线书级头部都在 `## 教案提纲表` 下写两列表，docx 侧由共享的 `style_front_page.py` 重排（见 §3）——**picture-writing＝三区**（各区以整行加粗区头 `**N、区名**` 起头，只写区名、不带 `—— 副题`）；**writing-lesson＝无区头单表 6 行**（2026-07-29 用户定稿，区头与「怎么落地」行一并删除，课时信息回到「课题·课时」行末段）。行名口径＝教研通用词。三条不可推断的硬线：① **行名是 `style_front_page.py` `PROFILES[*]["rules"]` 的键，改 md 必同步改脚本**，否则该行掉回 `plain` 样式；② 线名行在本课名后打「（本课）」标记；要点区值内可用成对 `**…**` 强调（writing 全文 `*` 禁令在提纲表节内放行）；③ **行名与事实源各自不同、不得互抄**——picture-writing 取 `picture-writing/references/course-map.md`（24 方法·四学期 64 课次），writing-lesson 取 `writing-lesson/references/course-map.md`（六阶轴 + 63 任务全表）。具体区划与行名清单以脚本 `PROFILES` 表＋两线各自 `lesson-structure.md` 为准。lesson-plan（读书会）不适用此形态。
- **收尾**：每课时末 `本课完。`，全文末 `全课完。`。
- **交付双道工序**：先逐项 `checklist.md` 自检（合规），再独立复盘 `review-rubric.md`（质量）。**第二道复盘已独立为冷启动执行**：由 `laojohn-detail-review` 承载，正常**派一个全新（fresh，非 fork）子 agent**或在新会话里跑，**不在生成会话里自审**（顺接自审会为自己的设计辩护，沦为走过场；无法另起时才降级为同会话「显式封存生成过程后自审」）。各 skill 的 `review-rubric.md` 是各自五维与审稿人协议的唯一源——detail-review 按文档类型加载、不复制内容，改 rubric 即同时改了冷审依据；现有三份 rubric（lesson-plan/writing-lesson/picture-writing）与 detail-review 判型表一一对应，**新增课型须同时补 rubric 与判型行**，否则冷审加载不到判据、空转。
- **上课场景现实约束（三条详案线通用 · 2026-07-31 立）**：老约翰是**校外机构课**，不是校内课堂。哪怕课型定位写着「校内同步习作」，那指的也只是**跟着校内教材进度走**，上课场景仍在机构——**学生手边没有课本/教科书，也没有校内作息**。故详案禁写「翻开课本」「书上第 X 页」「照课本上说的做」「找个晨读的时间」「课间」「班主任」这类假设；教材图、教材题面一律**投屏出示**，凡要学生看图看字的地方须确认投屏清晰。同族既有约束：教室无黑板白板、禁写板书，学生动手一律走学习单。**「校内同步」四个字最容易诱发这类误设，写作课线尤其要防。**
- **真实性红线**：伪摘录禁令——无可逐字核对的真实原文，禁止输出带引号的"原文"或"——节选自…"，一律占位；事实/页码/情节只来自档案，不得凭模型记忆补写（越是名作越易记错）。

## 5. 其它跨技能红线

- **「绝不联网」红线的作用域 + 看图写话生图例外口**：全仓「绝不联网、绝不凭记忆」红线**专指"事实不许凭网络或记忆补"**——书目/书封/页码/情节/人物只来自书籍档案（下游唯一事实源），不因网络搜到或模型记忆而混入。**`laojohn-picture-writing` 的自动生图闭环（按 imgspec 规格调 AiHubMix 文生图 + 多模态视觉验收）不属此禁**：方向与"从网络捞事实"相反——**规格是事实源、生成图必须服从规格**，并经「真图 vs 必须可见清单」自动验收 + 人工抽查双重把关（守门禁 4）。**铁律：生成插画不是"事实"，绝不可反过来用图去改写规格/正文的情节·数字**。此例外仅限看图写话生图；其余技能维持零网络调用。

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
| 写作课详案 | `<年级册>-第N单元-<题目>-写作课详案.md` / `.docx`（如 `三上-第一单元-猜猜他是谁-写作课详案.md`）。**「第N单元」是写作课线全部产物的统一课次标识段**（2026-08-02 立）：单元号用**中文数字**、取 `writing-lesson/references/course-map.md` §三全表的「单元」列，年级册与单元、单元与题目之间均用半角连字符；配套物料/PPT/讲稿/中间稿/打包的**子目录名与文件名前缀**一律同此口径（`<年级册>-第N单元-<题目>`），PPT/讲稿**文件名内**仍是纯题目、不带年级单元。**不在教材单元序列的自拟主题省略单元段**（`三年级-写秋天的公园-写作课详案.md`）。**文内标题与环节命名体例的唯一源＝`writing-lesson/references/title-naming.md`**（2026-07-26 定稿；看图写话那套 `｜` 分隔与 `######` 副标**不适用**本线）。改体例须同时改其 `lesson-structure.md` §三与 `checklist.md`——三处曾自相矛盾 |
| 看图写话详案 | `<年级册>（<季>）第 N 次 · <课型>.md` / `.docx`（如 `二上（秋）第 1 次 · 方法课.md`；**不带主题、不带「看图写话详案」尾缀**，课次/课型按 picture-writing `course-map.md` §四 64 课次表取）。**一课次一目录**（2026-08-03 立）：md/docx/配图 docx/生图提示词 txt 四件与 `图位\` 同住 `看图写话详案输出\<课次>\`，目录名＝文件 stem，顶层不再平铺任何详案文件——`图位\` 的完整路径未变，故存量取图口径（配套稿纸 `anchor_img`、打包 glob、冷审核图）不受影响。标题体例＝三行（唯一源 `picture-writing/references/title-naming.md`），其中 `######` 期次副标**承载文件名口径、`style_front_page.py` 靠它判型，不可省**；期号仅为内部方法编号，禁入对外产物 |

各物料的输出目录与文件命名权威表见 `README.md`「SKILL 与输出目录对照」（此处不重列，避免双写漂移）。

## 8. 产物不进 git（提交纪律）

各输出目录的**渲染产物**（docx/pptx/pdf/jpg/渲染 html/png，及 `读书会整套文件打包输出\`、`读书会课件PPT输出\`、`写作课件PPT输出\` 整目录）已 gitignore——它们都能从 md/json 源 + 引擎脚本重渲，只存本地不进仓库。**只提交 md/json 源与输入资产**（书籍档案、中间稿/讲稿 md、各 `_content.json`/`-manifest.json`、书籍封面、品牌资产、skill 参考件、看图写话图位 png）。提交前 `git status` 里不该出现产物文件；若出现，说明有人改了 `.gitignore` 或新增了未纳规则的输出目录——新输出目录要同步补 ignore 规则，**严禁用 `git add -f` 把产物强加回来**。

**唯一的例外类别：`读书会原书插图\` 里的图不入库，但它不是产物、也重渲不出来**——那是原书扫描件（版权材料），刻意 gitignore（与 `读书会书籍封面\` 全 tracked 相反：封面是可公开的书目图，这里是整页扫描）。所以换机器/新克隆后配图版详案必然报「缺图待补」，这是预期行为，不是链路坏了；补图凭据是各书同目录的 `_图单.md`（**它入库**）。**别为了「让 git 完整」把扫描件强加进来。**
