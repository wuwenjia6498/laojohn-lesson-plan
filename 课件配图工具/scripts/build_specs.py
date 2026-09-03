"""拆解器：详案 + PPT → 项目 JSON（含每页图位规格与提示词）。

分工是这个脚本的全部设计：
  程序（extract_deck.py）定**事实**——页码、画幅、图位在哪、有几处；
  模型定**内容**——这一页该画什么、哪些页是同一个人、哪些页碰版权；
  规则库（拆解规则.md）定**写法**——比喻怎么拆、参考图怎么指名、什么时候不写文字。
三者都不该互相代劳。让模型去数页码，就会得到手抄清单那种错位 1–3 页的结果；
让程序去判"这页该画什么"，则根本判不了。

两阶段调用，不是一次吐完：
  阶段一先盘角色 —— 哪些人物跨页复现、要出几张定妆图，这是**全局决策**，
  必须在逐页写 prompt 之前定死，否则每页各自描述一个"戴眼镜的男孩"，
  挂载栏无从填起，成图每页一张脸。
  阶段二才逐页出规格，并把阶段一的角色清单作为**已知条件**喂进去。
"""
import argparse, json, pathlib, re, sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import imgclient

ROOT = pathlib.Path(__file__).resolve().parents[1]
RULES = ROOT / "拆解规则.md"


def docx_to_text(path):
    """把详案 docx 按正文顺序拍成纯文本：段落一行一段，表格一行一行、单元格用「 | 」隔开。

    只走正文（body），页眉页脚不进来——那是「老约翰深度阅读」品牌页眉，不是教学内容。
    页标 〖PPT 第N页 · …〗 在 docx 里是独占一行的普通文字段，原样保留，
    所以 `split_by_pagetag` 对 docx 来的详案照样按页切得开。
    合并单元格 python-docx 会重复返回同一对象，按 _tc 去重，否则表格一行会出现两遍同一格。
    """
    from docx import Document                      # 只在真的传 docx 时才 import
    from docx.table import Table
    from docx.text.paragraph import Paragraph
    doc = Document(str(path))
    lines = []
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            lines.append(Paragraph(child, doc).text.replace("\x0b", "\n"))
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                cells, seen = [], set()
                for c in row.cells:
                    if id(c._tc) in seen:
                        continue
                    seen.add(id(c._tc))
                    # 格内换行（md 表格里的 <br>）拍成空格，否则一格会把表格行拆成两行
                    cells.append(" ".join(pp.text for pp in c.paragraphs).replace("\x0b", " ").replace("\n", " ").strip())
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
    return "\n".join(lines)


def load_plan(path):
    """读详案（.md / .txt / .docx）。整篇喂，不做摘要——摘要会先一步丢掉必现细节的来源原文，
    而 R5「来源可追溯」正是靠原文句撑着的。

    docx 是 2026-09-03 加的入口：审核方常只回传 docx 而不回传 md（详见仓库根 CLAUDE.md §9），
    要求先手工转 md 等于多一道容易忘的工序。转出来的文本与 md 版差别只在 Markdown 标记
    （`##`、`**`、`>`）没了——`来源` 核对走的是 `_norm`（已剥标点空白），不受影响。
    """
    path = pathlib.Path(path)
    if path.suffix.lower() == ".docx":
        txt = docx_to_text(path)
    else:
        txt = path.read_text(encoding="utf-8")
    txt = re.sub(r"<!--.*?-->", "", txt, flags=re.S)   # 注释区不是教学内容
    return txt.strip()


def split_by_pagetag(plan):
    """按详案里的页标 〖PPT 第N页 · 环节 · 标题〗 把正文切成 {页码: 该页对应的详案段落}。

    写作课线定稿后会做「页标回注」，14 份详案里 12 份都有这一层 —— 有它就不必让模型
    自己去猜哪段详案讲的是哪一页。这直接决定 `来源` 准不准：模型手里只有整篇详案时，
    写来源基本靠找相似句；给了本页原文，它就是照着抄。

    ⚠ 没有页标的详案返回空 dict，上层照旧整篇喂 —— 退化，不报错。
    """
    tags = list(re.finditer(r"〖PPT\s*第\s*(\d+)\s*页[^〗]*〗", plan))
    if not tags:
        return {}
    out = {}
    for i, m in enumerate(tags):
        end = tags[i + 1].start() if i + 1 < len(tags) else len(plan)
        out[f"P{int(m.group(1)):02d}"] = plan[m.start():end].strip()
    return out


