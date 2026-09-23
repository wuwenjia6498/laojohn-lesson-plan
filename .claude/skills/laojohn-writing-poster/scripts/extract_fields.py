# -*- coding: utf-8 -*-
r"""extract_fields.py —— 写作课详案 → 单元海报骨架 data.json（两段式第 1 步：机械抽取）

    PYTHONUTF8=1 python extract_fields.py <写作课详案.md> [--out <data.json>] [--dry-run]

默认输出 <项目根>/写作课海报输出/<课次>/<课次>-习作海报.json（--out 覆盖，默认 None）。
--dry-run 只把结果打到 stdout、不落盘（对全部详案跑一遍回归用）。

字段三分类（契约唯一源 references/data_schema.md）：
  A 类  本脚本机械抽、照抄不改写：课次/年级册/单元/题目/文体/胶囊/三卡固定栏目名/CTA 固定项
  C 类  留【…待 AI 提炼…】占位，由 AI 读 _sources 证据块填实（唯一写字处，只许压缩改写详案已有内容）
  _sources  证据块：提纲表两行原文、两课时环节名、「学写法」环节的提醒句/对比段、同课次配套 json 的可复用句

解析依据＝ laojohn-writing-lesson/references/lesson-structure.md §四 锁死的首页结构与课时/环节标题体例。
已知形态差异（2026-09-20 对 24 份详案实测）：副标题不在固定行号、可无空格、可无括号文体；
第 2 课时环节数 2 或 3；`[授课提示：…]` 有的有有的没有——先整段剔除再切分。
已有 json 再跑：只刷新 course/capsule/_sources，AI 已填的 C 类字段保留（不会被占位覆盖）。
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

H1_RE = re.compile(r"^#\s*《(?P<topic>[^》]+)》\s*·\s*写作课教学设计\s*$", re.M)
SUB_RE = re.compile(
    r"^(?P<gl>[一二三四五六]年级[上下]册)·(?P<unit>第[一二三四五六七八]单元)\s*校内同步写作"
    r"(?:（(?P<genre>[^）]+)）)?\s*$", re.M)
ROW_RE = re.compile(r"^\|\s*(?P<k>课题·课时|能力阶段|同类习作顺序|教材要求|学习目标|核心技法)\s*\|\s*(?P<v>.+?)\s*\|\s*$", re.M)
TIP_RE = re.compile(r"^\[授课提示：.*?\]\s*$", re.M | re.S)
LESSON_RE = re.compile(r"^## (?P<n>第[12]课时) · (?P<name>.+?)\s*$", re.M)
APPENDIX_RE = re.compile(r"^## 附[：:]", re.M)
SECTION_RE = re.compile(r"^### (?P<no>[一二三四五六七八九十]+)、(?P<name>.+?)（约\s*(?P<min>\d+)\s*分钟[^）]*）\s*$", re.M)
TEACHER_RE = re.compile(r"^师：(?P<s>.+?)\s*$", re.M)
COMPARE_RE = re.compile(r"^师：第(?P<i>[一二])段：(?P<s>.+?)\s*$", re.M)
BOLD_RE = re.compile(r"\{b\}(.+?)\{/b\}")
WARN_KEYS = ("流水账", "不是", "不要", "别", "而是", "这就是")

# 三张卡的固定栏目名（63 张统一，机械写死；痛点与教法合并一卡，再递进到收获与滋养）
CARD_LABELS = [("pain", "写作难点 · 教法"), ("gain", "能力收获"), ("spirit", "成长收获")]

PH = {
    "subtitle": "【副题待 AI 提炼：8–14 字，压缩自 _sources.companion.oneline 或 学习目标 行】",
    "pain_head": "【卡①标题待 AI 提炼：≤10 字，概括式短语，如「跳出流水账困局」，取自 _sources.warn_sentences 与 compare.bad】",
    "pain_lines": "【卡①正文待 AI 提炼：两段共 ≤60 字，第一段写孩子最常见的那个真实问题，第二段「教会孩子…」写本课这一招怎么做】",
    "gain_head": "【卡②标题待 AI 提炼：≤10 字，学完多出来的那项能力，如「让情绪跃然纸上」】",
    "gain_lines": "【卡②正文待 AI 提炼：一段 ≤60 字，「告别…」起句，写做到以后文章是什么样，取自 核心技法 与 companion.skills_text】",
    "spirit_head": "【卡③标题待 AI 提炼：≤10 字，这类写作长在孩子身上的东西，如「不可被复制的内心体悟」】",
    "spirit_lines": "【卡③正文待 AI 提炼：两段共 ≤60 字，写这一课在能力之上的价值；唯一允许价值判断式表述、不逐句反查详案的卡】",
    "outcome": "【CTA 产出句待 AI 提炼：≤14 字，如「完成孩子的第一篇完整日记」，压缩自 学习目标 行末句】",
    "subject": "【插画主体待 AI 提炼：40–120 字，只写物件不写人不写字，取详案里出现的载体；写法见 references/illustration-prompt.md】",
}


def strip_tips(md):
    return TIP_RE.sub("", md)


def split_lessons(md):
    """返回 {"第1课时": (课型名, 正文), "第2课时": (...)}；正文截到下一课时或「## 附」为止。"""
    out = {}
    marks = list(LESSON_RE.finditer(md))
    end_all = APPENDIX_RE.search(md)
    end_all = end_all.start() if end_all else len(md)
    for i, m in enumerate(marks):
        nxt = marks[i + 1].start() if i + 1 < len(marks) else end_all
        out[m.group("n")] = (m.group("name").strip(), md[m.end():min(nxt, end_all)])
    return out


