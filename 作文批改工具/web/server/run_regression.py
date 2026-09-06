# -*- coding: utf-8 -*-
"""真实模型的回归测试：三篇基准习作连跑，核判断层有没有退化。

    PYTHONUTF8=1 python 作文批改工具/web/server/run_regression.py [模型id]

先跑 make_test_sheets.py 生成稿纸。不启服务、直接打模型，跑完不留文件。

核五件（前三件是硬线，红了就是不合格）：
1. **引用逐字校验** —— evidence / quoted_sentence / highlights[].quote 必须
   逐字出现在原文里。找不到＝编造，这是真实性红线在批改工具上的落点。
2. **判据方向** —— 三篇是刻意设计的三种形态，判反了说明判断层不可用。
3. **depends_on** —— A 篇①不成立时，②必须记「不适用」而不是硬判。
4. 点评卡开头是否撞套路（防同质化那道防线在真实模型上还灵不灵）。
5. 有没有越界提错别字（素材里埋了两处「经长」）。
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
    q = str(quote or "").strip()
    if not q:
        return "ok"
    if q in source:
        return "ok"
    if norm(q) and norm(q) in norm(source):
        return "loose"
    return "bad"


async def grade_one(pack, img, prev_heads):
    """走与 /api/grade 同一条路：批完立刻做引用校正，回归测的才是线上行为。"""
    b64 = base64.b64encode(img.read_bytes()).decode()
    msgs = srv.build_messages(pack, [(b64, "image/jpeg")], prev_heads)
    r = srv.parse_json(await srv.call_model(msgs))
    r["_fix"] = srv.fix_quotes(r)
    srv.recount_fillers(r)             # 与 /api/grade 同一道后处理，别漏
    srv.check_paragraphs(r)
    srv.trim_verdict_tail(r)
    srv.enforce_grade_rules(pack, r)
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
            print(f"  ①②③"[no] + f" {v}{flag}")

        # 2 引用逐字校验
        quotes = [("evidence", c.get("evidence")) for c in r.get("checks", [])]
        quotes += [("quoted_sentence", r.get("quoted_sentence"))]
        quotes += [("highlight", h.get("quote")) for h in (r.get("highlights") or [])]
        # 语言毛病可以引原句（结构四项不引），引了就同样受逐字铁律管
        quotes += [("语言毛病", g.get("quote"))
                   for g in ((r.get("language") or {}).get("issues") or []) if g.get("quote")]
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
        if "经长" in card_all or "错别字" in card_all or "别字" in card_all:
            fails.append(f"{key} 篇提到了错别字（越界，那一层归老师）")
            print("  ✗ 提到了错别字——越界")

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

    if fails:
        print(f"\n不合格 {len(fails)} 项：")
        for f in fails:
            print(f"  · {f}")
    else:
        print("\n五项全过。")
    print("\n机器判不了、要你自己看的：批语像不像人话；"
          "是对家长说话还是对学生说话；下次方向具不具体到能做。")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
