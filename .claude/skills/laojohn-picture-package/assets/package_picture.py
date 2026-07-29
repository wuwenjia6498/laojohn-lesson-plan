# -*- coding: utf-8 -*-
r"""
老约翰 · 看图写话整套文件打包脚本

把一次看图写话课散落在各输出目录里的成品，复制归集进一个交付文件夹：

    看图写话整套文件打包输出\<课次>\
    ├── 课堂用图\           ← 看图写话详案输出\<课次>\图位\*.png（主/练/备，投屏与打印用）
    ├── 配套物料\           ← 看图写话配套输出\<课次>\*.pdf（支架小卡/兜底纸条/稿纸/教师家长页）
    └── <课次>-配图.docx    ← 看图写话详案输出\（放根目录，主交付件一眼可见）

约定：
- 复制不移动——各原始输出目录是单一事实源，绝不破坏。
- 详案 docx 择优只收一份：有回插图版 `<课次>-配图.docx` 就只收它；
  没有（图还没回插）才回落收无图版 `<课次>.docx`，并在汇总里显式警告。
- 默认只收对外成品（docx/png/pdf）；--with-sources 时额外把可编辑源与内部件
  （详案 md、生图提示词 txt、被择优淘汰的无图版 docx、图位 _验收报告.md、配套 html/_data.json）一并打包。
- 缺料不报错、不阻断：跳过并在汇总里标「缺」，让用户知道哪些物料还没生成。
- 看图写话线没有 PPT／讲稿链（不进 ppt-draft→ppt），故无「课件PPT」「逐页讲稿」分类。

用法（课次名含空格与「·」，务必整体加引号）：
    PYTHONUTF8=1 python package_picture.py "二上（秋）第 1 次 · 方法课"
    PYTHONUTF8=1 python package_picture.py "二上（秋）第 1 次 · 方法课" --with-sources
    PYTHONUTF8=1 python package_picture.py "二上（秋）第 1 次 · 方法课" --dest "C:/Users/xx/Desktop/第1次"
"""
import argparse
import shutil
import sys
from pathlib import Path

# 每个分类两种取件模式：
#   prefer 模式：按序取第一个命中的 glob 作为成品（择优），其余命中的降级为源文件；
#   globs 模式：命中 glob 的文件，扩展名 in primary → 始终复制，否则视为源文件。
# 两种模式下，源文件都只在 --with-sources 时复制。
# sources：无条件视为源文件的补充 glob（默认跳过）。
CATEGORIES = [
    {
        "label": "看图写话详案",
        "dest": "",
        "prefer": [
            ("看图写话详案输出/{unit}-配图.docx", "成品·配图版"),
            ("看图写话详案输出/{unit}.docx", "成品·无图版(⚠图未回插)"),
        ],
        "sources": [
            "看图写话详案输出/{unit}.md",
            "看图写话详案输出/{unit}-生图提示词.txt",
        ],
    },
    {
        "label": "课堂用图",
        "dest": "课堂用图",
        # 图位目录下的 _历史/_画风测试/_合格基线 等子目录不是文件，自动排除；
        # _验收报告.md 是内部核验件，落入源文件（默认跳过）。
        "globs": ["看图写话详案输出/{unit}/图位/*"],
        "primary": {".png", ".jpg", ".jpeg"},
    },
    {
        "label": "配套物料",
        "dest": "配套物料",
        # 支架小卡/兜底纸条/看图写话稿纸/教师家长页：pdf 是成品，html/_data.json 是源。
        # 纯口头课只出「支架小卡+教师家长页」两件，属正常，不算缺料。
        "globs": ["看图写话配套输出/{unit}/*"],
        "primary": {".pdf"},
    },
]


def _skip(src: Path, seen: set) -> bool:
    """非文件、重复命中、Office 临时锁文件（~$）一律跳过。"""
    return (not src.is_file()) or (src in seen) or src.name.startswith("~$")


