# -*- coding: utf-8 -*-
r"""备课视频链第 3 步：旁白稿机检 + **闸门 A**。

    PYTHONUTF8=1 python audit_narration.py <课次> [--by <审稿人>] [--json]

机检八项（判据唯一源＝`references/narration-style.md`，本脚本只实现可机械判定的那部分）：
  1 单页字数 90–340        2 全片 4300–6800        3 单句 ≤45 字
  4 结构完整（locate/do 必有，bridge 已废除，role 合法）
  5 禁用词（市井口语／学术术语／AI 腔套语）
  6 **禁整句照搬详案**：连续 ≥26 字相同，或全页相同字占比 ≥30%（引语豁免）
    —— 不按片段命中判：技法名与任务指令本就该一字不差，首版误报过 7 处
  7 禁把「参考：」的学生答案讲成标准答案
  8 禁学生姓名、内部称谓、替总部承诺（师训／班型／课时费／效果数据）
  9 **增量占比**：why+risk 字数 ≥ 30%、带 risk 的页 ≥ 30%、上游卡点素材 ≥ 8 条
    —— 前两项判「这支片给没给出它承诺的东西」，第三项判「上游撑不撑得起」
另自查弯引号铁律（ASCII 直引号为零）与起手式重复。

⚠ **根 `tone_gate.py` 现在还不能直接拿来扫旁白稿**：它的 writing 档是按详案体例写的，而旁白稿的人读视图 md 用 `**locate**：` 做块标，会被它的「星号禁用」条一口气报 94 处 FAIL。
但它的 INFO 层（技法口令高密度项、破折号计数、池 6/7 词频）**手动跑一遍很有用**——起手式重复这个毛病就是它先捣出来的。
给 tone_gate 加一个 narration 档是 Phase 1 的事。

**闸门语义（照 laojohn-ppt 的 audit_against_plan.py → animate_pptx.py）**：
`--by <人>` 把 `{plan_md5, shotlist_md5, narration_md5, by, at, issues}` 写进旁白稿的
`meta.audit`；`synth_voice.py` 启动时校验三个 md5 与当前文件一致，对不上拒绝合成。

⚠ **闸门守的是「审过」不是「全绿」**——issues 非空照样可以 `--by` 放行，这与仓内既有
口径一致。反过来**机检全过也不等于审完**：旁白讲得对不对、教学判断有没有说错，
机器给不出，人仍须把 md 通读一遍。它真正拦的是两件事：旁白是对外件必须过人眼；
TTS 花钱，改一个字就得重合成整页。
"""
import argparse
import datetime
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root, md5  # noqa: E402

PAGE_MIN, PAGE_MAX = 90, 340
# 结构页不该套教学页的下限：片头就该两句话说完（实测 55 字），
# 拿 90 字卡它等于逼着写废话。
PAGE_RANGE = {"cover": (30, 160), "lesson_split": (30, 200), "outro": (70, 340)}
FILM_MIN, FILM_MAX = 4300, 6800
SENT_MAX = 45
COPY_LEN = 12          # 滑窗粒度：连续 12 字相同就算这段被详案覆盖
COPY_RUN_FAIL = 26     # 单段连续逐字相同达这个长度＝整句抄了
COPY_RATIO_FAIL = 0.30 # 全页被覆盖比例：超过就是在复述师话
COPY_RATIO_WARN = 0.20
# 增量闸：why+risk 是这支片子唯一的增量（详案与课件老师都有）。
# 0921 实测过一版：why+risk 只占 20%、risk 只占 3%，
# 而旁白总字数是详案师话的 94%——等于陪老师把详案读了一遍。
INCREMENT_MIN = 0.30
RISK_PAGES_MIN = 0.30      # 至少这么多比例的页要有卡点
REQUIRED = ("locate", "do")
ROLES = ("locate", "do", "why", "risk", "bridge", "end")
# `end` 是片尾专属的结束语。0921 用户指出片子「没有结束语」——讲完卡点戛然而止。
# 根因是早先为了删掉「期待下次课」那类客套，把收束一并禁掉了；
# **「不说空洞客套」和「不给收束」是两回事**。end 给老师一个落点（下一步动手做什么），
# 仍受 BANNED["客套话"] 约束，所以不会退回祝愿与道别。
END_MIN, END_MAX = 20, 60

