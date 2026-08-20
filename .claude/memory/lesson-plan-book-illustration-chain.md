---
name: lesson-plan-book-illustration-chain
description: 读书会详案原书插图链路已落地(0730):新顶层目录+回插件升共享件PROFILES;附三条回归方法坑
metadata: 
  node_type: memory
  type: project
  originSessionId: dda14290-74bf-4d41-9824-2df60aa644ae
  modified: 2026-07-30T03:42:54.280Z
---

2026-07-30 为《神笔马良》L2 详案引入原书插图，落地了「读书会详案配图」这条链路（本次只做详案 docx，PPT 上屏与阅读单吃图**未做**，用户已知并同意分期）。

**图片落点＝新顶层目录 `读书会原书插图\<书名>\`**（与 `读书会书籍封面\` 同层，属跨链路共享输入资产）：`插-01.png` 两位编号、全书连号、半角连字符，也认 `.jpg/.jpeg`；同目录 `_图单.md`（出处/画面描述/拟用环节）**入库**，扫描件本身**2026-08-20 起已入库**（私有仓库；旧口径「永不入库」已作废，见 [[two-person-sync-0820]]）。**封面绝不挪进此目录**——引擎找不到封面是静默跳过，一挪丢封面页且不报错。

**详案写法**：`【图位:插-01｜图注】` 单独成行紧跟师话，全角 `｜` 后是图注（渲染成图下方 10.5pt 灰色小字）。**禁 `![](…)`**——引擎不解析，会把源码原样印进 Word。规则写进 `课案Markdown约定规范.md` §10 + `checklist.md`「原书插图」5 条。

**架构**：看图写话的回插件升为共享件 `laojohn-lesson-plan\assets\insert_images_docx.py`（同 `style_front_page.py` 成例：后处理层 + 顶部 `PROFILES` 表收敛课型差异），picture 侧改 importlib 薄 shim 只注入 `imgspec_parser.image_dir`。**共享件绝不 import imgspec_parser**（私有模块，反向依赖会让读书会线故障依赖看图写话文件树）。前缀集收敛为 `imgspec_parser.CODE_PREFIXES` 单一常量（原「三处正则须同步」的警告已可作废）。`插` 与 `主练备格锚例` 天然隔离、互不误认。

**Why**：共享 docx 引擎有 5 个消费者（16 本读书会详案/writing-lesson/picture-writing/reading-assessment/lecture_notes_to_docx），为一条链在它里面加 `![](…)` 分支要回归全部，收益代价严重不匹配。

**How to apply**：
1. **凡 `PROFILES` 里有的字段，CLI 与上游脚本默认值一律 `None`**——给硬默认会永久盖住课型档且**完全静默**（docx 打开只是图偏大，无任何报错）。`build_picture_lesson.py` 原本 `--width-cm default='12'` 就是这个坑的上一层实例，已一并修掉。
2. **回归基线必须是「同 md + 同引擎，旧脚本 vs 新脚本」**。直接拿存量 `-配图.docx` 当基线会误判：7 月那批产物重渲后 paras/tables 本就变了（md 或引擎期间有改动），与本次改动无关。正确做法＝`git show HEAD:<脚本>` 取旧版并排跑，比正文文本 sha256。
3. 比 docx 一致性**别用 `hash()`**（按进程随机化，不可比），用 `hashlib.sha256`。
4. **探针脚本别叫 `inspect.py`**——撞标准库，lxml 内部 `import inspect` 会拿到它，报 docx 循环导入。
5. 有封面页的详案是**两节**，页眉在 `sections[1]`；`sections[0]`（封面节）页眉刻意为空，探针只看 sec0 会误判「页眉丢了」。

相关：[[docx-engine-title-heading-layout]]、[[picture-writing-generate-locally]]、[[downstream-shared-layer-and-token-facts]]
