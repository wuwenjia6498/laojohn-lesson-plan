# -*- coding: utf-8 -*-
"""
avoid_card.py · 写作课详案「本篇避让卡」生成器（2026-09-11 立）

为什么有这个脚本
----------------
生成新详案前要查反同质化台账与零件池（variation-ledger.md 33k 字符 + variation-pools.md 27k 字符），
整读进上下文既贵又分散注意力。本脚本把「这一篇需要避开什么」压成一张 ≤30 行的卡片：
  1. 本任务在 situation-anchors.md 的那一行（官方情境／官方反馈活动／连排课改造／同文体邻篇）；
  2. 强避让范围内各篇已用的零件（同年级全部 + 相邻年级同文体），字段取
     场景原型／实体载体／热身动作／主反馈游戏／第二层反馈／开场钩子／示范文题材；
  3. 同文体最近 2 篇的「话轮骨架」（池 9：三串至少换一串）；
  4. 弱避让（年级差 ≥2 的同文体）只列场景原型类型；
  5. 「禁止逐字复用」清单里的串（全局生效，只列引号内的串）。
避让强度口径 = variation-pools.md「距离化避让规则」；字段定义 = variation-ledger.md §一。
本脚本只读不写：真相来源仍是各详案文件尾的指纹块，台账文件本身不被读取。

用法
----
  PYTHONUTF8=1 python .claude/skills/laojohn-writing-lesson/assets/avoid_card.py --grade 六上 --genre 想象 --task 变形记
  可选：--batch <篇名子串,…>  把同批次的篇也算进强避让；--dir 指定详案目录；--out 写到文件。
  --genre 按指纹块「文体」字段做子串匹配（「想象」可匹配「想象·变形」「想象·童话」）。

红线
----
  * 卡片只给零件层与话轮层，措辞层（池 6/7/8）有意不进（那层归冷审与润色脚本）。
  * 指纹块缺字段的篇照常列出、值写「—」，不要静默跳过（跳过 = 漏避让）。
  * 本任务自己的指纹块（题目相同）不列入避让对象。
"""
import argparse
import io
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL = HERE.parent
REF = SKILL / "references"
ROOT = SKILL.parents[2]

FP_RE = re.compile(r"<!--\s*VARIATION-FINGERPRINT(.*?)-->", re.S)
FIELDS_PARTS = ["场景原型", "实体载体", "热身动作", "主反馈游戏", "第二层反馈", "开场钩子", "示范文题材"]
GRADE_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6}


def read(p):
    return io.open(p, encoding="utf-8").read()


def parse_fp(text):
    m = FP_RE.search(text)
    if not m:
        return None
    d = {}
    for ln in m.group(1).splitlines():
        ln = ln.strip()
        if not ln:
            continue
        mm = re.match(r"([^:：]+)[:：]\s*(.*)$", ln)
        if mm:
            d[mm.group(1).strip()] = mm.group(2).strip()
    return d


def grade_of(book):
    return GRADE_NUM.get((book or "")[:1], None)


def short(v, n=38):
    """取零件的类型名：截到第一个括号前，再限长。"""
    if not v:
        return "—"
    v = re.split(r"[（(]", v, maxsplit=1)[0].strip() or v.strip()
    return v if len(v) <= n else v[: n - 1] + "…"


def load_pieces(d):
    out = []
    for p in sorted(Path(d).glob("*-写作课详案*.md")):
        if p.name.startswith("_"):
            continue
        fp = parse_fp(read(p))
        if fp is None:
            out.append({"file": p.name, "_nofp": True, "mtime": p.stat().st_mtime})
            continue
        fp["file"] = p.name
        fp["mtime"] = p.stat().st_mtime
        out.append(fp)
    return out


def anchor_row(task):
    text = read(REF / "situation-anchors.md")
    for ln in text.splitlines():
        if ln.startswith("|") and task in ln.split("|")[1]:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) >= 5 and cells[0] != "任务":
                return cells
    return None