def deck_digest(deck, by_page=None):
    """把 deck.json 压成给模型看的形式：保留页码、文本、主图位画幅与版面占用，
    丢掉 EMU 坐标那些模型用不上也读不懂的数字。

    ⚠ 版面那几个数**必须带上**：规则库第二节第 4 句要模型据此判断
    "这页还塞不塞得下图"，字段不传过去，那条规则就是一句空话。"""
    out = []
    for pg in deck["页"]:
        main = [i for i in pg["图片"] if i["是主图位"]]
        item = {
            "页码": pg["页码"],
            "主图位": [{"画幅": i["画幅"], "面积占比": i["面积占比"]} for i in main],
            "文本": pg["文本块"],
            "版面": {"字数": pg.get("字数"), "文本块数": pg.get("文本块数"),
                     "表格数": pg.get("表格数"), "版面占用": pg.get("版面占用")},
        }
        if by_page and pg["页码"] in by_page:
            item["本页对应的详案原文"] = by_page[pg["页码"]]
        out.append(item)
    return out


SYS = """你是课件配图的规格师。只输出 JSON，不要任何解释性文字。
中文引号一律用全角双引号与单引号；JSON 字符串内绝不出现半角直引号——
半角直引号会当场把 JSON 打断（实测：给「身边的人」加半角引号写进用途字段，整份解析失败）。
本项目全线本来也有全角引号的硬规定，两件事在这里是同一条。"""

STAGE1 = """下面是一节课的教学详案、这节课 PPT 的逐页内容，以及一份**实测得出的规则库**。

你的任务是**第一阶段：盘点角色与画风**，还不要写逐页图位。

{style}

## 规则库（必须遵守，每条都是实测结论）
{rules}

## 教学详案
{plan}

## PPT 逐页内容（页码与主图位由程序从 pptx 量出，是事实，不要改动）
{deck}

## 输出这份 JSON

{{
  "project": "课程名",
  "style_card": {{
    "画风档": "一句话说清画风",
    "色板": "主色与对比色",
    "人物年龄设定": "从详案里的年级推出来",
    "场景基调": "主要场景",
    "概念母题": "贯穿全课的视觉母题；没有就填空字符串",
    "通用禁区": "按 R5，默认含『画面内不出现任何文字』",
    "前缀基底": "画风与色调，会拼在每条 prompt 最前面。按 R1 不写头身比；按 R6 若这里写死了画风，就不要再挂风格锚图",
    "人物条目": "人物年龄与身份的那一句，单独一段（如『主体人物为8到9岁的中国小学生』）",
    "文字禁令": "画面内文字的禁令那一句（如『画面中不出现任何文字』）",
    "_前缀备注": "说明你按哪几条规则做了取舍"
  }},
  "characters": [
    {{
      "id": "定妆A",
      "画幅": "1:1",
      "prompt": "定妆图提示词，写死可复述的识别特征，纯浅色背景",
      "挂载": [],
      "出现页码": ["P04", "P06"],
      "_说明": "为什么需要这张"
    }}
  ],
  "角色盘点": [
    {{"人物": "主角色男孩", "出现页码": ["P04","P06"], "是否需要定妆图": true, "理由": "跨 N 页复现"}}
  ]
}}

要求：
1. **把上面每一个有主图位的页逐页看一遍**，逐页列出这一页会出现哪些人物，
   再据此汇总跨页复现的角色。不要凭印象只挑几页 —— 漏掉的那页会换一张脸，且无声。
   `角色盘点` 里每个角色的 `出现页码` 必须是完整的，不是举例。
2. 需要定妆图的主角色，按第三节给**半身 + 全身**两张（全身那张是比例基准）。
3. 剪影、变体这类由定妆图**编辑而来**的角色件也列进 characters，挂载写来源。
4. 定妆图本身 `挂载` 为空数组——它是基准。
   ⚠ 前缀**必须拆成 `前缀基底` / `人物条目` / `文字禁令` 三段**，不要合成一整句：
   有的页要画的是书册、铅笔这类没有人的静物，有的页要允许出现书封文字，
   到时候按页开关只需决定这两段拼不拼。合成一句就只能靠字符串替换去裁，
   换一种措辞就静默失效。
5. **`characters` 的准入条件只有两条，不满足的一个都不许列**：
   ① 该角色在 `角色盘点` 里 `是否需要定妆图` 为 true；或
   ② 它是第三之二节认定的剪影/背影/变体件（此时 `挂载` 必须非空）。
   实测反复出错：模型在 `_说明` 里写着"按规则只出现一页不给定妆图"，
   却仍把它列进了 characters —— **先按盘点定名单，再逐个填写，不要边写边决定。**
6. 每个 character 的 `出现页码` 必须填全，与 `角色盘点` 对得上。"""


