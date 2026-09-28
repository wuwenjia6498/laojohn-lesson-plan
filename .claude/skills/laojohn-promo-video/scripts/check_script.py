# -*- coding: utf-8 -*-
r"""宣传片链：脚本机检 + 素材钉 md5 + 闸门 A 记账。

    PYTHONUTF8=1 python check_script.py <线> <课次> [--pin] [--by <人>]

    --pin   给还没钉 md5 的 B-roll 素材补钉（首次选图后跑一次）；已钉的只核对不改写
    --by    人工看过脚本后记账：把 {script_md5, by, at, issues} 写进 meta.audit。
            gen_clips.py 校验它，脚本改过一个字就得重新记账。
            **闸门守的是「人审过」，不要求机检全绿**——FAIL 照样可以放行，但会记在账上。

脚本结构（第五版，2026-09-27；表演写法沿用第三版，用户判「最自然」）：
    segments[]  一段＝讲解员一个 H3 片段
        role     hook / pain / method / compare / class / spirit / cta / close（温情收尾、不念扫码）
        lines    台词，一句＝一条字幕
        shots[]  段内 1～2 镜：{station, framing, move, from_line, beats[{word, do}]}
                 station 取档案 stations；framing 只许近景三档；beats＝「说到某词时做某动作」
        broll[]  盖画不盖声的穿插：{at: 第几句(0 起), src, dur, layout?, motion?, focus?, fit?, crop?, pan?, md5?, card?}
                 照片、本课海报、课件页、课件插图都走这里（横版页三种放法见 SKILL.md「穿插」）：
                 layout full（缺省，整屏；fit contain 整页居中 / cutout 透明底插图铺米色底）
                        split（上半屏讲解员、下半屏课件）/ pan（裁出一条放大横摇，pan=[起,止]）

FAIL（必须处理）：
    - 首段不是 hook、末段不是 cta、缺 AI 标识、缺讲解员
    - 单段台词超 SEG_MAX 字、单句超 LINE_MAX 字（字幕两行）
    - 段内超 2 镜、framing / move / station 取值不对、from_line 顺序错
    - 讲解员自称真实老师/讲个人教学经历（AI 人像说「我班上有个孩子」＝虚构，真实性红线）
    - 关键词卡 kw 超 10 字、例句卡 line 超 22 字；B-roll 单张超 3.5 秒
    - 素材找不到 / md5 对不上；直引号、直角引号；广告法绝对化用语、承诺提分、报价
WARN：总字数偏离 60 秒目标、段数、相邻段机位景别相同、后期字卡一段超过 1 张、真实课堂照片少于 2 张。
"""
import argparse
import datetime
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _shared as S  # noqa: E402
import h3_prompt as H  # noqa: E402

LINE_MAX = 28               # 一句＝一条字幕，竖屏两行 × 14 字
SEG_MAX = 50                # 口播腔一段一个意思
CHARS_TARGET = (200, 280)   # 第三版节奏 ≈ 4.5 字/秒 + 段首尾余量，≈ 55~65 秒
FRAMINGS = ("close-up", "medium close-up", "three-quarter")
MOVES = ("push", "handheld", "track", "pull", "still")
KW_MAX, LINE_CARD_MAX, BROLL_MAX = 10, 22, 3.5
ROLES = ("hook", "pain", "method", "compare", "class", "spirit", "cta", "close")
BANNED = [
    # 广告法绝对化用语（“最关键的一步”是教学术语，不在此列——只拦成词的绝对化）
    "最好", "最佳", "最强", "最优", "最先进", "第一品牌", "顶级", "极致", "国家级", "全网",
    # 营销腔与承诺
    "必读", "不可错过", "神作", "爆款", "逆袭", "家长必看", "赶紧", "速来", "秒杀",
    "提分", "保证", "包过", "一定能", "满分", "100%",
    # 价格
    "价格", "优惠", "免费", "元/", "￥", "¥",
]
# 讲解员是 AI 人像：不许冒充具体老师、不许讲「我教过的孩子」类亲历（没有这个人，就没有这段经历）
SELF_CLAIM = re.compile(r"我(们)?(班|的学生|的班|教过|带过|上课时|课上)|我是.{0,4}老师|我姓")
QUOTE_BAD = re.compile(r"[\"'「」『』]")


def texts_of(sc):
    for seg in sc.get("segments") or []:
        for i, ln in enumerate(seg.get("lines") or []):
            yield seg["id"], "line%d" % (i + 1), ln
        for j, b in enumerate(seg.get("broll") or []):
            if (b.get("card") or {}).get("text"):
                yield seg["id"], "broll%d.card" % (j + 1), b["card"]["text"]
    end = (sc.get("meta") or {}).get("end") or {}
    for k in ("subtitle", "cta"):
        if end.get(k):
            yield "end", k, end[k]


