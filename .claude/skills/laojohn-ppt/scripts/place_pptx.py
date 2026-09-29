# -*- coding: utf-8 -*-
"""外部 PPT 认领归位：把丢在 `写作课件PPT输出\\` 根目录的 pptx 收进课次子目录并规范命名。

写作课 PPT 改由外部平台生成后，用户的动作是「出好 PPT 丢进根目录」。但打包脚本
`package_writing.py` 只 glob `写作课件PPT输出/{unit}/*`——**散在根目录的件收不到**，
交付时会漏掉老师真正要用的那份（已踩过一次）。本脚本是后处理链的第 1 步。

    PYTHONUTF8=1 python place_pptx.py [--dry-run] [--root <项目根>]

认领规则：拿 pptx 文件名剥掉 PPT/课件/日期/版本一类尾缀后的串，去和
`写作课详案输出\\*-写作课详案.md` 的**课次标识与题目段双向**比对（外部平台导出的名字
可能只有题目，也可能已经是规范全名）。**命中 0 个或多个一律列候选让人选，绝不猜。**

命名规则（2026-08-26 改）：一律 `<年级册>-第N单元-<题目>-课件PPT.pptx`，与详案、配套、
中间稿的课次标识段对齐。**旧口径是 `<题目>-全课.pptx`（文件名内不带年级单元），已作废**——
存量 12 份已随本次改名一并迁移，`CLAUDE.md` §7 那条也同步推翻了。
两节合一与否仍要读 pptx 判定（眉标为纯数字的课时分隔页 >= 2 即合一），但**不再影响文件名**，
只在分节/单节时提示人工确认要不要在尾缀前补课型段。
"""
import argparse
import os
import re
import shutil
import sys

from pptx import Presentation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PPT_DIR = "写作课件PPT输出"
PLAN_DIR = "写作课详案输出"
PLAN_SUFFIX = "-写作课详案.md"

# 文件名里对认领无意义的尾缀/前缀噪声
NOISE = re.compile(
    r"(?:课件|投屏|终版|定稿|最终|修改|新|全课)?"
    r"(?:PPT|ppt|pptx)?"
    r"(?:[-_ ]*v?\d+(?:\.\d+)*)?"        # v2 / 1.3 / -2
    r"(?:[-_ ]*\d{4}[-_.]?\d{2}[-_.]?\d{2})?"   # 20260801 / 2026-08-01
    r"$"
)


def is_pptx(name):
    """`~$…` 是 Office 打开文档时的临时锁文件，不是课件。"""
    return name.lower().endswith(".pptx") and not name.startswith("~$")


def units(root):
    """课次标识 -> 题目。课次标识即详案文件名去掉尾缀，如 三上-第一单元-猜猜他是谁。"""
    out = {}
    d = os.path.join(root, PLAN_DIR)
    if not os.path.isdir(d):
        sys.exit("找不到 %s——确认工作目录是项目根" % d)
    for fn in os.listdir(d):
        if fn.startswith("_"):                   # `_润色报告-<课次>-写作课详案.md` 之类的报告件，不是课次
            continue
        if fn.endswith(PLAN_SUFFIX):
            unit = fn[: -len(PLAN_SUFFIX)]
            out[unit] = unit.split("-")[-1]      # 末段＝题目
    return out


def strip_noise(stem):
    prev = None
    while prev != stem:                          # 反复剥，应对 “猜猜他是谁PPT终版2”
        prev = stem
        stem = NOISE.sub("", stem).strip(" -_")
    return stem


def claim(stem, unit_map):
    """返回命中的课次列表。先精确、再双向子串。

    精确匹配走**双键**：课次标识（三上-第一单元-猜猜他是谁）与纯题目（猜猜他是谁）都算。
    2026-08-26 起规范名带课次标识段，剥噪后得到的正是课次标识——只比纯题目的话，
    重跑认领（如外部件重复投放判重）会从精确跌到下面那行的模糊子串。而 `写日记`/`写观察日记`、
    `续写故事`/`缩写故事` 这类题目互为子串的课次已经存在，模糊匹配迟早撞车。
    """
    key = strip_noise(stem)
    if not key:
        return []
    exact = [u for u, t in unit_map.items() if key in (u, t)]
    if exact:
        return exact
    return [u for u, t in unit_map.items() if t in key or key in t]