STAGE2 = """接上一步。角色与画风**已经定了**（见下），现在做**第二阶段：逐页图位规格**。

## 规则库（必须遵守）
{rules}

## 教学详案
{plan}

## PPT 逐页内容
{deck}

## 已定的画风与角色（不要改动，直接引用 id）
{stage1}

## 输出这份 JSON

⚠ **`slides` 要覆盖每一个需要配图的页，不只是程序标了主图位的那些。**
程序只看得见 PPT 里**已有**的图片；一份还没配图的课件，图位在文件里没有任何痕迹。
实测对照人工成品：程序量出 6 处，人工实际配了 18 处 —— 漏掉的 13 处全是
程序看不见的。所以你要按规则库第二节的三句问**逐页判断**，该配的都写进 slides。

{{
  "slides": [
    {{
      "页码": "P04",
      "用途": "这张图在这一页干什么（一句话）",
      "类型": "例子 / 场景 / 道具 / 素材（见规则库第三节）",
      "角色组合": "出现哪些角色，用上面的 id",
      "画幅": "照抄程序量出的主图位画幅",
      "通道": "生成 / 复用 / 人工素材位",
      "主体": "画面主体",
      "必现细节": ["可验收的具体细节，3-6 条"],
      "来源": ["每条必现细节对应的详案或 PPT 原文句，与必现细节一一对应"],
      "prompt": "完整提示词（不含风格前缀，前缀由程序拼）",
      "挂载": ["参考图 id，顺序有意义，定妆图放第一位"],
      "复用": "仅当通道为『复用』时填：复用哪一页的图，写那一页的页码",
      "去人物条目": "布尔。这一页画的是静物、没有人时填 true，程序会把人物那段前缀去掉",
      "允许画面文字": "布尔。仅在确实要画面内文字时填 true（R5 默认关）",
      "_说明": "判断理由；通道为人工素材位时必须写清为什么"
    }}
  ],
  "逐页判断": [
    {{"页码": "P02", "要不要图": false, "不配的类别": "首尾插页", "理由": "课时分隔页，只有序号和课时名"}}
  ]
}}

要求：
1. **程序标了主图位的页，必须逐页给出规格，一页都不能漏**（那是已有证据的图位）。
2. **其余每一页也要逐页过一遍。每一页都要配图**（规则库第二节）：
   - **唯一的例外是首尾插页**：课时分隔页（只有序号和课时名）、结束页（THE END）。
     封面要配。
   - **表格页也要配** —— 构思表、旁批表、整页示范文、要点清单这些页照样给一幅图，
     版面挤就配小一点、配一条呼应内容的道具或装饰。
     **不接受「版面被占满」「只是文字讲道理」这类理由。**
   - 判**要**的 → 直接写进 `slides`，规格和别的页一样完整；
   - 判**不要**的 → 写进 `逐页判断`，只能是首尾插页这一类。
   ⚠ **每一页都必须出现在 slides 或 逐页判断里，两者之和等于总页数。**
   实测漏掉过 13 处：模型只挑了自认为要图的一页写上，其余 16 页一声不吭 ——
   沉默不是判断，而且没人看得出它漏了。
3. **一页举了几件事，就是几个图位**（奖状 / 草莓 / 乐高＝三条），
   页码写成 `P10-1`、`P10-2`、`P10-3`。按规则库第三节，例子类是最容易漏的一类。
   ⚠ **例外**：逐页判断里判为「需要图、但因版权只能人工找素材」的，
   要**同时**在 slides 里补一条 `通道` 为 `人工素材位` 的记录（`prompt` 留空字符串）——
   它得占住那个位置，交付清单上才有它这一行，否则这页会被当成"不需要图"整个漏掉。
3. `必现细节` 与 `来源` **必须等长、一一对应**（规则库第五节：漏抄是无声的）。
   来源写成「详案：<原文>」或「PPT P06：<原文>」时，冒号后**必须是能在原文里逐字找到的句子**，
   不能填你自己的推理（「PPT P01封面需要主角色剪影呈现悬念」这种是推理，不是原文）。
   这条细节若来自角色设定、画风卡或规则库，就照实写「角色设定：…」「画风档：…」「R5：…」；
   若确实无出处、是你补的，写「（推断）」+ 理由。**编一个来源比不写来源更坏 ——
   它让人以为核过了。**
4. ⚠ 凡画面里有纸、本子、黑板、卡片的页，**prompt 里必须写明**
   「纸上只有波浪线示意，不出现任何可辨认文字、不出现英文字母」——
   通用前缀那句禁令兜不住，模型会自己往纸上填英文假字。
5. 逐条自查 R2/R3/R4/R5：数量写没写确定数字、比喻拆没拆、挂载有没有在正文指名、
   画面文字是不是默认关掉了。
5. 同一张图在多页复用的，第二次起 `通道` 写 `复用`，`_说明` 里写复用哪一页。"""


STYLE_GIVEN = """## 用户指定的画风（照抄，不要自己改写）
{v}"""
STYLE_NONE = """## 画风
用户没有指定画风。按规则库三之二，由你从学段与内容推一个，
并在 `_前缀备注` 里**明写这是你推的、待用户确认**。"""


class DecodeFailed(RuntimeError):
    """拆解没拿到可用结果。

    **抛异常而不是 SystemExit**：这是个库函数，该由调用方决定是退出进程（CLI）
    还是记一条任务失败（Web）。早先这里直接 SystemExit，而 Web 的后台线程只捕
    Exception —— SystemExit 继承 BaseException，于是线程静默死掉、任务永远停在
    running，界面一直转圈。**失败被显示成了「还在跑」**，比报错更难查。
    """


