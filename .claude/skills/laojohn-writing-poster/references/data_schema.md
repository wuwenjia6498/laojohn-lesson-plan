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
| `cards[2].rows` | `## 第1课时 · 写作指导课` / `## 第2课时 · 当堂写作与评改课` 去尾字「课」 | 恒定 |
| `cta.fit`「适合小学三年级」/ `cta.sessions`「2 节专项课」 | 年级映射 / 常量（提纲表末段「2课时连排」全线恒定） | — |
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
| `subtitle` | 副题 | `companion.oneline` 优先，无则「学习目标」行 | 8–14 字，一句话说清这一课练什么 |
| `cards[0].head` | 卡① 标题 | `warn_sentences` 里的否定式提醒（如「这就是“流水账”」→「别写成流水账」），无则 `teacher_warn0`，再无则「核心技法」行前半 | ≤8 字 |
| `cards[0].body` | 卡① 正文 | 同环节师话里「该怎么做」的正面句 | 16–30 字，一句话，不带引号 |
| `cards[1].items` | 卡② 四关键词 | 「核心技法」「学习目标」行 + `companion.skills_b` | 恰好 4 项、各 2–5 字；每项都能在来源里指出原词 |
| `cards[2].rows[0][1]` | 卡③ 第 1 行 | 只许换成第 1 课时某环节名里的 ≤4 字短语（「说说新鲜事，打开思路」→「打开思路」） | 第 2 行「当堂写作与评改」禁改 |
| `cta.outcome` | 「产出第一篇完整日记」 | 「学习目标」行末句（「写成一篇日记」） | ≤12 字，「产出…」式 |
| `illustration.subject` | 生图画面 | 本课情境：示范文最关键的那一刻 › 教材题面／创设情境 › 学写法正例（不是文具静物） | 40–120 字，谁在哪里做什么＋2–4 件细节物件，可有人物、禁文字，写法见 `illustration-prompt.md` |
| `illustration.no_people` | 可选 | 题面本身是物件时置 true，判读才把人物当硬失败 | 布尔，默认不写 |
| `illustration.style` | 手绘风格编号（可空） | 人选：从手绘风格库画廊挑 001–274 的编号（静物友好清单见 `illustration-prompt.md`） | 三位数字串如 `"169"`；空则走通用水彩前缀。**不设全线默认，按单元自选**（2026-09-20 用户定） |

缺失处理：`subtitle` 空则隐藏；卡① head+body 皆空、卡② 少于 2 项、卡③ 无行 → 整卡隐藏、其余卡等分；`cta.outcome` 空则只显示「2 节专项课」。
**对外物料禁写「待补充」，宁可留空不编。**

## 配置类 · `render_writing_poster.py` 渲染时读，不落进 json

- `品牌资产\logo.png`、`品牌资产\qrcode.png`（单一源，`--logo/--qr` 可覆盖）。
- `品牌资产\校区信息.json`：`address` / `phone` / `note` / `cta`；值空则该行隐藏，四项全空整块隐藏。json 内若已有 `campus` 键则优先（单张海报人工覆盖口）。
- 插画：同目录 `<课次>-插画.jpg`（`--illustration` 可覆盖）；缺则留奶油空区并 stderr 提示。

## 回执（`gen_illustration.py` 回写）

`illustration.file / provider / model / prompt_used / generated_at / style_used{number,name,reference_image}|null / judge{verdict: pass|fail|unknown|skipped, obs}`。
