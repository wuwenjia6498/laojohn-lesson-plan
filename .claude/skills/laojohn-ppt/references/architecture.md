# PPT 引擎架构 · 按课型分 profile（接缝细则）

> 接缝原则（永不 fork、禁课型分支）本体在根 `CLAUDE.md` §3——那里是跨技能硬约束的唯一源；本文件承接其下的实现细节，2026-07-27 由 CLAUDE.md 下沉至此。改本文件不需要动 CLAUDE.md；改接缝原则本身必须先改 CLAUDE.md。

## 一、两层结构

- **共享层（课型无关、单一源）**：`scripts/helpers.py`（文本框/表格/字体/点击动画/渐变/占位等底层件）、`parser.py`（中间稿解析）、`build_ppt.py`（装配主流程）。
- **呈现层（按 profile 分模块）**：
  - `layouts_common.py`——公共元素 + 参数化封面基函数 + END 页；
  - `layouts_reading.py`——读书会 6 页型 `RENDERERS_READING`；
  - `layouts_writing.py`——写作课 `RENDERERS_WRITING`；
  - `theme_writing.py`——写作课视觉变体；
  - `layouts_promo.py`——对外宣讲 `RENDERERS_PROMO`（2026-08-24 新增，非课堂件）；
  - `theme_promo.py`——宣讲视觉变体（取已发布招生海报的品牌色板，不沿用课件深灰蓝）。
- `build_ppt.py` 按中间稿元信息 `文体：` 查 **`PROFILES` 表**选 profile（**缺省 = 读书会**，向后兼容）。
  该表是**唯一分派点**，新增课型只加一行：

  ```python
  PROFILES = {"": RENDERERS_READING, "写作": RENDERERS_WRITING, "宣讲": RENDERERS_PROMO}
  ```

  查不到即显式报错。**刻意不用「非写作即读书会」的三元式**——那样 `文体：写作课`
  （多打一个字）会静默落回读书会 renderer，整份稿按错版式烘出来还不报错。
- **新增课型的视觉/页型时只动该 profile 的 layouts_* + theme_*，绝不往 reading/writing renderer 或 helpers 里塞课型分支**——否则共享引擎退化成条件分支堆。

### ⚠ 两个页型名不可改（改了完全静默）

`封面` 与 `环节标题` 这两个字符串是 `build_ppt.py` 里**课型无关逻辑的判据**：
前者决定「首页不是封面就自动补一页」，后者决定「按环节标题自动编章节序号」。
任何 profile 都必须沿用这两个名字。若为了「宣讲件叫章节页更自然」把名字改掉，
会同时丢掉自动封面判定与章节编号，**且不报任何错**。

## 二、页型枚举按 profile 裁决

`parser.PAGE_TYPES` 是语法全集；某页型在某 profile 下是否有效，按该 profile 的 `RENDERERS_<profile>` 字典裁决。

- **读书会 6 种**：封面 / 环节标题 / 引导问题 / 原文齐读 / 要点小结 / 填空表格。
- **宣讲 12 种**（`文体：宣讲`）：封面 / 环节标题（章节大间隔页）/ 主张 / 数据面板 /
  体系全景 / 流程时间轴 / 并列卡片 / 双栏对照 / 图集 / 满屏图 / 收尾 / 要点小结（清单页），
  另有自带的 `_END`（**不出现「THE END / 下一次再见」**，见第五节）。
- **写作课自成一套**：
  - 共用：封面 / 环节标题 / 填空表格（构思表·五感表·评价量表）；
  - **弃用**：引导问题 / 要点小结（读书会"思辨追问"的 Q 水印 + 红方块隐喻，套写作讲解会把连贯话切碎）；
  - 写作专属页型见下节。

## 三、写作专属页型

