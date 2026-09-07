# -*- coding: utf-8 -*-
"""标准包静态闸门：把机器能判的不变量一次判完，判断性内容留给核对清单。

    PYTHONUTF8=1 python 作文批改工具/validate_packs.py [某个包.json]

无参＝全量。退出码 0/1。分 FAIL（必须修）/ WARN（人眼看一眼）两级。

**它回答的是「你填的这句话是不是详案里的原话」，不回答「你填的是不是该填的那句」。**
后者机器判不了，留给 标准包核对清单/ 里每课一份的人工凭据。唯一沾边的是 C19
覆盖度弱校验，且它只报 WARN——机器没资格裁决判据对不对。

三条设计纪律：
1. grade_of / public_view / PACKS 一律 importlib 从 web/server/main.py 载入。
   副作用是好事：载入即触发 load_packs()，等于用服务端自己的加载器过了一遍。
2. 逐字比对的标点规范化与 run_regression.py:43 的 PUNCT 同源。这里不 import 它
   （那会连带拉起 make_test_sheets 及其 PIL 依赖），改为启动时读源码比对 pattern
   是否仍一致——分叉了会报警，且零额外依赖。
3. 本文件里凡是弯引号一律写 \\u201c 这类转义，不写字面字符。Write 工具会把字面
   弯引号规范化成 ASCII（见项目记忆 write-tool-normalizes-curly-quotes），而 D 组
   恰恰要拿弯引号当判据，写死字面字符等于自己把尺子弄弯。
"""
import difflib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ_ROOT = HERE.parent
PACK_DIR = HERE / "标准包"
CHECKLIST_DIR = HERE / "标准包核对清单"
SERVER = HERE / "web" / "server"

LQ, RQ = "“", "”"          # 中文左右双引号
LSQ, RSQ = "‘", "’"        # 中文左右单引号
CORNER = "「」『』"  # 直角引号，全仓禁用

# 与 run_regression.py:43 同源，见文件头纪律 2。
PUNCT = re.compile(
    "[\\s，。、；：？！" + LQ + RQ + LSQ + RSQ + "（）《》…—·,.;:?!\"'()]"
)

CANON_BANDS = ["基础过关", "良好达标", "优秀进阶"]
TOP_KEYS = [
    "schema_version", "lesson_id", "source", "meta", "learning_goal",
    "core_technique", "three_checks", "bands", "not_in_scope",
]
META_KEYS = ["grade_volume", "unit", "topic", "genre", "ability_stage",
             "textbook_requirement"]
OPTIONAL_LIST_FIELDS = ["technique_moves", "plan_card_rows", "revision_marks",
                        "model_essay_anchor_sentences",
                        "teacher_light_comment_examples"]
