# -*- coding: utf-8 -*-
r"""批次横审 · 跨篇重复字串粗筛(n-gram)

用途:每完成一个生产批次(约 12-16 篇写作课详案),扫 写作课详案输出\*.md,
找出「出现在 >=2 篇里的重复字串」,供冷审 agent/人工判别哪些是真句癖、
应补进 variation-pools.md「禁止逐字复用」清单。

本脚本是确定性粗筛:只负责把候选捞全,不负责判断。合理固定件(骨架话术、
格式教学语等)命中后请加进下方 WHITELIST,而不是无视报告。

用法(项目根目录下):
    PYTHONUTF8=1 python .claude/skills/laojohn-writing-lesson/assets/batch_ngram_scan.py
    可选参数: --dir 写作课详案输出  --n 10  --min-len 12  --min-files 2  --top 200  --out 报告.txt
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict

# 合理固定件白名单:骨架话术/机制名/格式教学语等,按规范本来就每篇复现,
# 掩蔽后不参与重复检测。批次横审第 2 步确认的"合理固定件"补录到这里。
WHITELIST = [
    "学生互动分享",
    "学生自由分享",
    "（教师总结）",
    "本课完。",
    "全课完。",
    "本环节完。",
    "【教师示范文】",
    "【语言运用】",
    "【思维能力】",
    "【审美创造】",
    "【文化自信】",
    "习作讲评指导环节",
    "单次课课后用",
    "系列课作下次课开场",
    "可选·两用",
    "只填关键词、不画图",
    "开头空两格",
    "对照三档标准",
    "一篇一肯定一改处",
]

MASK = "\x00"


def load_lines(path):
    """读一份详案,返回参与检测的规范化行(不含标题/表格/注释/指纹块)。"""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    # 去 HTML 注释(含 VARIATION-FINGERPRINT 指纹块)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    lines = []
    for raw in text.splitlines():
        s = raw.strip()
        if not s:
            continue
        # 标题与表格行按体例本就同构,不参与句癖检测
        if s.startswith("#") or s.startswith("|"):
            continue
        # 示范文引用块参与检测(去掉引用前缀)
        s = re.sub(r"^(?:>\s*)+", "", s).strip()
        if not s:
            continue
        # 纯分隔线
        if set(s) <= set("-–—=·*"):
            continue
        # 去空白后掩蔽白名单,防止跨白名单串拼出伪重复
        s = re.sub(r"\s+", "", s)
        for w in WHITELIST:
            s = s.replace(re.sub(r"\s+", "", w), MASK)
        lines.append(s)
    return lines


def scan(files, n, min_len, min_files):
    per_file_lines = {}
    gram_files = defaultdict(set)
    for path in files:
        name = os.path.splitext(os.path.basename(path))[0]
        lines = load_lines(path)
        per_file_lines[name] = lines
        seen = set()
        for line in lines:
            for i in range(len(line) - n + 1):
                g = line[i : i + n]
                if MASK in g or g in seen:
                    continue
                seen.add(g)
                gram_files[g].add(name)
    shared = {g for g, fs in gram_files.items() if len(fs) >= min_files}

    # 每文件内把相邻的共享 gram 合并成最长片段
    span_files = defaultdict(set)
    for name, lines in per_file_lines.items():
        for line in lines:
            i = 0
            L = len(line)
            while i <= L - n:
                if line[i : i + n] in shared:
                    j = i
                    while j + 1 <= L - n and line[j + 1 : j + 1 + n] in shared:
                        j += 1
                    span = line[i : j + n]
                    if len(span) >= min_len:
                        span_files[span].add(name)
                    i = j + 1
                else:
                    i += 1

    # 片段真实文件数:按子串归属重算(合并后长片段可能只在部分文件完整出现)
    joined = {name: "\n".join(lines) for name, lines in per_file_lines.items()}
    results = []
    for span in span_files:
        owners = sorted(name for name, body in joined.items() if span in body)
        if len(owners) >= min_files:
            results.append((span, owners))

    # 去嵌套:同文件集合下,被更长片段包含的短片段不重复报
    results.sort(key=lambda x: (-len(x[1]), -len(x[0])))
    kept = []
    for span, owners in results:
        covered = any(
            span in k_span and set(owners) <= set(k_owners) for k_span, k_owners in kept
        )
        if not covered:
            kept.append((span, owners))
    return kept


def main():
    ap = argparse.ArgumentParser(description="跨篇重复字串粗筛")
    ap.add_argument("--dir", default="写作课详案输出", help="详案目录(默认 写作课详案输出)")
    ap.add_argument("--n", type=int, default=10, help="n-gram 长度(默认 10 字)")
    ap.add_argument("--min-len", type=int, default=12, help="报告的最短片段长(默认 12 字)")
    ap.add_argument("--min-files", type=int, default=2, help="至少出现的篇数(默认 2)")
    ap.add_argument("--top", type=int, default=200, help="最多报告条数(默认 200)")
    ap.add_argument("--out", default=None, help="报告另存路径(默认只打印)")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    files = sorted(glob.glob(os.path.join(args.dir, "*.md")))
    if len(files) < 2:
        print(f"目录 {args.dir} 下不足 2 份 .md,无从横向比对。")
        return 1

    kept = scan(files, args.n, args.min_len, args.min_files)

    out_lines = [
        f"批次横审粗筛报告 · 扫描 {len(files)} 篇 · 重复片段 {len(kept)} 条"
        f"(n={args.n}, 最短 {args.min_len} 字, ≥{args.min_files} 篇)",
        "判读提示:骨架话术/格式教学语等合理固定件 → 补进脚本 WHITELIST;"
        "真句癖(同款比喻/反问/口令跨篇复现) → 补进 variation-pools.md「禁止逐字复用」清单;"
        "教师导演腔(如「一下子就看见」「请不太举手的同学」) → 「导演腔套路」条;"
        "发令词/讲评用语(先别急/谁愿意/立起来/流水账/怦怦直跳) → 池6/池7 轮换,勿进 WHITELIST。",
        "",
    ]
    for span, owners in kept[: args.top]:
        out_lines.append(f"[{len(owners)}篇 · {len(span)}字] {span}")
        out_lines.append(f"    出现于: {'、'.join(owners)}")
    if len(kept) > args.top:
        out_lines.append(f"…… 其余 {len(kept) - args.top} 条从略(--top 调大可看全)")

    report = "\n".join(out_lines)
    print(report)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(report + "\n")
        print(f"\n报告已存: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
