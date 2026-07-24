---
name: laojohn-picture-materials
description: 把一份「老约翰」看图写话课详案(.md)转成配套课堂印刷件——支架小卡(三层支架卡·裁切版)、兜底纸条(写不动兜底填空条·裁切版)、看图写话稿纸(本课图位+格子稿纸+写话格式提醒)、教师家长页(教师上课速览 + 家长一页纸，2 页 A4)。四件均为可直接打印的 A4，排版对齐同步写作配套的品牌样式。当用户提到:根据看图写话详案生成配套物料/支架小卡/兜底纸条/看图写话稿纸/写话学习单/教师速览/家长一页纸，或看图写话详案产出后说"把配套物料出了/做套教具"时，使用本 skill。注意:生成看图写话详案本身属 laojohn-picture-writing；整本书阅读的学习单属 laojohn-reading-sheet；校内同步习作(写作课)的配套属 laojohn-writing-materials；本技能只管看图写话详案的配套物料。
---

# laojohn-picture-materials · 看图写话配套物料

把一份**看图写话课详案**（`laojohn-picture-writing` 产出）转成四类**可直接打印的 A4 课堂印刷件**。排版设计风格对齐 `laojohn-writing-materials`（同步写作配套）的品牌壳与令牌——**渲染引擎、品牌 logo、格子稿纸骨架都单一源复用 writing-materials，不复制逻辑**。

## 产出四件（各自独立 PDF + 可编辑 HTML）

| 物料 | 页数 | 内容 | 模板 / 入口 |
|------|------|------|------------|
| **支架小卡** | 1 页（8 张/页，2×4 裁切） | 本课支架卡（三素句结构条 `chips` / 细节四方向等提示卡 `quad`），每人一张随身 | `template_cards.html` / `render_cards.py` |
| **兜底纸条** | 1 页（7 条/页，竖排裁切） | 只发写不动孩子的填空续写条（开头＋加细节句式） | `template_slips.html` / `render_slips.py` |
| **看图写话稿纸** | 1 页 | 本课锚图 + 格子稿纸（18 列动态行）+ 写话格式小提醒 | `template_sheet.html` / `render_sheet.py` |
| **教师家长页** | 2 页 | P1 教师速览（时间轴 / 过关判定 / 评价三级 / 下水例文 / 物料清单）；P2 家长一页纸（一句话说清 / 好坏对照 / 好句本亲子任务 / 避开两件） | `template_teacher_parent.html` / `render_teacher_parent.py` |

> **纯口头课（免"写"）**：如一上会看课，无当堂写作 → **只出支架小卡 + 教师家长页**，不出兜底纸条、不出稿纸（无写作环节，纸条/稿纸无落点）。有当堂写作的课四件全出。

## 路径约定（移动硬盘，禁硬编码盘符）

本项目在移动硬盘，盘符随挂载变（`e:\`、`h:\` 等）。**执行前用 `(Get-Location).Path` 确认实际盘符。**

- **输入**：`<项目根>\看图写话详案输出\<年级册>（<季>）第 N 次 · <课型>.md`
- **输出目录**：`<项目根>\看图写话配套输出\<详案stem>\`（stem = 详案文件名去 `.md`，如 `二上（秋）第 1 次 · 方法课`）
- **命名**：`<详案stem>-<物料名>_data.json` → 同名 `.html` / `.pdf`（产物基名由 `_shared.out_base()` 去 `_data` 尾缀得出）。物料名 = `支架小卡` / `兜底纸条` / `看图写话稿纸` / `教师家长页`。
- **锚图**：稿纸内联的本课主图取 `看图写话详案输出\<详案stem>\图位\锚-01.png`（详案生图产物）；缺则稿纸留"老师另发/贴图"占位框。

## 本机渲染环境（踩中静默失败或乱码）

- 用 `python`，**不是 `python3`**（Store 占位别名，exit 49）。
- `_shared.py` 已自动设 `PLAYWRIGHT_BROWSERS_PATH`；手动跑前也可 `export PLAYWRIGHT_BROWSERS_PATH="C:/Users/69491/AppData/Local/ms-playwright"`。
- 命令一律加 `PYTHONUTF8=1`（避免中文路径/字符 GBK 报错）。
- 依赖：`playwright`（chromium）出 PDF、`pypdf` 核页数（缺则跳过核验，非致命）。

## 工作流

1. **定位详案**，读全文。判断课型：有无当堂写作环节（决定出不出兜底纸条/稿纸）。
2. **抽取数据**，按 `references/data_schema_*.md` 四份契约（详案锚点 → 字段的唯一映射源），为每件物料手写一份 `data.json`，落输出目录。
   - 事实源锁死详案：支架卡内容取详案内联卡 + `## 附：本课支架…` 附录；兜底句式取第 2 课时"当堂写作"环节的纸条 fenced 块；写话格式取 `〔写话小提醒〕`；教师时间轴取 `## 第N课时` + `### 环节…（N 分钟）`（分钟逐字）；过关判定/评价三级/下水例文/好句本课后逐字取详案对应区块。
