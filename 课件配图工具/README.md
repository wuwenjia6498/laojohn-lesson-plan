# 课件配图工具 · 第一阶段：五项待验规则 + 整课跑批

本目录当前**只做 PRD §7 的开发前置验证**，不是 Web 应用。

PRD（《课件配图工具-需求文档PRD.md》）第 7 节列了五条待验规则。本阶段用《猜猜他是谁》
打样清单的最小验证集（定妆 A / P6 / P16 / 剪影转制，另借 P13 测数量）把它们实测一遍，
再用同一份清单整课跑批，检验清单结构够不够用。

## ⚠ 头号纪律：每条规则只对它被测出来的那条通道成立

PRD 原话是「Gemini 的经验迁到豆包必须逐条重验」，**反过来一样成立**。工具支持两条
生图通道，`--provider` 一换，规则库就得整套重验，不得沿用：

| 通道 | 生图模型 | 调用方式 |
|---|---|---|
| `doubao` | 火山方舟 Seedream（`doubao-seedream-5-0-pro-260628`） | `/images/generations`，画幅给像素串 |
| `gemini` | AiHubMix 上的 Nano Banana Pro（`gemini-3-pro-image-preview`） | 原生 google-genai，**没有 images.generate**，画幅给 `aspect_ratio`+`image_size` |

产出目录、验证输出、验收记录**全部按通道分开存**。这不是为了整齐：若两条通道共用
一个目录，新图会悄悄覆盖已验收的旧图，而 `_验收记录.json` 还写着「已通过」——
验收记录就成了假的。

## 跑法

```bash
cp .env.example .env      # 填入 ARK_API_KEY
python scripts/verify_rules.py --provider gemini   # 在 Gemini 上跑五项
python scripts/verify_rules.py --provider doubao   # 在豆包上跑五项
python scripts/verify_rules.py --only T1          # 只跑某项
python scripts/verify_rules.py --reuse --outdir 验证输出/<某轮>   # 复用已有图，只重算结论（不再计费生图）

# 整课跑批（三阶段，两道人工闸门不可跳过）
python scripts/run_lesson.py 课件项目/猜猜他是谁.json --stage char
python scripts/run_lesson.py 课件项目/猜猜他是谁.json --approve char --by <验收人>
python scripts/run_lesson.py 课件项目/猜猜他是谁.json --stage pages
python scripts/run_lesson.py 课件项目/猜猜他是谁.json --approve pages --by <验收人>
python scripts/run_lesson.py 课件项目/猜猜他是谁.json --stage export
```

产物在 `验证输出/<时间戳>/`：逐项子目录存图，另有 `结果.json` 与 `验证报告.md`。

## 自动拆解（2026-08-28 起）

原先那份 `课件项目/猜猜他是谁.json` 是照着打样清单**手抄**的。手抄有两个躲不掉的毛病：
页码靠人数（实测与真实 PPT 错位 1–3 页，「上台读」标成 P19、实际在 P20），
以及**漏抄是无声的**（漏一条必现细节，成图就少一条，验收单上也不会有那一行可勾）。

现在这份 JSON 由两个脚本自动产出：

```bash
# ① 程序层：从 pptx 量出「哪页要图、什么画幅」——纯确定性判断，不调模型、不花钱
python scripts/extract_deck.py <课件.pptx> -o 拆解底稿/<课>-deck.json
python scripts/extract_deck.py <课件.pptx> --dump-sizes    # 换新模板时先看这个校准阈值

# ② 模型层：读详案 + deck，产出角色清单与逐页规格
python scripts/build_specs.py 拆解底稿/<课>-deck.json <详案.md|.docx>  -o 拆解底稿/<课>-拆解.json --model claude-opus-4-5     --style "水彩儿童插画：柔和水彩质感、干净留白"
python scripts/build_specs.py ... --stage1-only            # 只盘角色，先看再往下
python scripts/build_specs.py ... --reuse-stage1 <角色盘点.json>   # 阶段一不重跑
```

**分工是这套东西的全部设计**：

| 谁 | 定什么 | 为什么不能换手 |
|---|---|---|
| `extract_deck.py` | 页码、画幅、图位在哪、有几处 | 让模型数页码，就会得到手抄清单那种错位 |
| `build_specs.py` + 模型 | 这页该画什么、哪些页是同一个人、哪些页碰版权 | 程序判不了教学内容 |
| `拆解规则.md` | 比喻怎么拆、参考图怎么指名、什么时候不写画面文字 | 规则是量出来的资产，改它不必改代码 |

图位识别靠**面积占比**：实测主插图 9%–17% 画布面积、眉标条 0.7%、logo 0.4%，
中间隔着 11.9 倍的空档，阈值 0.03 切在真实空隙上。⚠ 换一套 PPT 模板必须先用
`--dump-sizes` 确认那道空档还在。

**详案页标是免费的对齐信息**：写作课详案定稿后会做页标回注（`〖PPT 第6页 · …〗`），
14 份里 12 份有。脚本按页标把详案切段、逐页附给模型，`来源` 就是照着抄而不是找相似句；
没有页标的详案退化成整篇喂，不报错。

`build_specs.py` 末尾的机检只查**程序查得了的那几条**（漏页、画幅对不对、
必现细节与来源等不等长、挂了参考图有没有在正文指名、角色件零引用、
来源句在不在原文里）。**比喻拆没拆、必现细节准不准、画面对不对，程序判不了，必须看图。**

**五项的结论看 `验证结论.md`**——那是经人工逐张看图复核后的正式结论，机器报告只是它的素材。

## 五项对应关系

| 编号 | PRD 待验项 | 验证集里的落点 |
|---|---|---|
| T1 | 头身比控制 | 定妆 A（全身像三档对照） |
| T2 | 禁止式表述 | P13 四人围坐（数量） |
| T3 | 局部编辑可靠性 | 剪影转制 / 改毛衣颜色 / 四人改三人 |
| T4 | 画面内中文 | P5 书封渲染中文 / P16 跑道查背景杂字 |
| T5 | 多参考图权重 | P6 跨页一致性（定妆图 + 异风格锚同挂） |

## 脚本

- `scripts/imgclient.py`——双通道生图/判读客户端（`make_client("gemini"|"doubao")`），两家的画幅写法、参考图塞法、返回格式差异全收敛在这里。
- `scripts/verify_rules.py`——五项验证 CLI。
- `scripts/run_lesson.py`——整课跑批 CLI（char → 闸门1 → pages → 闸门2 → export）。
- `scripts/measure_ratio.py`——头身比像素量测。凡量化判据都走它，不问视觉模型：让模型估百分比既慢（实测触发超长推理直到超时）又不可信。

## 两条纪律

1. **API Key 只从环境变量 / `.env` 读**，任何脚本里不得写死；`.env` 已被根 `.gitignore` 拦截。
2. **机器判读只作初筛，结论以人工看图为准**。视觉模型能数人数、能认颜色，判不了"像不像同一个孩子""风格漂没漂"——这正是 PRD 里两道人工闸门存在的理由。
3. **判读失败 ≠ 判定不通过**。二者混同会让报告写出与实际图完全相反的结论（2026-08-27 账户欠费时真实发生过）。`judge_failed()` 闸门守着这条，改 verdict 逻辑时不要绕过它。
