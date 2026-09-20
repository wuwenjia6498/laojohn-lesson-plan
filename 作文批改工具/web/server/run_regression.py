# -*- coding: utf-8 -*-
"""真实模型的回归测试：三篇基准习作连跑，核判断层有没有退化。

    PYTHONUTF8=1 python 作文批改工具/web/server/run_regression.py [模型id]

先跑 make_test_sheets.py 生成稿纸。不启服务、直接打模型，跑完不留文件。

核六件（前三件是硬线，红了就是不合格）：
1. **引用逐字校验** —— evidence / quoted_sentence / highlights[].quote 必须
   逐字出现在原文里。找不到＝编造，这是真实性红线在批改工具上的落点。
2. **判据方向** —— 三篇是刻意设计的三种形态，判反了说明判断层不可用。
3. **depends_on** —— A 篇①不成立时，②必须记「不适用」而不是硬判。
4. 点评卡开头是否撞套路（防同质化那道防线在真实模型上还灵不灵）。
5. 有没有越界提错别字（主批改的批语里仍一个字不许提）。
6. 错别字校对层：A 篇两处「经长」都抓到、B/C 篇零误报、三篇都跑成（0917 加）。
7. 用词与修辞两类判断型毛病：报了就必须引得出原句；任何一栏都不许劝人「多用比喻」
   （三篇基准稿纸都没有比喻，这一栏一旦开始劝，三十篇就会全被劝去硬安比喻）（0920 加）。
"""
import asyncio
import base64
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


srv = _load("main")
sheets = _load("make_test_sheets")

# 判据方向的期望。写成「不许是什么」而非「必须是什么」——判定用词允许模型有
# 自己的措辞，但方向判反了就是判断层不可用。
EXPECT = {
    "A": {1: {"not": ["达成"]}, 2: {"must": ["不适用"]}, 3: {"not": ["达成"]}},
    "B": {1: {"must": ["达成", "部分达成"]}, 2: {"not": ["达成"]}},
    "C": {1: {"must": ["达成", "部分达成"]}, 2: {"must": ["达成", "部分达成"]}},
}
PUNCT = re.compile(r"[\s，。、；：？！“”‘’（）《》…—·,.;:?!\"'()]")

# 素材里埋的错别字，模型读稿时**必然**读成正字（这正是「错别字层不做」的原因）。
# 比对引用前先按这张表把原文规范化，否则会把预期行为误判成编造。
# ⚠ 0917 补：这条「必然」只对 gpt-4o 成立。豆包 doubao-seed 系列读的是学生写下的字
# （经长／kù子原样保留），所以原文与引用两边都要归一，见 check_quote。
TYPO_READ = {"经长": "经常"}

# 固定起手式：一个班二三十份发同一个群，起手动词一样就是一个模子。
# 实测 gpt-4o 三篇全是「孩子写到……」，只比前 8 字漏得掉，得单独抓。
# 起手式黑名单。⚠ 一个变体一个串，别指望前缀能覆盖变体——「孩子在作文中」这个串
# 原先没收，于是三篇点评卡全用它起头，这道防线整批静默放过（2026-08-27 实测）。
OPENERS = ["孩子写到", "孩子写道", "孩子写的", "孩子在作文中", "孩子在这篇作文中",
           "同学写到", "同学笔下", "家长您好", "这篇文章", "这篇写"]


# 空夸词表取自服务端，别在这里另写一份（那正是「改一处不改另一处」的老毛病）
EMPTY_WORDS = srv.EMPTY_WORDS


def norm(s):
    return PUNCT.sub("", str(s or ""))


def check_quote(quote, source):
    """返回 ok / loose / bad —— 严格逐字、去标点后一致、查无此句。"""
    # 引用也过一遍 TYPO_READ：保真的模型（豆包）会把「经长」原样抄下来，
    # 只归一原文不归一引用，会把它判成「编造」——两种读法都算对（0917）
    for wrong, right in TYPO_READ.items():
        quote = quote.replace(wrong, right)
    q = str(quote or "").strip()
    if not q:
        return "ok"
    if q in source:
        return "ok"
    if norm(q) and norm(q) in norm(source):
        return "loose"
    return "bad"


