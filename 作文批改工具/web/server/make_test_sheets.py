# -*- coding: utf-8 -*-
"""把效果样例里的三篇模拟习作渲成 18 列格子稿纸，作为**回归基准**。

    PYTHONUTF8=1 python 作文批改工具/web/server/make_test_sheets.py

产物进 `_testdata/`（已 gitignore），随时可重生成。改提示词、换模型之后拿这三张
重跑一遍，就能看出判断层有没有退化——三篇是刻意设计的三种形态：

    A 五个优点并列罗列    → ①没抓住 ②应记「不适用」 ③换名字一字不用改
    B 抓住「爱笑」但只有结论 → ①抓住 ②还不够 ③基本换得掉
    C 抓住「爱管闲事」有画面 → ①抓住 ②做到 ③换不掉

文字逐字取自 `Phase0试用包/效果样例_猜猜他是谁.md`，**故意保留其中的错别字「经长」**
——用来验「不批错别字」这条边界有没有被模型自作主张突破。
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import sys

W, H = 1240, 1754
COLS, CELL, GAP = 18, 58, 4
PITCH = CELL + GAP
LEFT = (W - COLS * PITCH + GAP) // 2
TOP = 330
KAI = "C:/Windows/Fonts/simkai.ttf"
HEI = "C:/Windows/Fonts/simhei.ttf"

PIECES = {
    "A": ("林小满",
          "我们班有一个同学，他长得很高，头发短短的，眼睛大大的。他很爱运动，"
          "经长在操场上跑步，跑得很快。他学习也很好，每次考试都考得很好，老师"
          "经长表扬他。他还很乐于助人，同学有困难他都会去帮忙。他的性格很开朗，"
          "总是笑嘻嘻的。他是一个很好的人，我很喜欢和他做朋友。你猜出他是谁了吗？"),
    "B": ("周予安",
          "我要写的这个人特别爱笑。她一天到晚都在笑，好像没有什么事情能让她不"
          "开心。上课的时候她笑，下课的时候她也笑。有一次老师批评她了，她低着头，"
          "可是过了一会儿又笑起来了。她笑起来很好看，眼睛弯弯的。同学们都喜欢她，"
          "因为她的笑很有感染力。她笑的时候我们也想笑。你猜她是谁？"),
    "C": ("陈知遥",
          "他最大的毛病就是爱管闲事。谁的事他都要插一脚。上个星期我和同桌为了"
          "一块橡皮吵起来，他不知道从哪儿冲过来，两只手一边按住一个，说：“都别"
          "吵了，听我说！”结果他自己也不知道该说什么，站在那儿愣了半天，脸都红了。"
          "扫地的时候他也管，谁扫得不干净他就跟在后面指：“这儿，这儿还有，你没看"
          "见吗？”可是自己那一块地，他忘了扫。有一次他管过头了，把小陈说哭了，"
          "他又慌了，从口袋里摸出一颗糖塞给人家。你猜他是谁？"),
}
TITLE = "猜猜他是谁"


def render(key, out):
    name, body = PIECES[key]
    im = Image.new("RGB", (W, H), (253, 252, 250))
    d = ImageDraw.Draw(im)
    f_title = ImageFont.truetype(HEI, 46)
    f_small = ImageFont.truetype(HEI, 26)
    f_hand = ImageFont.truetype(KAI, 44)

    d.text((LEFT, 90), f"《{TITLE}》", font=f_title, fill=(40, 40, 38))
    d.text((W - LEFT - 330, 104), "姓名", font=f_small, fill=(122, 117, 104))
    d.text((W - LEFT - 265, 96), name, font=f_hand, fill=(30, 40, 90))
    d.line((W - LEFT - 270, 150, W - LEFT - 60, 150), fill=(180, 172, 158), width=2)
    d.text((W - LEFT - 40, 104), "班级", font=f_small, fill=(122, 117, 104))
    d.line((LEFT, 200, W - LEFT, 200), fill=(200, 53, 43), width=3)
    d.text((LEFT, 225), "老约翰 · 同步习作　作文稿纸", font=f_small, fill=(122, 117, 104))

    chars = ["　", "　"] + list(body)      # 开头空两格
    rows = (len(chars) + COLS - 1) // COLS
    for r in range(max(rows, 16)):
        for c in range(COLS):
            x, y = LEFT + c * PITCH, TOP + r * PITCH
            d.rectangle((x, y, x + CELL, y + CELL), outline=(214, 208, 196))
    for i, ch in enumerate(chars):
        if ch == "　":
            continue
        r, c = divmod(i, COLS)
        x, y = LEFT + c * PITCH, TOP + r * PITCH
        bb = d.textbbox((0, 0), ch, font=f_hand)
        d.text((x + (CELL - (bb[0] + bb[2])) / 2, y + (CELL - (bb[1] + bb[3])) / 2 - 2),
               ch, font=f_hand, fill=(28, 38, 96))
    im.save(out, quality=92)
    print(f"{key}  {name}  {len(chars)-2} 字  {rows} 行  -> {out.name}")


if __name__ == "__main__":
    outdir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "_testdata"
    outdir.mkdir(parents=True, exist_ok=True)
    for k in "ABC":
        render(k, outdir / f"sheet{k}.jpg")