BANNED = {
    "市井口语": ["搞定", "一波", "直接起飞", "拿捏",
                                 "牵引机", "开卷", "插针", "爆款", "干货"],
    "学术术语": ["支架式学习", "元认知", "具身认知",
                                 "最近发展区", "建构主义", "深度学习"],
    "AI 腻套语": ["不仅仅是", "不仅是", "更是一种",
                              "让每个孩子都", "真正做到", "赋能",
                              "闭环", "赛道", "维度",
                              "仪式感", "共同的记忆", "责任感"],
    # 空泛点题：**放到任何一节课里都成立**，所以哪儿都没说。
    # 0921 张祖庆视角审片点名：「自选详写重点能让他们的文章更有个人特色，避免千篇一律」——
    # 这一句拿掉，那一页什么都不少。机器只查得出这一类的固定搭配，
    # 判不了的那部分仍要靠人读。
    "空泛点题": ["千篇一律", "更有个人特色", "更加生动", "更有画面感了",
                 "提升写作水平", "激发兴趣", "培养语感", "打下基础",
                 "受益匪浅", "事半功倍", "水到渠成"],
    "客套话": ["期待下次", "下次课再见", "祝教学",
                           "各位老师", "提醒老师们"],
    "替总部承诺": ["师训", "班型", "课时费", "招生",
                                       "续报率", "总部会", "我们机构"],
}
# 画面描述：老师正看着屏幕，把标题念一遍没有任何信息量。
# 0921 用户两次点名（先片头「封面上印着」，后教学页「屏幕上写着」）。
# 只抓明确的描述句式，不抓正常提到材料内容的句子。
SCREEN_DESC = re.compile(
    r"屏幕上[是写显最先出]|封面上[印是写]|"
    r"这一页显示|页面上[是写]|屏幕中央")
# 片尾专属：课已经上完了，再出现这些课中动作就是时间线错乱。
# 0921 实测：片尾写了「巡视时盯住两点」，而那时候根本没学生可巡。
OUTRO_BANNED = ["巡视", "收作品", "收上来", "走一圈", "当堂"]
OPENER_LEAK = re.compile(r"[^。！？；\s]{0,10}起头[：:，]|以「[^」]{0,14}」起头")
# 人称跑偏：旁白是对老师说的，写着写着会滑成对学生说。
# 0921 实测 s11 的 locate：「现在每人选一个你最想写的变化，轻声试着说一说」——
# 这是站在教室里对孩子说的话，不是讲给老师听的备课。引语内除外。
TO_STUDENTS = re.compile(r"同学们|现在每人|请大家|我们一起来|大家一起")
STUDENT_VOICE = re.compile(r"学生会回答|学生的答案是|"
                           r"正确答案是|标准答案")
QUOTE_SPAN = re.compile(r"[『“‘][^』”’]{0,60}[』”’]")


def narration_digest(doc):
    """旁白正文的内容哈希。`synth_voice.py` 用同一个函数重算并与 meta.audit 比对——
    改了任何一个字都会对不上，闸门就拦住（TTS 花钱，不能拿旧审核放行新稿子）。"""
    import hashlib
    payload = json.dumps([{"id": s.get("id"), "blocks": s.get("blocks")}
                          for s in doc.get("shots", [])],
                         ensure_ascii=False, sort_keys=True)
    return hashlib.md5(payload.encode("utf-8")).hexdigest()


def norm(s):
    """比对用的归一化：去掉标点与空白，只留字，免得一个逗号差异就漏掉照搬。"""
    return re.sub(r"[\s　，。！？；：、—…"
                  r"「」『』“”‘’（）]", "", s or "")