def check(sc, pin=False, profile=None):
    fails, warns = [], []
    meta = sc.get("meta") or {}
    segs = sc.get("segments") or []
    if not segs:
        return ["没有 segments"], [], 0
    if segs[0].get("role") != "hook":
        fails.append("首段须是 role=hook（开头就是讲解员特写说痛点）")
    if segs[-1].get("role") not in ("cta", "close"):
        fails.append("末段须是 role=cta（扫码引导）或 close（温情收尾、不引导扫码）")
    if not meta.get("ai_label"):
        warns.append("画面无 AI 标识（meta.ai_label 空）；按《人工智能生成合成内容标识办法》，发布时应在平台勾选 AI 生成声明")
    if not meta.get("presenter"):
        fails.append("meta.presenter 为空：用哪位讲解员")
    if not 5 <= len(segs) <= 8:
        warns.append("%d 段，60 秒片子宜 5~7 段" % len(segs))
    end = meta.get("end") or {}
    if end.get("style") == "closing":       # 片尾呼应首页：要一张插画、不放二维码
        ep = S.resolve(end["illus"]) if end.get("illus") else ""
        if not ep or not os.path.exists(ep):
            fails.append("meta.end.style=closing 须给 illus（本课海报插画），且文件存在")
        else:
            real = S.md5_of(ep)
            if not end.get("md5"):
                if pin:
                    end["md5"] = real
                    print("  钉 md5  end  %s" % end["illus"])
                else:
                    fails.append("片尾插画未钉 md5（跑 --pin）")
            elif end["md5"] != real:
                fails.append("片尾插画 md5 对不上：%s" % end["illus"])
    op = meta.get("opening")
    if op:                                  # 片头首页图（可选）
        for k in ("header", "title", "subtitle", "illus"):
            if not op.get(k):
                fails.append("meta.opening.%s 为空（header 取详案首页那一行标头，按行拆成列表）" % k)
        ip = S.resolve(op["illus"]) if op.get("illus") else ""
        if ip and not os.path.exists(ip):
            fails.append("片头插图不存在：%s" % op["illus"])
        elif ip:
            real = S.md5_of(ip)
            if not op.get("md5"):
                if pin:
                    op["md5"] = real
                    print("  钉 md5  opening  %s" % op["illus"])
                else:
                    fails.append("片头插图未钉 md5（跑 --pin）")
            elif op["md5"] != real:
                fails.append("片头插图 md5 对不上：%s" % op["illus"])

    total = 0
    for sid, where, t in texts_of(sc):
        bare = t.replace("{b}", "").replace("{/b}", "")
        if QUOTE_BAD.search(bare):
            fails.append("%s.%s 有直引号或直角引号：%s" % (sid, where, t))
        for w in BANNED:
            if w in bare:
                fails.append("%s.%s 含禁用词「%s」：%s" % (sid, where, w, t))
        if where.startswith("line"):
            total += H.plen(bare)
            if len(bare) > LINE_MAX:
                fails.append("%s.%s 超 %d 字（%d）：%s" % (sid, where, LINE_MAX, len(bare), t))
            if SELF_CLAIM.search(bare):
                fails.append("%s.%s 讲解员自称真实老师或讲亲历（AI 人像没有这段经历）：%s" % (sid, where, t))
    lo, hi = CHARS_TARGET
    if not lo <= total <= hi:
        warns.append("台词总字数 %d，60 秒目标 %d~%d" % (total, lo, hi))

    stations = (profile or {}).get("stations") or {}
    photos, prev, hidden = 0, None, 0.0
    for seg in segs:
        sid = seg.get("id", "?")
        if seg.get("role") not in ROLES:
            fails.append("%s role 只认 %s" % (sid, "/".join(ROLES)))
        shots = seg.get("shots") or []
        if not shots:
            fails.append("%s 没有 shots（这一段在哪儿、什么景别、怎么动）" % sid)
        if len(shots) > 2:
            fails.append("%s 段内 %d 镜，最多 2 镜" % (sid, len(shots)))
        last_from = -1
        for i, sh in enumerate(shots):
            tag = "%s.shot%d" % (sid, i + 1)
            if sh.get("framing", "close-up") not in FRAMINGS:
                fails.append("%s framing 只许 %s（中远景脸会糊）" % (tag, " / ".join(FRAMINGS)))
            if sh.get("move", "push") not in MOVES:
                fails.append("%s move 只认 %s" % (tag, "/".join(MOVES)))
            fl = sh.get("from_line", 0)
            if (i == 0 and fl != 0) or fl <= last_from or fl >= len(seg.get("lines") or [None]):
                fails.append("%s from_line 须从 0 起、逐镜递增、落在台词范围内" % tag)
            last_from = fl
            if profile and sh.get("station") and sh["station"] not in stations:
                fails.append("%s 区域「%s」不在档案 stations（%s）" % (tag, sh["station"], "/".join(stations)))
            for bt in sh.get("beats") or []:
                if profile and bt.get("do") not in profile.get("actions", {}):
                    warns.append("%s 动作「%s」不在档案 actions 里，将按原话写进提示词" % (tag, bt.get("do")))
                if bt.get("word") and bt["word"] not in "".join(seg.get("lines") or []):
                    fails.append("%s 节拍词「%s」不在本段台词里" % (tag, bt["word"]))
        n = H.plen("".join(seg.get("lines") or []))
        if n > SEG_MAX:
            fails.append("%s 台词 %d 字，超单段上限 %d" % (sid, n, SEG_MAX))
        if shots:
            look = (shots[0].get("station"), shots[0].get("framing", "close-up"))
            if prev and look == prev:
                warns.append("%s 开场机位与上一段结尾一样（%s／%s），相邻段换区域或景别" % ((sid,) + look))
            prev = (shots[-1].get("station"), shots[-1].get("framing", "close-up"))
        brolls = seg.get("broll") or []
        if sum(1 for b in brolls if b.get("src", "").startswith("card:")) > 1:
            warns.append("%s 后期字卡超过 1 张，手机上读不过来" % sid)
        for j, b in enumerate(brolls):
            tag = "%s.broll%d" % (sid, j + 1)
            if not 0 <= b.get("at", -1) < len(seg.get("lines") or []):
                fails.append("%s at 须是本段第几句（0 起）" % tag)
            if b.get("dur", 0) > BROLL_MAX or b.get("dur", 0) <= 0:
                fails.append("%s dur 须在 0~%.1f 秒" % (tag, BROLL_MAX))
            src = b.get("src", "")
            if src.startswith("card:"):
                kind = src[5:]
                t = (b.get("card") or {}).get("text", "").replace("{b}", "").replace("{/b}", "")
                cap = {"kw": KW_MAX, "line": LINE_CARD_MAX}.get(kind)
                if cap is None:
                    fails.append("%s 卡片只认 card:kw / card:line" % tag)
                elif len(t) > cap:
                    fails.append("%s %s 卡超 %d 字（%d）：%s" % (tag, kind, cap, len(t), t))
                continue
            lay = b.get("layout", "full")
            if lay not in ("full", "split", "pan"):
                fails.append("%s layout 只认 full / split / pan" % tag)
            if b.get("fit") not in (None, "contain", "cutout"):
                fails.append("%s fit 只认 contain / cutout" % tag)
            cr = b.get("crop")
            if cr is not None and not (len(cr) == 4 and 0 <= cr[0] < cr[2] <= 1 and 0 <= cr[1] < cr[3] <= 1):
                fails.append("%s crop 须是 [x0,y0,x1,y1]，0~1 且左上小于右下" % tag)
            if lay == "pan" and not (len(b.get("pan") or []) == 2 and all(0 <= v <= 1 for v in b["pan"])):
                fails.append("%s pan 须是 [起, 止]，各 0~1（裁出那条里的横向位置）" % tag)
            if lay == "full":
                hidden += b.get("dur", 0)
            path = S.resolve(src)
            if not os.path.exists(path):
                fails.append("%s 素材不存在：%s" % (tag, src))
                continue
            if src.startswith("assets:"):
                photos += 1
            real = S.md5_of(path)
            if not b.get("md5"):
                if pin:
                    b["md5"] = real
                    print("  钉 md5  %s  %s" % (tag, src))
                else:
                    fails.append("%s 素材未钉 md5（跑 --pin）：%s" % (tag, src))
            elif b["md5"] != real:
                fails.append("%s 素材 md5 对不上（素材库重编号或文件被换过）：%s" % (tag, src))
    if total and hidden > 0.55 * total / H.CHARS_PER_SEC:
        warns.append("整屏穿插约 %.0f 秒，超过全片一半多，讲解员露面太少（分屏 split 不算不露面）" % hidden)
    if photos < 2:
        warns.append("真实课堂照片只穿插了 %d 张，家长看的是真课堂，宜 2~3 张" % photos)
    return fails, warns, total