async def grade_one(pack, img, prev_heads):
    """走与 /api/grade **同一个函数**，回归测的才是线上行为。

    此前这里手抄了一份后处理链，几个月下来悄悄少了六道兜底（focus/concrete/order/
    cap_band/回炉/拼音），回归绿着、线上却不是那回事。0917 起统一走 grade_pipeline。"""
    b64 = base64.b64encode(img.read_bytes()).decode()
    r = await srv.grade_pipeline(pack, [(b64, "image/jpeg")], prev_heads)
    qc = r.get("quote_check") or {}
    r["_fix"] = (qc.get("fixed", 0), qc.get("suspect", 0))
    return r


async def main():
    model = sys.argv[1] if len(sys.argv) > 1 else srv.CFG["grade_model"]
    srv.CFG["grade_model"] = model
    pack = srv.PACKS["3a-u1-caicai-tashishui"]
    outdir = HERE / "_testdata"
    print(f"模型：{model}\n" + "=" * 62)

    results, heads, fails = {}, [], []

    for key in "ABC":
        img = outdir / f"sheet{key}.jpg"
        if not img.exists():
            print(f"缺 {img.name}，先跑 make_test_sheets.py")
            return 1
        name, body = sheets.PIECES[key]
        body_raw = body                             # 未归一的原文：错别字层要对着它核
        for wrong, right in TYPO_READ.items():      # 见 TYPO_READ 注释
            body = body.replace(wrong, right)
        try:
            r = await grade_one(pack, img, heads)
        except Exception as e:
            print(f"\n【{key} 篇】调用失败：{e}")
            fails.append(f"{key} 篇调用失败")
            continue
        results[key] = r
        if r.get("parent_card"):
            heads.append(r["parent_card"][:24])

        print(f"\n【{key} 篇 · {name}】读到姓名：{r.get('student_name') or '（空）'}"
              f"　档位：{r.get('band')}")
        if (r.get("student_name") or "").strip() != name:
            fails.append(f"{key} 篇姓名读错：{r.get('student_name')}")

        # 1 判据方向
        exp = EXPECT.get(key, {})
        for c in r.get("checks", []):
            no, v = c.get("no"), c.get("verdict", "")
            rule, flag = exp.get(no), ""
            if rule:
                if "must" in rule and v not in rule["must"]:
                    flag = f"  ✗ 应为 {'／'.join(rule['must'])}"
                    fails.append(f"{key}篇第{no}条判成「{v}」，应为 {'／'.join(rule['must'])}")
                elif "not" in rule and v in rule["not"]:
                    flag = f"  ✗ 不应判「{v}」"
                    fails.append(f"{key}篇第{no}条不该判「{v}」")
            # 序号取 [no-1]：原先写成 "  ①②③"[no]，两个前导空格把标签整体错了一位——
            # 屏幕上的「①」其实是第②条，第①条印成空白。fails 里的序号一直是对的，只是眼睛看错。
            # 判没达成的必须给怎么改（0917 加）：老师要的不是结论，是改哪句、怎么改
            derived = any(pc.get("no") == no and pc.get("check_kind") == "derived"
                          for pc in pack.get("three_checks") or [])
            if v in ("部分达成", "未达成") and not derived and not str(c.get("advice") or "").strip():
                flag += "  ✗ 没给怎么改"
                fails.append(f"{key}篇第{no}条判「{v}」却没给 advice")
            print("  " + "①②③"[no - 1] + f" {v}{flag}")

        # 2 引用逐字校验
        quotes = [("evidence", c.get("evidence")) for c in r.get("checks", [])]
        quotes += [("quotes", q) for c in r.get("checks", []) for q in (c.get("quotes") or [])]
        quotes += [("quoted_sentence", r.get("quoted_sentence"))]
        quotes += [("highlight", h.get("quote")) for h in (r.get("highlights") or [])]
        # 语言毛病可以引原句（结构四项不引），引了就同样受逐字铁律管
        quotes += [("语言毛病", g.get("quote"))
                   for g in ((r.get("language") or {}).get("issues") or []) if g.get("quote")]
        if ((r.get("whole_piece") or {}).get("flow") or {}).get("demo_from"):
            quotes += [("语句示范原句", r["whole_piece"]["flow"]["demo_from"])]
        w = r.get("whole_piece") or {}   # 结构四项不举原文，不参与引用校验
        bad = loose = 0
        for label, q in quotes:
            st = check_quote(q, body)
            if st == "bad":
                bad += 1
                print(f"  ✗ 编造引用（{label}）：{str(q)[:44]}…")
                fails.append(f"{key}篇编造引用（{label}）")
            elif st == "loose":
                loose += 1
        fx, sp = r.get("_fix", (0, 0))
        print(f"  引用 {len(quotes)} 处：逐字符合 {len(quotes)-bad-loose}"
              f"，标点有出入 {loose}，查无此句 {bad}"
              f"　（校正前已自动对回原文 {fx} 处、标可疑 {sp} 处）")

        # 取消「判得好就留空」之后，模型最可能的退化是把判定重说一遍
        #（判「完整」写「结构完整」）。这是唯一能机检出来的形态。
        for k, lab in (("completeness", "完整性"), ("order", "叙述顺序"),
                       ("paragraph", "分段"), ("detail", "详略"), ("flow", "语句")):
            v = w.get(k) or {}
            vd, nt = str(v.get("verdict") or ""), str(v.get("note") or "")
            if vd == "不适用":
                continue
            if not nt:
                fails.append(f"{key} 篇「{lab}」的 note 空着——判得好也要说清好在哪")
                print(f"  ✗ {lab} note 空着")
            elif [x for x in EMPTY_WORDS if x in nt]:
                w2 = [x for x in EMPTY_WORDS if x in nt]
                fails.append(f"{key} 篇「{lab}」的 note 用了空话{w2}：{nt}")
                print(f"  ✗ {lab} note 空话{w2}：{nt}")
            elif vd and vd in nt:
                rest = nt.replace(vd, "").strip("，。、；：“”‘’（）()… ")
                if len(rest) < 6:
                    fails.append(f"{key} 篇「{lab}」的 note 只是把判定重说一遍：{nt}")
                    print(f"  ✗ {lab} note 除了「{vd}」没别的：{nt}")
                else:
                    print(f"  · {lab} note 里带了判定词「{vd}」，看看能不能删掉：{nt}")

        lang = r.get("language") or {}
        print(f"  亮点 {len(r.get('highlights') or [])} 处｜"
              f"结构 " + "／".join(f"{k}:{(w.get(v) or {}).get('verdict','?')}"
                                   for k, v in (("完整", "completeness"), ("顺序", "order"),
                                                ("分段", "paragraph"), ("详略", "detail")))
              + f"｜语句:{(w.get('flow') or {}).get('verdict','?')}"
              + "｜语言毛病:" + ("／".join(g.get("kind", "?")
                                          for g in (lang.get("issues") or [])) or "无"))
        kinds = [g.get("kind") for g in (lang.get("issues") or [])]
        # 判断类的两类各最多一条（模型不守，由 tidy_language 截）
        for kd in ("用词不当", "修辞不当"):
            if kinds.count(kd) > 1:
                fails.append(f"{key} 篇「{kd}」报了 {kinds.count(kd)} 条——tidy_language 的截断没生效")
                print(f"  ✗ 「{kd}」{kinds.count(kd)} 条，程序该只留一条")
        # 每条毛病都得带改法（0918 加）。程序补的那条口水词没有改法（detail 带「——一篇里反复用同一个词」），豁免
        for g in lang.get("issues") or []:
            if str(g.get("detail") or "").endswith("一篇里反复用同一个词"):
                continue
            if not str(g.get("fix") or "").strip():
                fails.append(f"{key} 篇语言毛病「{g.get('kind')}」没给改法 fix")
                print(f"  ✗ 毛病「{g.get('kind')}」没给改法")
            elif [x for x in EMPTY_WORDS if x in str(g.get("fix"))]:
                fails.append(f"{key} 篇语言毛病「{g.get('kind')}」的改法带空夸词：{g.get('fix')}")
            if g.get("kind") == "用词重复":
                print(f"  · 用词重复（程序已复核）：{g.get('detail')}")
            # 「读出来」的那两类：程序核不了判得对不对，只核它有没有落在一句真原文上
            if g.get("kind") in ("用词不当", "修辞不当"):
                if not str(g.get("quote") or "").strip():
                    fails.append(f"{key} 篇「{g.get('kind')}」没引原句——tidy_language 的兜底没生效")
                    print(f"  ✗ 「{g.get('kind')}」没引原句")
                print(f"  · {g.get('kind')}（判得对不对要你自己看）：{g.get('detail')}")
                if g.get("kind") == "修辞不当":
                    print("    ⚠ 三篇基准稿纸都没用比喻拟人，这条多半是误报，看一眼")
        # 语句一栏的示范：不通就改顺，通篇短句就连成长句；判「通顺」且 note 说的是短句却没示范，报
        fl = w.get("flow") or {}
        if fl.get("demo_from") and fl.get("demo_to"):
            print(f"  语句示范：「{fl['demo_from']}」→「{fl['demo_to']}」")
            if [x for x in EMPTY_WORDS if x in str(fl["demo_to"])]:
                fails.append(f"{key} 篇语句示范带空夸词：{fl['demo_to']}")
        elif fl.get("verdict") in ("个别不畅", "多处不通") or "短句" in str(fl.get("note") or ""):
            fails.append(f"{key} 篇语句判「{fl.get('verdict')}」／note「{fl.get('note')}」却没给示范")
            print(f"  ✗ 语句没给示范：{fl.get('verdict')}／{fl.get('note')}")
        over = [w for w in srv.FILLERS if body.count(w) >= 3]
        if over and "口水词" not in kinds:
            fails.append(f"{key} 篇「{over[0]}」用了 {body.count(over[0])} 次却没报口水词"
                         f"——recount_fillers 的兜底没生效")
            print(f"  ✗ 口水词到线没报：{over}")
        print(f"  语言整体：{lang.get('overall', '')}")
        # 这三张基准稿纸都是三年级，详略必须记「不适用」——年级分支没生效的话，
        # 模型会给三年级硬判「重点一笔带过」，而这栏一旦说空话，整层就没人看了
        dv = (w.get("detail") or {}).get("verdict")
        if dv != "不适用":
            fails.append(f"{key} 篇三年级的详略判成了「{dv}」，应记「不适用」")
            print(f"  ✗ 三年级不该判详略，却判了「{dv}」")
        print(f"  焦点：{r.get('focus', '')}")
        print(f"  点评卡：{r.get('parent_card', '')}")

        # 5 越界提错别字
        card_all = " ".join(str(r.get(k, "")) for k in
                            ("parent_card", "teacher_note", "focus"))
        # 只认「评论错别字」的词，不认「经长」这个串本身：保真模型引用学生原句时
        # 会原样带出「经长」，那是「一字不差」的本义，不是越界（0917 换豆包后照出来的误报）
        if any(w in card_all for w in ("错别字", "别字", "写错", "错字", "应为")):
            fails.append(f"{key} 篇提到了错别字（越界，那一层归老师）")
            print("  ✗ 提到了错别字——越界")
        # 「用词不当」判的是词不是字，最容易被拿来夹带错别字（A 篇的「经长」正是诱饵）。
        # 这里词表比上面窄：改法里说「这个词用错了」是本分，只有「错别字／别字／错字」才越界。
        lang_all = " ".join(str(g.get(k2) or "")
                            for g in ((r.get("language") or {}).get("issues") or [])
                            for k2 in ("detail", "fix"))
        if any(w in lang_all for w in ("错别字", "别字", "错字")):
            fails.append(f"{key} 篇语言毛病里提到了错别字（越界）")
            print("  ✗ 语言毛病里提到了错别字——越界")

        # 6 错别字校对层：A 篇两处「经长」要都抓到，B/C 篇一处不许报，三篇都得跑成。
        #   误报比漏报伤——报到老师那里的每一条他都要对着稿纸核。
        tc = r.get("typos_check") or {}
        ty = r.get("typos") or []
        if tc.get("status") != "ok":
            fails.append(f"{key} 篇错别字校对没跑成（{tc.get('reason', '?')}）")
            print("  ✗ 错别字校对没跑成")
        else:
            off = [t for t in ty if norm(t.get("sentence", "")) not in norm(body_raw)]
            if off:
                fails.append(f"{key} 篇错别字条目对不回原文：" + "、".join(str(t.get("sentence", ""))[:15] for t in off))
                print("  ✗ 错别字条目对不回原文")
            shown = "、".join(f'{t.get("wrong")}→{t.get("right")}' + ("" if t.get("sure") else "(待核)") for t in ty) or "无"
            if key == "A":
                hit = {norm(t.get("sentence", "")) for t in ty if "经长" in str(t.get("wrong", ""))}
                print(f"  错别字：报 {len(ty)} 处（{shown}）｜「经长」命中 {len(hit)}/2")
                if len(hit) < 2:
                    fails.append(f"A 篇「经长」两处只抓到 {len(hit)} 处")
                    print("  ✗ 「经长」没抓全")
            else:
                print(f"  错别字：报 {len(ty)} 处（期望 0）：{shown}")
                if ty:
                    fails.append(f"{key} 篇错别字误报 {len(ty)} 条：{shown}")
                    print("  ✗ 错别字误报")

    # 4 点评卡开头撞不撞
    print("\n" + "=" * 62)
    def skeleton(key, r):
        """去掉姓名再比句式——三篇都写「××同学……」，只比前几字会因名字不同而漏判。"""
        t = norm(r.get("parent_card", ""))
        for k2 in results:
            t = t.replace(norm(sheets.PIECES[k2][0]), "")
        return t
    opens = {k: skeleton(k, v) for k, v in results.items()}
    for a in results:
        for b in results:
            if a < b and opens[a][:8] and opens[a][:8] == opens[b][:8]:
                fails.append(f"{a}、{b} 两篇点评卡开头雷同（去掉姓名后前 8 字相同）")
    for op in OPENERS:
        hit = [k for k, v in results.items()
               if norm(v.get("parent_card", "")).startswith(norm(op))]
        if len(hit) >= 2:
            fails.append(f"{'、'.join(hit)} 篇都用「{op}」起头——固定起手式")
    print("点评卡开头（已去姓名）：" + "　｜　".join(f"{k}「{v[:12]}…」" for k, v in opens.items()))
    # 对学生说话是实测常见毛病：点评卡是给家长看的
    for k, v in results.items():
        card = v.get("parent_card", "")
        if "你可以" in card or "你写" in card or "你看你" in card or "期待你" in card:
            fails.append(f"{k} 篇点评卡在跟孩子说话（应是跟家长说）")

    # 6 语言整体评价撞不撞车
    #
    # 这是加通用维度之后最可能的退化，也是唯一能机检出来的同质化。实测规律：
    # 约束一收紧，模型就找一个新模板躲进去——让它评语言，它会给三十篇写出同一句。
    # 三张基准稿纸差异很大（一篇写得实、一篇流水账、一篇没写完），
    # 语言评价还一模一样，就说明它在套模板而不是在读这一篇。
    print()
    print("语言整体评价：")
    for k, v in results.items():
        print(f"  {k}「{(v.get('language') or {}).get('overall', '')}」")
    ov = {k: norm((v.get("language") or {}).get("overall", "")) for k, v in results.items()}
    for a in results:
        for b in results:
            if a < b and ov[a] and ov[a] == ov[b]:
                fails.append(f"{a}、{b} 两篇语言整体评价一字不差地相同——模型在套模板")
    # 空话也要抓：这几个词是规则里点名禁止的
    for k, t in ov.items():
        for w2 in EMPTY_WORDS:
            if w2 in t:
                fails.append(f"{k} 篇语言评价用了空话「{w2}」")

    # 7 不许劝人硬加比喻：没用修辞不是毛病，写进任何一栏都会逼出三十篇假比喻
    NO_RHETORIC = ("缺少修辞", "缺乏修辞", "没有用修辞", "没有使用修辞", "未使用修辞",
                   "多用比喻", "多用修辞", "多用一些修辞", "适当运用修辞", "运用修辞手法",
                   "加入比喻", "用上比喻", "增加修辞")
    print()
    for k, v in results.items():
        lg2 = v.get("language") or {}
        blob = " ".join([str(v.get(x) or "") for x in ("parent_card", "teacher_note", "focus")]
                        + [str(lg2.get("overall") or "")]
                        + [str(g.get(x) or "") for g in (lg2.get("issues") or [])
                           for x in ("detail", "fix")]
                        + [str((c or {}).get(x) or "") for c in (v.get("checks") or [])
                           for x in ("comment", "advice")]
                        + [str((y or {}).get("note") or "")
                           for y in (v.get("whole_piece") or {}).values()])
        hit = [w for w in NO_RHETORIC if w in blob]
        if hit:
            fails.append(f"{k} 篇在劝人加修辞（「{hit[0]}」）——没用比喻不是毛病")
            print(f"  ✗ {k} 篇劝人加修辞：{hit}")

    if fails:
        print(f"\n不合格 {len(fails)} 项：")
        for f in fails:
            print(f"  · {f}")
    else:
        print("\n七项全过。")
    print("\n机器判不了、要你自己看的：批语像不像人话；"
          "是对家长说话还是对学生说话；下次方向具不具体到能做。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
