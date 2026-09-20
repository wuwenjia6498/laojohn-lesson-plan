# 单元海报 data.json 字段契约（唯一源）

文件：`<项目根目录>\写作课海报输出\<年级册>-第N单元-<题目>\<课次>-习作海报.json`。
`_` 开头的键是证据块与回执，渲染忽略、机检跳过。引用词语一律弯引号“”，禁 ASCII 直引号、禁 emoji、禁「待补充」。

## A 类 · `extract_fields.py` 机械抽（照抄不改写，AI 不动）

| 字段 | 详案锚点 | 缺失 |
|---|---|---|
| `course.id` / `grade_vol` / `unit` / `topic` | 文件名 `<年级册>-第N单元-<题目>-写作课详案.md`（fullmatch 正则，题目可含 `＿＿`/`“”`）；`topic` 以 H1 `# 《…》· 写作课教学设计` 为准 | topic 硬门槛报错 |
| `course.grade_label`「三年级上册」 | `grade_vol` 映射 | — |
| `course.genre`「应用文·日记」 | 副标题 `X年级X册·第N单元 校内同步写作（文体）` 括号；缺则提纲表「课题·课时」行第 2 段去「·校内同步」 | 留空（不上海报） |
| `capsule`「三年级上册｜第二单元同步习作」 | `grade_label` + `unit` 拼接 | — |
| `cards[*].kind` / `label` | 三卡固定栏目名（63 张统一）：`problem`＝写作难点 / `method`＝这一课怎么教 / `result`＝孩子能学会什么 | 恒定，AI 不改 |
| `cta.fit`「适合小学三年级」/ `cta.sessions`「2 节课」 | 年级映射 / 常量（提纲表末段「2课时连排」全线恒定） | — |
| `_sources.outline` | 提纲表「学习目标」「核心技法」「教材要求」原文 | 留空 |
| `_sources.lesson1_sections` / `lesson2_sections` | `### 一、…（约 N 分钟）` 环节名与分钟 | 留空 |
| `_sources.warn_sentences` | 第 1 课时「学写法」环节 `师：` 行里含「流水账／不是／不要／别／而是／这就是」的句子，≤4 条 | 留空 |
| `_sources.compare.bad/good` | 同环节 `师：第一段：…` / `师：第二段：…` 审题辨析对比段 | 留空 |
| `_sources.companion` | 同课次 `写作配套输出\<课次>\` 的家长用 `onepager.oneline`、学生用 `worksheet.skills` 的 `{b}` 词（`skills_b`）、教师用 `overview.warns[0]` | 无配套则空 |

已有 json 再跑 `extract_fields.py`：只刷新 `course` / `capsule` / `_sources`，C 类保留。

## C 类 · AI 填（唯一写字处；只许压缩改写详案已有内容，逐条反查依据）

| 字段 | 上海报位置 | 从哪里压缩 | 上限 / 规则 |
|---|---|---|---|
| `title` | 毛笔大标题 | 默认已填 `topic`，可直接用；改写只许「学会／写好 + 题目」式或与「学习目标」同义 | ≤8 字；**避开全角 `＿＿`**（毛笔体缺字），如《＿＿让生活更美好》→「让生活更美好」 |
| `subtitle` | 副题 | `companion.oneline` 优先，无则「学习目标」行 | **≤18 字**（56px 单行硬上限约 19 字），一句话说清这一课最核心的写作突破 |
| `cards[0].head` / `lines` | 卡① 写作难点 | `warn_sentences`、`compare.bad`：孩子最常见的一个真实问题 | head ≤7 字（如「总写成流水账？」）；lines 2–3 行、每行 ≤10 字 |
| `cards[1].head` / `lines` | 卡② 这一课怎么教 | 「核心技法」行与学写法环节师话：本课最核心的一招怎么做 | 同上（如「一天只写一件事」） |
| `cards[2].head` / `lines` | 卡③ 孩子能学会什么 | 详案里这一招做到后文章是什么样、`companion.skills_b` | 同上（如「让心情看得见」） |
| `cta.outcome` | 「完成孩子的第一篇完整日记」 | 「学习目标」行末句（「写成一篇日记」） | ≤14 字，「完成…」式 |
| `illustration.subject` | 生图画面 | 本课情境：示范文最关键的那一刻 › 教材题面／创设情境 › 学写法正例（不是文具静物） | 40–120 字，谁在哪里做什么＋2–4 件细节物件，可有人物、禁文字，写法见 `illustration-prompt.md` |
| `illustration.no_people` | 可选 | 题面本身是物件时置 true，判读才把人物当硬失败 | 布尔，默认不写 |
| `illustration.style` | 手绘风格编号（可空） | 人选：从手绘风格库画廊挑 001–274 的编号（静物友好清单见 `illustration-prompt.md`） | 三位数字串如 `"169"`；空则走通用水彩前缀。**不设全线默认，按单元自选**（2026-09-20 用户定） |

**三卡＝家长三问**（2026-09-20 母版定）：孩子最容易卡在哪儿 → 这节课教他哪一招 → 上完课能写成什么样。对应家长最关心的三件事：我家孩子是不是有这个问题、老师到底怎么教、学完有什么变化。**「2 节课／当堂写作与评改／构思表」这类交付方式一律不上卡片**，只在底部橙条出现。

`head` ≤7 字是版式硬约束（卡片内宽约 285px、36px 字号一行约 7.9 字）；`lines` 每行 ≤10 字（28px 字号），超了自动折行会打乱三卡行数齐平。

缺失处理：`subtitle` 空则隐藏；某卡 head 与 lines 皆空 → 整卡隐藏、其余卡等分；`cta.outcome` 空则只显示「2 节课」。
**对外物料禁写「待补充」，宁可留空不编。**

## 配置类 · `render_writing_poster.py` 渲染时读，不落进 json

- `品牌资产\logo.png`、`品牌资产\qrcode.png`（单一源，`--logo/--qr` 可覆盖）。
- `品牌资产\校区信息.json`：`address` / `phone` / `note` / `cta`；值空则该行隐藏，四项全空整块隐藏。json 内若已有 `campus` 键则优先（单张海报人工覆盖口）。
- 插画：同目录 `<课次>-插画.jpg`（`--illustration` 可覆盖）；缺则留奶油空区并 stderr 提示。

## 回执（`gen_illustration.py` 回写）

`illustration.file / provider / model / prompt_used / generated_at / style_used{number,name,reference_image}|null / judge{verdict: pass|fail|unknown|skipped, obs}`。