def call(client, tmpl, model, max_tokens=64000, **kw):
    prompt = tmpl.format(**kw)
    r = client.chat(prompt, system=SYS, model=model, max_tokens=max_tokens)
    if "_error" in r or "_raw" in r:
        why = r.get("_error")
        if not why:
            raw = r.get("_raw", "")
            tail = raw.rstrip()[-60:]
            # 结尾没闭合就是被截断 —— 说「解析不成 JSON」会把人引去查格式，
            # 而真正要做的是调高上限。实测两次都栽在这：32000 不够时，
            # finish_reason 没报截断，只落进解析失败。
            if not tail.rstrip().endswith(("}", "]")):
                why = (f"**输出被截断**（收到 {len(raw)} 字，上限 max_tokens={max_tokens}）。"
                       f"结尾停在：…{tail}　"
                       f"——不是格式问题，是没写完。调高 --max-tokens 再跑。")
            else:
                why = f"模型回了内容但解析不成 JSON（{len(raw)} 字），结尾是：…{tail}"
        # 把原始返回落盘：解析失败时光看结尾 60 字判断不了坏在哪，
        # 得能打开整份看。文件一次性覆盖，不留历史。
        try:
            dbg = RULES.parent / "拆解底稿" / "_最近一次解析失败.txt"
            dbg.parent.mkdir(parents=True, exist_ok=True)
            dbg.write_text(r.get("_raw") or r.get("_error") or "", encoding="utf-8")
            why += f"　原始返回已存到 {dbg}"
        except Exception:
            pass
        raise DecodeFailed("拆解没拿到可用结果——这是【未知】不是【没有图位】。" + why)
    return r


def _norm(t):
    """比对来源句用：去掉标点、空白、引号差异，只留字。
    模型转录时全角半角、弯直引号常不一致，按原样比会全军覆没。"""
    return re.sub(r"[^\w一-鿿]", "", t or "")


def audit_sources(spec, plan, deck, min_len=6):
    """核对每条 `来源` 是不是真的在详案或 PPT 里 —— 这条程序完全查得了，就该程序查。

    模型会**编来源**：实测 P21 必现细节写「另一个是扎马尾的女孩」，
    标的来源却是详案里一句没有「扎马尾」三个字的话。`来源` 字段的全部价值就在于可核，
    编出来的来源比没有来源更坏 —— 它让人以为核过了。

    ⚠ **只核对自称引自详案 / PPT 的那些**。来源合法的不止这两种：
    「角色设定：…」「画风档：…」「R5：…」分别指向角色件、风格卡和规则库，
    那些内容本来就不在详案里，拿原文去比会把它们全判成编造。
    第一版没做这个区分，17 条报警里 15 条是误报 —— **误报率这么高的检查等于没有检查**，
    人会连着真报警一起忽略。

    只报「整句在原文里找不到」，不追究语义是否对应。
    """
    hay = _norm(plan) + _norm(json.dumps(deck, ensure_ascii=False))
    bad = []
    for sl in spec.get("slides", []):
        for det, src in zip(sl.get("必现细节", []), sl.get("来源", [])):
            if not re.search(r"详案|PPT|P\d", src.split("：")[0]):
                continue                                     # 非原文来源，不归这条查
            body = re.sub(r"（.*?）|\(.*?\)", "", src)       # 先剥自注，再切标注前缀
            body = re.split(r"[：:]", body)[-1].strip()       # 顺序反了会把括号内容当成原文
            # 省略号节略是合法引法（「现在，请你先在心里选定一个人……选好了吗？」
            # 两头都在详案第 52 行里，中间省掉一串）。按整句比会把它误判成编造，
            # 所以拆成片段逐段核 —— 每段都得真在原文里，节略才算诚实。
            parts = [x for x in re.split(r"…+|\.{3,}|…", body) if _norm(x)]
            miss = [x for x in parts if len(_norm(x)) >= min_len and _norm(x) not in hay]
            if not parts or not miss:
                continue
            if all(len(_norm(x)) < min_len for x in parts):
                continue                                     # 片段都太短，比对无意义
            bad.append((sl["页码"], det[:26], miss[0][:40]))
    return bad