def plan_corpus(plan_md):
    with open(plan_md, encoding="utf-8") as f:
        lines = [ln.strip() for ln in f]
    keep = [ln for ln in lines
            if ln.startswith("师：") or ln.startswith("〔") or ln.startswith(">")]
    return norm("".join(keep))


def check(doc, plan_norm, shotlist):
    issues = []
    by_id = {s["id"]: s for s in shotlist["shots"]}
    total = 0
    for s in doc["shots"]:
        sid = s["id"]
        blocks = s.get("blocks")
        if not blocks:
            issues.append({"shot": sid, "level": "FAIL", "kind": "未生成",
                           "msg": "这一页没有旁白"})
            continue
        roles = [b.get("role") for b in blocks]
        # 结构页的豁免：
        #   片头——不要 locate（封面印着什么老师自己看得见，再说一遍就是凑话）
        #   片尾——不要 locate（THE END 老师看得见），末块必须是 end
        EXEMPT = {"cover": ("locate",), "outro": ("locate",)}
        kind = (by_id.get(sid) or {}).get("kind")
        need = [r for r in REQUIRED if r not in EXEMPT.get(kind, ())]
        for r in need:
            if r not in roles:
                issues.append({"shot": sid, "level": "FAIL", "kind": "缺块",
                               "msg": "缺 %s" % r})
        for r in roles:
            if r not in ROLES:
                issues.append({"shot": sid, "level": "FAIL", "kind": "非法 role",
                               "msg": str(r)})
        # bridge 已废除：写了就是白占篇幅（26 页里 25 页是同一句「…了，再翻页」）。
        if "bridge" in roles:
            issues.append({"shot": sid, "level": "FAIL", "kind": "写了 bridge",
                           "msg": "翻页提示已废除，这层篇幅给 risk／why"})
        # 片尾必须有结束语，且必须是片尾最后一块——不然片子讲完卡点就断了。
        if kind == "outro":
            if "end" not in roles:
                issues.append({"shot": sid, "level": "FAIL", "kind": "没有结束语",
                               "msg": "片尾缺 end 块，片子会戛然而止"})
            elif roles[-1] != "end":
                issues.append({"shot": sid, "level": "FAIL", "kind": "结束语不在末尾",
                               "msg": "end 后面还有别的块"})
            else:
                n_end = len(blocks[-1].get("text", ""))
                if not END_MIN <= n_end <= END_MAX:
                    issues.append({"shot": sid, "level": "WARN", "kind": "结束语长度",
                                   "msg": "%d 字，宜 %d–%d" % (n_end, END_MIN, END_MAX)})
        elif "end" in roles:
            issues.append({"shot": sid, "level": "FAIL", "kind": "end 用错地方",
                           "msg": "结束语只能出现在片尾页"})
        text = "".join(b.get("text", "") for b in blocks)
        n = len(text)
        total += n
        lo, hi = PAGE_RANGE.get(kind, (PAGE_MIN, PAGE_MAX))
        if n < lo or n > hi:
            issues.append({"shot": sid, "level": "FAIL", "kind": "字数",
                           "msg": "%d 字，超出 %d–%d" % (n, lo, hi)})
        elif sid in by_id:
            b = by_id[sid]["budget_chars"]
            if n < b * 0.7 or n > b * 1.35:
                issues.append({"shot": sid, "level": "WARN", "kind": "偏离预算",
                               "msg": "%d 字 vs 预算 %d" % (n, b)})
        for ln in s.get("lines", []):
            if ln["chars"] > SENT_MAX:
                issues.append({"shot": sid, "level": "WARN", "kind": "句长",
                               "msg": "%d 字：%s" % (ln["chars"], ln["text"][:24])})
        # 客套话要先剔引语再查：片尾页的 locate 会引述页面标题
        # 『 THE END · 下次课再见 』，那是屏幕上印着的字，不是旁白在说客套话。
        # AI 腻套语、替总部承诺那几类不豁免——引语里也不该有。
        text_noquote = QUOTE_SPAN.sub("", text)
        for cat, words in BANNED.items():
            hay = text_noquote if cat == "客套话" else text
            for w in words:
                if w in hay:
                    issues.append({"shot": sid, "level": "FAIL", "kind": cat, "msg": w})
        for b in blocks:
            m = SCREEN_DESC.search(b.get("text", ""))
            if m:
                issues.append({"shot": sid, "level": "FAIL",
                               "kind": "描述画面",
                               "msg": "%s…（老师看得见，别念屏幕）" % m.group(0)})
                break
        if kind == "outro":
            for w in OUTRO_BANNED:
                if w in text:
                    issues.append({"shot": sid, "level": "FAIL",
                                   "kind": "片尾写了课中动作",
                                   "msg": "%s（片尾是课后回顾，没学生可巡了）" % w})
        # why 漏写：有必守/设计意图素材却不讲，等于把唯一的增量扔了。
        # 0921 六上四实测：s09–s13 五页各带 keep3+why1，旁白里一页都没 why。
        if kind not in ("cover", "outro", "lesson_split") and "why" not in roles:
            d = (by_id.get(sid) or {}).get("delivery") or {}
            n_src = len(d.get("keep") or []) + len(d.get("why") or [])
            if n_src:
                issues.append({"shot": sid, "level": "WARN", "kind": "why 漏写",
                               "msg": "有 %d 条必守／设计意图没讲" % n_src})
        # 块间复说：逐页点名「why 必写」之后的副作用——
        # 模型把同一条必守先在 do 里预告一遍，再在 why 里原句说一遍。
        # 0921 六上四 s13：do 末句与 why 首句一字不差（坎必须来自环境和人物本身…）。
        # 逐页看不出来，连着听就是同一句话说两遍。
        bt = {b.get("role"): norm(b.get("text", "")) for b in blocks}
        # 课时说错：切片里缺「第几课时」时模型会自己编。
        # 0921 实测 s02（第 1 课时的分隔页）旁白两次说成「第二节课」，
        # 而画面上明明印着「01 写作指导课」——**看片的人一眼就看出来，机器原先看不出来**。
        les = (by_id.get(sid) or {}).get("lesson")
        if les:
            said = set(re.findall(r"第([一二两1２])[节]?课时?", text))
            num = {"1": 1, "一": 1, "２": 2, "2": 2, "二": 2, "两": None}
            for x in said:
                v = num.get(x)
                if v and v != les:
                    issues.append({"shot": sid, "level": "FAIL", "kind": "课时说错",
                                   "msg": "旁白说「第%s课」，这一页是第 %d 课时" % (x, les)})
                    break
        # locate 接管衔接之后会写长：判据给的是 25–45 字，实测冒到 58 字，
        # 二十六页累加就把全片顶出 6800 的硬闸。单页先报，别等全片 FAIL 才发现。
        for b in blocks:
            if b.get("role") == "locate" and len(b.get("text", "")) > 65:
                issues.append({"shot": sid, "level": "WARN", "kind": "locate 过长",
                               "msg": "%d 字（宜 25–55）" % len(b["text"])})
        # locate 与 do 说同一件事：0921 张祖庆视角点名 s26——
        # locate「让学生通过增补细节拉开详略差距」、do「先看学生是否对照自检发现不足」，
        # 一件事换个说法讲两遍，听的人会以为自己漏了什么，回头再听一遍才发现没漏。
        ld = [norm(b.get("text", "")) for b in blocks
              if b.get("role") in ("locate", "do")]
        if len(ld) == 2 and ld[0] and ld[1]:
            hit = ""
            a0 = ld[0]
            for i in range(0, max(0, len(a0) - 10 + 1)):
                if a0[i:i + 10] in ld[1]:
                    k = 10
                    while i + k <= len(a0) and a0[i:i + k] in ld[1]:
                        k += 1
                    if k - 1 > len(hit):
                        hit = a0[i:i + k - 1]
            if hit:
                issues.append({"shot": sid, "level": "WARN", "kind": "locate 与 do 重合",
                               "msg": "重了 %d 字：%s" % (len(hit), hit[:18])})
        # 块内自复述：同一句话在一块里说两三遍。
        # 0921 六上四 s12：why 里「写在哪里最管用？就写在遇到坎的时候」连说三遍。
        # 根因是那一页的 keep/why 素材挂错了页，模型被「必写 why」逼着凑字。
        for role, bn in bt.items():
            for i in range(0, max(0, len(bn) - 12 + 1)):
                if bn[i + 12:].find(bn[i:i + 12]) >= 0:
                    issues.append({"shot": sid, "level": "WARN", "kind": "块内自复述",
                                   "msg": "%s 里「%s…」说了不止一遍"
                                          % (role, bn[i:i + 12])})
                    break
        for ra, rb in (("do", "why"), ("do", "risk"), ("why", "risk")):
            a, b2 = bt.get(ra), bt.get(rb)
            if not a or not b2:
                continue
            hit = ""
            for i in range(0, max(0, len(a) - 12 + 1)):
                if a[i:i + 12] in b2:
                    k = 12
                    while i + k <= len(a) and a[i:i + k] in b2:
                        k += 1
                    if k - 1 > len(hit):
                        hit = a[i:i + k - 1]
            if hit:
                issues.append({"shot": sid, "level": "WARN", "kind": "块间复说",
                               "msg": "%s 与 %s 重了 %d 字：%s"
                                      % (ra, rb, len(hit), hit[:20])})
        # 轮换池指令泄漏：prompt 里写的是「从学生的变化起头：这一步过了，他们才能…」，
        # 模型把**指令那半句**也抄进了正文（0921 五上四 s09 实测一处）。
        # 逐页点名治住了漏写，代价是指令措辞本身会被当成句子开头——两头都要看。
        m = OPENER_LEAK.search(text)
        if m:
            issues.append({"shot": sid, "level": "FAIL", "kind": "轮换池指令泄漏",
                           "msg": "%s…（那是写法说明，不是台词）" % m.group(0)[:16]})
        m2 = TO_STUDENTS.search(text_noquote)
        if m2:
            issues.append({"shot": sid, "level": "WARN", "kind": "对学生说话",
                           "msg": "%s…（旁白是对老师说的）" % m2.group(0)})
        if STUDENT_VOICE.search(text):
            issues.append({"shot": sid, "level": "FAIL", "kind": "学生答案当标准",
                           "msg": STUDENT_VOICE.search(text).group(0)})
        if '"' in text or "'" in text:
            issues.append({"shot": sid, "level": "FAIL", "kind": "ASCII 直引号",
                           "msg": "弯引号铁律"})
        # 直角引号在字幕带里显得生硬，0921 用户定：旁白正文只用弯引号。
        bad = [c for c in "「」『』" if c in text]
        if bad:
            issues.append({"shot": sid, "level": "FAIL", "kind": "直角引号",
                           "msg": "%s（旁白正文只用 “”／‘’）" % "".join(bad)})
        # 同形嵌套：“…“…”…” 念出来分不清层次，多半是拿引号包了旁白自己的话。
        if re.search(r"“[^”]*“", text) or re.search(r"‘[^’]*‘", text):
            issues.append({"shot": sid, "level": "WARN", "kind": "引号同形嵌套",
                           "msg": "引号里套引号——内层换成不加引号的说法"})
        # 照搬检测：先挖掉引语（判据允许引用 keep 点名的那句），再滑窗比对。
        # ⚠ 判的是**比例与最长连续段**，不是「出现过相同的 12 字」——
        # 技法名、学生任务指令、情境设定本来就必须与详案一字不差（仓内对技法名有硬要求），
        # 按片段命中判会把这些全误报成照搬。首版就误报了 7 处，条条都是该一致的术语。
        body = norm(QUOTE_SPAN.sub("", text))
        covered = [False] * len(body)
        longest, run = 0, 0
        for i in range(0, max(0, len(body) - COPY_LEN + 1)):
            if body[i:i + COPY_LEN] in plan_norm:
                for k in range(i, i + COPY_LEN):
                    covered[k] = True
        for flag in covered:
            run = run + 1 if flag else 0
            longest = max(longest, run)
        ratio = (sum(covered) / float(len(body))) if body else 0.0
        if longest >= COPY_RUN_FAIL:
            issues.append({"shot": sid, "level": "FAIL", "kind": "照搬详案",
                           "msg": "连续 %d 字落在详案里（要引就包成『…』）" % longest})
        elif ratio >= COPY_RATIO_FAIL:
            issues.append({"shot": sid, "level": "FAIL", "kind": "照搬详案",
                           "msg": "全页 %.0f%% 与详案逐字相同" % (ratio * 100)})
        elif ratio >= COPY_RATIO_WARN:
            issues.append({"shot": sid, "level": "WARN", "kind": "追得近",
                           "msg": "全页 %.0f%% 与详案逐字相同" % (ratio * 100)})
    if total < FILM_MIN or total > FILM_MAX:
        issues.append({"shot": "-", "level": "FAIL", "kind": "全片字数",
                       "msg": "%d 字，超出 %d–%d" % (total, FILM_MIN, FILM_MAX)})
    issues += check_stock_phrases(doc)
    issues += check_increment(doc, shotlist, total)
    # 页码指代：bridge 删掉后 locate 接管衔接，模型转头页页报「上一页」——
    # 同一个「指令措辞被照抄」的根因，0921 一天里第五次。老师连着听，说「刚才」就够了。
    n_ref = sum(t.count("上一页") + t.count("下一页")
                for s in doc.get("shots", [])
                for t in [b.get("text", "") for b in (s.get("blocks") or [])])
    if n_ref > 2:
        issues.append({"shot": "-", "level": "WARN", "kind": "页码指代太多",
                       "msg": "全片说了 %d 次「上一页／下一页」，改用「刚才」「前面」" % n_ref})
    return issues, total