def main():
    ap = argparse.ArgumentParser(description="宣传片脚本机检")
    ap.add_argument("line")
    ap.add_argument("unit")
    ap.add_argument("--pin", action="store_true")
    ap.add_argument("--by")
    a = ap.parse_args()

    sc, path = S.load_script(a.line, a.unit)
    profile = None
    try:
        profile = S.load_presenter(sc["meta"]["presenter"])
    except (SystemExit, KeyError) as e:
        print("  ⚠ 讲解员档案未加载，区域与动作不核：%s" % e)
    fails, warns, total = check(sc, pin=a.pin, profile=profile)
    secs = sum(s.get("seconds") or H.seconds_for(s.get("lines") or []) for s in sc.get("segments") or [])
    print("%s：%d 段 · 台词 %d 字 · 生成约 %d 秒" % (a.unit, len(sc.get("segments") or []), total, secs))
    for f in fails:
        print("  ✗ FAIL  " + f)
    for w in warns:
        print("  ⚠ WARN  " + w)
    if not fails and not warns:
        print("  ✓ 机检全过")

    if a.by:
        sc.setdefault("meta", {})["audit"] = {
            "script_md5": S.script_digest(sc), "by": a.by,
            "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "issues": fails + warns}
        print("  闸门 A 已记账：%s（带 %d 条未清项）" % (a.by, len(fails) + len(warns)))
    if a.pin or a.by:
        S.save_json(sc, path)
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