def audit(spec, deck):
    """机检——只查**规则库里能用程序查的那几条**，查不了的老实说查不了。

    ⚠ 这里的每一条通过都不代表规格对，只代表"没犯这几种低级错"。
    R3（比喻拆没拆）、必现细节准不准、画面对不对，程序判不了，必须人看图。
    本项目已经栽过一次「机检全绿≠审查完成」，不再假装机检能替人。
    """
    issues = []
    main_pages = {pg["页码"] for pg in deck["页"] if pg["主图位数"]}
    got = {s["页码"] for s in spec.get("slides", [])}

    # 一页可以拆成 P05-1 / P05-2 多个图位，那时 P05 本身不会出现在 slides 里，
    # 不能算漏。按所属页归并后再比。
    got_base = {x.split("-")[0] for x in got}
    for miss in sorted(main_pages - got_base):
        issues.append(f"[漏页] {miss} 程序量出有主图位，规格里没有")

    # 每一页都得有个结论：要么进 slides，要么在逐页判断里写明为什么不配图。
    # 沉默跳过是查不出来的 —— 实测漏掉 13 处，其中大部分页一声不吭，
    # 既不在 slides 也不在判断表里，界面上看起来一切正常。
    all_pages = {pg["页码"] for pg in deck["页"]}
    judged = {x.get("页码") for x in (spec.get("_逐页判断") or spec.get("_候选页") or [])}
    # 一页多图位会写成 P10-1 / P10-2，归回它所属的页
    covered = {p.split("-")[0] for p in got} | judged
    # 除首尾插页外，每一页都该配图（规则库第二节）。这条现在判得了：
    # 不再需要区分「是不是表格页」—— 那个判据机器判不了，也不用判了。
    for x in (spec.get("_逐页判断") or spec.get("_候选页") or []):
        if x.get("要不要图"):
            continue
        pg_ = x.get("页码", "")
        if any(y["页码"].split("-")[0] == pg_ for y in spec.get("slides", [])):
            continue                      # 已拆成 P06-1/-2/-3 进了清单，是配了不是没配
        why = (x.get("不配的类别") or "") + (x.get("理由") or "")
        if re.search(r"人工素材|版权", why):
            continue                      # 人工素材位是第四类，不算不配图
        if not re.search(r"首尾|分隔|结束|封底|THE END", why, re.I):
            issues.append(f"[该配图] {pg_} 判了不配图（{(x.get('理由') or '')[:24]}…）"
                          f"——除首尾插页外每页都要配，表格页也要配")

    silent = sorted(all_pages - covered)
    if silent:
        issues.append(f"[无结论] {len(silent)} 页既没进 slides 也没写进逐页判断，"
                      f"等于没判断过：{'、'.join(silent[:12])}"
                      + ("…" if len(silent) > 12 else ""))
    # ⚠ 这里**不再**报「程序没量出主图位却写进 slides」。
    # 那条判据 2026-08-28 作废：新设计的核心就是让模型在没有占位图的页上补图位
    # （例子类、道具类几乎全在那种页上）。旧判据会把这次 16 处里的 10 处报成错，
    # 而它们恰恰是对照人工成品补回来的。
    # 只保留一条：页码得是这份 pptx 里真有的页，别编出一个 P99 来。
    known = {pg["页码"] for pg in deck["页"]}
    for extra in sorted(got):
        if extra.split("-")[0] not in known:
            s = next(x for x in spec["slides"] if x["页码"] == extra)
            issues.append(f"[页码] {extra} 不是这份 pptx 里的页（共 {len(known)} 页），"
                          f"用途：{s.get('用途','')}")

    ratio = {}
    for pg in deck["页"]:
        m = [i["画幅"] for i in pg["图片"] if i["是主图位"]]
        if m:
            ratio[pg["页码"]] = m

    # 模型会「说出规则、然后照样违反」：实测有一件的 _说明 里写着
    # 「按规则只出现一页不给定妆图」，却仍旧躺在 characters 里。自相矛盾程序查得到。
    roster = spec.get("_角色盘点") or spec.get("角色盘点") or []
    no_need = {r.get("人物", "") for r in roster if not r.get("是否需要定妆图")}
    for c in spec.get("characters", []):
        pages = c.get("出现页码") or []
        if len(pages) == 1 and not c.get("挂载"):
            issues.append(f"[定妆] 角色件「{c['id']}」只出现在 {pages[0]} 一页且不挂任何参考图，"
                          f"按规则三不该给定妆图（单页角色当页描述即可）")
        say = str(c.get("_说明", ""))
        if "不给定妆图" in say or "不需要定妆" in say:
            issues.append(f"[矛盾] 角色件「{c['id']}」的说明自称不该给定妆图，却仍在 characters 里")

    # 用实际挂载反向补全角色件的出现页码：阶段二才是最终决定，阶段一那份是初判。
    for c in spec.get("characters", []):
        used_on = {sl["页码"].split("-")[0] for sl in spec.get("slides", [])
                   if c["id"] in (sl.get("挂载") or [])}
        if used_on:
            c["出现页码"] = sorted(set(c.get("出现页码") or []) | used_on)

    ids = {c["id"] for c in spec.get("characters", [])}
    for s in spec.get("slides", []):
        p = s["页码"]
        if p in ratio and s.get("画幅") not in ratio[p]:
            issues.append(f"[画幅] {p} 程序量出 {ratio[p]}，规格写了 {s.get('画幅')}")
        det, src = s.get("必现细节", []), s.get("来源", [])
        if len(det) != len(src):
            issues.append(f"[来源] {p} 必现细节 {len(det)} 条、来源 {len(src)} 条，不等长")
        # R4：挂了参考图却没在正文指名，等于没挂
        if s.get("挂载") and not re.search(r"参考图|参考第|挂载", s.get("prompt", "")):
            issues.append(f"[R4] {p} 挂了 {s['挂载']}，但 prompt 正文没有一处提到参考图")
        # 挂载项有两种：角色件 id，或**别页的页码**（对比图、同场景变体要挂上一张，
        # 光在文字里写「和上一张同样构图」没用，模型看不到那张）。
        pages_all = {x["页码"] for x in spec.get("slides", [])}
        for m in s.get("挂载", []):
            if m == p:
                issues.append(f"[自挂] {p} 把自己挂成了参考图 —— 重出时会拿上一版当参考，"
                              f"越改越偏离描述")
            elif m in pages_all:
                other = next(x for x in spec["slides"] if x["页码"] == m)
                if p in (other.get("挂载") or []):
                    issues.append(f"[互挂] {p} 与 {m} 互相挂对方 —— 谁先生成谁就没有参考，"
                                  f"留一个方向即可")
                if other.get("通道") == "人工素材位":
                    issues.append(f"[挂载] {p} 挂了 {m}，但那一页是人工素材位、不会生成图")
            elif m not in ids:
                issues.append(f"[挂载] {p} 挂了「{m}」，既不是角色件、也不是清单里的页码")
        if s.get("通道") not in ("生成", "复用", "人工素材位"):
            issues.append(f"[通道] {p} 通道值非法：{s.get('通道')}")

        text = (s.get("prompt", "") or "") + " ".join(s.get("必现细节", []))
        # R2：给了总数又逐个点名个体 —— 实测「恰好3个…1个站前面、台下2个、其中1人举手」
        # 出来是 4 个人。总数写一遍就够，谁在干什么交给模型。
        # 要抓的是「总数之外又写了**分组数**」：恰好3个…台下2个…→ 人数写了两遍。
        # ⚠ 不能一见到人数短语就报：「其中1个是主角色男孩」是**指认主角所必需**的，
        # 一律算进去会把改对了的页也报出来（第一版就是这样，三页全误报）。
        # 所以：总数记下来，「1」放行，剩下还有别的数字才是分组数。
        m = re.search(r"恰好\s*([0-9一二三四五六七八九十]+)\s*[个位名本张]", text)
        if m:
            CN = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
                  "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
            nums = []
            for t in re.findall(r"([0-9]+|[一二两三四五六七八九十])\s*[个位名]", text):
                nums.append(int(t) if t.isdigit() else CN.get(t, 1))
            total = nums[0] if nums else None
            groups = [n for n in nums[1:] if n != 1 and n != total]
            if groups:
                issues.append(f"[R2] {p} 写了总数「恰好{m.group(1)}」，又写了分组人数 {groups}"
                              f"——人数写了两遍，实测会画成别的数字；只给总数、别点名到人")
        # 三之四：**整页只有**「不需要定妆图」的人物时，不该挂定妆件去画他。
        # ⚠ 判据必须是「只有」：一页完全可以主角配角同框（上台朗读＋台下同学），
        # 那时挂主角定妆是对的。第一版写成「出现任一不需定妆的人物就报」，
        # 把这类正常页全报了 —— 误报会让人连真报警一起忽略。
        # 判据换成「挂的这个件本来就不该出现在这一页」——比数人物可靠得多。
        # ⚠ 但 `出现页码` 是**阶段一**写的，阶段二看得更细、可能在更多页用到它，
        # 那不是错。所以下面先用 slides 的实际挂载把它补全（见 audit 开头），
        # 只有补全之后仍对不上的才报。
        # ⚠ 别拿「盘点说这个人物不需要定妆图」当判据：剪影这类**变体件**在盘点里
        # 同样标着「不需要定妆图」（它本来就不是定妆图），可封面页挂剪影件恰恰是对的。
        # 第一版那么写，把 P01/P05 两张挂对了的全报成错。
        # 同一角色挂了两张参考图（半身+全身），而正文没说明「是同一个人」——
        # 模型会当成两个人物各画一个。实测 P13 因此出现两个一模一样的男孩抱着树。
        mounts = s.get("挂载") or []
        if len(mounts) >= 2:
            stems = {re.sub(r"[-_](半身|全身|剪影|深蓝剪影).*$", "", m) for m in mounts}
            txt2 = (s.get("prompt", "") or "")
            if len(stems) == 1 and "同一个人" not in txt2 and "同一人" not in txt2:
                issues.append(f"[同一人] {p} 给同一个角色挂了 {len(mounts)} 张参考图"
                              f"（{'、'.join(mounts)}），但正文没写明这两张是同一个人 ——"
                              f"模型会当成两个人物，各画一个。")

        # 画面里有人、却一张定妆图都没挂 —— 那个人下一页就换脸了。
        # 这条程序查得了：文本里出现「男孩/女孩/学生/孩子」而挂载为空即可疑。
        # 实测漏过三处（P05-1、P05-2、P13）：阶段一没把这几页算进主角色的出现页码，
        # 阶段二照名单挂载，于是同一个「上台朗读」的动作，一页挂了、一页没挂。
        if spec.get("characters") and s.get("通道") == "生成" and not (s.get("挂载") or []):
            txt = (s.get("prompt", "") or "") + " ".join(s.get("必现细节", []))
            if re.search(r"男孩|女孩|学生|孩子|同学", txt):
                issues.append(f"[漏挂] {p} 画面里有人物，却没挂任何定妆图"
                              f"——这一页的人会和别页长得不一样。"
                              f"确实是无关路人才留空，是主角就挂上。")

        for mid in (s.get("挂载") or []):
            c = next((x for x in spec.get("characters", []) if x["id"] == mid), None)
            pages = (c or {}).get("出现页码") or []
            # 页码可能是 P06-1 这种「一页多图位」写法，归回它所属的页再比，
            # 否则 P06-1 永远对不上补全进去的 P06。
            if c and pages and p.split("-")[0] not in pages:
                issues.append(f"[三之四] {p} 挂了「{mid}」，可这个角色件自己声明只出现在 "
                              f"{pages}——不是这一页的人，挂错比不挂更糟")

        # 画到纸面的页要单独禁字：通用前缀兜不住，模型会往纸上填英文假字
        # （实测 27 张里 5 张出现 Lorem ipsum，投屏就是一页英文）。
        surf = (s.get("prompt") or "") + "".join(s.get("必现细节") or [])
        if s.get("通道") == "生成" and re.search(r"稿纸|日记本|本子|纸上|黑板|屏幕|作文纸|表格纸|卡片", surf):
            if not re.search(r"不出现任何文字|不出现文字|无文字|不出现英文|波浪线", surf):
                issues.append(f"[会长字] {p} 画面里有纸或本子，却没写禁文字 ——"
                              f"模型会往上面填英文假字。要在本页 prompt 写"
                              f"「只有波浪线示意，不出现任何可辨认文字、不出现英文字母」")

    # 静物页撞车：同一件道具画满整套课件。程序数得了 —— 从各页 prompt 里
    # 抽名词短语太脆，但「主体」字段和必现细节第一条足够看出画的是什么。
    # 实测《写日记》22 张里 8 张是「日记本+文具」的变体，翻起来非常单调。
    props = {}
    for s in spec.get("slides", []):
        if s.get("通道") != "生成" or s.get("类型") not in ("道具", None, ""):
            continue
        txt = (s.get("主体") or "") + "　" + "".join((s.get("必现细节") or [])[:1])
        for kw in ("日记本", "稿纸", "笔记本", "铅笔", "作文纸", "本子"):
            if kw in txt:
                props.setdefault(kw, []).append(s["页码"])
                break
    for kw, pgs in props.items():
        if len(pgs) > 3:
            issues.append(f"[撞车] 「{kw}」被画了 {len(pgs)} 页（{'、'.join(pgs)}）"
                          f"——同一件道具整套不要超过三次，按第三节先找"
                          f"「本页讲的那件事」「本课已出现过的例子」")

    # 建了却没有任何一页挂它的角色件 —— 白生成一张，且往往意味着该挂它的页挂错了
    used = {m for s in spec.get("slides", []) for m in (s.get("挂载") or [])}
    used |= {m for c in spec.get("characters", []) for m in (c.get("挂载") or [])}
    for c in spec.get("characters", []):
        if c["id"] not in used:
            issues.append(f"[零引用] 角色件「{c['id']}」建了，但没有任何一页或任何角色件挂它"
                          f"——要么某页该挂它却挂错了，要么它根本不必生成")
    return issues


