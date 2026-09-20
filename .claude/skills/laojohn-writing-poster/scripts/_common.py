# -*- coding: utf-8 -*-
r"""laojohn-writing-poster · 本 skill 三个脚本共用的小件（skill 私有，不跨 skill 复用）。

    parse_course_id(name)   文件名/课次标识段 → {grade_vol, unit, topic, id}
    grade_label(gv)         "三上" → "三年级上册"；grade_fit(gv) → "适合小学三年级"
    repo_root(start)        从任一路径向上找含 品牌资产 的目录 ＝ 项目根（禁硬编码盘符）
    check_text(data)        渲染前机检：占位 / ASCII 直引号 / emoji / 「待补充」 → 问题清单

课次标识段口径（CLAUDE.md §7）：`<年级册>-第N单元-<题目>`。题目可含全角 ＿＿ 与弯引号 “”，
因此**只用 fullmatch 正则、绝不 split('-')**（题目内也可能出现连字符）。
"""
import json
import re
from pathlib import Path

# 文件名：三上-第二单元-写日记-写作课详案.md ／ 课次标识段：三上-第二单元-写日记
COURSE_RE = re.compile(
    r"^(?P<gv>[一二三四五六][上下])-(?:(?P<unit>第[一二三四五六七八]单元)-)?(?P<topic>.+?)"
    r"(?:-写作课详案)?(?:\.md)?$"
)

GRADE = {"一": "一年级", "二": "二年级", "三": "三年级", "四": "四年级", "五": "五年级", "六": "六年级"}


def parse_course_id(name):
    """接受文件名、stem 或课次标识段；返回 dict，解析不出抛 ValueError。"""
    m = COURSE_RE.fullmatch(Path(name).name if ("/" in name or "\\" in name) else name)
    if not m:
        raise ValueError("文件名不合课次口径 <年级册>-第N单元-<题目>：%s" % name)
    gv, unit, topic = m.group("gv"), m.group("unit") or "", m.group("topic")
    cid = "-".join(x for x in (gv, unit, topic) if x)
    return {"grade_vol": gv, "unit": unit, "topic": topic, "id": cid}


def grade_label(gv):
    return GRADE[gv[0]] + ("上册" if gv[1] == "上" else "下册")


def grade_fit(gv):
    return "适合小学" + GRADE[gv[0]]


def repo_root(start):
    p = Path(start).resolve()
    for cand in (p, *p.parents):
        if (cand / "品牌资产").is_dir():
            return cand
    raise SystemExit("找不到项目根（向上未见 品牌资产 目录）：%s" % start)


# ---- 渲染前机检 ------------------------------------------------------------
PH_RE = re.compile(r"【[^】]*(?:待|请|提炼|补充)[^】]*】")
ASCII_QUOTE_RE = re.compile(r"[\"']")
EMOJI_RE = re.compile("[\U0001F000-\U0001FAFF☀-➿⬀-⯿️]")
SKIP_KEYS = {"prompt_used", "judge", "model", "provider", "file", "generated_at"}


def _walk(obj, path, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith("_") or k in SKIP_KEYS:
                continue
            _walk(v, "%s.%s" % (path, k) if path else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk(v, "%s[%d]" % (path, i), out)
    elif isinstance(obj, str):
        out.append((path, obj))


def check_text(data):
    """返回 [(路径, 问题描述)]；空列表＝通过。"""
    strings, problems = [], []
    _walk(data, "", strings)
    for path, s in strings:
        if PH_RE.search(s):
            problems.append((path, "残留 AI 提炼占位"))
        if ASCII_QUOTE_RE.search(s):
            problems.append((path, "含 ASCII 直引号（须用全角 “” ‘’）"))
        if EMOJI_RE.search(s):
            problems.append((path, "含 emoji/生僻符号"))
        if "待补充" in s or "请回填" in s:
            problems.append((path, "含「待补充/请回填」字样（不得进对外物料）"))
    return problems


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
