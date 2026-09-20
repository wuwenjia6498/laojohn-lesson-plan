---
name: writing-poster-tool-0920
description: 写作课单元招生海报工具 laojohn-writing-poster 立项与四项决策（2026-09-20）：独立 skill、每单元 AI 插画、OFL 毛笔体入库、校区信息 json；三上二样张已过，批量未跑
metadata:
  type: project
---

2026-09-20 用户拿外部做的《学会写日记》（三上二）海报样张，要求做「按写作课详案自动出每单元习作海报」的工具。当天立项并做完三上二样张。

**四项用户拍板（改方案前先看这四条）**
1. 中央插画＝**每单元 AI 生图**（否掉「按六文体建固定图库」与「人工提供」）：`gen_illustration.py` importlib 复用 `课件配图工具\scripts\imgclient.py`（Gemini 通道），判读四问，**判读失败记 unknown 不记 fail**（照 verify_rules 的 judge_failed 闸门）。插画入库（重渲不出来的输入资产），候选图不入库。
2. 毛笔标题字＝下载 **OFL「Ma Shan Zheng」入库** `assets/fonts/`（一次性联网取工具件，用户授权；**以 woff2 存**——ttf 5.7MB 过不了 pre-commit 的 5MB 软拦，读取需 fontTools+brotli）；渲染时 fontTools 子集化只嵌标题几个字（html 0.8MB 而非 7.8MB）。**title 须避开全角 `＿＿`**，该字体无此字。
3. 底部地址/电话/行动句＝根目录 **`品牌资产\校区信息.json`**，空则整行隐藏；**初建留空**——样张上的宁波地址与手机号是占位，不得抄进对外物料。
4. **独立 skill**（2026-07 用户定「写作课配套独立于读书会重设计」，course-poster 写作模式当时已删、不重开），只借 `_jpg_render.py` 同一条 JPG 引擎；**先出三上二一份样张验收，过关再批量**。

**Why（不可从代码推断的几条）**
- 文字层能全自动，是因为 `lesson-structure.md` §四 把首页/课时/环节结构锁死；24 份实测两个课时 H2 全恒定，但第 1 课时环节名各不相同（「打开思路」只在《写日记》），所以卡③第 1 行不能写死，只许 AI 用环节名短语微调。
- 副标题不在固定行号（11 份第 2 行、13 份第 3 行）、4 份无括号文体、1 份无空格——抽取按内容匹配不按行号。
- `.gitignore` 不能写 `写作课海报输出/**/*.jpg`，会把 `-插画.jpg` 一起吞掉；现用 `*-习作海报.jpg` + `*.候选.jpg` 两条。
- 本机 Git Bash 的 quoted heredoc 会把 `\` 折成 `\`，超长 heredoc 静默截断——脚本里的反斜杠用 chr(92) 或分两段写。

**How to apply**
- 排下一课次海报：`extract_fields.py` → 填 C 类 7 处（契约 `references/data_schema.md`，配套 json 有句先复用）→ `gen_illustration.py` → `render_writing_poster.py`。机检拦「占位/直引号/emoji/待补充」。
- ⚠ **logo 源 `品牌资产\logo.png` 只有 292px 宽**，海报 200px 位在 2 倍截图下略软；用户换 ≥600px 的 logo 重渲即清晰，位置不动（单一源）。
- 打包 `laojohn-writing-package` **暂不收海报**（对外招生件是否进交付包留用户定）。
- 未做：其余 23 份详案的 C 类与生图（解析回归 24/24 已过）；`校区信息.json` 地址电话待用户填。
**手绘风格库接入（同日下午追加）**：用户级 skill `handdraw-style-prompter`（274 个编号风格，MIT，装在 `%USERPROFILE%\.claude\skills\`、不在仓）接进 `gen_illustration.py`：`illustration.style`／`--style` 给编号 ⇒ 提示词换成「风格名+参考作者+正向特征+主体+固定约束+参考图隔离声明」并把参考图作 `images` 传给 Gemini（该库对 Gemini 判「能力未知」⇒ 特征+参考图双保险）。**两项拍板**：不设全线默认、按单元自选（不填走通用水彩前缀）；索引整份拷进 `assets/handdraw/styles.json`，参考图只拷用过的编号进 `assets/handdraw/refs/`（首次用自动拷、入库，同事机器不装风格库也能重生）。三上二试过 #169 彩铅、#222 钢笔淡彩，均一次判读通过；库里大半风格写人，特征带「人物」的编号与无人约束打架，静物友好清单在 `references/illustration-prompt.md`。浏览器工具打不开 file:// 画廊，只能手动开。

**⚠ 插画画面口径（同日晚用户纠正）**：首版口径「只画物件、不画人」出来的全是本子＋笔＋橡皮，用户否掉：「不是和详案内容相关的画面」。现行口径＝**画面取本课情境**，按序取：示范文最关键的那一刻 › 教材题面／创设情境 › 学写法正例；可有小学生／教师，**只禁文字**（黑板屏幕纸面留白）；题面本身是物件时才画静物并置 `no_people: true`。判读 `has_person` 默认只记不拦。三上二改成「放学路上蹲看蚂蚁搬饼干渣」、三上三改成「推门看见蜡烛气球与屏幕里的爸妈」，均一次判读通过。

相关：[[writing-materials-tools-removed]]、[[promo-materials-render-chain]]、[[downstream-shared-layer-and-token-facts]]、[[bash-heredoc-file-writing-pitfalls]]
