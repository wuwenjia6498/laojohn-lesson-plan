# -*- coding: utf-8 -*-
r"""
老约翰 · 课程交付打包脚本

把一本书散落在各输出目录里的成品，复制归集进一个交付文件夹：

    读书会课程打包输出\<书名>\
    ├── 课件PPT\            ← 读书会课件PPT输出\<书名>\*.pptx
    ├── 课件下游物料\        ← 读书会配套输出\<书名>\（书目卡/海报/阅读指南/抢先看导图/教学导图/反馈话术）
    ├── 阅读单\             ← 读书会阅读单输出\<书名>\<书名>-阅读单-全套.pdf + <书名>-阅读单.pptx
    ├── 逐页讲稿\           ← 读书会课件讲稿输出\<书名>\*.docx（md 是源，默认不收）
    ├── <书名>-课案详案.docx  ← 读书会详案输出\（放根目录）
    └── <书名>_阅读测评.docx  ← 读书会配套输出\<书名>\（放根目录）

约定：
- 复制不移动——各原始输出目录是单一事实源，绝不破坏。
- 默认只收对外成品（pptx/pdf/jpg/png/docx；逐页讲稿只收 docx）；
  --with-sources 时额外把可编辑源文件（md/json/html 中间稿）一并打包。
- 缺料不报错、不阻断：跳过并在汇总里标「缺」，让用户知道哪些物料还没生成。

用法：
    PYTHONUTF8=1 python package_course.py 洞
    PYTHONUTF8=1 python package_course.py 洞 --with-sources
    PYTHONUTF8=1 python package_course.py 洞 --root E:\laojohn-lesson-plan --dest C:\Users\xx\Desktop\洞
"""
import argparse
import shutil
import sys
from pathlib import Path

# 每个分类：dest 子目录（""=打包根目录）、若干 glob 模板、该类「成品」扩展名。
# 命中 glob 的文件：扩展名 in primary → 始终复制；否则视为源文件，仅 --with-sources 时复制。
CATEGORIES = [
    {
        "label": "课案详案",
        "dest": "",
        "globs": ["读书会详案输出/{book}-课案详案.*"],
        "primary": {".docx"},
    },
    {
        "label": "阅读测评",
        "dest": "",
        "globs": ["读书会配套输出/{book}/{book}_阅读测评.*"],
        "primary": {".docx"},
    },
    {
        "label": "投屏PPT",
        "dest": "课件PPT",
        "globs": ["读书会课件PPT输出/{book}/*"],
        "primary": {".pptx"},
    },
    {
        "label": "逐页讲稿",
        "dest": "逐页讲稿",
        "globs": ["读书会课件讲稿输出/{book}/*"],
        "primary": {".docx"},  # 只收 docx 打印件；md 视为源（默认跳过，--with-sources 才收）
    },
    {
        "label": "学生阅读单",
        "dest": "阅读单",
        # 只收全套合订 PDF + 可编辑 PPTX；散张单页（单张 pdf/png/html）不进交付包
        "globs": ["读书会阅读单输出/{book}/{book}-阅读单-全套.pdf", "读书会阅读单输出/{book}/{book}-阅读单.pptx"],
        "primary": {".pdf", ".pptx"},
    },
    {
        "label": "下游配套物料",
        "dest": "课件下游物料",
        "globs": [
            "读书会配套输出/{book}/{book}_书目卡.*",
            "读书会配套输出/{book}/{book}_海报.*",
            "读书会配套输出/{book}/{book}_阅读指南.*",
            "读书会配套输出/{book}/{book}_抢先看.*",
            "读书会配套输出/{book}/{book}_教学导图.*",
            "读书会配套输出/{book}/《{book}》_课程反馈话术.*",
            "读书会配套输出/{book}/{book}_课程反馈话术*.*",  # *_content.json 变体
        ],
        "primary": {".jpg", ".jpeg", ".png", ".pdf", ".docx"},
    },
]


def gather(root: Path, book: str, with_sources: bool):
    """返回 [(category_label, [(src_path, picked_bool, reason)])]，picked=是否复制。"""
    plan = []
    for cat in CATEGORIES:
        items = []
        seen = set()
        for tmpl in cat["globs"]:
            pat = tmpl.format(book=book)
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
    ap = argparse.ArgumentParser(description="把一本书的全部成品归集进一个交付文件夹")
    ap.add_argument("book", help="书名（不带书名号），如：洞")
    ap.add_argument("--root", default=None, help="项目根目录（默认当前工作目录）")
    ap.add_argument("--out", default=None,
                    help="打包输出顶层目录名（默认：读书会课程打包输出）")
    ap.add_argument("--dest", default=None, help="直接指定打包目标文件夹（覆盖 --out/<书名>）")
    ap.add_argument("--with-sources", action="store_true", help="连可编辑源文件(md/json/html)一起打包")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不实际复制")
    args = ap.parse_args()

    book = args.book.strip().strip("《》").strip()
    root = Path(args.root).resolve() if args.root else Path.cwd()
    out_top = args.out or "读书会课程打包输出"
    dest_root = Path(args.dest).resolve() if args.dest else (root / out_top / book)

    if not root.exists():
        print(f"[错误] 项目根目录不存在：{root}")
        sys.exit(1)

    print(f"项目根目录 : {root}")
    print(f"打包目标   : {dest_root}")
    print(f"包含源文件 : {'是' if args.with_sources else '否（仅成品）'}")
    print(f"模式       : {'演练(dry-run)' if args.dry_run else '复制'}")
    print("=" * 60)

    plan = gather(root, book, args.with_sources)

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
