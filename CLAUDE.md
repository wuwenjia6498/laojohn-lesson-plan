# CLAUDE.md · 老约翰深度阅读课案生产工作台

本文件是给 AI agent 看的**跨技能硬约束**。完整目录结构、数据流图、各 SKILL 输出目录对照、生产流程，见 `README.md`——本文件不重复，只固化"改任何 SKILL/脚本都必须守住"的不变量。

---

## 1. 移动硬盘 · 路径约定（单一声明）

本项目存放在移动硬盘，盘符随挂载变动（`e:\`、`h:\` 等）。所有 SKILL 与脚本以 `<项目根目录>` 表示项目路径：**执行前用 `(Get-Location).Path` 确认实际盘符，禁止硬编码盘符。** 各 SKILL.md 里重复的这段警告以本条为准。

**本机渲染/脚本环境（跑任何 python 物料脚本都适用，踩中会静默失败或乱码）：**
- **用 `python`，不要 `python3`**——`python3` 是 Microsoft Store 占位别名，会以 exit 49 直接退出。
- **跑渲染脚本前先 `export PLAYWRIGHT_BROWSERS_PATH="C:/Users/69491/AppData/Local/ms-playwright"`**，否则 Playwright 去找不存在的 `/opt/pw-browsers` 报错。
- **python 命令一律加 `PYTHONUTF8=1`**，避免脚本里 ✓ 等字符触发 GBK `UnicodeEncodeError`、中文路径乱码。

## 2. 数据流主链

```
laojohn-book-profile（建档 · 下游唯一事实来源）
        └─→ laojohn-lesson-plan（整本书课案详案）
                └─→ ppt-draft→ppt / book-card / course-poster /
                    reading-guide / lesson-mindmap / teaching-mindmap / course-feedback
```

- **书籍档案是事实源头**：lesson-plan 生成详案时不再翻原书，只依赖 `书籍档案\<书名>书籍档案.md`。档案错一处、详案跟着错一处，且下游无从发现。
- **书目/出版类基本信息（出版社/字数/页数/ISBN/出版年/译者/作者/类型/主题/获奖）的唯一固定源 = 书籍档案的 `## 海报/指南元数据` 机读块**。课案是教学文档、不收录这些字段，所以书目卡/海报/阅读指南/抢先看导图/反馈话术要这类信息时一律从该机读块取（book-card、course-poster 脚本正则解析，其余物料由 AI 读取）；绝不从课案正文猜或凭记忆补。
- **缺失字段的呈现：「待补充」只存在于书籍档案机读块（人工回填提示），绝不进入对外物料**。生成的成品里某项基本信息没有就**留空白**——信息表/信息栏保留栏位、值空白（不写"待补充/请回填"、不画占位框）；获奖块、思维导图节点这类列表项缺失则**整条隐藏**；反馈话术等正文缺页数就不提，不写「【请补充…】」。
- **`laojohn-writing-lesson`（写作/习作课）是独立平行分支**：吃「习作主题 + 年级」+ `references/archive/` 习作档案，**不进**上面这条以书籍档案为源头的链路。

## 3. 共享资产 · 单一事实源（禁副本）

新增/换图一律改这里，不要在 skill 内另存副本：

| 资产 | 唯一源 | 谁在用 |
|------|--------|--------|
| 品牌 logo / 二维码 | `品牌资产\logo.png`、`品牌资产\qrcode.png` | book-card、course-poster |
| 书籍封面 | `书籍封面\<书名>.jpg/png`（书名不带书名号） | poster、book-card、reading-guide |
| 书籍档案 | `书籍档案\<书名>书籍档案.md` | lesson-plan 及所有消费档案的下游 |
| docx 排版引擎 | `.claude\skills\laojohn-lesson-plan\assets\md_to_laojohn_docx.py` | lesson-plan、writing-lesson（跨技能复用同一条流水线） |

> 现存物理副本（`laojohn-ppt\assets\logo\`、`laojohn-course-poster\assets\qrcode.png` / `assets\covers\`）属历史遗留；以根目录单一源为准，勿据副本做新决策。

## 4. 详案类两核心共用的不变量（lesson-plan / writing-lesson）

两个核心 SKILL 先后独立开发，以下骨架两边必须一致，改一处要想到另一处：

- **中文弯引号铁律**：正文一律全角 `""` / `''`，**严禁** ASCII 直引号 `"` `'`（Markdown 语法/代码/英文路径除外）。源 `.md` 阶段就要正确，不依赖引擎安全网兜底；旧文件批修用根 `fix_quotes_md.py`，校验用 `check_quotes.py`。
- **行内强调禁令**：正文禁用 `**` `*` `__`（引擎不解析，星号会原样印进 docx）。
- **固定话术骨架**：`师：`（师话）/ `参考：`（参考答案）/ 整行 `学生互动分享`·`学生自由分享` / `（教师总结）`。
- **三维目标标签**：`【知识技能】` / `【过程方法】` / `【情感价值】`。
- **收尾**：每课时末 `本课完。`，全文末 `全课完。`。
- **交付双道工序**：先逐项 `checklist.md` 自检，再独立复盘 `review-rubric.md`（"审稿人协议五条"：身份重置 / 默认有问题 / 先摘后算 / 量化下限 / 真实性红线不豁免）。
- **真实性红线**：伪摘录禁令——无可逐字核对的真实原文，禁止输出带引号的"原文"或"——节选自…"，一律占位；事实/页码/情节只来自档案，不得凭模型记忆补写（越是名作越易记错）。

## 5. 全项目废弃约定

- **`【PPT换页-PXX】` 已废弃**（lesson-plan、writing-lesson 详案均不再写）。分页权归 `laojohn-ppt-draft`，由它按"教学节拍"自行切页；详案只需 `## 第N课时 · 课型` 划课时、`### 一、xx` 划环节。
- docx 引擎仍把残留换页点渲染成橙色，**仅为向后兼容旧 docx**，新稿一律不产出。

## 6. 两核心 SKILL 的边界（防混用）

| | laojohn-lesson-plan | laojohn-writing-lesson |
|---|---|---|
| 对象 | 整本书阅读读书会 | 校内同步习作（写作）课 |
| 技法 | **不讲写作技法** | **正面讲技法是本分**（阅读课的"不讲技法"铁律不适用） |
| 课时 | L1/L2 两节、L3–L6 四节，每节 60 分钟 | 固定两节连排，每节 45 分钟 |
| 吃什么 | 书籍档案 | 习作主题 + 年级 + `archive/` 习作档案 |

**依赖声明**：`writing-lesson` 单向复用 `lesson-plan` 的资源——docx 引擎、`assets\课案Markdown约定规范.md`、`references\visualization-tools.md`、`references\grade-structure.md`（L1–L6 人设）。**改动这些文件的路径或契约前，必须同步检查 writing-lesson 是否受影响**（它没有自己的副本，会静默失效）。

## 7. 命名口径

| 产物 | 命名 |
|------|------|
| 书籍档案 | `<书名>书籍档案.md`（**无连字符、不带书名号**——下游脚本按此路径查档案，带横杠会查不到） |
| 课案详案 | `<书名>-课案详案.md` / `.docx` |
| 写作课详案 | `<年级册>-<题目>-写作课详案.md` / `.docx` |

各物料的输出目录与文件命名权威表见 `README.md`「SKILL 与输出目录对照」（此处不重列，避免双写漂移）。
