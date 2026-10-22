# -*- coding: utf-8 -*-
"""
quote_length —— 读书会详案「原文朗读篇幅」机检（只读、不改文件）。

阈值口径的唯一源是 references/checklist.md「原文摘录篇幅」条，本脚本只照搬数字：
单次朗读与每课时总量各有上限；一次朗读＝连续 `>` 引块（中间只隔空行或〖PPT…〗页标的算同一次），去空白、去行末页码计字。
另列师话里 ≥20 字的引号内容供人工判断（首次给出的原文计入总量）。
超限只是信号：全书高潮、结尾原句这类整段读的例外，由人判断师话里有没有交代。

用法：
  PYTHONUTF8=1 python quote_length.py <详案.md> [...] [--level L5]
学段缺省从 H1 的「X年级」推（一二→L1–L2，三四→L3–L4，五六→L5–L6）。
"""
import argparse
import re
import sys

LIMITS = {"L1-L2": 100, "L3-L4": 150, "L5-L6": 180}
LESSON_LIMITS = {"L1-L2": 250, "L3-L4": 400, "L5-L6": 500}  # 每课时引文总量（主闸）
SHARE_SIGNAL = 6.0  # 全篇引文占比参考线（%）
GRADE_BAND = {"一": "L1-L2", "二": "L1-L2", "三": "L3-L4", "四": "L3-L4", "五": "L5-L6", "六": "L5-L6"}
PAGE_TAIL = re.compile(r"P\d+(?:-P?\d+)?\s*$")
SHIHUA_QUOTE = re.compile(r"“([^”]{20,})”")  # 师话里 ≥20 字的引号内容：可能是把原文搬进师话躲计数


def band_of(text, level):
    if level:
        n = int(level.lstrip("Ll")[0])
        return ("L1-L2", "L1-L2", "L3-L4", "L3-L4", "L5-L6", "L5-L6")[n - 1]
    m = re.search(r"^#\s*([一二三四五六])年级", text, re.M)
    return GRADE_BAND[m.group(1)] if m else None


def readings(lines):
    """返回 [(字数, 起始行号, 课时, 环节)]。"""
    out, cur, start, lesson, step = [], 0, 0, "", ""
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if s.startswith("## "):
            lesson = s[3:].strip()
        elif s.startswith("### "):
            step = s[4:].strip()
        if s.startswith(">"):
            body = PAGE_TAIL.sub("", s.lstrip("> "))
            if not cur:
                start = i
            cur += len(re.sub(r"\s", "", body))
        elif s == "" or s.startswith("〖PPT"):
            continue
        else:
            if cur:
                out.append((cur, start, lesson, step))
            cur = 0
    if cur:
        out.append((cur, start, lesson, step))
    return out


def check(path, level):
    text = open(path, encoding="utf-8").read()
    band = band_of(text, level)
    if not band:
        print(f"{path}: H1 里推不出年级，请用 --level 指定")
        return
    limit = LIMITS[band]
    rs = readings(text.split("\n"))
    total = sum(r[0] for r in rs)
    share = 100 * total / max(1, len(re.sub(r"\s", "", text)))
    over = [r for r in rs if r[0] > limit]
    print(f"== {path}")
    print(f"学段 {band}，单次朗读上限 {limit} 字；朗读 {len(rs)} 次，引文共 {total} 字，占全文 {share:.1f}%"
          + ("（超过参考线 %.0f%%）" % SHARE_SIGNAL if share > SHARE_SIGNAL else ""))
    per = {}
    for n, _, lesson, _ in rs:
        key = lesson.split("·")[0].strip() or "（课时前）"
        per[key] = per.get(key, 0) + n
    cap = LESSON_LIMITS[band]
    print(f"各课时引文（上限 {cap} 字）：" + "；".join(f"{k} {v} 字" + ("⚠超" if v > cap else "") for k, v in per.items()))
    if not over:
        print("超限段：无")
    else:
        print(f"超限段 {len(over)} 处：")
        for n, start, lesson, step in over:
            print(f"  第 {start} 行  {n} 字  {lesson} ｜ {step}")
    longq = [(i, len(re.sub(r"\s", "", q))) for i, ln in enumerate(text.split("\n"), 1)
             if ln.startswith("师：") for q in SHIHUA_QUOTE.findall(ln)]
    if longq:
        print(f"师话长引语 {len(longq)} 处（≥20 字，人工判断：首次给出的原文计入课时总量，复引已读句子不计）：")
        print("  " + "；".join(f"第 {i} 行 {n} 字" for i, n in longq))


def main():
    ap = argparse.ArgumentParser(description="读书会详案原文朗读篇幅机检")
    ap.add_argument("files", nargs="+")
    ap.add_argument("--level", help="覆盖学段，如 L5")
    a = ap.parse_args()
    for f in a.files:
        check(f, a.level)


if __name__ == "__main__":
    sys.exit(main())
