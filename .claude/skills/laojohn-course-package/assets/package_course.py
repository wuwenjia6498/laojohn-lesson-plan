# -*- coding: utf-8 -*-
r"""
老约翰 · 课程交付打包脚本

把一本书散落在各输出目录里的成品，复制归集并**按用户定稿口径改名**（2026-10-26 用户定，
样例 L3《稻草人》）：

    读书会整套文件打包输出\3上《稻草人》\                ← <年级><上/下>《书名》
    ├── 教师用\
    │   ├── 《稻草人》教学逐页讲稿\
    │   │   └── 《稻草人》导读课-逐页讲稿.docx …        ← 读书会课件讲稿输出\<书名>\*.docx
    │   ├── 《稻草人》导读课.pptx …                      ← 读书会课件PPT输出\<书名>\*.pptx
    │   ├── 《稻草人》教学思维导图.pdf                   ← 读书会配套输出\<书名>_教学导图.pdf
    │   └── 《稻草人》课案详案.docx                      ← 读书会详案输出\（有配图版 -配图.docx 一并收）
    ├── 宣传推广、日常服务类\
    │   └── 《稻草人》海报.jpg / 课程反馈话术.docx / 书目卡.jpg
    ├── 学生用\
    │   ├── 《稻草人》（学生用资料）.pdf / .pptx          ← 阅读单全套合订 PDF + 可编辑 PPTX（「阅读单」一律改称「学生用资料」）
    │   └── 《稻草人》抢先看.pdf / 阅读指南.pdf
    └── 《稻草人》阅读测评.docx                          ← 放根目录

年级取书籍档案机读块「等级：Lx」→ x 年级；上/下册无从得知时一律写「上」（用户后期手改），
已知时用 --term 下 指定。

约定：
- 复制不移动——各原始输出目录是单一事实源，绝不破坏。
- 默认只收对外成品；--with-sources 时额外把可编辑源文件（md/json/html）一并打包（同样改名）。
- 缺料不报错、不阻断：跳过并在汇总里标「缺」。

用法：
    PYTHONUTF8=1 python package_course.py 稻草人
    PYTHONUTF8=1 python package_course.py 稻草人 --term 下
    PYTHONUTF8=1 python package_course.py 洞 --dest C:\Users\xx\Desktop\洞
"""
import argparse
import importlib.util
import re
import shutil
import sys
from pathlib import Path

TEACHER = "教师用"
PROMO = "宣传推广、日常服务类"
STUDENT = "学生用"

# 每个分类：dest 子目录（""=打包根目录；{t}=《书名》）、若干 glob、成品扩展名、改名规则。
# 改名通用规则：去掉源文件名开头的「书名-」「书名_」「《书名》_」，换成「《书名》」；
# rename 字典再把去前缀后的 stem 映射成新 stem（如 教学导图 → 教学思维导图）。
CATEGORIES = [
    {
        "label": "课案详案",
        "dest": TEACHER,
        "globs": ["读书会详案输出/{book}-课案详案.*", "读书会详案输出/{book}-课案详案-配图.docx"],
        "primary": {".docx"},
    },
    {
        "label": "投屏PPT",
        "dest": TEACHER,
        "globs": ["读书会课件PPT输出/{book}/*"],
        "primary": {".pptx"},
    },
    {
        "label": "教学思维导图",
        "dest": TEACHER,
        "globs": ["读书会配套输出/{book}/{book}_教学导图.*"],
        "primary": {".pdf"},
        "rename": {"教学导图": "教学思维导图"},
    },
    {
        "label": "逐页讲稿",
        "dest": TEACHER + "/{t}教学逐页讲稿",
        "globs": ["读书会课件讲稿输出/{book}/*"],
        "primary": {".docx"},  # 只收 docx 打印件；md 视为源（默认跳过，--with-sources 才收）
    },
    {
        "label": "宣传推广物料",
        "dest": PROMO,
        "globs": [
            "读书会配套输出/{book}/{book}_海报.*",
            "读书会配套输出/{book}/《{book}》_课程反馈话术.*",
            "读书会配套输出/{book}/{book}_课程反馈话术*.*",  # *_content.json 变体
            "读书会配套输出/{book}/{book}_书目卡.*",
        ],
        "primary": {".jpg", ".jpeg", ".png", ".docx"},
    },
    {
        "label": "学生用资料",
        "dest": STUDENT,
        # 只收全套合订 PDF + 可编辑 PPTX；散张单页不进交付包
        "globs": ["读书会阅读单输出/{book}/{book}-阅读单-全套.pdf", "读书会阅读单输出/{book}/{book}-阅读单.pptx"],
        "primary": {".pdf", ".pptx"},
        "rename": {"阅读单-全套": "（学生用资料）", "阅读单": "（学生用资料）"},
    },
    {
        "label": "抢先看/阅读指南",
        "dest": STUDENT,
        "globs": ["读书会配套输出/{book}/{book}_抢先看.*", "读书会配套输出/{book}/{book}_阅读指南.*"],
        "primary": {".pdf"},
    },
    {
        "label": "阅读测评",
        "dest": "",
        "globs": ["读书会配套输出/{book}/{book}_阅读测评.*"],
        "primary": {".docx"},
    },
]


