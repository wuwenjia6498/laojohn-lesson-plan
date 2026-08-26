# -*- coding: utf-8 -*-
r"""
老约翰 · 写作课整套文件打包脚本

把一节写作课（同步习作）散落在各输出目录里的成品，复制归集进一个交付文件夹：

    写作课整套文件打包输出\<年级册>-第N单元-<题目>\      ← 单层平铺，无子文件夹（2026-08-26 改）
    ├── <年级册>-第N单元-<题目>-写作课详案.docx   ← 写作课详案输出\
    ├── <年级册>-第N单元-<题目>-课件PPT.pptx      ← 写作课件PPT输出\<课次>\*.pptx
    │                          （2026-08-03 起：外部平台生成 + 本仓注入动画的成品。
    │                           务必确保该目录里没有作废的旧烘焙件，否则会一起被收进交付包）
    └── <年级册>-第N单元-<题目>-学生用/教师用/家长用.pdf  ← 写作配套输出\<课次>\*.pdf

约定：
- 复制不移动——各原始输出目录是单一事实源，绝不破坏。
- 默认只收对外成品（pptx/pdf/docx）；--with-sources 时额外把可编辑源文件（md/json/html）一并打包。
- **写作课线不再有逐页讲稿**（2026-08-03 停产，目录已撤）；读书会线的讲稿由 laojohn-course-package 收，与本脚本无关。
- 缺料不报错、不阻断：跳过并在汇总里标「缺」，让用户知道哪些物料还没生成。

用法：
    PYTHONUTF8=1 python package_writing.py 三上-第六单元-这儿真美
    PYTHONUTF8=1 python package_writing.py 三上-第六单元-这儿真美 --with-sources
    PYTHONUTF8=1 python package_writing.py 三上-第六单元-这儿真美 --dest "C:/Users/xx/Desktop/这儿真美"
"""
import argparse
import shutil
import sys
from pathlib import Path

# 每个分类：dest 子目录（""=打包根目录）、若干 glob 模板、该类「成品」扩展名。
# 命中 glob 的文件：扩展名 in primary → 始终复制；否则视为源文件，仅 --with-sources 时复制。
CATEGORIES = [
    {
        "label": "写作课详案",
        "dest": "",
        "globs": ["写作课详案输出/{unit}-写作课详案.*"],
        "primary": {".docx"},
    },
    {
        "label": "投屏PPT",
        "dest": "",
        "globs": ["写作课件PPT输出/{unit}/*"],
        "primary": {".pptx"},
    },
    {
        "label": "配套物料",
        "dest": "",
        # 三侧配套：pdf 是成品；html/_data.json 是源（默认跳过）
        "globs": ["写作配套输出/{unit}/*"],
        "primary": {".pdf"},
    },
]


def gather(root: Path, unit: str, with_sources: bool):
    """返回 [(category, [(src_path, picked_bool, reason)])]，picked=是否复制。"""
    plan = []
    for cat in CATEGORIES:
        items = []
        seen = set()
        for tmpl in cat["globs"]:
            pat = tmpl.format(unit=unit)
            for src in sorted(root.glob(pat)):
                if not src.is_file() or src in seen:
                    continue
                if src.name.startswith("~$"):   # 跳过 Office 打开文件时的临时锁文件
                    continue
                seen.add(src)
                ext = src.suffix.lower()
                if ext in cat["primary"]:
                    items.append((src, True, "成品"))
                elif with_sources:
                    items.append((src, True, "源文件"))
                else:
                    items.append((src, False, "源文件(已跳过)"))
        plan.append((cat, items))
    return plan


def main():
    ap = argparse.ArgumentParser(description="把一节写作课的全部成品归集进一个交付文件夹")
    ap.add_argument("unit", help="课次标识 <年级册>-第N单元-<题目>，如：三上-第六单元-这儿真美")
    ap.add_argument("--root", default=None, help="项目根目录（默认当前工作目录）")
    ap.add_argument("--out", default=None,
                    help="打包输出顶层目录名（默认：写作课整套文件打包输出）")
    ap.add_argument("--dest", default=None, help="直接指定打包目标文件夹（覆盖 --out/<课次>）")
    ap.add_argument("--with-sources", action="store_true", help="连可编辑源文件(md/json/html)一起打包")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不实际复制")
    args = ap.parse_args()

    unit = args.unit.strip().strip("《》").strip()
    root = Path(args.root).resolve() if args.root else Path.cwd()
    out_top = args.out or "写作课整套文件打包输出"
    dest_root = Path(args.dest).resolve() if args.dest else (root / out_top / unit)

    if not root.exists():
        print(f"[错误] 项目根目录不存在：{root}")
        sys.exit(1)

    print(f"项目根目录 : {root}")
    print(f"打包目标   : {dest_root}")
    print(f"包含源文件 : {'是' if args.with_sources else '否（仅成品）'}")
    print(f"模式       : {'演练(dry-run)' if args.dry_run else '复制'}")
    print("=" * 60)

    plan = gather(root, unit, args.with_sources)

    total_copied = 0
    summary = []
    for cat, items in plan:
        picked = [it for it in items if it[1]]
        skipped = [it for it in items if not it[1]]
        dest_dir = dest_root / cat["dest"] if cat["dest"] else dest_root
        dest_label = (cat["dest"] + "\\") if cat["dest"] else "（根目录）"

        if not picked and not skipped:
            print(f"[缺] {cat['label']:<10} 未找到任何文件 —— 该物料可能还没生成")
            summary.append((cat["label"], 0, "缺"))
            continue

        if picked and not args.dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{cat['label']}] → {dest_label}")
        for src, _, reason in picked:
            target = dest_dir / src.name
            if args.dry_run:
                print(f"    + {src.relative_to(root)}  ({reason})")
            else:
                shutil.copy2(src, target)
                print(f"    ✓ {src.name}  ({reason})")
            total_copied += 1
        for src, _, reason in skipped:
            print(f"    - {src.name}  ({reason})")
        summary.append((cat["label"], len(picked), "OK" if picked else "仅源文件被跳过"))

    print("=" * 60)
    print("汇总：")
    for label, n, status in summary:
        flag = "✓" if status == "OK" else ("✗" if status == "缺" else "·")
        print(f"  {flag} {label:<12} 复制 {n} 个文件  [{status}]")
    missing = [s[0] for s in summary if s[2] == "缺"]
    print("-" * 60)
    print(f"共复制 {total_copied} 个文件 → {dest_root}")
    if missing:
        print(f"⚠ 缺失物料（未生成或命名不符）：{ '、'.join(missing) }")
    if args.dry_run:
        print("（dry-run：未实际写入任何文件）")


if __name__ == "__main__":
    main()