def check_increment(doc, shotlist, total):
    """增量含量：why+risk 占全片多少。

    **这是判「这支片子到底给了不与他手里没有的东西」的唯一硬指标。**
    do 写得再好也是详案里有的；why/risk 才是配套旁注里那层、老师无处可看的。
    同时报该课次的卡点素材存量：素材太少就不是写稿的错，是上游空。
    """
    out = []
    inc = 0
    risk_pages = 0
    for s in doc.get("shots", []):
        has_risk = False
        for b in s.get("blocks") or []:
            if b.get("role") in ("why", "risk"):
                inc += len(b.get("text", ""))
            if b.get("role") == "risk":
                has_risk = True
        if has_risk:
            risk_pages += 1
    n = max(1, len(doc.get("shots", [])))
    ratio = inc / float(total or 1)
    if ratio < INCREMENT_MIN:
        out.append({"shot": "-", "level": "WARN", "kind": "增量偏低",
                    "msg": "why+risk 只占 %.0f%%（下限 %.0f%%）"
                           "——剩下的多半是老师手里已有的"
                           % (ratio * 100, INCREMENT_MIN * 100)})
    if risk_pages < n * RISK_PAGES_MIN:
        out.append({"shot": "-", "level": "WARN", "kind": "卡点太少",
                    "msg": "只有 %d/%d 页写了学生会卡在哪" % (risk_pages, n)})
    # 上游素材存量（分镜单里数）：少于 8 条就不是写稿能解决的
    src = 0
    for s in shotlist.get("shots", []):
        src += len(s["source"].get("refs") or [])
        src += len([m for m in (s["source"].get("materials") or [])
                    if m.startswith("〔应答")])
        src += len(s.get("warns") or []) + len(s.get("nono") or [])
    if src < 8:
        out.append({"shot": "-", "level": "WARN", "kind": "上游素材薄",
                    "msg": "全课可用卡点素材只有 %d 条"
                           "（参考：／〔应答〕／易错点）——"
                           "**不是写稿的错，是这一课撑不起一支片**" % src})
    return out