def strip_book_prefix(name: str, book: str) -> str:
    """去掉文件名开头的书名前缀（含其后的 - 或 _），返回余下部分（含扩展名）。"""
    for pre in (f"《{book}》_", f"《{book}》-", f"《{book}》", f"{book}_", f"{book}-"):
        if name.startswith(pre):
            return name[len(pre):]
    return name


def target_name(src: Path, book: str, rename) -> str:
    rest = strip_book_prefix(src.name, book)
    stem, suffix = (rest[: -len(src.suffix)], src.suffix) if src.suffix else (rest, "")
    if rename and stem in rename:
        stem = rename[stem]
    return f"《{book}》{stem}{suffix}"


def grade_of(root: Path, book: str):
    """从书籍档案机读块读「等级：Lx」→ 'x'；读不到返回 None。"""
    profile = root / "读书会书籍档案" / f"{book}书籍档案.md"
    meta_py = root / ".claude/skills/laojohn-book-profile/scripts/profile_meta.py"
    if not profile.exists() or not meta_py.exists():
        return None
    spec = importlib.util.spec_from_file_location("profile_meta", meta_py)
    pm = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pm)
    level = pm.simple_field(pm.meta_section(pm.read(profile)), "等级") or ""
    m = re.search(r"L\s*([1-6])", level)
    return m.group(1) if m else None


def gather(root: Path, book: str, with_sources: bool):
    """返回 [(category, [(src_path, picked_bool, reason)])]，picked=是否复制。"""
    plan = []
    for cat in CATEGORIES:
        items, seen = [], set()
        for tmpl in cat["globs"]:
            for src in sorted(root.glob(tmpl.format(book=book))):
                if not src.is_file() or src in seen or src.name.startswith("~$"):
                    continue
                seen.add(src)
                if src.suffix.lower() in cat["primary"]:
                    items.append((src, True, "成品"))
                elif with_sources:
                    items.append((src, True, "源文件"))
                else:
                    items.append((src, False, "源文件(已跳过)"))
        plan.append((cat, items))
    return plan


def main():
    ap = argparse.ArgumentParser(description="把一本书的全部成品归集进一个交付文件夹")
    ap.add_argument("book", help="书名（不带书名号），如：稻草人")
    ap.add_argument("--root", default=None, help="项目根目录（默认当前工作目录）")
    ap.add_argument("--out", default=None, help="打包输出顶层目录名（默认：读书会整套文件打包输出）")
    ap.add_argument("--dest", default=None, help="直接指定打包目标文件夹（覆盖 --out/<年级册《书名》>）")
    ap.add_argument("--grade", default=None, help="年级数字（默认取书籍档案「等级：Lx」）")
    ap.add_argument("--term", default="上", choices=["上", "下"], help="上/下册（不知道就留默认「上」，用户后期手改）")
    ap.add_argument("--with-sources", action="store_true", help="连可编辑源文件(md/json/html)一起打包")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不实际复制")
    args = ap.parse_args()

    book = args.book.strip().strip("《》").strip()
    root = Path(args.root).resolve() if args.root else Path.cwd()
    if not root.exists():
        print(f"[错误] 项目根目录不存在：{root}")
        sys.exit(1)

    grade = args.grade or grade_of(root, book)
    if not grade:
        print("[错误] 书籍档案里读不到「等级：Lx」，请用 --grade 指定年级")
        sys.exit(1)
    folder = f"{grade}{args.term}《{book}》"
    dest_root = Path(args.dest).resolve() if args.dest else (root / (args.out or "读书会整套文件打包输出") / folder)

    print(f"项目根目录 : {root}")
    print(f"打包目标   : {dest_root}")
    print(f"包含源文件 : {'是' if args.with_sources else '否（仅成品）'}")
    print(f"模式       : {'演练(dry-run)' if args.dry_run else '复制'}")
    print("=" * 60)

    total_copied, summary = 0, []
    for cat, items in gather(root, book, args.with_sources):
        picked = [it for it in items if it[1]]
        skipped = [it for it in items if not it[1]]
        sub = cat["dest"].format(t=f"《{book}》")
        dest_dir = dest_root / sub if sub else dest_root
        dest_label = (sub.replace("/", "\\") + "\\") if sub else "（根目录）"

        if not items:
            print(f"[缺] {cat['label']:<10} 未找到任何文件 —— 该物料可能还没生成")
            summary.append((cat["label"], 0, "缺"))
            continue
        if picked and not args.dry_run:
            dest_dir.mkdir(parents=True, exist_ok=True)

        print(f"[{cat['label']}] → {dest_label}")
        for src, _, reason in picked:
            name = target_name(src, book, cat.get("rename"))
            if args.dry_run:
                print(f"    + {src.relative_to(root)}  →  {name}  ({reason})")
            else:
                shutil.copy2(src, dest_dir / name)
                print(f"    ✓ {name}  ({reason})")
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
    if args.term == "上" and not args.dest:
        print("提示：册次按默认写「上」，若实为下册请用 --term 下 重跑或手改文件夹名")
    if missing:
        print(f"⚠ 缺失物料（未生成或命名不符）：{ '、'.join(missing) }")
    if args.dry_run:
        print("（dry-run：未实际写入任何文件）")


if __name__ == "__main__":
    main()
