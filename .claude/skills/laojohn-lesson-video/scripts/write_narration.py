# -*- coding: utf-8 -*-
r"""备课视频链第 2 步：分镜单 → 旁白稿。**全链唯一调模型的一步。**

    PYTHONUTF8=1 python write_narration.py <课次> [--only s03,s08] [--export-md] [--provider gemini]

产出 `<课次>-旁白稿.json`（源，入库，人工在这里定稿）+ `--export-md` 的人读视图。

三条设计决定：

1. **判据不在这个文件里。** prompt 里的写法规则是**读 `references/narration-style.md` 原文**
   注入的，不是抄一份。改那份 md 就同时改了生成、机检、人工审稿三处口径——
   抄一份的话，第二次改 md 时这里就悄悄过期了。

2. **按环节分批，不整篇一次生成。** 一次吐 26 页会撞 max_tokens（imgclient 有截断检测，
   但截了还得重跑）；且同环节内的页要共享上下文，后一页才接得住前一页。
   每批带上一批末页的最后一块原文做接缝。

3. **失败不写空旁白。** 任一批 `_error`，已成功的批次照常落盘、失败批 blocks 置 null
   并 exit 1，靠 `--only` 重跑。写一段空的蒙混过去，会一路混到成片里才被发现。
"""
import argparse
import importlib.util
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root, md5  # noqa: E402

BATCH_MAX = 6
PAGE_HARD_MAX = 340    # 与 audit_narration.PAGE_MAX 一致：超过就是 FAIL，当场重写比事后返工便宜

# locate 起手式轮换池。**靠提示词说「别重复」治不住**——首版实测 23 页里 23 页都以
# 「这一页是」开头、20 页以「屏幕上是」接续，连听 20 分钟像复读机，而逐页看毫无问题。
# 所以改成**程序按页序指定**：每页在 prompt 里被点名用哪一种起手，模型照着写。
# 同族经验见记忆 writing-correction-tool-0818（批改工具的开场白也是这么治的）。
#
# ⚠ **池子里一条都不许是「描述屏幕上有什么」**（0921 用户第二次点名）。
# 老师正看着屏幕，把标题念一遍没有任何信息量——「屏幕上写着『先在心里选定一个人』」
# 这种等于白说。locate 要回答的是「这一页拿来干什么」，不是「这一页长什么样」。
#
# ⚠ **池子里给的是「开头怎么起」，不是「写什么角度」**。0921 第二次返工学到的：
# 上一版六个角度内容各不相同，但因为都是「说这一页…」，
# 落笔后 22 条里 19 条以「这一页」开头（86%）——角度换了，调没换。
# ⚠ **六条全部带衔接（0921 晚改）**。bridge 废除后用户反馈「前后衔接不上」——
# 查下来根因是：**过渡本该由 locate 承担，而旧池六条里只有一条真的在接上一页**
# （「学生刚…」），其余五条各说各的，页与页之间就成了硬切。
# 现在六条只换**怎么接**，不换**接不接**——接是 locate 的固有职责。
LOCATE_OPENERS = [
    "以「学生刚…」起头，先说他们手里已经有什么，再说这一页干什么",
    "以「有了…，才能…」起头，把刚才那一步的结果当成这一页的条件",
    "以「刚才是…，这一页换成…」起头，点出这一步的转换",
    "先说这一页要解决什么，再用半句回扣刚才没解决完的那个问题",
    "以老师的动作起头（到这儿你先做什么），动作里带出刚收到的那个结果",
    "以抛给学生的那个问题起头，点一句它是从刚才哪一步长出来的",
]
# do 与 risk 同病。**轮换池只给 locate 是不够的**：
# 0921 六上四实测，29 页里 **27 页的 do 以「这一页」开头**、
# **15 页直接写「这一页只有一件事不能错」**、13 页的 risk 以「学生可」开头。
# 后两个数字指向同一个根因：**判据文档里的范例句被当成了模板**。
# 这已经是同一个根因第三次犯（前两次：片尾「巡视时」、locate 「屏幕上是」）——
# **凡是写进判据文档的范例句，都会被逐字抄。**
DO_OPENERS = [
    "直接从动作起头：到这儿你先做什么",
    "从「最容易做错的是…」起头",
    "先说怎么看出做对了，再说怎么做",
    "从一个具体时机起头：学生…之后，你…",
    "从「别急着…」或「先别…」起头，点出要按住的那一下",
    "从这一步的产出物起头：这一步结束时手里该有什么",
]
WHY_OPENERS = [
    "从「不这么做会怎样」起头",
    "从「这一步的位置不能换：…」起头",
    "从「…可以放开，但…得守住」起头",
    "从学生的变化起头：这一步过了，他们才能…",
    "从「这一招是后面…的底子」起头",
    "直接说它解决的是哪一个毛病",
]
RISK_OPENERS = [
    "从学生会说出的那句话起头（直接引那个典型答法）",
    "从「收上来的东西会…」起头，说老师会碰到什么",
    "从「卡住的不是…而是…」起头",
    "从应对动作起头：遇上这种，你追问一句…",
    "从两类学生的分化起头：一类会…另一类会…",
    "从「这儿最容易卡在…」起头",
]
# 片尾禁词从机检那边取，两处共用单一源——写稿时逐词告诉模型，写完程序再查一遍，
# 不合格当场重写。0921 实测：只在硬线里写「绝不能出现巡视时」，两个课次里都犯了。
from audit_narration import OUTRO_BANNED, END_MIN, END_MAX  # noqa: E402