def check_stock_phrases(doc):
    """起手式重复。**这是听觉上最要命的一项，而单页逐页看永远发现不了。**
    首版实测：「这一页是」23 页里出现 23 次、「屏幕上是」20 次、「一共四次点击」11 次——
    每页单看都没毛病，连起来听 20 分钟像复读机。
    只报 WARN：真正的解法是生成侧轮换起手式（见 write_narration 的 LOCATE_OPENERS），
    这里负责让它藏不住。"""
    out = []
    by_role = {}
    for s in doc.get("shots", []):
        for b in s.get("blocks") or []:
            by_role.setdefault(b.get("role"), []).append(b.get("text", ""))
    n_shots = max(1, len(doc.get("shots", [])))
    for role, texts in by_role.items():
        # 前 3 字与前 6 字都查：「这一页」正好 3 字，只比前 6 字的话
        # 22 条里 19 条同头也报不出来（0921 实际漏过一次）。
        heads = {}
        for t in texts:
            for n in (3, 6):
                if len(t) >= n:
                    heads[t[:n]] = heads.get(t[:n], 0) + 1
        for h, c in sorted(heads.items(), key=lambda kv: -kv[1]):
            if c >= max(4, int(n_shots * (0.35 if len(h) <= 3 else 0.45))):
                out.append({"shot": "-", "level": "WARN", "kind": "起手式重复",
                            "msg": "%s 块有 %d/%d 页以「%s」开头"
                                   % (role, c, n_shots, h)})
    return out


