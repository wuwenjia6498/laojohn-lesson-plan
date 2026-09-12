# -*- coding: utf-8 -*-
r"""批次横审 · 跨篇重复字串粗筛(n-gram)

用途分两档,同一套 n-gram 引擎:

【A 批次横审】每完成一个生产批次(约 12-16 篇写作课详案),扫 写作课详案输出\*.md,
找出「出现在 >=2 篇里的重复字串」,供冷审 agent/人工判别哪些是真句癖、
应补进 variation-pools.md「禁止逐字复用」清单。

【B 单篇 vs 邻篇(--focus,2026-08-17 增设)】交付前对**一份新稿**跑,只报「本篇与邻篇
共有」的片段。起因:「禁止逐字复用」清单只收录**已被发现**的句癖,新写的句子撞上邻篇
但不在清单里 → 机检不报、生成侧不查,要等冷审 Pass B 逐句通读才发现(实测一篇 26 处,
且模板来源不是行文基准篇、正是**相邻的上一篇**)。本模式把那一步人工比对变成机器捞候选。
不给 --against 时,邻篇默认取 --dir 下除本篇外的全部。

本脚本是确定性粗筛:只负责把候选捞全,不负责判断。合理固定件(骨架话术、
格式教学语等)命中后请加进下方 WHITELIST,而不是无视报告。

用法(项目根目录下):
    # A 批次横审
    PYTHONUTF8=1 python .claude/skills/laojohn-writing-lesson/assets/batch_ngram_scan.py
    # B 单篇 vs 指定邻篇(交付前自检,checklist E 组)
    PYTHONUTF8=1 python .claude/skills/laojohn-writing-lesson/assets/batch_ngram_scan.py \
        --focus "写作课详案输出/五上-第二单元-“漫画”老师-写作课详案.md" \
        --against "写作课详案输出/五上-第一单元-我的心爱之物-写作课详案.md"
    可选参数: --dir 写作课详案输出  --n 10  --min-len 12  --min-files 2  --top 200  --out 报告.txt
    (--against 可给多份,逗号分隔或重复给)
"""
import argparse
import glob
import os
import re
import sys
from collections import defaultdict