def forbidden_strings():
    text = read(REF / "variation-pools.md")
    m = re.search(r"##\s*已知「禁止逐字复用」.*?(?=\n## |\Z)", text, re.S)
    if not m:
        return []
    out = []
    for ln in m.group(0).splitlines():
        if ln.lstrip().startswith("- "):
            q = re.findall(r"「([^」]{4,})」", ln)
            if q:
                out.append(q[0])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--grade", required=True, help="册级，如 六上")
    ap.add_argument("--genre", required=True, help="文体，如 想象／写人／记事／写景")
    ap.add_argument("--task", required=True, help="题目，如 变形记")
    ap.add_argument("--batch", default="", help="同批次篇名子串，逗号分隔")
    ap.add_argument("--dir", default=str(ROOT / "写作课详案输出"))
    ap.add_argument("--out", default="")
    a = ap.parse_args()

    g = grade_of(a.grade)
    if g is None:
        sys.exit("--grade 须以 一～六 开头，如 六上")
    batch = [s for s in a.batch.split(",") if s.strip()]
    pieces = load_pieces(a.dir)
    lines = []
    L = lines.append

    L(f"# 本篇避让卡 · {a.grade}《{a.task}》（{a.genre}）")
    row = anchor_row(a.task)
    if row:
        L(f"官方情境：{row[1]}")
        L(f"官方反馈活动：{row[2]}")
        L(f"连排课改造：{row[3]}")
        L(f"同文体邻篇：{row[4]}")
    else:
        L("锚点表未命中本任务：按 variation-pools 池 0 文体映射兜底，并在详案头部注明推定来源。")

    strong, weak, nofp = [], [], []
    for fp in pieces:
        if fp.get("_nofp"):
            nofp.append(fp["file"])
            continue
        if a.task and a.task in (fp.get("题目") or ""):
            continue
        pg = grade_of(fp.get("册级"))
        same_genre = a.genre in (fp.get("文体") or "")
        in_batch = any(b in fp["file"] for b in batch)
        if pg == g or (pg is not None and abs(pg - g) == 1 and same_genre) or (in_batch and same_genre):
            strong.append(fp)
        elif same_genre and pg is not None and abs(pg - g) >= 2:
            weak.append(fp)

    L("")
    L(f"## 强避让（零件必须有别）· {len(strong)} 篇")
    if not strong:
        L("（无）")
    for fp in strong:
        parts = "／".join(f"{k}={short(fp.get(k))}" for k in FIELDS_PARTS)
        L(f"- {fp.get('册级','—')}《{fp.get('题目','—')}》[{short(fp.get('文体'),12)}]：{parts}")

    L("")
    same = sorted([fp for fp in pieces if not fp.get("_nofp") and a.genre in (fp.get("文体") or "") and a.task not in (fp.get("题目") or "")],
                  key=lambda x: x["mtime"], reverse=True)[:2]
    L("## 同文体最近 2 篇的话轮骨架（③④⑦ 三串至少换一串的序列形态）")
    if not same:
        L("（无同文体成稿）")
    for fp in same:
        L(f"- {fp.get('册级','—')}《{fp.get('题目','—')}》：{fp.get('话轮骨架') or '—（该篇未填，请直接读其 ③④⑦ 正文）'}")

    if weak:
        L("")
        L("## 弱避让（类型可复用、由头必须换）")
        L("；".join(f"{fp.get('册级','—')}《{fp.get('题目','—')}》场景={short(fp.get('场景原型'),16)}" for fp in weak))

    fb = forbidden_strings()
    L("")
    L(f"## 禁止逐字复用的串（全局，{len(fb)} 条，近似同款也算）")
    for i in range(0, len(fb), 4):
        L("；".join(fb[i:i + 4]))

    if nofp:
        L("")
        L("⚠ 无指纹块、未纳入比对的篇：" + "、".join(nofp))

    text = "\n".join(lines) + "\n"
    if a.out:
        io.open(a.out, "w", encoding="utf-8", newline="").write(text)
    sys.stdout.write(text)


if __name__ == "__main__":
    main()