| 页型 | 用途与视觉 |
|------|-----------|
| **情境任务** | 设定情境/发布任务/课尾寄语，整段陈述不拆编号 |
| **写法讲解** | 讲写法·归纳要点·开放问句；克制序号：并列圆点·有序描边序号，去 Q 水印 |
| **活动指令** | 组织学生动手做；步骤条：深灰蓝方块 + 竖连接线 |
| **示范文** | 整篇教师范文塞一页、字号按字数自适应缩放，不拆页（区别于读书会原文齐读的大字满屏单段）。**默认分句上色**——`图例` 声明码=名、正文 `[码:片段]` 标注，渲染成顶部颜色图例 + 正文按手法上色，把"哪句写颜色/声音/比喻/中心句"显性化 |
| **双栏对照** | 审题辨析/评改对照/逐句批注，左右并置 |
| **写作任务** | 静默写作定格，计时/字数 chip |
| **实景观察**（v8） | 给学生看真实场景图 + 逐感官追问：图上·绿说明条·图外问答·答案红字点击；`场景：图=｜名=｜问=｜答=` 重复行 |

- **全课统一分类上色**：同一课的五感观察表（填空表格）、旁批表（双栏对照行模式）可复用示范文的同一 `图例`（同码同序）做单元格分类上色，三页颜色全课统一——调色板单一源 `layouts_common.CATEGORY_PALETTE`，`add_table(cell_colors=)` 纯参数化不分课型。
- **旧页型兜底**：写作 profile 的 `引导问题/要点小结` 渲染器**重定向到 `render_teach`（去水印兜底）**——即便残留旧中间稿也不出 Q 水印/红方块。

## 四、v8 可选视觉版式选择器

- 字段：`标题样式：强调/竖条`、`要点样式：竖排/卡片/卡片强调/步骤/图文/节点`、真图通道 `配图建议：图=<路径>`。
- 适用范围：写作 profile 用；`render_teach`/`render_task_intro` 认，`render_activity` 不认。
- 不声明 = 默认版式，向后兼容；带 `参考：` 答案的页版式让位问答揭示。

## 四点五、读书会 v9 新样式（按书主题色 + 图感知版式，2026-10-06）

- **开关**：中间稿元信息 `主题色：<色名>`（parser → `Deck.theme_color` → ctx 透传）。不写＝现行样式，存量书重烘逐形状不变（回归基线：8 本 32 份读书会＋写作 4 份＋宣讲 1 份＋各 examples，共 41 份）。
- **分派位置**：`layouts_reading.py` 各 renderer 开头 `th = _v9(ctx)`，声明了就转 `layouts_reading_v9.py` 的同名函数；旧代码一行不动。这是读书会 profile **内部**的样式变体，不是课型分支，共享层不知情。
- **色板**：`theme.READING_THEMES`（蓝／橙／灰蓝／绿，每色含 main／band／answer／card 四槽），`resolve_reading_theme` 查不到即报错。用 ctx 传而不改 theme 模块属性：各模块 `from theme import X` 在 import 时就固定了名字，函数默认参数也在定义时求值，改模块属性传不过去，还会串到复用读书会 renderer 的写作 profile。
- **共享层只加带默认值的参数与一个原语**：`draw_anchor(bar_color=)`、`draw_cover_triangle(color)`、`_render_cover_base(tri_color=, underlay=, title_box=, meta_box=)`、`render_end(anchor_color=)`、`resolve_image`（从 layouts_writing 提上来）、`helpers.add_picture_fit`（等比 contain、允许出血、按透明区裁边）、`image_has_alpha`。
- **图感知**：带透明通道＝抠图，贴右下出血；否则＝场景图，放右栏圆角。缺图不画占位框、改全宽；文字放不下（问答字号低于 18pt、引文低于 20pt）就弃图。分节页、表格页、END 不放图。
- **build_ppt 附带两项只读检查**（课型无关）：缺图清单、`jump_back_pages` 动画回跳；另有 `--strict-images` 参数，缺图时不出件。
- 字段写法见 `laojohn-ppt-draft/references/field-extraction.md` §5b 与 `image-suggestion.md`；配图链路见 `课件配图工具/scripts/reading_deck.py` 头注释。

## 五、字段写法的唯一源

写作页型字段写法（含 v8 实景观察 + 版式选择器合法值速查）的唯一源 = `laojohn-ppt-draft/references/writing-mode.md` §2 / §2.5 / §2.6 / §2.7。本文件不复述字段语法，只管架构与渲染归属。
