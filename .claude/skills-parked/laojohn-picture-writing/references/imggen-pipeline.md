# 自动生图闭环（可选 · 接 AiHubMix 文生图 API）

> 2026-07-27 由 SKILL.md 下沉，本文件为脚本用法与验收细则唯一源；SKILL.md「自动生图闭环」节只留摘要与指针。**opt-in**——不跑则只交付详案+工单，行为不变。密钥承载约定见根 `CLAUDE.md` §1。

把文末「生图工单」从手工外包升级为自动调用文生图 + 多模态视觉验收，闭合「详案→生图→验收→回插 docx」。**三脚本在 `scripts/`，纯本地依赖（openai SDK，缺包自动装）：**

| 脚本 | 职责 |
|---|---|
| `imgspec_parser.py` | 解析工单 imgspec 块 + 扫描正文 `【图位:编号】`（纯标准库、无网络；可单跑自测）。**`--export` 导出 `<详案stem>-生图提示词.txt`**（与 md 并排；每图一段拼装后完整提示词——含清单拼入与画风令牌、和实际喂模型一致——＋验收清单，供快速查看/手工喂外部工具；工单区包注释后 Markdown 预览不可见，看提示词用这条命令最方便） |
| `generate_images.py` | 调 AiHubMix 文生图存 `图位\<编号>.png`，再调视觉模型对照「必须可见元素清单」逐项验收：**主图与练笔图（严格档）缺项→强调缺项重生(≤max_retries)，仍缺则标「需人工」；备选图宽松、缺项仅告警；格式图跳过**。出 `图位\_验收报告.md`。**出图顺序固定 主图→练笔图→备选图**，主图落盘后自动作参考图传给后两类（日志「沿用主图画风」／练笔图「沿用主图画风与角色」）——**练笔图的「同族异时」靠这张参考图锁角色**，文字描述锁不住脸与发型。启动时若工单缺某一图位会打印「[告警] 工单缺图位：…」（只告警不拦生成，交付硬门在 checklist 与冷审）。**画风本身由 `references/style-tokens.md` 定义、经 `imgspec_parser` 常量按角色统一注入两档**（主图与练笔图 clean 档偏清晰可读、备选图 atmos 档偏氛围），写图位规格时不再逐图写风格形容词 |
| `insert_images_docx.py` | 调共享引擎出基础 docx，再把每处 `【图位:编号】` 就地换成真图（缺图留灰字「待补」、不报错），另存 `<详案名>-配图.docx`（**不碰共享引擎、不覆盖无图版**）。⚠ **实现已上移为两线共享件** `.claude/skills/laojohn-lesson-plan/assets/insert_images_docx.py`（见 CLAUDE.md §3），本目录同名文件是薄 shim，只负责注入本线取图口径 `imgspec_parser.image_dir`；页眉/前缀集/图宽等课型差异在共享件 `PROFILES['picture']` 里 |
| `build_picture_lesson.py` | 一键串生图+回插 |

## generate_images.py 两个专用开关

- **`--verify-only`**：只按现行规格验收已有的图、绝不重生（规格收紧后回验用；缺图记为需人工，不代生）。
- **`--only <编号> --edit "要改的这一处：…"`**：**定向编辑**——以现行真图为基准做最小改动、其余锁死（用于整图已人工核准、只有某个局部不达标，如手指指向落空、族裔画错；从零重生会丢掉画对却难描述的光影与脸型）。编辑前版本自动备份进 `图位\_历史\`，改完复验并**强制人工看图**，且**须把改动补写进规格**（不补则下次重生又丢）。

## 设置密钥（首次）

复制 `scripts/imggen.config.example.json` 为 `imggen.config.json` 填 `api_key`（已 gitignore），或设环境变量 `AIHUBMIX_API_KEY`（优先）。

## 生图后端按 image_model 自动分两条路（AiHubMix 文档实测，脚本已自动选）

- **Gemini Nano Banana 系**（如 `gemini-3-pro-image-preview` = Nano Banana Pro，默认）：走**原生 google-genai 客户端**、`gemini_base_url=https://aihubmix.com/gemini`，尺寸用 `aspect_ratio`(4:3 等)+`image_size`(1K/2K/4K)，**无 images.generate 端点**；
- **FLUX.1-Kontext-pro 等**：走 OpenAI 兼容 `images.generate`(/v1)，用 `size`。
- **验收 `vision_model`** 始终走 `/v1` chat（`gpt-4o` 即可）。

