# -*- coding: utf-8 -*-
"""reading_deck.py - 读书会课件配图链路的两头：中间稿 → 生图项目 JSON；验收 → 回填 `图=`。

出图本身不在这里：复用 run_lesson（页目／角色件）与 gen_cutouts（透明底抠图），
一本书一个项目 `课件项目/读书会-<书名>.json`，四课共用一张风格卡（手绘编号）和同一批定妆图。

    python scripts/reading_deck.py spec     <书名> [--handdraw 043]   # 读四份中间稿，生成/合并项目 JSON
    python scripts/run_lesson.py  课件项目/读书会-<书名>.json --stage char    # 定妆（角色件，人工写进 characters）
    python scripts/run_lesson.py  课件项目/读书会-<书名>.json --stage pages   # 场景图
    python scripts/gen_cutouts.py 课件项目/读书会-<书名>.json                 # 抠图（封面人物等）
    python scripts/reading_deck.py status   <书名>                     # 每页：有没有图、验没验
    python scripts/reading_deck.py approve  <书名> --by <验收人> [--only 导读课-P05 …]
    python scripts/reading_deck.py backfill <书名>                     # 只回填已验收的图

中间稿配图建议的写法（唯一源 laojohn-ppt-draft/references/image-suggestion.md）：
    配图建议：<篇目·场景>｜<章节>｜建议元素：…｜形=抠图|场景｜画面=<生图描述>[｜插=插-NN][｜击=N][｜图=<回填>]

⚠ 闸门在 backfill：只回填本脚本验收记录（`_读书会验收.json`）里登记过、且 md5 没变的图。
  图重生一次就得重验——run_lesson 自己的闸门 2026-08-28 起已改成不阻断，所以真闸门放在接入点。
⚠ `插=封面` 取书封（`读书会书籍封面/<书名>.jpg|png`，书封单一源，不复制进原书插图目录）。
⚠ 原书插图（`插=`）优先于 AI 图，不过本脚本的验收（扫描件取图凭据是 `_图单.md`）；
  用之前仍须对照 `_图单.md` 的「画文不一致」警告，由写中间稿的人把关。
⚠ 画风一本书定一次（唯一源 image-suggestion.md §三点五）：有原书插图→选最接近的手绘编号，必要时风格卡写
  `风格参考图`（扫描件只取画风，先试 2–3 页防照搬衣着道具）；没有→选 2–3 个候选编号交用户挑。
⚠ AI 图不入库（2026-10-06 用户定）：换机器重烘前须先重出图并重验，否则那几页按无图版式出。
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
HERE = pathlib.Path(__file__).resolve().parent
TOOL = HERE.parent                       # 课件配图工具/
REPO = TOOL.parent                       # 仓库根
DRAFT_DIR = REPO / "读书会课件中间稿输出"
SCAN_DIR = REPO / "读书会原书插图"
COVER_DIR = REPO / "读书会书籍封面"     # 书封单一源（CLAUDE.md §3，绝不挪进原书插图目录）
PROVIDER = "gpt-image"                   # 抠图只有 gpt-image 能直出透明底，整本书钉这一条通道

SUG_RE = re.compile(r"^配图建议\s*[:：]\s*(.+)$")
NONE = {"无", "无配图", "无（页面已满）", "—"}
TEXT_BAN = "画面中不出现任何文字、不出现英文字母和数字"


def project_path(book):
    return TOOL / "课件项目" / f"读书会-{book}.json"


def outdir(book):
    return TOOL / "课件产出" / f"读书会-{book}" / PROVIDER


def drafts(book):
    fs = sorted((DRAFT_DIR / book).glob("*-中间稿.md"))
    if not fs:
        raise SystemExit(f"⛔ 找不到中间稿：{DRAFT_DIR / book}\\*-中间稿.md")
    return fs


def parse_sug(val):
    segs = [s.strip() for s in re.split(r"\s*[｜|]\s*", val) if s.strip()]
    out = {"label": [], "形": "", "画面": "", "插": "", "击": "", "图": ""}
    for s in segs:
        m = re.match(r"^(形|画面|插|击|图)\s*[=＝]\s*(.*)$", s)
        if m:
            out[m.group(1)] = m.group(2).strip()
        else:
            out["label"].append(s)
    return out


def scan_pages(md_path):
    """逐页取配图建议：[(课时, 页码P05, 行号, 第几条, 解析结果)]。"""
    lines = md_path.read_text(encoding="utf-8").splitlines()
    course = ""
    for ln in lines[:12]:
        m = re.match(r"^课时\s*[:：]\s*(.+?)\s*$", ln)
        if m:
            course = m.group(1)
    page, k, res = None, 0, []
    for i, ln in enumerate(lines):
        m = re.match(r"^##\s*P(\d+)\s*\|", ln.strip())
        if m:
            page, k = f"P{int(m.group(1)):02d}", 0
            continue
        m = SUG_RE.match(ln.strip())
        if m and page and m.group(1).strip() not in NONE:
            k += 1
            res.append((course, page, i, k, parse_sug(m.group(1))))
    return res


def key_of(course, page, k):
    return f"{course}-{page}" + (f"-{k}" if k > 1 else "")


# ---------------------------------------------------------------- spec
def cmd_spec(book, handdraw):
    pp = project_path(book)
    d = json.loads(pp.read_text(encoding="utf-8")) if pp.exists() else {
        "project": {"名称": f"读书会-{book}", "通道": PROVIDER, "类型": "读书会"},
        "style_card": {"手绘编号": "", "人物年龄设定": "", "人物条目": "",
                       "文字禁令": TEXT_BAN,
                       "_前缀备注": "画风只靠手绘编号；人物外貌锚点写进 characters 定妆件，各页 prompt 挂载定妆图"},
        "characters": [], "slides": [], "抠图件": [],
    }
    if handdraw:
        d["style_card"]["手绘编号"] = str(handdraw).lstrip("#")
    if not d["style_card"].get("手绘编号"):
        print("提示：风格卡还没填手绘编号（--handdraw），出图前必须补上，否则四课画风不统一。")
    old_slides = {s["页码"]: s for s in d.get("slides", [])}
    old_cuts = {c["id"]: c for c in d.get("抠图件", [])}
    new_slides, new_cuts, changed = [], [], []
    for md in drafts(book):
        for course, page, _i, k, s in scan_pages(md):
            key = key_of(course, page, k)
            label = "｜".join(s["label"])
            if not s["画面"] and not s["插"]:
                print(f"  ! {key} 配图建议缺 画面=，跳过（{label}）")
                continue
            src = {"中间稿": md.name, "页": page, "建议": label}
            if s["插"]:
                new_slides.append(old_slides.get(key) or {
                    "页码": key, "通道": "人工素材位", "画幅": "4:3", "用途": "原书插图",
                    "_说明": (f"书封（{COVER_DIR.name}/{book}）" if s["插"] == "封面"
                              else f"原书插图 {s['插']}（{SCAN_DIR.name}/{book}/）"), "来源": src})
                continue
            if s["形"] == "抠图":
                item = old_cuts.get(key)
                if item and item.get("_画面") != s["画面"]:
                    changed.append(key)
                    item = None
                new_cuts.append(item or {"id": key, "画幅": "3:4", "prompt": s["画面"],
                                         "_画面": s["画面"], "挂载": [], "来源": src})
            else:
                item = old_slides.get(key)
                if item and item.get("_画面") != s["画面"]:
                    changed.append(key)
                    item = None
                new_slides.append(item or {"页码": key, "通道": "生成", "画幅": "4:3",
                                           "用途": "场景", "prompt": s["画面"], "_画面": s["画面"],
                                           "挂载": [], "去人物条目": False, "来源": src})
    gone = (set(old_slides) | set(old_cuts)) - {x["页码"] for x in new_slides} - {x["id"] for x in new_cuts}
    d["slides"], d["抠图件"] = new_slides, new_cuts
    pp.parent.mkdir(parents=True, exist_ok=True)
    pp.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {pp.relative_to(REPO)}：场景 {sum(1 for x in new_slides if x['通道']=='生成')}、"
          f"抠图 {len(new_cuts)}、原书插图 {sum(1 for x in new_slides if x['通道']=='人工素材位')}")
    if changed:
        print("  画面描述改过、已按新描述重置（须重出图、重验）：" + "、".join(changed))
    if gone:
        print("  中间稿里已没有、从项目里删掉：" + "、".join(sorted(gone)))
    if not d["characters"]:
        print("  提示：characters 为空。主要人物跨页出现时，先手写定妆件（外貌锚点），各页 挂载 它。")


# ---------------------------------------------------------------- 取图
def image_for(book, key, s):
    """该页应使用的图文件（可能不存在）与是否需验收。"""
    if s["插"]:
        base = (COVER_DIR / book) if s["插"] == "封面" else (SCAN_DIR / book / s["插"])
        for ext in (".png", ".jpg", ".jpeg"):
            f = base.with_name(base.name + ext)
            if f.exists():
                return f, False
        return base.with_name(base.name + ".png"), False
    od = outdir(book)
    if s["形"] == "抠图":
        return od / "抠图" / f"{key}.png", True
    return od / "页目" / f"{key}.jpg", True


def md5(f):
    return hashlib.md5(pathlib.Path(f).read_bytes()).hexdigest()


def gate_path(book):
    return outdir(book) / "_读书会验收.json"


def read_gate(book):
    g = gate_path(book)
    return json.loads(g.read_text(encoding="utf-8")) if g.exists() else {}


def all_items(book):
    for md in drafts(book):
        for course, page, i, k, s in scan_pages(md):
            yield md, i, key_of(course, page, k), s


def cmd_status(book):
    gate = read_gate(book)
    rows = []
    for md, _i, key, s in all_items(book):
        f, need = image_for(book, key, s)
        if not f.exists():
            st = "缺图"
        elif not need:
            st = "原书插图"
        elif gate.get(key, {}).get("md5") == md5(f):
            st = "已验收"
        elif key in gate:
            st = "图已变·须重验"
        else:
            st = "待验收"
        rows.append((key, st, "｜".join(s["label"])[:30]))
    for r in rows:
        print("  %-18s %-10s %s" % r)
    from collections import Counter
    print("合计：" + "，".join(f"{k} {v}" for k, v in Counter(r[1] for r in rows).items()))


def cmd_approve(book, by, only):
    gate = read_gate(book)
    n = 0
    for _md, _i, key, s in all_items(book):
        if only and key not in only:
            continue
        f, need = image_for(book, key, s)
        if not need or not f.exists():
            continue
        gate[key] = {"文件": str(f.relative_to(outdir(book))).replace("\\", "/"), "md5": md5(f),
                     "验收人": by, "时间": datetime.datetime.now().isoformat(timespec="seconds")}
        n += 1
    if not n:
        raise SystemExit("⛔ 没有可验收的图（还没出图，或 --only 写错了页码）。")
    gate_path(book).write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ 已记验收 {n} 张，验收人：{by}。下一步：reading_deck.py backfill {book}")


def cmd_backfill(book):
    gate = read_gate(book)
    edits = {}            # md -> {行号: 新行}
    done, skipped = 0, []
    for md, i, key, s in all_items(book):
        f, need = image_for(book, key, s)
        if not f.exists():
            skipped.append((key, "缺图"))
            continue
        if need and gate.get(key, {}).get("md5") != md5(f):
            skipped.append((key, "未验收或图已变"))
            continue
        rel = os.path.relpath(f, md.parent).replace("\\", "/")
        lines = edits.setdefault(md, {})
        src = md.read_text(encoding="utf-8").splitlines()[i]
        body = SUG_RE.match(src.strip()).group(1)
        segs = [x for x in re.split(r"\s*[｜|]\s*", body) if x.strip()
                and not re.match(r"^图\s*[=＝]", x.strip())]
        lines[i] = "配图建议：" + "｜".join(segs + [f"图={rel}"])
        done += 1
    for md, ch in edits.items():
        text = md.read_text(encoding="utf-8")
        ls = text.splitlines()
        for i, new in ch.items():
            ls[i] = new
        md.write_text("\n".join(ls) + ("\n" if text.endswith("\n") else ""), encoding="utf-8")
    print(f"✓ 回填 {done} 处 图=")
    if skipped:
        print(f"  未回填 {len(skipped)} 处（这些页按无图版式出）：")
        for k, why in skipped:
            print(f"    {k}：{why}")


def main():
    ap = argparse.ArgumentParser(description="读书会课件配图：spec / status / approve / backfill")
    ap.add_argument("cmd", choices=["spec", "status", "approve", "backfill"])
    ap.add_argument("book", help="书名（不带书名号，同中间稿目录名）")
    ap.add_argument("--handdraw", help="spec：手绘风格编号（如 043）")
    ap.add_argument("--by", help="approve：验收人")
    ap.add_argument("--only", nargs="*", help="approve：只验这几页（如 导读课-P05）")
    a = ap.parse_args()
    if a.cmd == "spec":
        cmd_spec(a.book, a.handdraw)
    elif a.cmd == "status":
        cmd_status(a.book)
    elif a.cmd == "approve":
        if not a.by:
            raise SystemExit("⛔ approve 须带 --by <验收人>")
        cmd_approve(a.book, a.by, a.only)
    else:
        cmd_backfill(a.book)


if __name__ == "__main__":
    main()
