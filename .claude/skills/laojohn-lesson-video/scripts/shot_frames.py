# -*- coding: utf-8 -*-
r"""备课视频链第 4 步：PPT → 逐页 PNG 帧。

    PYTHONUTF8=1 python shot_frames.py <课次> [--fallback-repo-pptx] [--size 1920x1080]
                                        [--force] [--check]

**薄壳**：真源是 `laojohn-ppt\tools\shot_assets.py` 的 `pptx_to_png_batch(src, jobs)`
（PowerPoint COM 单会话导多页）。**绝不在这里另存一份 COM 导出代码**——那个函数里
沉淀的四个 COM 坑（Quit 后重开失败、位置参数 vs 命名参数、WPS 抢注、gen_py 缓存损坏）
重写必然重踩一遍。

画面源＝`_备课视频工作区\<课次>\source.pptx`（外部终稿，整目录 gitignore）。
取不到就报错，**不静默回退**仓内 anim 版——两者页码可能不一致，静默回退会产出
一批「旁白讲的和画面不是同一页」的废片，而这种失配没有任何报错。

`--check` 出 `_出图体检.md`：用 PIL 算每帧非背景像素占比，异常页列出来请人看一眼
（防终稿某页是空白或占位）。
"""
import argparse
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root  # noqa: E402

DEFAULT_SIZE = (1920, 1080)


def load_shot_assets(root):
    p = os.path.join(root, ".claude", "skills", "laojohn-ppt", "tools", "shot_assets.py")
    if not os.path.exists(p):
        raise SystemExit("找不到出图真源：%s\n"
                         "  （改过 laojohn-ppt 的目录名？"
                         "薄壳按相对路径定位，改名会静默断链）" % p)
    spec = importlib.util.spec_from_file_location("shot_assets", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ink_ratio(path):
    """非背景像素占比。缩到 200px 宽再算——只是用来挑空白页，不需要精度。"""
    from PIL import Image
    im = Image.open(path).convert("L")
    im.thumbnail((200, 200))
    px = list(im.getdata())
    if not px:
        return 0.0
    bg = max(set(px), key=px.count)
    return sum(1 for v in px if abs(v - bg) > 18) / float(len(px))


def main():
    ap = argparse.ArgumentParser(description="PPT 逐页出帧")
    ap.add_argument("unit")
    ap.add_argument("--fallback-repo-pptx", action="store_true")
    ap.add_argument("--size", default="%dx%d" % DEFAULT_SIZE)
    ap.add_argument("--force", action="store_true", help="已存在也重导")
    ap.add_argument("--check", action="store_true", help="另出出图体检")
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    sl_path = os.path.join(src.out_dir, a.unit + "-分镜单.json")
    with open(sl_path, encoding="utf-8") as f:
        sl = json.load(f)
    w, h = (int(x) for x in a.size.lower().split("x"))

    pptx, kind = src.visual_pptx(fallback=a.fallback_repo_pptx)
    ac = sl["meta"].get("align_check") or {}
    if ac.get("source") != kind:
        print("  ⚠ 分镜单是按「%s」算的对齐，这次出图用的是"
              "「%s」——页码可能对不上，"
              "先重跑 build_shotlist.py" % (ac.get("source"), kind))
    if ac.get("result") == "review" and not ac.get("confirmed_by"):
        print("  ⚠ align_check 还是 review 且无人确认：%s" % ac.get("note"))

    fdir = os.path.join(src.out_dir, "frames")
    os.makedirs(fdir, exist_ok=True)
    pages = sorted({p for s in sl["shots"] for p in s["pages"]})
    head = (ac.get("head_unused") or [])
    tail = (ac.get("tail_unused") or [])
    pages = sorted(set(pages) | set(head) | set(tail))   # 片头封面、片尾 THE END 也要出
    jobs, skipped = [], 0
    for p in pages:
        out = os.path.join(fdir, "p%02d.png" % p)
        if os.path.exists(out) and not a.force:
            skipped += 1
            continue
        jobs.append((p, out))

    print("%s · 画面源 %s(%s) · 共 %d 页，待导 %d，已有 %d"
          % (a.unit, os.path.basename(pptx), kind, len(pages), len(jobs), skipped))
    if jobs:
        sa = load_shot_assets(root)
        print("  PowerPoint COM 导图中（卡住多半是那份 pptx "
              "正被 PowerPoint/WPS 打开，先去关窗口）...", flush=True)
        res = sa.pptx_to_png_batch(pptx, jobs, size=(w, h))
        bad = [r for r in (res or []) if r and len(r) > 1 and r[1]]
        for r in bad:
            print("  ✗ %s" % (r,))
        if bad:
            raise SystemExit(1)

    if a.check:
        rows = []
        for p in pages:
            f = os.path.join(fdir, "p%02d.png" % p)
            if os.path.exists(f):
                rows.append((p, ink_ratio(f), os.path.getsize(f) // 1024))
        med = sorted(r[1] for r in rows)[len(rows) // 2] if rows else 0
        cpath = os.path.join(src.out_dir, "_出图体检.md")
        with open(cpath, "w", encoding="utf-8", newline="\n") as f:
            f.write("# %s · 出图体检\n\n" % a.unit)
            f.write("画面源：`%s`（%s），%d 帧，"
                    "尺寸 %dx%d。中位墨水量 %.3f。\n\n"
                    % (os.path.relpath(pptx, root), kind, len(rows), w, h, med))
            f.write("| 页 | 墨水量 | KB | 备注 |\n|---|---|---|---|\n")
            for p, ink, kb in rows:
                note = ""
                if ink < med * 0.35:
                    note = "← 画面很空，看一眼是不是空页/占位"
                f.write("| %d | %.3f | %d | %s |\n" % (p, ink, kb, note))
        thin = [p for p, ink, _ in rows if ink < med * 0.35]
        print("✓ 体检 %s%s"
              % (os.path.relpath(cpath, root),
                 ("（%d 页偏空：P%s）"
                  % (len(thin), ",".join(str(x) for x in thin))) if thin else ""))
    print("✓ %s" % os.path.relpath(fdir, root))


if __name__ == "__main__":
    main()
