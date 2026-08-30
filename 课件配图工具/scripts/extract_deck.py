"""从一份 .pptx 里抽出「每页有什么、哪里要配图」的结构化底稿。

这一层**全是确定性的程序判断，不调模型**——页码、画幅、图位位置这类东西
交给模型是浪费且不可靠（手抄清单就是靠人数页码，结果和真实 PPT 错位 1–3 页，
「上台读」标成 P19 实际在 P20，串位一路歪到底）。模型只该做它非做不可的那部分：
看懂这一页在教什么、该画什么。

主图位怎么认：靠**面积占比**，不靠位置也不靠出现顺序。
  实测这份课件：主插图 9%–17% 画布面积，眉标条 0.7%，logo 0.4%，小徽标 0.07%。
  差了一个半数量级，中间是空的，所以 3% 这条线切在真实空隙上、不是我拍的。
  ⚠ 但这是**一份**课件量出来的规律。换一套模板必须重看 `--dump-sizes` 的直方图，
  确认那道空隙还在——判据分不开的时候，宁可不报警也别硬给结论。

另一件必须留给人的事：**没有大图的页，不等于不需要图**。
  P03「猜超人/孙悟空」现在只有两张 0.5in 小图，按面积它不是图位；
  可它恰恰需要一张大图，只是因为版权才改成人工素材位。
  所以本脚本对这类页只标 `候选`，把判断权交出去，绝不替人决定「这页不用图」。
"""
import argparse, json, pathlib, sys
from pptx import Presentation
from pptx.util import Emu

# 画幅档：生图接口只认这几档，量出来的任意比例要归到最近的一档
RATIOS = {"1:1": 1.0, "3:4": 0.75, "4:3": 1.333, "16:9": 1.778, "9:16": 0.5625}


def snap_ratio(w, h):
    """把实测宽高比归到最近的一档，同时把实测值原样带出来供人复核。"""
    if not h:
        return None, None
    r = w / h
    best = min(RATIOS, key=lambda k: abs(RATIOS[k] - r))
    return best, round(r, 3)


def extract(pptx_path, min_area=0.03):
    prs = Presentation(str(pptx_path))
    cw, ch = prs.slide_width, prs.slide_height
    canvas = cw * ch
    pages = []
    for idx, slide in enumerate(prs.slides, 1):
        texts, images, n_tables = [], [], 0
        for sh in slide.shapes:
            if getattr(sh, "has_table", False):
                n_tables += 1
            if sh.shape_type == 13:  # PICTURE
                if sh.width is None or sh.height is None:
                    continue
                share = (sh.width * sh.height) / canvas
                ratio, raw = snap_ratio(sh.width, sh.height)
                images.append({
                    "宽英寸": round(Emu(sh.width).inches, 2),
                    "高英寸": round(Emu(sh.height).inches, 2),
                    "面积占比": round(share, 4),
                    "画幅": ratio,
                    "实测比": raw,
                    "左占比": round(sh.left / cw, 3) if sh.left is not None else None,
                    "上占比": round(sh.top / ch, 3) if sh.top is not None else None,
                    "是主图位": share >= min_area,
                })
            if sh.has_text_frame:
                t = sh.text_frame.text.strip()
                if t:
                    texts.append(t)
        main = [i for i in images if i["是主图位"]]
        # 版面占用情况 —— 判「这页还塞得下图吗」的依据。
        # 对照人工成品得出：真正不配图的页不是「讲道理的页」，而是**版面已经满了**
        # 的页（课时分隔、整页表格、长清单）。只靠内容判断会把一半该配图的页判掉。
        occupied = sum(
            (sh.width or 0) * (sh.height or 0)
            for sh in slide.shapes
            if getattr(sh, "width", None) and getattr(sh, "height", None)
        )
        pages.append({
            "页码": f"P{idx:02d}",
            "文本块": texts,
            "图片": images,
            "主图位数": len(main),
            "主图位画幅": [i["画幅"] for i in main],
            "字数": sum(len(t) for t in texts),
            "文本块数": len(texts),
            "表格数": n_tables,
            "版面占用": round(occupied / canvas, 2),
        })
    return {
        "源文件": pptx_path.name,
        "页数": len(pages),
        "画布": f"{Emu(cw).inches:.2f}x{Emu(ch).inches:.2f}in",
        "主图位面积阈值": min_area,
        "页": pages,
    }


def dump_sizes(deck):
    """把全部图片按面积占比排序打出来——换新模板时先看这个，
    确认「主图 / 装饰件」之间那道空隙还在，再信 min_area 这条线。"""
    rows = []
    for pg in deck["页"]:
        for im in pg["图片"]:
            rows.append((im["面积占比"], pg["页码"], im["宽英寸"], im["高英寸"], im["画幅"]))
    rows.sort(reverse=True)
    print(f"{'面积占比':>9}  {'页码':4} {'尺寸(in)':>12}  画幅")
    prev = None
    for share, pg, w, h, ratio in rows:
        gap = ""
        if prev is not None and prev > 0 and share > 0:
            if prev / share >= 3:
                gap = f"   <<< 断层 {prev / share:.1f}x"
        print(f"{share:9.4f}  {pg:4} {w:5.2f}x{h:<5.2f}  {ratio}{gap}")
        prev = share


def main():
    ap = argparse.ArgumentParser(description="从 pptx 抽出配图底稿（纯程序判断，不调模型）")
    ap.add_argument("pptx", help=".pptx 路径")
    ap.add_argument("-o", "--out", help="输出 json 路径；不给则打印摘要")
    ap.add_argument("--min-area", type=float, default=0.03,
                    help="主图位面积占比阈值，缺省 0.03（实测断层在 0.7%%–9%% 之间）")
    ap.add_argument("--dump-sizes", action="store_true", help="打印全部图片面积排序，用于校准阈值")
    a = ap.parse_args()

    path = pathlib.Path(a.pptx)
    if not path.exists():
        sys.exit(f"找不到文件：{path}")
    deck = extract(path, a.min_area)

    if a.dump_sizes:
        dump_sizes(deck)
        return

    if a.out:
        p = pathlib.Path(a.out)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"已写出 {p}")

    n_main = sum(pg["主图位数"] for pg in deck["页"])
    print(f"\n{deck['源文件']}｜{deck['页数']} 页｜画布 {deck['画布']}｜主图位 {n_main} 处\n")
    for pg in deck["页"]:
        head = pg["文本块"][0][:24] if pg["文本块"] else "(无文字)"
        title = pg["文本块"][1][:34] if len(pg["文本块"]) > 1 else ""
        if pg["主图位数"]:
            mark = "■ " + "/".join(pg["主图位画幅"])
        else:
            mark = "· 无大图"
        print(f"  {pg['页码']}  {mark:12}  {head} ｜ {title}")


if __name__ == "__main__":
    main()