def main():
    ap = argparse.ArgumentParser(description="旁白稿机检与闸门 A")
    ap.add_argument("unit")
    ap.add_argument("--by", help="审稿人（给了就把审核记账写回旁白稿）")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    npath = os.path.join(src.out_dir, a.unit + "-旁白稿.json")
    spath = os.path.join(src.out_dir, a.unit + "-分镜单.json")
    for p in (npath, spath):
        if not os.path.exists(p):
            raise SystemExit("缺文件：%s" % p)
    with open(npath, encoding="utf-8") as f:
        doc = json.load(f)
    with open(spath, encoding="utf-8") as f:
        sl = json.load(f)

    issues, total = check(doc, plan_corpus(src.plan_md), sl)
    fails = [i for i in issues if i["level"] == "FAIL"]
    warns = [i for i in issues if i["level"] == "WARN"]

    if a.json:
        print(json.dumps(issues, ensure_ascii=False, indent=1))
    else:
        rate = sl["meta"].get("rate_cps", 4.7)
        print("%s：%d 页，%d 字，约 %.1f 分钟"
              % (a.unit, len(doc["shots"]), total, total / rate / 60 + 1.5))
        print("FAIL %d · WARN %d" % (len(fails), len(warns)))
        for i in fails + warns:
            print("  [%s] %-6s %-10s %s" % (i["level"], i["shot"], i["kind"], i["msg"][:60]))

    if a.by:
        doc["meta"]["audit"] = {
            "by": a.by,
            "at": datetime.date.today().isoformat(),
            "plan_md5": md5(src.plan_md),
            "shotlist_md5": md5(spath),
            # 对**旁白正文本身**取哈希，不是对文件——把 audit 写进文件后文件就变了，
            # 拿文件 md5 会立刻自我失效。下游用同一个函数重算，比的是同一样东西。
            "narration_md5": narration_digest(doc),
            "issues": ["%s/%s/%s" % (i["level"], i["shot"], i["kind"]) for i in issues],
        }
        with open(npath, "w", encoding="utf-8", newline="\n") as f:
            json.dump(doc, f, ensure_ascii=False, indent=2)
        print("\n✓ 已记账：%s / %s（issues %d 条，非空照样放行）"
              % (a.by, doc["meta"]["audit"]["at"], len(issues)))
        print("  下一步可跑 synth_voice.py")
    elif fails:
        print("\n审完确认无误后，用 --by <你的名字> 放行"
              "（issues 非空也能放行，闸门守的是「审过」）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