依赖（缺包自动装）：openai SDK（验收/flux）；选 gemini 时另需 google-genai。

## 运行

沿用全仓约定 `python` 非 `python3`、`PYTHONUTF8=1`：

```
export AIHUBMIX_API_KEY=sk-xxx
PYTHONUTF8=1 python scripts/build_picture_lesson.py "看图写话详案输出/<课次>/<课次>.md"
# <课次> = <年级册>（<季>）第 N 次 · <课型>，目录名与文件 stem 同名（一课次一目录）
```

## 落盘格式：`.png` 必须真的是 PNG（★ 2026-08-04 实测踩中）

模型（Gemini 通道）返回的字节**常常是 JPEG**。`generate_one` 原先把返回字节直接写进 `<编号>.png`，
只有 `trim_border` **真的裁到白边**那一次会经 PIL 重存、按扩展名编码成 PNG——所以「哪张是真 PNG」
取决于有没有白边可裁，**纯属偶然**。实录：同一课三张图，主-01（裁过白边）是真 PNG，练-01 与
备-01 是**披着 `.png` 外衣的 JPEG**。

- **怎么暴露的**：**Photoshop 打不开**——它按扩展名派发解析模块，拿 PNG 模块读 JPEG 数据，报
  「文件格式模块不能解析该文件」。**预览、PIL、python-docx 都按内容嗅探，一路无感**，所以能混到交付。
- **已修**：`generate_one` 落盘后、`trim_border` 之前插一道 `ensure_real_png()`（非 PNG 签名即用 PIL
  转存为真 PNG 并打印一行），机制与理由写在该函数 docstring（单一源）。
- **不要改成把文件重命名为 `.jpg`**：`<编号>.png` 是取图契约（`imgspec_parser.image_dir` 与
  `insert_images_docx.py` 按它定位），改名即断链。
- **转换不再损失画质**——模型给的就是 JPEG，那已经是原件，转 PNG 只是让容器与扩展名一致。
  但 `image-spec.md`「凡要量的、要判有没有的，先确认手上是原件」那条仍然适用：**这类图经过一次
  JPEG 有损，别拿它做精细色差判定**。
- **存量修复**：对已产出的图位目录跑一遍即可（含 `_历史\`）——
  `python -c "import sys;sys.path.insert(0,r'<skill>\scripts');from generate_images import ensure_real_png;[ensure_real_png(p) for p in __import__('glob').glob('*.png')]"`。
  修完**须重跑回插**，否则 docx 里嵌的还是旧字节。

## 验收红线（不可省）

自动视觉验收**只是把门禁 4「真图 vs 必须可见清单」终检自动化**，**不取消人工最终抽查**——视觉模型对"只有一个小孩""季节=春"这类隐性约束判定偏弱，**主图与练笔图务必人工再扫一眼**（练笔图还要人工确认「是不是同一个角色」与「意外点读不读得出来」——这两条机器都判不了）。生成图服从规格、规格服从教学，**绝不可反过来用生成图去改写正文/规格的事实**（详见 CLAUDE.md 受约束例外口）。

产物落点全在该课次目录 `看图写话详案输出\<课次>\` 内：图存 `图位\<编号>.png`、验收报告 `图位\_验收报告.md`、配图版 `<课次>-配图.docx`（与详案 md 并排）。取图口径的唯一源是 `imgspec_parser.image_dir()`＝**详案 md 的同级 `图位\`**；它对旧平铺布局（md 与同名子夹并排，如 skill 内 `_临时_角色定妆\`）保留回落分支，勿删。
