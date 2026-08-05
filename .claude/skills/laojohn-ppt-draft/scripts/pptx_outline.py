# -*- coding: utf-8 -*-
"""从已定稿的 pptx 抽出逐页骨架，作为撰写「逐页讲稿」的对位依据。

写作课 PPT 改由外部平台生成后，讲稿的页序事实源不再是中间稿，而是**外部 pptx 的实际页序**。
撰写讲稿前先跑本脚本，拿到每页的眉标 / 标题 / 屏上文字 / 点击次数，逐页对着写。

    PYTHONUTF8=1 python pptx_outline.py <foo.pptx> [-o outline.md]

「点击次数」是撰写的硬约束：某页有 6 次点击，口播就得有 6 个对应的推进节拍，
不能一段念完——否则老师照着念会与屏幕脱节。
"""
import argparse
import os
import re
import sys
import zipfile

from pptx import Presentation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def clicks_per_slide(path):
    z = zipfile.ZipFile(path)
    out = {}
    for name in z.namelist():
        m = re.match(r"ppt/slides/slide(\d+)\.xml$", name)
        if m:
            xml = z.read(name).decode("utf-8", "ignore")
            out[int(m.group(1))] = xml.count('nodeType="clickEffect"')
    z.close()
    return out


def slide_texts(slide):
    """按阅读顺序（先上后下、同带先左后右）取出屏上文字。"""
    items = []
    for sh in slide.shapes:
        if sh.has_text_frame and sh.text_frame.text.strip():
            top = sh.top if sh.top is not None else 0
            left = sh.left if sh.left is not None else 0
            items.append((top, left, sh.text_frame.text.strip()))
        if getattr(sh, "has_table", False) and sh.has_table:
            rows = []
            for r in sh.table.rows:
                rows.append(" | ".join(c.text.strip().replace("\n", " ") for c in r.cells))
            if rows:
                top = sh.top if sh.top is not None else 0
                left = sh.left if sh.left is not None else 0
                items.append((top, left, "［表格］\n" + "\n".join(rows)))
    band = 500000  # 约半厘米，同一横带内按左右排
    items.sort(key=lambda it: (it[0] // band, it[1]))
    return [t for _, _, t in items]


def main():
    ap = argparse.ArgumentParser(description="从 pptx 抽逐页骨架（撰写讲稿用）")
    ap.add_argument("pptx")
    ap.add_argument("-o", "--out", default=None, help="输出 .md（默认 <同名>-页序骨架.md）")
    args = ap.parse_args()

    prs = Presentation(args.pptx)
    clicks = clicks_per_slide(args.pptx)
    n = len(prs.slides._sldIdLst)

    lines = ["# %s · 页序骨架" % os.path.basename(args.pptx),
             "",
             "> 撰写逐页讲稿的对位依据：讲稿页序须与此严格 1:1。",
             "> 「点击」列是硬约束——N 次点击就要有 N 个推进节拍。",
             "",
             "| 页 | 点击 | 眉标 | 标题 |",
             "| --- | --- | --- | --- |"]
    for idx, slide in enumerate(prs.slides, 1):
        t = slide_texts(slide)
        kicker = t[0].replace("\n", " ") if t else ""
        title = t[1].replace("\n", " ") if len(t) > 1 else ""
        lines.append("| P%02d | %d | %s | %s |" % (idx, clicks.get(idx, 0), kicker, title))

    lines += ["", "---", ""]
    for idx, slide in enumerate(prs.slides, 1):
        t = slide_texts(slide)
        lines.append("## P%02d ｜ 点击 %d 次" % (idx, clicks.get(idx, 0)))
        lines.append("")
        for i, seg in enumerate(t):
            tag = "眉标" if i == 0 else ("标题" if i == 1 else "屏上")
            lines.append("- **%s**：%s" % (tag, seg.replace("\n", "  \n  ")))
        lines.append("")

    out = args.out or os.path.splitext(args.pptx)[0] + "-页序骨架.md"
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("共 %d 页、%d 次点击 -> %s" % (n, sum(clicks.values()), out))


if __name__ == "__main__":
    main()