def gather(root: Path, unit: str, with_sources: bool):
    """返回 [(category, [(src_path, picked_bool, reason)])]，picked=是否复制。"""
    plan = []
    for cat in CATEGORIES:
        items = []
        seen = set()

        # ① 择优取件：第一个命中的算成品，后续命中的降级为源
        picked_primary = False
        for tmpl, reason in cat.get("prefer", []):
            for src in sorted(root.glob(tmpl.format(unit=unit))):
                if _skip(src, seen):
                    continue
                seen.add(src)
                if not picked_primary:
                    items.append((src, True, reason))
                    picked_primary = True
                else:
                    items.append((src, with_sources, "源文件·同名替代版"))

        # ② 常规取件：按扩展名区分成品/源
        for tmpl in cat.get("globs", []):
            for src in sorted(root.glob(tmpl.format(unit=unit))):
                if _skip(src, seen):
                    continue
                seen.add(src)
                if src.suffix.lower() in cat.get("primary", set()):
                    items.append((src, True, "成品"))
                else:
                    items.append((src, with_sources, "源文件"))

        # ③ 无条件源文件
        for tmpl in cat.get("sources", []):
            for src in sorted(root.glob(tmpl.format(unit=unit))):
                if _skip(src, seen):
                    continue
                seen.add(src)
                items.append((src, with_sources, "源文件"))

        plan.append((cat, items))
    return plan


def list_available(root: Path):
    """课次名含空格与「·」，易打错；找不到时列出详案输出目录里的可选课次。"""
    d = root / "看图写话详案输出"
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md") if p.is_file())


def main():
    ap = argparse.ArgumentParser(description="把一次看图写话课的全部成品归集进一个交付文件夹")
    ap.add_argument("unit", help='课次标识（=详案文件名 stem），如："二上（秋）第 1 次 · 方法课"')
    ap.add_argument("--root", default=None, help="项目根目录（默认当前工作目录）")
    ap.add_argument("--out", default=None,
                    help="打包输出顶层目录名（默认：看图写话整套文件打包输出）")
    ap.add_argument("--dest", default=None, help="直接指定打包目标文件夹（覆盖 --out/<课次>）")
    ap.add_argument("--with-sources", action="store_true",
                    help="连可编辑源与内部件(md/txt/json/html/无图版docx/验收报告)一起打包")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不实际复制")
    args = ap.parse_args()

    unit = args.unit.strip().strip("《》").strip()
    root = Path(args.root).resolve() if args.root else Path.cwd()
    out_top = args.out or "看图写话整套文件打包输出"
    dest_root = Path(args.dest).resolve() if args.dest else (root / out_top / unit)

    if not root.exists():
        print(f"[错误] 项目根目录不存在：{root}")
        sys.exit(1)

    print(f"项目根目录 : {root}")
    print(f"课次       : {unit}")
    print(f"打包目标   : {dest_root}")
    print(f"包含源文件 : {'是' if args.with_sources else '否（仅成品）'}")
    print(f"模式       : {'演练(dry-run)' if args.dry_run else '复制'}")
    print("=" * 60)

    plan = gather(root, unit, args.with_sources)

    total_copied = 0
    summary = []
    no_image_docx = False
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
            if "无图版" in reason:
                no_image_docx = True
            target = dest_dir / src.name
            if args.dry_run:
                print(f"    + {src.relative_to(root)}  ({reason})")
            else:
                shutil.copy2(src, target)
                print(f"    ✓ {src.name}  ({reason})")
            total_copied += 1
        for src, _, reason in skipped:
            print(f"    - {src.name}  ({reason}·已跳过)")
        summary.append((cat["label"], len(picked), "OK" if picked else "仅源文件被跳过"))

    print("=" * 60)
    print("汇总：")
    for label, n, status in summary:
        flag = "✓" if status == "OK" else ("✗" if status == "缺" else "·")
        print(f"  {flag} {label:<12} 复制 {n} 个文件  [{status}]")
    missing = [s[0] for s in summary if s[2] == "缺"]
    print("-" * 60)
    print(f"共复制 {total_copied} 个文件 → {dest_root}")
    if no_image_docx:
        print("⚠ 详案收的是【无图版】——未找到 `-配图.docx`，说明图还没回插；"
              "回插后重跑打包即可换成配图版。")
    if missing:
        print(f"⚠ 缺失物料（未生成或课次名不符）：{ '、'.join(missing) }")
        if total_copied == 0:
            avail = list_available(root)
            if avail:
                print("  该课次一个文件都没命中，可选课次名（取自 看图写话详案输出\\*.md）：")
                for name in avail:
                    print(f"    · {name}")
    if args.dry_run:
        print("（dry-run：未实际写入任何文件）")


if __name__ == "__main__":
    main()
