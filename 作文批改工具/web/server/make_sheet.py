# -*- coding: utf-8 -*-
"""给任意一课造一张模拟稿纸，供 smoke_real.py 打真实模型用。

    PYTHONUTF8=1 python 作文批改工具/web/server/make_sheet.py [素材key] [输出目录]

**不改 `make_test_sheets.py`**：它的 `PIECES`/`TITLE` 是模块级常量，直接改会连带
毁掉 `_testdata/sheetA-C.jpg`，而 `run_regression.py` 还靠那三张跑《猜猜他是谁》
的判断层回归。本脚本 importlib 载入它、在**自己进程内**临时改那两个常量再调
`render()`，原三张不受影响。

素材写在下面 `SHEETS` 里、跟着仓走，是为了**可复现**：实测结论只有连着素材看才
有意义（哪一处是刻意埋的、模型判对没判对）。每课的素材都该写清楚埋了什么。

`render()` 是把正文一个字一个格连续填下去的，不认 `\\n`。这里用「补齐到行宽的
全角空格」实现换行——全角空格在 `render()` 里会被跳过不画，正好当填充用。
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# key -> (标题, 姓名, 正文分段, 这份素材刻意埋了什么)
SHEETS = {
    "guancha": (
        "写观察日记",
        "林小舟",
        [
            "十月八日 星期三 晴",
            "今天老师发了三杯黄豆。我这杯的豆子圆圆的，黄黄的，硬得像小石子。我用手指按了按，一点都按不动。它泡在水里，杯底沉了一层。",
            "十月十一日 星期六",
            "豆子又长大了一点。皮松了，能看见一条缝。",
            "十月十四日 星期二 阴",
            "豆子又长大了一点，比上次更大了。真神奇。",
        ],
        [
            "第一则没有跟上次比，只写了初始样子——这是详案要求的正确写法，"
            "看模型会不会按缺对比误判它未达成（验第②条 judge_by 里那条反向刹车）",
            "第二则的头一行只有日期星期、缺天气——看模型判第①条为部分达成，"
            "而不是因为 not_in_scope 写着不看格式就整条跳过（验 exceptions 豁免）",
            "第二、三则写的是同一处变化（都是又长大了一点）——看第③条判不判得出重复",
            "第三则末尾埋了空话真神奇（该课 empty_words 里的原词）",
        ],
    ),
}


def build_body(paragraphs, cols):
    """段间补全角空格到行宽，模拟另起一行。"""
    out = []
    for p in paragraphs:
        out.append(p)
        pad = (-len(p)) % cols
        out.append("　" * pad)
    return "".join(out)


def main():
    key = sys.argv[1] if len(sys.argv) > 1 else "guancha"
    if key not in SHEETS:
        print("没有这份素材：" + key + "　可选：" + "、".join(SHEETS))
        return 1
    outdir = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "_testdata"
    outdir.mkdir(parents=True, exist_ok=True)

    title, name, paragraphs, planted = SHEETS[key]
    mts = _load("make_test_sheets")
    # 只在本进程内改，原 PIECES/TITLE 不落盘
    mts.TITLE = title
    mts.PIECES = dict(mts.PIECES)
    mts.PIECES[key] = (name, build_body(paragraphs, mts.COLS))

    out = outdir / ("sheet_" + key + ".jpg")
    mts.render(key, out)
    print("\n这份稿纸刻意埋了：")
    for i, p in enumerate(planted, 1):
        print("  " + str(i) + ". " + p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