# 合理固定件白名单:骨架话术/机制名/格式教学语等,按规范本来就每篇复现,
# 掩蔽后不参与重复检测。批次横审第 2 步确认的"合理固定件"补录到这里。
# ⚠ 标题行（`#` 开头）与表格行在 load_lines 里**先于掩蔽被整行剔除**——其中的串
#   永远匹配不到，**不必也不能进白名单**（2026-09-01 审计：曾误收 4 条同型死条目）。
#   给生成方的要求语（如「一篇一肯定一改处」）也不是详案正文串，同样不收。
WHITELIST = [
    "学生互动分享",
    "学生自由分享",
    "（教师总结）",
    "本课完。",
    "全课完。",
    "本环节完。",
    "【教师示范文】",
    "习作讲评指导环节",  # 单篇件：批次档(--min-files 2)空转，留作 --focus 双篇模式用
    "只填关键词",   # 2026-09-01 改短核心：8 篇续写各异（不写整句/三至五个字…），顿号版 0 命中
    "开头空两格",
    "对照三档标准",  # 单篇件：批次档(--min-files 2)空转，留作 --focus 双篇模式用
    # ↓ 2026-08-17 单篇模式上线后补录:体例层固定件,按规范全线统一措辞或统一口径,
    #   本就该每篇复现,报出来只会淹没真句癖。判据=「改了它反而破体例」。
    # 附加讲评块的头部两句(措辞由 title-naming §四 全线统一)
    "本环节供教师灵活取用",
    "可在单次课课后批阅学生习作后集中讲评一次，也可作为系列课下一次课的开场",
    "从本班当堂完成的稿子中选 2–3 篇，对照本课三条技法各选一类",
    "不计入本课 45+45 分钟，讲评的是学生当堂完成的稿子，不布置新的写作任务。",
    "讲评中凡出现 ＿＿＿ 处，务必替换为本班学生习作中的真实句子，切勿虚构。",
    "讲评时投屏或朗读，不具名、不排名次。",
    "每篇对照技法用一句话记下好在哪里、欠缺在哪里。",
    # 讲评块的占位槽括注体例(lesson-structure §三:全角 ＿＿＿ + 括注直写动作指令)
    "＿＿＿",
    "（读该生",
    "（读一句典型的",  # 单篇件：批次档(--min-files 2)空转，留作 --focus 双篇模式用
    # ⑥巡视四类处理块(提示层规范指导语:同一套分层处置口径便于另一位老师照做,
    #   2026-08-17 用户线上裁决「有意保留、不逐篇换写法」)
    "[教师巡视，只做正向介入，不纠错字、不改病句、不打断书写顺畅的学生。按学情分四类处理——]",
    "[书写顺畅型：不打断，走过时轻声一句“接着写”，为其留出书写空间。]",
    "接不下去型：写完",
    "内容空泛型：整段都是",
    "答出一句就让他直接写进去。",
    "草草收尾型：",
    "篇幅明显偏短——先肯定再推一步：",
    # ↓ 2026-08-31 补录:剥掉 〖…〗 页标后浮出水面的体例固定件(判据同上「改了它反而破体例」)。
    #   ⚠ 只收体例层,**师话一律不收**——「师：老师先填一张给你们看。」5 篇同款是真句癖,
    #   该进 variation-pools「禁止逐字复用」清单,不是白名单。
    "学生动笔写作（填表约3分钟；教师巡视）",
    "供教师判断用，不必念给学生）〕",              # 标签纪律⑥.4 硬要求的括注
    "单元校内同步写作",                              # 头部信息行体例
    "年级上册·第",
    "不计入两节连排的45+45，",
    "[操作：把选中的几篇誊清或拍图投屏；不具名，或先征得学生同意]",
    "对照本课技法写明它好在哪里、欠缺在哪里",              # 附录讲评块(title-naming §四 全线统一)
    "真实性提示：下面师话里凡",
    "处，务必替换为本班学生作品中真实写出的句子。",
    # ⑦评改期的固定动作提示
    "延迟到此刻统一处理行文与错别字",  # 单篇件：批次档(--min-files 2)空转，留作 --focus 双篇模式用
    "学生动笔写作（自改；教师巡视答疑）",
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
        # 剥掉 〖PPT第N页·环节名·副标题〗 页标(2026-08-31 补)——它是 ppt-draft 页标回注写进来
        # 的机器标记、不是行文,且每篇体例相同必然全线复现。⚠ 它进不了 WHITELIST:白名单按逐字
        # 匹配,而页标带页码、环节名各篇不同,列不完。**不剥它的后果是整份报告被淹没**:2026-08-31
        # 实测 373 条重复片段里,前几十条全是 `〖PPT第2页·课时分隔·写作指导课〗`(12 篇)这类页标,
        # 真句癖排在后面没人看得到——17 篇附录讲评收尾用同一个模子(「好就好在用上了这节课的
        # X——…往后你再…」7 篇逐字骨架+4 篇变体),批次横审一直在跑却从没被处置,根因就在这里。
        s = re.sub(r"〖[^〗]*〗", "", s).strip()
        if not s:
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



def _lesson_mds(d):
    """目录下的详案 .md,**排除 `_` 前缀的报告/记录文件**(2026-08-31 补)。
    `写作课详案输出/` 里同住着 `_文风判据卡-20260830.md`、`_优化版-…md`、`_冷审复审-…md`、
    `_张祖庆…md` 等报告与候选稿——它们不是详案,却被一起扫进句癖检测,把规则文件名
    (`lesson-structure.md`)、判据术语这类词报成「跨篇重复片段」。
    **本过滤仍必要**:2026-09-13 虽把四份已落地的历史诊断件挪进了 `_归档/`(非递归 glob
    自然不扫),活件仍住在顶层。实测:排除前扫 22 篇、排除后 17 篇,与当时真实的详案数一致。"""
    return [p for p in sorted(glob.glob(os.path.join(d, "*.md")))
            if not os.path.basename(p).startswith("_")]

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
    ap.add_argument(
        "--focus",
        default=None,
        help="单篇模式:只报「本篇与邻篇共有」的片段(交付前自检用)",
    )
    ap.add_argument(
        "--against",
        action="append",
        default=None,
        help="--focus 的比对邻篇(可重复给或逗号分隔;不给则取 --dir 下其余全部)",
    )
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    focus_name = None
    if args.focus:
        if not os.path.isfile(args.focus):
            print(f"--focus 找不到文件: {args.focus}")
            return 1
        focus_name = os.path.splitext(os.path.basename(args.focus))[0]
        if args.against:
            others = []
            for item in args.against:
                others.extend(p for p in item.split(",") if p.strip())
            missing = [p for p in others if not os.path.isfile(p)]
            if missing:
                print("--against 找不到文件: " + "、".join(missing))
                return 1
        else:
            others = [
                p
                for p in _lesson_mds(args.dir)
                if os.path.abspath(p) != os.path.abspath(args.focus)
            ]
        files = [args.focus] + others
    else:
        files = _lesson_mds(args.dir)
    if len(files) < 2:
        print(f"不足 2 份 .md,无从横向比对。")
        return 1

    kept = scan(files, args.n, args.min_len, args.min_files)
    if focus_name:
        kept = [(span, owners) for span, owners in kept if focus_name in owners]

    if focus_name:
        head = (
            f"单篇邻篇比对报告 · 本篇「{focus_name}」 vs 邻篇 {len(files) - 1} 篇 · "
            f"共有片段 {len(kept)} 条(n={args.n}, 最短 {args.min_len} 字)"
        )
    else:
        head = (
            f"批次横审粗筛报告 · 扫描 {len(files)} 篇 · 重复片段 {len(kept)} 条"
            f"(n={args.n}, 最短 {args.min_len} 字, ≥{args.min_files} 篇)"
        )
    out_lines = [
        head,
        "判读提示:骨架话术/格式教学语等合理固定件 → 补进脚本 WHITELIST;"
        "真句癖(同款比喻/反问/口令跨篇复现) → 补进 variation-pools.md「禁止逐字复用」清单;"
        "教师导演腔(如「一下子就看见」「请不太举手的同学」) → 「导演腔套路」条;"
        "发令词/讲评用语(先别急/谁愿意/立起来/流水账/怦怦直跳) → 池6/池7 轮换,勿进 WHITELIST。",
        "",
    ]
    if focus_name:
        out_lines.insert(
            1,
            "单篇模式提示:本报告只是候选,**不是判决**——事务性师话与技法口令本就会近似,"
            "逐条按 pools 裁决序判(说得出口 > 不重复;通行说法不受配额;宁可重复不许自造)。"
            "命中的**教学话轮序列**(不只是措辞)属零件层、冷审改不动,须回生成侧换设计。",
        )
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