def merged(path):
    """是否两节合一：眉标为纯数字的课时分隔页 >= 2。"""
    try:
        prs = Presentation(path)
    except Exception as e:                       # 损坏或非 pptx，交给人处理
        print("   ! 读不出这份 pptx（%s），跳过命名判断" % e)
        return None
    n = 0
    for slide in prs.slides:
        texts = [sh.text_frame.text.strip() for sh in slide.shapes
                 if sh.has_text_frame and sh.text_frame.text.strip()]
        if texts and re.match(r"^\d+$", texts[0]):
            n += 1
    return n >= 2


def main():
    ap = argparse.ArgumentParser(description="把根目录的外部 pptx 认领归位到课次子目录")
    ap.add_argument("--root", default=".", help="项目根目录（默认当前目录）")
    ap.add_argument("--dry-run", action="store_true", help="只打印计划，不动文件")
    args = ap.parse_args()

    root = os.path.abspath(args.root)
    ppt_root = os.path.join(root, PPT_DIR)
    if not os.path.isdir(ppt_root):
        sys.exit("找不到 %s" % ppt_root)

    unit_map = units(root)
    loose = [f for f in os.listdir(ppt_root)
             if is_pptx(f) and os.path.isfile(os.path.join(ppt_root, f))]
    if not loose:
        print("根目录没有待认领的 pptx——%s\\ 下的散件为空。" % PPT_DIR)
        return

    moved = held = 0
    for fn in sorted(loose):
        src = os.path.join(ppt_root, fn)
        stem = os.path.splitext(fn)[0]
        hits = claim(stem, unit_map)
        print("\n[%s]" % fn)

        if len(hits) != 1:
            held += 1
            print("   认领失败：命中 %d 个课次（题目解析为 %r）" % (len(hits), strip_noise(stem)))
            for u in (hits or sorted(unit_map)):
                print("       - %s" % u)
            print("   请改名或手工放入对应子目录后重跑。")
            continue

        unit = hits[0]
        m = merged(src)
        # 命名只认课次标识，与合一与否无关（见文件头「命名规则」）
        name = "%s-课件PPT.pptx" % unit
        dst_dir = os.path.join(ppt_root, unit)
        dst = os.path.join(dst_dir, name)

        print("   认领 -> %s" % unit)
        print("   %s，命名为 %s" % (
            "判定两节合一" if m else
            ("判定分节/单节——若同课次还有另一份，请人工在 -课件PPT 前补课型段" if m is False
             else "无法判定合一与否"), name))

        if os.path.exists(dst):
            held += 1
            print("   ! 目标已存在同名文件，停下不覆盖：%s" % dst)
            continue

        # 子目录里的其它 pptx 会被打包一起收走，必须提醒
        # 并排入库的 `-配图版.pptx`（2026-09-29 立）是参考件、打包只认精确名，不算
        others = [f for f in os.listdir(dst_dir) if is_pptx(f) and not f.endswith("-配图版.pptx")] if os.path.isdir(dst_dir) else []
        if others:
            print("   ! 该子目录已有 %d 份 pptx，打包会一并收走——确认是否作废件：" % len(others))
            for f in others:
                print("       - %s" % f)

        if args.dry_run:
            print("   (dry-run) 将移动到 %s" % dst)
        else:
            os.makedirs(dst_dir, exist_ok=True)
            shutil.move(src, dst)
            print("   已移动 -> %s" % os.path.relpath(dst, root))
        moved += 1

    print("\n%s：认领 %d 份，待处理 %d 份" % ("计划" if args.dry_run else "完成", moved, held))
    if moved and not args.dry_run:
        print("下一步：跑 inspect_pptx.py 出分组工作单（后处理链第 2 步）")


if __name__ == "__main__":
    main()