def main():
    try:
        _main()
    except DecodeFailed as e:      # CLI 侧仍以非零码退出，行为与从前一致
        print(str(e), file=sys.stderr)
        raise SystemExit(2)


def _main():
    ap = argparse.ArgumentParser(description="详案 + PPT → 项目 JSON（拆解器）")
    ap.add_argument("deck", help="extract_deck.py 产出的 deck.json")
    ap.add_argument("plan", help="教学详案 .md / .txt / .docx")
    ap.add_argument("-o", "--out", required=True, help="输出项目 json")
    ap.add_argument("--provider", default=None, help="gemini / doubao，缺省读 .env")
    ap.add_argument("--model", default=None, help="拆解用的文本模型，缺省读 .env")
    ap.add_argument("--stage1-only", action="store_true", help="只跑角色盘点，便于先看再往下")
    ap.add_argument("--reuse-stage1", help="复用已有的阶段一结果 json，跳过重跑")
    ap.add_argument("--max-tokens", type=int, default=64000,
                    help="单次输出上限。每页都配图后输出变长，32000 会被截断（实测）")
    ap.add_argument("--style", default=None,
                    help="指定画风（如「水彩儿童插画：柔和水彩质感、干净留白」）。"
                         "不给则由模型推一个并标注待确认——画风是审美选择，不该让模型替你定")
    a = ap.parse_args()

    imgclient.load_dotenv()
    client = imgclient.make_client(a.provider)
    rules = RULES.read_text(encoding="utf-8")
    deck = json.loads(pathlib.Path(a.deck).read_text(encoding="utf-8"))
    plan = load_plan(a.plan)
    by_page = split_by_pagetag(plan)
    deck_txt = json.dumps(deck_digest(deck, by_page), ensure_ascii=False, indent=1)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # 阶段一结果是**中间产物**，写进 拆解底稿/ 而不是 -o 的同目录：
    # 落在 课件项目/ 里会被项目列表当成一个项目扫出来（实测 Web 端 500）。
    s1_path = RULES.parent / "拆解底稿" / (out.stem + "-角色盘点.json")
    s1_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"通道 {type(client).__name__}｜模型 {a.model or client.text_model}")
    tag = f"页标对齐 {len(by_page)} 页" if by_page else "详案无页标，整篇喂（退化模式）"
    print(f"详案 {len(plan)} 字｜PPT {deck['页数']} 页｜主图位 "
          f"{sum(pg['主图位数'] for pg in deck['页'])} 处｜{tag}\n")

    if a.reuse_stage1:
        s1 = json.loads(pathlib.Path(a.reuse_stage1).read_text(encoding="utf-8"))
        print(f"阶段一：复用 {a.reuse_stage1}")
    else:
        print("阶段一·盘点角色与画风 …")
        style = STYLE_GIVEN.format(v=a.style) if a.style else STYLE_NONE
        s1 = call(client, STAGE1, a.model, a.max_tokens,
                  rules=rules, plan=plan, deck=deck_txt, style=style)
        s1_path.write_text(json.dumps(s1, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  已写 {s1_path}")
    for c in s1.get("characters", []):
        print(f"  角色件 {c['id']:10} 幅{c.get('画幅'):5} 挂载={c.get('挂载')}")
    for r in s1.get("角色盘点", []):
        flag = "需定妆" if r.get("是否需要定妆图") else "不需要"
        print(f"  盘点 {r.get('人物',''):14} {flag}  {r.get('出现页码')}")

    if a.stage1_only:
        return

    print("\n阶段二·逐页图位规格 …")
    s2 = call(client, STAGE2, a.model, a.max_tokens, rules=rules, plan=plan, deck=deck_txt,
              stage1=json.dumps(s1, ensure_ascii=False, indent=1))

    # run_lesson.py 读的是 project["名称"]，这里直接落成它要的形状，
    # 免得中间再垫一层手工转换 —— 拆解产出应当可以直接开跑。
    pj = s1.get("project", "")
    # 逐页判断里判为「需要图、但只能人工找素材」的，程序补进 slides 占位。
    # 提示词里要求模型自己补，实测它照样只写在判断表里 —— 这是个确定性转换，
    # 与其反复叮嘱不如程序做掉。漏了它的后果是导出清单里没有这一行，
    # 整页在交付时被当成「不需要图」静默跳过。
    slides = list(s2.get("slides", []))
    have = {x.get("页码") for x in slides}
    for cand in s2.get("逐页判断") or s2.get("候选页") or []:
        pg = cand.get("页码")
        if not cand.get("要不要图") or pg in have:
            continue
        slides.append({
            "页码": pg, "用途": cand.get("若要则") or "（待人工找素材）",
            "角色组合": "", "画幅": "1:1", "通道": "人工素材位",
            "主体": cand.get("若要则", ""), "必现细节": [], "来源": [],
            "prompt": "", "挂载": [],
            "_说明": f"由逐页判断补入：{cand.get('理由', '')}",
        })
    # 留一份初稿：人改过描述之后还得能退回拆解器最初写的那版。
    # 与历史图同理 —— 覆盖一次就找不回来的东西，都要先留底。
    for sl in slides:
        if sl.get("prompt") and "_初稿prompt" not in sl:
            sl["_初稿prompt"] = sl["prompt"]
    slides.sort(key=lambda x: x["页码"])

    spec = {"project": pj if isinstance(pj, dict) else {"名称": str(pj)},
            "style_card": s1.get("style_card", {}),
            "characters": s1.get("characters", []), "slides": slides,
            "_逐页判断": s2.get("逐页判断") or s2.get("候选页") or [], "_角色盘点": s1.get("角色盘点", [])}
    out.write_text(json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  已写 {out}")

    print(f"\n机检（只查程序查得了的几条，查不了的见脚本 audit 注释）")
    issues = audit(spec, deck)
    for pg, det, src in audit_sources(spec, plan, deck):
        issues.append(f"[来源不实] {pg}「{det}」标的来源在详案和 PPT 里都找不到：{src}")
    if issues:
        for i in issues:
            print("  ⚠", i)
        print(f"\n共 {len(issues)} 处。机检有问题**不代表**规格其余部分是对的。")
    else:
        print("  低级错误一处没有。")
    print("  ⚠ 比喻拆没拆、必现细节准不准、画面对不对——程序判不了，必须看图。")
    print(f"\n用量：{client.usage}")


if __name__ == "__main__":
    main()