ID_RE = re.compile(r"^[1-6][ab]-u\d+$")
SLUG_RE = re.compile(r"^[1-6][ab]-u\d+-[a-z0-9-]+$")
GRADE_CN = "一二三四五六"
# judge_by 的量化门槛：可数说法 + 反例，缺一即没写完。
COUNTABLE = re.compile(r"[处条样段件次篇句]|以上|两|三|至少|超过")
COUNTEREX = re.compile(r"不算|不是|算不上|不能算|不作数")
# C19 取实词做锚时要滤掉的通用词，留着会让任何判据都「命中」。
STOPWORDS = {"一个", "一件", "这个", "那个", "自己", "别人", "他们", "我们",
             "什么", "怎么", "这样", "那样", "可以", "能够", "或者", "以及",
             "还有", "就是", "不是", "没有", "出来", "起来", "一下", "一样"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def norm(s):
    return PUNCT.sub("", str(s or ""))


def punct_in_sync():
    """读 run_regression.py 源码比对 PUNCT，防两处口径静默分叉。"""
    src_file = SERVER / "run_regression.py"
    if not src_file.exists():
        return None
    m = re.search(r'PUNCT = re\.compile\(r"(.+)"\)', src_file.read_text(encoding="utf-8"))
    if not m:
        return None
    # 源码里是 raw string，双引号写成 \" ；两边都归一后再比，否则永远报分叉。
    return m.group(1).replace("\\\"", "\"") == PUNCT.pattern


class Report:
    def __init__(self, name):
        self.name = name
        self.fails = []
        self.warns = []

    def fail(self, code, msg, *extra):
        self.fails.append((code, msg, extra))

    def warn(self, code, msg, *extra):
        self.warns.append((code, msg, extra))

    def dump(self):
        print("\n=== " + self.name + " ===")
        if not self.fails and not self.warns:
            print("  OK")
        for code, msg, extra in self.fails:
            print("  FAIL [" + code + "] " + msg)
            for line in extra:
                print("        " + str(line))
        for code, msg, extra in self.warns:
            print("  WARN [" + code + "] " + msg)
            for line in extra:
                print("        " + str(line))


def walk_strings(obj, path=""):
    """遍历所有字符串值，跳过 lesson_id 与 source.* 路径字段。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            p = path + "." + str(k) if path else str(k)
            if p == "lesson_id" or p.startswith("source."):
                continue
            for item in walk_strings(v, p):
                yield item
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            for item in walk_strings(v, path + "[" + str(i) + "]"):
                yield item
    elif isinstance(obj, str):
        yield path, obj


def split_sentences(text):
    """详案按行切句并记住行号，供 FAIL 时给定位。"""
    out = []
    for lineno, line in enumerate(text.splitlines(), 1):
        for piece in re.split(r"[。？！；\n]", line):
            piece = piece.strip()
            if len(piece) >= 4:
                out.append((piece, lineno))
    return out


def hit(needle, source):
    """ok / loose / bad —— 严格逐字、去标点后一致、查无此句。"""
    q = str(needle or "").strip()
    if not q:
        return "ok"
    if q in source:
        return "ok"
    if norm(q) and norm(q) in norm(source):
        return "loose"
    return "bad"


def report_miss(rep, code, label, value, sents, level="fail"):
    """查无此句时打印详案里最相近的三句带行号——不给定位没人愿意修。"""
    pool = [s for s, _ in sents]
    near = difflib.get_close_matches(str(value), pool, n=3, cutoff=0.4)
    lines = ["填的是： " + str(value)[:90]]
    for cand in near:
        lineno = next(n for s, n in sents if s == cand)
        lines.append("详案 L" + str(lineno) + "： " + cand[:90])
    if not near:
        lines.append("详案里找不到相近的句子。")
    getattr(rep, level)(code, label, *lines)


def check_pack(path, srv, bp, sents_cache):
    d = json.loads(path.read_text(encoding="utf-8"))
    rep = Report(path.name)
    lid = d.get("lesson_id", "")

    # ---- A 装载与身份 ----
    if not SLUG_RE.match(str(lid)):
        rep.fail("A2", "lesson_id 格式不合规，应为 3a-u1-pinyin-slug 形态：" + str(lid))
    if srv.grade_of(d) == (99, 9, 999):
        rep.fail("A3", "grade_of 解析不出年级册单元，该包会沉到列表末尾")
    m = ID_RE.match(str(lid).rsplit("-", 1)[0] if "-" in str(lid) else "")
    head = re.match(r"^(\d)([ab])-u(\d+)", str(lid))
    meta = d.get("meta") or {}
    if head:
        g, ab, unit = int(head.group(1)), head.group(2), int(head.group(3))
        want_vol = GRADE_CN[g - 1] + "年级" + ("上" if ab == "a" else "下") + "册"
        if meta.get("grade_volume") != want_vol:
            rep.fail("A5", "lesson_id 与 meta.grade_volume 对不上：id 说 " + want_vol
                     + "，meta 写的是 " + str(meta.get("grade_volume")))
        want_unit = "第" + "零一二三四五六七八九十"[unit] + "单元" if unit <= 10 else None
        if want_unit and meta.get("unit") != want_unit:
            rep.fail("A5", "lesson_id 与 meta.unit 对不上：id 说 " + want_unit
                     + "，meta 写的是 " + str(meta.get("unit")))

    # ---- B schema 完整性 ----
    for k in TOP_KEYS:
        if k not in d:
            rep.fail("B7", "缺顶层字段 " + k)
    for k in META_KEYS:
        if not str(meta.get(k) or "").strip():
            rep.fail("B8", "meta." + k + " 缺失或为空")

    checks = d.get("three_checks") or []
    if len(checks) != 3:
        rep.fail("B9", "three_checks 应为 3 条，实为 " + str(len(checks)))
    for i, c in enumerate(checks, 1):
        if c.get("no") != i:
            rep.fail("B9", "three_checks 第 " + str(i) + " 条的 no 不是 " + str(i))
        text = str(c.get("text") or "")
        if len(text) < 6:
            rep.fail("B9", "第 " + str(i) + " 条 text 过短，疑似抽成碎片：" + text)
        disp = str(c.get("display_text") or "")
        # display_text＝界面上屏的规范维度名（text 是学生当堂听过的原话，只进提示词）。
        # 缺了不会报错、界面自动回退到原话——所以只有这条警告拦得住「新课漏填」。
        if not disp:
            rep.warn("B13", "第 " + str(i) + " 条缺 display_text，界面会回落到课堂原话")
        elif len(disp) > 26:
            rep.warn("B13", "第 " + str(i) + " 条 display_text 过长，上屏会折行：" + disp)
        jb = str(c.get("judge_by") or "")
        if not jb.strip():
            rep.fail("B9", "第 " + str(i) + " 条缺 judge_by")
        else:
            if not COUNTABLE.search(jb):
                rep.warn("B12", "第 " + str(i) + " 条 judge_by 没有可数门槛（几处/几段/两处以上），"
                         "模型会把一两句带过判成达成")
            if not COUNTEREX.search(jb):
                rep.warn("B12", "第 " + str(i) + " 条 judge_by 没写反例（什么不算），"
                         "缺了这一段就不算写完")
        dep = c.get("depends_on")
        if dep is not None and not (1 <= dep < c.get("no", 0)):
            rep.fail("B10", "第 " + str(i) + " 条 depends_on=" + str(dep) + " 非法，须小于本条 no")

    bands = d.get("bands") or {}
    if list(bands.keys()) != CANON_BANDS:
        note = " ".join(str(x) for x in (d.get("notes") or []))
        lvl = "warn" if "档位" in note or "归一" in note else "fail"
        getattr(rep, lvl)("B11", "bands 键名必须是 " + " / ".join(CANON_BANDS)
                          + "，实为 " + " / ".join(bands.keys())
                          + "（前端 bands.indexOf 精确匹配，对不上则汇总页三档全计 0 且不报错）")

    notes_text = " ".join(str(x) for x in (d.get("notes") or []))
    for f in OPTIONAL_LIST_FIELDS:
        if f in d and not d.get(f) and f not in notes_text:
            rep.warn("B14", f + " 留空但 notes 里没交代原因")

    try:
        rendered = bp.render_pack(d)
        for bad in ["{b}", "{/b}", "None", "{{"]:
            if bad in rendered:
                rep.fail("B13", "render_pack 结果里出现 " + bad
                         + "（多半是从 student_bundle 抄 essay.notes 漏剥富文本标记，"
                           "或 null 被拼进字符串）")
    except Exception as e:  # noqa: BLE001
        rep.fail("B13", "render_pack 抛异常：" + repr(e))

    # ---- C 逐字命中 ----
    plan_rel = ((d.get("source") or {}).get("detail_plan") or "")
    plan_path = PROJ_ROOT / plan_rel
    plan_text = ""
    if plan_rel and plan_path.exists():
        plan_text = plan_path.read_text(encoding="utf-8")
        if plan_rel not in sents_cache:
            sents_cache[plan_rel] = split_sentences(plan_text)
        sents = sents_cache[plan_rel]

        for i, c in enumerate(checks, 1):
            v = c.get("text")
            r = hit(v, plan_text)
            if r == "bad":
                report_miss(rep, "C15", "第 " + str(i) + " 条判据在详案里查无此句", v, sents)
            elif r == "loose":
                rep.warn("C15", "第 " + str(i) + " 条判据去标点后才命中，"
                         "多半是加粗星号或全角空格差异，请人眼确认：" + str(v)[:80])

        for v in (d.get("model_essay_anchor_sentences") or []):
            r = hit(v, plan_text)
            if r == "bad":
                report_miss(rep, "C16", "示范文锚句在详案里查无此句", v, sents)
            elif r == "loose":
                rep.warn("C16", "示范文锚句去标点后才命中：" + str(v)[:80])

        for k, v in bands.items():
            if hit(v, plan_text) == "bad":
                rep.warn("C17", "档位 " + str(k) + " 的文字在详案里找不到（bands 允许归并改写，"
                         "但请确认不是编的）")

        # 空话词允许抽取者归纳同类（它进提示词是当例子给模型看），故不要求逐字。
        # 仍报一句，是为了让人确认这些词确实是本课语境里的空话、不是套用别课的。
        miss_words = [str(w) for w in ((d.get("anti_patterns") or {}).get("empty_words") or [])
                      if hit(w, plan_text) == "bad"]
        if miss_words:
            rep.warn("C18", "这些空话词详案里没有原词（归纳同类是允许的，确认一下不是套用别课的）："
                     + "、".join(miss_words))

        # C19 覆盖度弱校验：用核心技法反查判据，只报 WARN。
        # 只取要点里的实词做锚，且要点自身要够长——否则「放在谁身上都行的话」这类
        # 反面例子也会被当成待覆盖要点，黄金样例都能报 2/5，警告一多就没人看了。
        tech = str(d.get("core_technique") or "")
        points = [p.strip() for p in re.split(r"[、，；]|——|—|→", tech) if len(p.strip()) >= 6]
        points = [p for p in points if not re.search(r"不写|不是|别写|这种|都行", p)]
        if points:
            blob = norm(" ".join(str(c.get("text", "")) + str(c.get("judge_by", ""))
                                 for c in checks))
            covered = 0
            for p in points:
                kws = [w for w in re.findall(r"[一-鿿]{2,3}", p)
                       if w not in STOPWORDS and len(w) >= 2]
                if any(w in blob for w in kws):
                    covered += 1
            # 只在一个要点都对不上时才报。关键词匹配对同义不同词的召回天生很差
            # （核心技法写「承接前三格图」、判据写「接住前文没有」，字面零重叠但
            # 说的是同一件事），中间比例报出来全是误报，警告一多就没人看了。
            # covered == 0 才是真信号：多半是判据整段抄成了别课的。
            if points and covered == 0:
                rep.warn("C19", "三条判据与本课核心技法字面上一个要点都对不上，"
                         "请确认判据不是抄成了别课的（措辞不同义同则属正常，"
                         "以核对清单第一项的覆盖度自问为准）")

    # ---- D 引号与字符 ----
    for p, s in walk_strings(d):
        if any(ch in s for ch in CORNER):
            rep.fail("D20", p + " 里出现直角引号，全仓禁用：" + s[:60])
        if '"' in s or "'" in s:
            rep.fail("D21", p + " 里出现 ASCII 直引号（Write 工具吞弯引号的直接症状）："
                     + s[:60])
        if s.count(LQ) != s.count(RQ):
            rep.fail("D22", p + " 左右双引号数量不配对（吞了一半的指纹）：" + s[:60])
        if re.search(r"[一-鿿][,.;:!?][一-鿿]", s):
            rep.warn("D23", p + " 中文之间夹了半角标点：" + s[:60])

    # ---- E 路径与来源 ----
    src = d.get("source") or {}
    if not plan_rel:
        rep.fail("E24", "source.detail_plan 未填")
    elif not plan_path.exists():
        rep.fail("E24", "source.detail_plan 指向的文件不存在：" + plan_rel)
    bundle = src.get("student_bundle")
    if bundle and not (PROJ_ROOT / bundle).exists():
        rep.fail("E24", "source.student_bundle 指向的文件不存在：" + str(bundle))
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(src.get("extracted_on") or "")):
        rep.fail("E25", "source.extracted_on 应为 YYYY-MM-DD，实为 "
                 + str(src.get("extracted_on")))
    # E26/E27：verified_by_human=true 自 2026-09-07 起兼有「允许上线」之义
    # （build_deploy.py 只打包 true 的包），所以 true 必须带凭据与留痕；
    # 翻它只走 confirm_pack.py，手改 JSON 漏掉确认人/日期在这里被拦。
    if src.get("verified_by_human") is True:
        stem = path.stem
        if not (CHECKLIST_DIR / (stem + "-核对清单.md")).exists():
            rep.fail("E26", "verified_by_human 标了 true，但找不到对应核对清单，"
                     "无凭据不许标已核")
        if not str(src.get("verified_by") or "").strip():
            rep.fail("E26", "verified_by_human 标了 true，但 verified_by（确认人）为空，"
                     "请用 confirm_pack.py 确认而不是手改")
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(src.get("verified_on") or "")):
            rep.fail("E26", "verified_by_human 标了 true，但 verified_on 不是 YYYY-MM-DD，实为 "
                     + str(src.get("verified_on")))
    else:
        leftover = [k for k in ("verified_by", "verified_on") if src.get(k)]
        if leftover:
            rep.warn("E27", "verified_by_human 不是 true 却带着 " + "、".join(leftover)
                     + "（撤销没撤干净？用 confirm_pack.py --revoke 清）")
    return rep


def main():
    if not PACK_DIR.exists():
        print("找不到标准包目录：" + str(PACK_DIR))
        return 1

    # 先自己把每个包解析一遍再载服务端。load_packs()（main.py:101）遇到语法坏掉的
    # JSON 是**直接抛异常**、不是跳过那一个包——一个坏包会让整个服务起不来。若先
    # _load("main")，闸门就跟着一起崩，吐一堆 traceback 而不告诉你是哪个包坏了。
    broken = []
    for f in sorted(PACK_DIR.glob("*.json")):
        try:
            json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            broken.append((f.name, repr(e)))
    if broken:
        print("\n以下标准包 JSON 语法坏掉了。**服务会整个起不来，不只是丢这一课**：")
        for name, err in broken:
            print("  FAIL [A0] " + name)
            print("        " + err)
        print("\n" + str(len(broken)) + " 个包解析失败，先修好再跑。")
        return 1

    srv = _load("main", SERVER / "main.py")
    bp = _load("build_prompt", HERE / "build_prompt.py")

    sync = punct_in_sync()
    if sync is False:
        print("WARN [P0] 本文件的 PUNCT 与 run_regression.py:43 已经分叉，"
              "逐字口径有两份，先对齐再跑。")
    elif sync is None:
        print("WARN [P0] 读不到 run_regression.py 的 PUNCT，跳过同源自检。")

    files = sorted(PACK_DIR.glob("*.json"))
    if len(sys.argv) > 1:
        want = Path(sys.argv[1]).name
        files = [f for f in files if f.name == want]
        if not files:
            print("没有这个包：" + sys.argv[1])
            return 1

    all_files = sorted(PACK_DIR.glob("*.json"))
    reps = []
    sents_cache = {}
    for f in files:
        try:
            reps.append(check_pack(f, srv, bp, sents_cache))
        except Exception as e:  # noqa: BLE001
            r = Report(f.name)
            r.fail("A1", "读不进来或校验中断：" + repr(e))
            reps.append(r)

    # A4 是全局项：两个包 lesson_id 撞了，load_packs 末行的 dict 推导会静默覆盖，
    # 一课凭空消失且 health 数字对不上——只有在这里查得到。
    glob_rep = Report("全局")
    if len(srv.PACKS) != len(all_files):
        glob_rep.fail("A4", "标准包目录有 " + str(len(all_files)) + " 个 json，"
                      "但服务端只装载了 " + str(len(srv.PACKS)) + " 个，"
                      "多半是两个包的 lesson_id 撞车被静默覆盖")
    if glob_rep.fails or glob_rep.warns:
        reps.append(glob_rep)

    for r in reps:
        r.dump()

    nf = sum(len(r.fails) for r in reps)
    nw = sum(len(r.warns) for r in reps)
    print("\n" + str(len(files)) + " 包 · " + str(nf) + " 失败 · " + str(nw) + " 警告")
    return 1 if nf else 0


if __name__ == "__main__":
    sys.exit(main())