def sections(body):
    return [{"no": m.group("no"), "name": m.group("name").strip(), "min": int(m.group("min"))}
            for m in SECTION_RE.finditer(body)]


def section_body(body, name_prefix):
    ms = list(SECTION_RE.finditer(body))
    for i, m in enumerate(ms):
        if m.group("name").startswith(name_prefix):
            nxt = ms[i + 1].start() if i + 1 < len(ms) else len(body)
            return body[m.end():nxt]
    return ""


def warn_sentences(text, limit=4):
    out = []
    for m in TEACHER_RE.finditer(text):
        s = m.group("s")
        if any(k in s for k in WARN_KEYS):
            out.append(s[:120])
        if len(out) >= limit:
            break
    return out


def companion(root, cid):
    """同课次配套 json 的可复用句（有则取、无则空）。"""
    d = root / "写作配套输出" / cid
    res = {}
    p = d / ("%s-家长用_data.json" % cid)
    if p.exists():
        res["oneline"] = C.load_json(p).get("onepager", {}).get("oneline", "")
    p = d / ("%s-学生用_data.json" % cid)
    if p.exists():
        sk = C.load_json(p).get("worksheet", {}).get("skills", "")
        res["skills_b"] = BOLD_RE.findall(sk)
        res["skills_text"] = BOLD_RE.sub(r"\1", sk)
    p = d / ("%s-教师用_data.json" % cid)
    if p.exists():
        w = C.load_json(p).get("overview", {}).get("warns", [])
        res["teacher_warn0"] = BOLD_RE.sub(r"\1", w[0]) if w else ""
    return res


def build(md_path):
    md_path = Path(md_path)
    raw = md_path.read_text(encoding="utf-8")
    md = strip_tips(raw)
    course = C.parse_course_id(md_path.name)

    m = H1_RE.search(md)
    if not m:
        sys.exit("硬门槛：找不到 H1「# 《题目》· 写作课教学设计」：%s" % md_path.name)
    topic = m.group("topic").strip()
    if topic != course["topic"]:
        print("  [警告] H1 题目「%s」≠ 文件名题目「%s」，以 H1 为准" % (topic, course["topic"]), file=sys.stderr)
        course["topic"] = topic

    rows = {mm.group("k"): mm.group("v").strip() for mm in ROW_RE.finditer(md)}
    sm = SUB_RE.search(md)
    genre = (sm.group("genre") or "").strip() if sm else ""
    if not genre and "课题·课时" in rows:
        segs = [s.strip() for s in rows["课题·课时"].split("│")]
        if len(segs) >= 2:
            genre = segs[1].replace("·校内同步", "").replace("校内同步", "").strip("· ")
    if not genre:
        print("  [提示] 未抽到文体，留空", file=sys.stderr)

    lessons = split_lessons(md)
    l1 = lessons.get("第1课时", ("", ""))
    l2 = lessons.get("第2课时", ("", ""))
    l1_secs, l2_secs = sections(l1[1]), sections(l2[1])
    learn = section_body(l1[1], "学写法")
    compare = {}
    for mm in COMPARE_RE.finditer(learn):
        compare["bad" if mm.group("i") == "一" else "good"] = mm.group("s")[:160]

    gl = C.grade_label(course["grade_vol"])
    unit = course["unit"]
    return {
        "course": {
            "id": course["id"], "grade_vol": course["grade_vol"], "unit": unit,
            "topic": topic, "grade_label": gl, "genre": genre,
        },
        "title": topic,
        "subtitle": PH["subtitle"],
        "capsule": "%s｜%s同步习作" % (gl, unit) if unit else "%s｜同步习作" % gl,
        "cards": [
            {"kind": kind, "label": label,
             "head": PH["%s_head" % kind], "lines": [PH["%s_lines" % kind]]}
            for kind, label in CARD_LABELS
        ],
        "cta": {"fit": C.grade_fit(course["grade_vol"]), "sessions": "2 节课", "outcome": PH["outcome"]},
        "illustration": {"subject": PH["subject"], "ratio": "4:3"},
        "_sources": {
            "md": md_path.name,
            "outline": {k: rows.get(k, "") for k in ("学习目标", "核心技法", "教材要求")},
            "lesson1_sections": l1_secs,
            "lesson2_sections": l2_secs,
            "warn_sentences": warn_sentences(learn),
            "compare": compare,
            "companion": companion(C.repo_root(md_path), course["id"]),
        },
    }


def main():
    ap = argparse.ArgumentParser(description="写作课详案 → 单元海报骨架 json")
    ap.add_argument("md", help="写作课详案 .md 路径")
    ap.add_argument("--out", default=None, help="输出 json 路径（默认 写作课海报输出/<课次>/<课次>-习作海报.json）")
    ap.add_argument("--dry-run", action="store_true", help="只打印不落盘")
    a = ap.parse_args()

    data = build(a.md)
    if a.dry_run:
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0
    cid = data["course"]["id"]
    out = Path(a.out) if a.out else C.repo_root(a.md) / "写作课海报输出" / cid / ("%s-习作海报.json" % cid)
    if out.exists():
        old = C.load_json(out)
        for k in ("title", "subtitle", "cards", "cta", "illustration", "theme_hue"):
            if k in old:
                data[k] = old[k]
        data["cta"]["fit"], data["cta"]["sessions"] = C.grade_fit(data["course"]["grade_vol"]), "2 节课"
        print("  [提示] 已有 json，仅刷新 course/capsule/_sources，C 类字段保留", file=sys.stderr)
    out.parent.mkdir(parents=True, exist_ok=True)
    C.dump_json(out, data)
    print("骨架已写：%s" % out)
    if not data["_sources"]["companion"]:
        print("  [提示] 无同课次配套 json，C 类只能从详案派生", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