# ⚠ **bridge 已废除（0921，张祖庆视角审片后定）。**
# 实测 26 页里 25 页的 bridge 是同一句「……了，再翻页」，占全片 8%、四百五十多字，
# **零信息量**——老师看着自己的课件，不需要人告诉他什么时候翻页。
# 这层篇幅一律让给 risk 与 why。ROLES 里留着它只为读旧稿，新稿写出来判 FAIL。
ROLES = ("locate", "do", "why", "risk", "bridge", "end")
DEPRECATED_ROLES = ("bridge",)
REQUIRED = ("locate", "do")


def md_path_of(src, unit):
    return os.path.join(src.out_dir, unit + "-旁白稿.md")


def export_md(doc, by_id, md_path):
    """人读视图。**只是视图**——读在 md 上，改在 json 上，md 重生会被冲掉。"""
    shots = doc.get("shots", [])
    total = doc["meta"].get("chars_total") or sum(s.get("chars") or 0 for s in shots)
    with open(md_path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# %s · 备课视频旁白稿\n\n" % doc["meta"].get("course", ""))
        f.write("> 共 %d 字，预估 %.1f 分钟。"
                "**在这份 md 上读、在 json 上改**"
                "（md 是重生的视图，改了会被冲掉）。\n\n"
                % (total, doc["meta"].get("est_minutes", 0)))
        for s in shots:
            sh = by_id.get(s["id"]) or {}
            f.write("## %s · P%s · %s\n\n"
                    % (s["id"], "-".join(str(x) for x in s["pages"]),
                       sh.get("title", "")))
            if not s.get("blocks"):
                f.write("（本页未生成）\n\n")
                continue
            for b in s["blocks"]:
                f.write("**%s**：%s\n\n" % (b["role"], b["text"]))


def load_imgclient(root):
    """薄壳：按相对路径载入课件配图工具的 imgclient（CLAUDE.md §3 真源+薄壳，禁复制）。
    ⚠ 改 skill 目录名或挪 scripts 目录会静默断链——报错时先确认这条路径还在。"""
    p = os.path.join(root, "课件配图工具", "scripts", "imgclient.py")
    if not os.path.exists(p):
        raise SystemExit("找不到生图/对话客户端：%s" % p)
    spec = importlib.util.spec_from_file_location("imgclient", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def batches(shots, only=None):
    """按环节切批：同一个 env.index 的连续页一批，超过 BATCH_MAX 再切。
    课时分隔/附录页 env 为空，各自单独成批（它们本就不该跟教学页混在一个上下文里）。"""
    out, cur, key = [], [], object()
    for sh in shots:
        if only and sh["id"] not in only:
            continue
        # 按**详案环节名**切，不按 env.index——末条 envs 是合并条时（merged-tail），
        # 第 2 课时三个环节会共用同一个 index，挤进一批后上下文互相污染。
        k = (sh["lesson"], sh["step"]["name"])
        if k != key or len(cur) >= BATCH_MAX or sh["step"]["name"] is None:
            if cur:
                out.append(cur)
            cur, key = [sh], k
        else:
            cur.append(sh)
    if cur:
        out.append(cur)
    return out


def shot_brief(sh):
    """交给模型的单页切片。只给它该看的，不给整篇——省 token，也防它跨页抄串。"""
    s = sh["source"]
    return {
        "id": sh["id"],
        "PPT页": sh["pages"],
        "页型": sh["kind"],
        "栏目": sh["kicker"],
        "眉标": sh["title"],
        # ⚠ **「这是第几课时」必须给**。0921 实测：课时分隔页的师话与舞台指令都是空的，
        # 模型手里只有眉标「写作指导课」四个字，就自己猜了个「第二节课」——
        # 而那一页是第 1 课时。切片里缺的基础事实，模型不会空着，它会编。
        "第几课时": sh.get("lesson"),
        "本课时包含的环节": sh.get("lesson_steps"),
        "上一页讲的是": sh.get("prev_title"),
        "所属环节": sh["step"]["name"],
        "环节标称分钟": sh["step"]["minutes"],
        "字数预算": sh["budget_chars"],
        "师话原文": s["teacher_lines"],
        "舞台指令": s["stage"],
        "材料与应答预案": s["materials"],
        "学生可能的答案": s["refs"],
        "学生活动占位": s["interaction"],
        "必守": (sh.get("delivery") or {}).get("keep", []),
        "可放开": (sh.get("delivery") or {}).get("free", []),
        "为什么这么设计": (sh.get("delivery") or {}).get("why", []),
        "易错点": sh.get("warns", []),
        "别这么做": sh.get("nono", []),
    }


def _required_blocks_note(sh):
    """这一页手里到底有多少素材，该写哪几块——逐页算好再告诉模型。
    课时分隔页只是告诉老师第二节干什么，不是教学页，不带 why/risk。"""
    # 结构页的豁免要与 audit_narration.EXEMPT 一致：
    # 片头不写 locate（封面印着什么老师自己看得见），片尾连 bridge 也不写。
    if sh["kind"] == "cover":
        return "只写 do 一块（不写 locate）"
    if sh["kind"] == "outro":
        return "do＋end 两块（不写 locate）"
    if sh["kind"] == "lesson_split":
        return "locate＋do 两块（不写 why/risk，全页 90–160 字）"
    d = sh.get("delivery") or {}
    n_why = len(d.get("keep") or []) + len(d.get("why") or [])
    n_risk = (len(sh.get("warns") or []) + len(sh.get("nono") or [])
              + len(sh["source"].get("refs") or [])
              + len([m for m in (sh["source"].get("materials") or [])
                     if m.startswith("〔应答")]))
    blocks = ["locate", "do"]
    tail = []
    if n_why:
        blocks.append("why")
        tail.append("必守／设计意图 %d 条" % n_why)
    if n_risk:
        blocks.append("risk")
        tail.append("卡点素材 %d 条" % n_risk)
    note = "＋".join(blocks)
    if tail:
        note += "（这一页手里有：%s）" % "、".join(tail)
    return note


def build_prompt(rules, meta, batch, prev_bridge, nxt_title):
    course = meta["course"]
    cl = meta.get("course_level") or {}
    head = [
        "你在为《%s》这节写作课写「备课视频旁白」。" % course,
        "先逐字读完下面的写法判据，再动笔。判据里每一条都是硬线。",
        "",
        "===== 写法判据（references/narration-style.md 原文）=====",
        rules,
        "===== 判据结束 =====",
        "",
        "【整课背景】",
        "本课目标：%s" % (meta.get("goal") or "（未提供）"),
    ]
    if cl.get("warns"):
        head.append("整课易错点全表（页级归属只是提示，"
                    "这里才是全集）：")
        head += ["  - " + w for w in cl["warns"]]
    if cl.get("nono"):
        head.append("整课「别这么做」全表：")
        head += ["  - " + w for w in cl["nono"]]
    if prev_bridge:
        head += ["", "【接缝】上一页的收尾是：%s" % prev_bridge,
                 "本批第一页要接得上，别重新开场。"]
    if nxt_title:
        head += ["", "【下一页】%s（本批最后一页讲完要能接到这儿）" % nxt_title]

    head += [
        "",
        "【本批页面】",
        json.dumps([shot_brief(s) for s in batch], ensure_ascii=False, indent=1),
        "",
        "【输出】只输出 JSON，结构如下，不要任何解释性文字：",
        '{"shots":[{"id":"s03","blocks":[{"role":"locate","text":"..."},'
        '{"role":"do","text":"..."},{"role":"why","text":"..."},'
        '{"role":"risk","text":"..."}]}]}',
        "role 只能是 locate/do/why/risk，locate 与 do 必须有。"
        "**不要写 bridge**——「……了，再翻页」这种翻页提示一句都不要，"
        "老师看着自己的课件，不需要人告诉他什么时候翻页。"
        "省下来的篇幅写进 risk 和 why。",
        "⚠ **do 不准复述流程**。「你先…然后…最后…」这种详案上一字不差地印着，"
        "老师不需要你念一遍。do 只讲**那一步**：哪一步做错了这一页就白上，"
        "以及怎么看出做对了。**do 不超过这一页字数的一半。**",
        "⚠ **卡点（risk）是这支片子唯一的增量，有素材就必须写**——"
        "详案和课件老师手里都有，只有「学生会卡在哪」他没处看。"
        "素材有四处，**前两处最容易被忽略**："
        "①「学生可能的答案」（详案的 `参考：`）——它是一张卡点地图，"
        "告诉你学生会往哪几个方向答、哪个方向是偏的；"
        "②「材料与应答预案」里的〔应答·…〕——那就是现成的「答偏了怎么办」，"
        "正是新手最怕的时刻；③ 易错点；④ 别这么做。"
        "这四处只要有一条与本页相关，**risk 就不能空着**。",
        "⚠ **引号只用弯引号 “”／‘’**，不许用 ASCII 直引号，"
        "**也不许用直角引号「」『』**——旁白正文最终要印成字幕，直角引号在字幕带里生硬。"
        "引号是留给「让老师照着说的原话」和「学生可能说出的答案」的，"
        "**别拿引号包旁白自己在讲的话**，也别让引号里再套引号。",
        "⚠ **要把详案里的现成话术交给老师时，必须包成引语**："
        "写成：这句话建议照着问：“…”　或　追问一句：“…”，"
        "让老师听得出这是可以照搬的原句、不是旁白自己在说。"
        "〔应答…〕里的追问句尤其要这么包——不包引号就会被判成照搬详案。",
        "⚠ **`keep`／`why` 里给的是详案原句，不是旁白稿**——"
        "必须改写成对老师说的话，不允许整条搬。"
        "又：给你的素材偶尔会挂错页（关键词挂的）。"
        "**若某条素材与本页画面内容对不上，就不要用它**，"
        "按本页真正在做的事写 why；**宁可这一块短一句，也不准把同一句话说两遍凑字**。",
        "⚠ **同一条必守只在 why 里说一次，do 里不要预告**。"
        "do 写动作（怎么做、怎么看出做对了），why 写道理（为什么非这么守不可）；"
        "两块写出同一句话，逐页看不出来，连着听就是重复。",
        "⚠ **why 同理：本页的 `delivery.keep` 或 `delivery.why` 非空，"
        "why 块就必须写**。实测过一版：五页各带着 3 条必守、1 条设计意图，"
        "旁白却一页都没写 why——那五页正好是示范文拆解的核心段，把唯一的增量漏了。",
        "⚠ **课时分隔页说的是「第几课时」，切片里的「第几课时」字段是唯一依据**，"
        "不要自己猜——页面上那个 01／02 是课时序号，别当成环节编号。",
        "⚠ **课时分隔页（lesson_split）只写 locate、do 两块**，"
        "不写 risk也不写 why，全页 90–160 字——它只是告诉老师第二节要干什么，不是教学页。",
        "**不要报点击次数**（「一共四次点击」这类一律不写）。",
        "**不要描述屏幕上有什么**：「屏幕上是…」「屏幕上写着…」"
        "「封面上印着…」「这一页显示…」一律不准写，**更不准把页面标题念一遍**。"
        "老师正看着屏幕，念一遍没有任何信息量。"
        "locate 要回答的是「这一页拿来干什么」，不是「这一页长什么样」。",
        "⚠ **「为什么这么设计」这条素材来自整个环节，有时是几个环节合并的，"
        "不一定针对本页**。读一遍，**不贴切就不写 why**——"
        "宁可这一页只有 locate 和 do，**绝不准自己编一条意义出来填上**。",
        "**下列词一个都不准出现**：不仅是、不仅仅是、更是一种、真正做到、"
        "让每个孩子都、仪式感、赋能、闭环、维度、期待下次课。"
        "还有：**不写空泛升华**（「为班级留下共同记忆」「体会写作的责任感」这类）"
        "——旁白只说老师要做什么、学生会怎么样，不做意义抢答。",
        "",
        "【字数】逐页目标如下，**这是硬指标不是参考**：",
    ] + [
        "  %s：目标 %d 字（不得低于 %d）"
        % (s["id"], s["budget_chars"], int(s["budget_chars"] * 0.85)) for s in batch
    ] + [
        "写完逐页数一遍字。不够就把 do 写得更具体"
        "（多交代一步动作、多说一句收到学生回答后怎么接），"
        "或把 why 里的必守、可放开分开说清楚。"
        "但不准拿师话原文凑数，也不准写空话。",
        "",
        # ⚠ **「有素材就必须写」写成通则是治不住的**——
        # 0921 实测：prompt 里写了硬线，29 页仍有11 页漏 why。
        # 改成**逐页点名该写哪几块、手里有几条素材**，同起手式轮换池的做法。
        "【本批逐页必写的块】按下表写，**列出来的块一个都不准缺**：",
    ] + [
        "  %s：%s" % (s["id"], _required_blocks_note(s)) for s in batch
    ] + [
        "",
        "【起手式】整片最忌每页一个调——"
        "逐页看不出来，连着听十几分钟像复读机。"
        "本批每页的 locate 按下面指定的角度写，**不准全用同一种**：",
    ] + [
        # 用全局页号取模，不用批内序号——每批都从 0 开始的话，
        # 跨批又会排出同一个循环图案，等于没轮换。
        "  %s：locate %s｜do %s｜why %s｜risk %s" % (
            s["id"],
            LOCATE_OPENERS[s["pages"][0] % len(LOCATE_OPENERS)],
            DO_OPENERS[s["pages"][0] % len(DO_OPENERS)],
            WHY_OPENERS[s["pages"][0] % len(WHY_OPENERS)],
            RISK_OPENERS[s["pages"][0] % len(RISK_OPENERS)])
        for s in batch
    ] + [
        "⚠ **「这一页」这四个字，本批所有块加起来最多用一次**。"
        "实测：locate 治住了，do 又变成 29 页里 27 页「这一页…」，"
        "其中 15 页一字不差地写「这一页只有一件事不能错」。"
        "**连听二十分钟就是复读机。**",
        "⚠ **每页的 locate 都要接住前一步**——"
        "片子是连着听十九分钟的，一页讲完直接跳到下一页，听的人会断线。"
        "⚠ **但正文里不许出现「上一页」「下一页」「这一页之前」这类页码指代**——"
        "老师是连着听的，说「刚才」「前面」「学生刚…」就够了；"
        "页页报一次「上一页」，就是换了个复读机。",
        "⚠ **locate 全长 25–55 字、最多两句**。接住前一步只要半句，"
        "剩下说清这一页干什么就够了——**别把 do 该讲的动作搬进 locate**。"
        "每页切片里的「上一页讲的是」就是给你接的；"
        "**但六页不要都用同一种接法**，按下面点名的角度接。",
        "⚠ **起手式那一栏写的是「怎么起头」的说明，不是让你把它照抄进正文**。"
        "比如指定「从学生的变化起头」，你要写的是「这一步过了，他们才能…」，"
        "**不是写成「学生的变化起头：这一步过了…」**——那是说明书漏进了台词。",
        "⚠ **上面那些判据里的例句，一字都不要搬**。"
        "它们只是告诉你语气落在哪个区间，不是句式模板。",
        "同理，why 不要页页都以「这一步的设计是为了…」起头，"

    ]
    kinds = {s["kind"] for s in batch}
    if "cover" in kinds:
        head += [
            "",
            "【片头页】这一页是课件封面。**只输出 do 一块，不要 locate**"
            "（封面上印着什么老师自己看得见，再描述一遍就是凑话）。"
            "**要极简**——老师是来看课的，不是来听说明书的。"
            "do 用一句话说清：这是几年级哪一册、第几单元的习作，题目是什么，"
            "写的是哪一类（写人／写景／状物／记事等）。bridge 引向第一个环节。"
            "**不要说「这支视频会带你逐页看…」这类导览话，不要报片长，"
            "不要建议怎么用这支片子**——这些老师自己会判断。",
        ]
    if "outro" in kinds:
        head += [
            "",
            "【片尾页】这一页是课件末页。**输出 do 与 end 两块**——"
            "不要 locate（屏幕上写着 THE END，老师自己看得见，再说一遍是凑话），"
            "也不要写任何翻页提示。"
            "do 就一件事：**把本课最要紧的两三条再点一遍**"
            "（技法是什么、哪一步最容易讲僵）。"
            "end 是**结束语，一到两句、25–50 字**，结构是「一句收束＋一个落点」："
            "先给一句明确的收尾（「这一课的备课讲解就到这里。」这类），"
            "再说下一步该动手做什么"
            "（上课前把哪样东西再过一遍、哪一处提前想好怎么接）。"
            "⚠ 结束语**不是客套话**：不祝愿、不道别、不说「期待」「祝教学顺利」"
            "「各位老师」，也不夸这堂课好。它是一句实在的交代，说完片子就结束。",
            "五条硬线："
            "① **这是课上完之后的回顾，不是课堂进行中**——"
            "**绝不能出现「巡视时」「收作品的时候」「让学生……」这类课中动作**，"
            "那时候课已经结束了，没有学生可巡视；"
            "② 人称还是「你」，不许写「提醒老师们」「各位老师」；"
            "③ **不写元叙述**（「这一页没有具体教学任务」这种一句都不要）；"
            "④ **不说客套话、不祝愿**（「期待下次课」「祝教学顺利」一律不写）；"
            "⑤ 不报片长、不说「这支视频」。"
            "**下面这几个词一个都不准出现（机检直接判 FAIL）：%s。**"
            "写完自己搜一遍。" % "、".join(OUTRO_BANNED),
            "下面是**另一节课（写景）**的片尾范例，**只看它的语气和落点，"
            "内容和用词一个字都不要搬**："
            "「这一课的关键是按着脚步走，走到哪写到哪，每一处只抓最先撞进眼睛的那一样。"
            "最容易讲僵的是第三环节——学生一旦开始排景物名字，这一课就白上了，"
            "那里得舍得停下来让他们改口。」"
            "——注意它全程是回顾的口气，没有一个课堂动作指令。"
            "你要写的是**本课**的技法与卡点。",
        ]
    return "\n".join(head)


OPENERS_P = "“‘（【「『《〈"
CLOSERS_P = "”’）】」』》〉"


def sentences(text):
    """按句末标点切句，但**两条引号相关的规矩必须守住**（0921 成片实测出来的）：

    ① 句末标点后紧跟的闭引号要**一起带走**，不能留给下一句当开头——
       `追问一句：“便利之后是什么画面？”帮助他们找到例子，`
       切错就成了 `…是什么画面？` ＋ `”帮助他们找到例子，`，**20 条字幕以闭引号起行**。
    ② **引号里面的句末标点不算句末**——`再问“这里有谁？他在做什么”，`
       在里头那个问号切开，引号块就被劈成两条字幕，照样以闭引号起行。

    ⚠ 这两件都不是折行的锅（`wrap()` 管的是一条字幕内部折两行），
    是**切句就切错了位置**；所以只改 wrap 查不出来，得直接扫成品 srt 才看得见。
    """
    out, buf, depth, i = [], "", 0, 0
    while i < len(text):
        c = text[i]
        buf += c
        if c in OPENERS_P:
            depth += 1
        elif c in CLOSERS_P:
            depth = max(0, depth - 1)
            # ③ 引号里的句子说完了（`…走吧。”` / `…适用吗？”`），闭引号一合上就是句末。
            # 不切的话，引号外若没有别的句末标点，整段会连成一条——
            # 0921 实测出过 74 字和 59 字的单条字幕，折两行怎么折都有一行顶满画面。
            if depth == 0 and len(buf) >= 2 and buf[-2] in "。！？；":
                # 闭引号后面可能还跟着逗号（`…是什么画面？”，帮助他们…`）。
                # 不一起带走，下一句就以逗号开头——0921 成片里剩的最后 4 条违规全是这个。
                while i + 1 < len(text) and text[i + 1] in CLOSERS_P + "，、":
                    i += 1
                    buf += text[i]
                out.append(buf)
                buf = ""
        elif c in "。！？；" and depth == 0:
            while i + 1 < len(text) and text[i + 1] in CLOSERS_P:
                i += 1
                buf += text[i]
            out.append(buf)
            buf = ""
        i += 1
    if buf.strip():
        out.append(buf)
    return out


def comma_pieces(text):
    """按引号外的逗号／顿号切片（给超长句二切用）。"""
    out, buf, depth = [], "", 0
    for c in text:
        buf += c
        if c in OPENERS_P:
            depth += 1
        elif c in CLOSERS_P:
            depth = max(0, depth - 1)
        elif c in "，、" and depth == 0:
            out.append(buf)
            buf = ""
    if buf:
        out.append(buf)
    return out


def split_lines(blocks):
    """切成 TTS 与字幕的最小单位：一句一条 → 一次合成 → 一条字幕 cue。
    句长 >45 字在逗号处二切；<8 字的尾句并回前一句（免得蹦出半秒的碎音频）。"""
    out = []
    for b in blocks or []:
        for part in sentences(b.get("text", "")):
            t = part.strip()
            if not t:
                continue
            if len(t) > 45:
                seg, buf = [], ""
                # 二切同样只在**引号外**的逗号处下刀，理由同 sentences()——
                # 在引号里切一刀，下一条字幕照样以闭引号起行。
                for piece in comma_pieces(t):
                    if len(buf) + len(piece) > 45 and buf:
                        seg.append(buf)
                        buf = piece
                    else:
                        buf += piece
                if buf:
                    seg.append(buf)
            else:
                seg = [t]
            for x in seg:
                if out and len(x) < 8:
                    out[-1]["text"] += x
                    out[-1]["chars"] = len(out[-1]["text"])
                else:
                    out.append({"i": len(out) + 1, "role": b.get("role"),
                                "text": x, "chars": len(x), "pause_after": 0.25})
    for n, ln in enumerate(out, 1):
        ln["i"] = n
    return out


def main():
    ap = argparse.ArgumentParser(description="备课视频旁白稿（调模型）")
    ap.add_argument("unit")
    ap.add_argument("--only", help="只重跑这几个 shot，逗号分隔")
    ap.add_argument("--provider", help="doubao|gemini，缺省跟 imgclient")
    ap.add_argument("--export-md", action="store_true", help="另出人读视图 md")
    ap.add_argument("--no-retry", action="store_true",
                    help="字数不足也不重写（省调用）")
    ap.add_argument("--dry-run", action="store_true", help="只打印分批与首批 prompt")
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    sl_path = os.path.join(src.out_dir, a.unit + "-分镜单.json")
    if not os.path.exists(sl_path):
        raise SystemExit("没有分镜单，先跑 build_shotlist.py：%s" % sl_path)
    with open(sl_path, encoding="utf-8") as f:
        sl = json.load(f)

    rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "..", "references", "narration-style.md")
    with open(rules_path, encoding="utf-8") as f:
        rules = f.read()

    teacher = src.load_json("teacher_json") or {}
    meta = dict(sl["meta"])
    meta["goal"] = re.sub(r"\{/?b\}", "", (teacher.get("overview") or {}).get("goal", ""))

    out_path = os.path.join(src.out_dir, a.unit + "-旁白稿.json")
    prev = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            prev = {s["id"]: s for s in json.load(f).get("shots", [])}

    # ⚠ `--export-md` 单用时**只导出，绝不重跑**。
    # 0921 踩过：旁白已经跑到 FAIL 0，想导个人读版 md 出来给人审，
    # 结果整篇被重新生成了一遍，覆盖掉定稿（新稿 WARN 从 3 涨回 5）。
    # 模型每次产出都不一样，重跑等于把审过的稿子换掉——闸门 A 记的 md5 也就白记了。
    if a.export_md and not a.only and prev:
        with open(out_path, encoding="utf-8") as f:
            doc = json.load(f)
        md_path = md_path_of(src, a.unit)
        export_md(doc, {s["id"]: s for s in sl["shots"]}, md_path)
        print("✓ 只导出已有旁白稿，未重跑 → %s"
              % os.path.relpath(md_path, project_root()))
        return

    # 逐页记下前一页的眉标——locate 要接住上一页，模型得知道上一页在讲什么。
    # 同批生成时彼此看不到对方的成稿，所以给的是分镜单里的标题，不是旁白原文。
    # 同课时的环节清单——课时分隔页自己没有素材，靠它才说得出这一节要干什么。
    steps_of = {}
    for sh in sl["shots"]:
        nm = (sh.get("step") or {}).get("name")
        if nm:
            steps_of.setdefault(sh.get("lesson"), [])
            if nm not in steps_of[sh["lesson"]]:
                steps_of[sh["lesson"]].append(nm)
    for i, sh in enumerate(sl["shots"]):
        sh["prev_title"] = sl["shots"][i - 1]["title"] if i else None
        sh["lesson_steps"] = steps_of.get(sh.get("lesson"))

    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    groups = batches(sl["shots"], only)
    by_id = {s["id"]: s for s in sl["shots"]}
    order = [s["id"] for s in sl["shots"]]
    print("%s：%d 页 → %d 批%s"
          % (a.unit, len(sl["shots"]), len(groups), "（--only）" if only else ""))

    if a.dry_run:
        for g in groups:
            print("  批 %s" % " ".join(s["id"] for s in g))
        print("\n----- 首批 prompt -----")
        print(build_prompt(rules, meta, groups[0], None, None)[:2500])
        return

    ic = load_imgclient(root)
    cli = ic.make_client(a.provider)
    results, failed = dict(prev), []
    prev_bridge = None
    for gi, g in enumerate(groups, 1):
        last_id = g[-1]["id"]
        nxt = order[order.index(last_id) + 1] if order.index(last_id) + 1 < len(order) else None
        nxt_title = by_id[nxt]["title"] if nxt else None
        prompt = build_prompt(rules, meta, g, prev_bridge, nxt_title)
        print("  [%d/%d] %s ..." % (gi, len(groups), " ".join(s["id"] for s in g)), flush=True)
        def absorb(resp):
            for item in resp["shots"]:
                sid = item.get("id")
                if sid not in by_id:
                    continue
                blocks = [b for b in item.get("blocks", [])
                          if b.get("role") in ROLES and b.get("text")]
                lines = split_lines(blocks)
                results[sid] = {"id": sid, "pages": by_id[sid]["pages"],
                                "budget_chars": by_id[sid]["budget_chars"],
                                "blocks": blocks, "lines": lines,
                                "chars": sum(x["chars"] for x in lines)}

        r = cli.chat(prompt, max_tokens=8000, as_json=True)
        if not isinstance(r, dict) or "_error" in r or "shots" not in r:
            msg = (r or {}).get("_error", "返回里没有 shots") if isinstance(r, dict) else str(r)[:200]
            print("      ✗ %s" % msg)
            failed += [s["id"] for s in g]
            for s in g:
                results[s["id"]] = {"id": s["id"], "pages": s["pages"], "blocks": None}
            continue
        absorb(r)
        # 实测模型对字数预算普遍只做到 6~7 成，全片会掉到下限以下。带着实际字数反馈重跑一次
        # 比事后人工发现便宜得多——只重跑不达标的那几页，不动已经写好的。
        # ⚠ 各项毛病要**并列查、查完再重写、重写后复查**。
        # 0921 踩过：这里原是 if/elif 链，s99 先命中「字数不足」，
        # 片尾禁词那一支就没机会跑；重写补足了字数，「巡视」照样留在稿子里，
        # 一路静默到机检才报 FAIL。一页可以同时犯好几样，一样都不能被前一支吃掉。
        if not a.no_retry:
            for _round in range(2):
                off = []
                for s in g:
                    r0 = results.get(s["id"], {})
                    n = r0.get("chars") or 0
                    why = []
                    if n < s["budget_chars"] * 0.8:
                        why.append("字数不足")
                    elif n > PAGE_HARD_MAX:      # 超硬上限，audit 会直接 FAIL
                        why.append("超长")
                    txt = "".join(b.get("text", "") for b in (r0.get("blocks") or []))
                    roles0 = [b.get("role") for b in (r0.get("blocks") or [])]
                    # locate 接管页间衔接之后普遍写长（实测冒到 81 字），
                    # 二十六页累加就把全片顶出 6800 的硬闸。判据里写了 25–45 字，
                    # 模型不遵守——照例，写成通则治不住，程序查了才管用。
                    lo = next((b.get("text", "") for b in (r0.get("blocks") or [])
                               if b.get("role") == "locate"), "")
                    if len(lo) > 65:
                        why.append("locate %d 字" % len(lo))
                    if s["kind"] == "outro":
                        # 片尾禁词不能只靠 prompt 里那句硬线——三个课次都写出了「巡视」。
                        hit = [w for w in OUTRO_BANNED if w in txt]
                        if hit:
                            why.append("片尾禁词:" + "、".join(hit))
                        if "end" not in roles0:
                            why.append("缺结束语")
                        else:
                            ne = len((r0["blocks"][-1] or {}).get("text", ""))                                 if roles0[-1] == "end" else 0
                            if not ne:
                                why.append("结束语不在末尾")
                            elif not END_MIN <= ne <= END_MAX:
                                why.append("结束语%d字" % ne)
                    if why:
                        off.append((s, n, why))
                if not off:
                    break
                fb = ["\n【重写】下面这几页不合格，"
                      "按同样的判据重写，只返回这几页："]
                for s, n, why in off:
                    tips = []
                    for w in why:
                        if w.startswith("片尾禁词"):
                            tips.append("出现了片尾不该有的课中动作词（%s）——"
                                        "片尾是课上完之后的回顾，那时候没有学生可巡视了，"
                                        "把这些词全部拿掉" % w.split(":", 1)[1])
                        elif w.startswith("结束语") and w != "缺结束语":
                            tips.append("%s，要求 %d–%d 字，"
                                        "一到两句说完，"
                                        "只留最要紧的那一个落点"
                                        % (w, END_MIN, END_MAX))
                        elif w == "缺结束语":
                            tips.append("缺 end 块：最后要有一到两句结束语，"
                                        "给老师一个落点（上课前该动手做什么），"
                                        "不祝愿不道别")
                        elif w.startswith("locate "):
                            tips.append("locate 写到了 %s，压到 55 字以内、"
                                        "最多两句——接住前一步只要半句，"
                                        "别把 do 该说的搬进来" % w.split()[1])
                        elif w == "字数不足":
                            tips.append("只写了 %d 字，目标 %d 字" % (n, s["budget_chars"]))
                        else:
                            tips.append("写了 %d 字，必须压到 %d 字以内，"
                                        "删掉最次要的一句，别把必守和学生卡点删掉"
                                        % (n, PAGE_HARD_MAX))
                    fb.append("  %s：%s。刚才的稿子：%s"
                              % (s["id"], "；".join(tips),
                                 json.dumps(results[s["id"]]["blocks"], ensure_ascii=False)))
                print("      ↺ 重写 %s"
                      % ",".join("%s(%s)" % (s["id"], "+".join(w)) for s, _, w in off),
                      flush=True)
                r2 = cli.chat(prompt + "\n".join(fb), max_tokens=8000, as_json=True)
                if not (isinstance(r2, dict) and "shots" in r2):
                    break
                absorb(r2)
        tail = results.get(last_id, {}).get("blocks") or []
        # bridge 废除后拿末页最后一块做接缝——接缝要的是「上一页讲到哪儿了」，
        # 本来也不非得是翻页提示那句。
        prev_bridge = tail[-1]["text"] if tail else None

    shots_out = [results[i] for i in order if i in results]
    total = sum(s.get("chars") or 0 for s in shots_out)
    rate = sl["meta"].get("rate_cps", 4.7)
    doc = {"meta": {"course": a.unit,
                    "plan_md5": sl["meta"].get("plan_md5"),
                    "shotlist_md5": md5(sl_path),
                    "provider": getattr(cli, "name", a.provider or "default"),
                    "chars_total": total,
                    "est_minutes": round(total / rate / 60.0 + 1.5, 1),
                    "usage": getattr(cli, "usage", {}),
                    "audit": None},
           "shots": shots_out}
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("\n总 %d 字，预估 %.1f 分钟 → %s"
          % (total, doc["meta"]["est_minutes"], os.path.relpath(out_path, root)))

    if a.export_md:
        export_md(doc, by_id, md_path_of(src, a.unit))
        print("✓ %s" % os.path.relpath(md_path_of(src, a.unit), root))

    if failed:
        print("\n✗ %d 页未生成：%s\n   重跑：--only %s"
              % (len(failed), ",".join(failed), ",".join(failed)))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