3. **核弯引号**：`data.json` 写完立即核验——正文一律弯引号 `""`/`''`，禁 `「」`、禁英文直引号 `"` `'`（Write 工具可能把弯引号规范成 ASCII，须回转）。可跑 `json.loads` + 扫 ASCII 直引号自查。
4. **逐件渲染**：
   ```bash
   PYTHONUTF8=1 python scripts/render_cards.py           <data.json> <out_dir>
   PYTHONUTF8=1 python scripts/render_slips.py           <data.json> <out_dir>
   PYTHONUTF8=1 python scripts/render_sheet.py           <data.json> <out_dir> [--anchor <锚-01.png>]
   PYTHONUTF8=1 python scripts/render_teacher_parent.py  <data.json> <out_dir>
   ```
   稿纸锚图优先 `--anchor`，否则取 data.json 的 `sheet.anchor_img`（相对路径按 CWD 解析，从项目根跑即可）。
5. **自检**：看渲染日志——`页数核验` 是否 OK（卡/条/稿纸=1 页，教师家长页=2 页）、有无 `sheet 超一页高` 溢出告警；溢出就压数据层文本或减重复份数重渲。目检 PDF：品牌壳一致、无 ASCII 直引号泄漏、锚图咬合正文。

## 红线（继承 CLAUDE.md §4 + 看图写话既有纪律）

- **弯引号铁律**：正文全角 `""`/`''`，禁 `「」`、禁英文直引号（Markdown/代码/英文路径除外）。
- **禁行内单星斜体 `*…*`、禁 HTML 样式标签**（`<mark>`/`<b>`/`<span>` 等）；富文本只认模板里的 `{b}…{/b}`（加粗），其余原样转义。
- **真实性红线不豁免**：下水例文、兜底句式、过关判定例句**逐字取详案不改**；情节/人物/数字/图面只来自详案（其事实又锁图位"必须可见元素清单"），**禁凭模型记忆补写**。伪摘录禁令照旧。
- **家长页禁虚构学生作品**：家长一页纸只讲能力与好坏对照（派生自过关判定/评价三级），**不编造孩子写的具体句子**；孩子真作留待教师课堂手填（本 skill 不出带学生作品的成长反馈结构件——那是同步写作配套的家长侧，看图写话家长页只出"怎么陪"一页纸）。
- **教具纪律入页眉话术**：支架卡"每人一张随身、能独立即撤"，兜底纸条"不全班发、只给写不动的孩子、能独立起句即撤不连用两次"，禁写"墙上张贴/板书"。

## 提交纪律（CLAUDE.md §8）

`_data.json` 是数据源、连同内联的图位 png 照常入库；`.html` / `.pdf` 是渲染产物、已 gitignore（`看图写话配套输出/**/*.{pdf,html}`）。提交前 `git status` 不该出现 `.html`/`.pdf`；**禁 `git add -f` 把产物强加回来**。

## 与相邻技能的边界

- 生成看图写话**详案本身** → `laojohn-picture-writing`（本 skill 只做配套印刷件，不生成/不改详案、不生图、不回插、不出 docx）。
- 整本书阅读的**学生学习单** → `laojohn-reading-sheet`。
- 校内**同步习作(写作课)配套** → `laojohn-writing-materials`（本 skill 的渲染引擎即单向复用它的 `scripts/_shared.py` 与格子稿纸骨架——改那些文件的契约前须回归两线）。

## 依赖声明（单向复用 writing-materials，改前必查）

本 skill **没有自己的渲染引擎副本**，`scripts/_shared.py` 是薄 shim，用 importlib 载入 `laojohn-writing-materials\scripts\_shared.py`（CLAUDE.md §3 声明的两线共享单一源）。改动 writing-materials 的 `_shared.py`（`render`/`inject`/`out_base`/`safe_pdf`/`check_pages` 签名或 `extra_images` 参数）、或格子稿纸 `buildGrid` 骨架前，**必须同步检查本 skill 是否受影响**（它会静默失效）。
