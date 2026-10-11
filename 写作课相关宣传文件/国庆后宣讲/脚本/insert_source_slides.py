# -*- coding: utf-8 -*-
"""把《四至六年级教材换新全面梳理》第 21 页（阅读与写作两条主线）插进主宣讲第一部分，替代原「家长需求」页（2026-10-10）。

用法：先跑 build_main.py，再跑本脚本（PYTHONUTF8=1 python insert_source_slides.py [主宣讲路径]）。
插在「结构性利好」页之后；页码已由 build_main.py 的 reserve(21) 预留。
插入走 PowerPoint COM（Slides.InsertFromFile 会把 13.33 英寸的源页按比例缩放到 20 英寸），
所以本机必须装有 PowerPoint，且主宣讲不能正被 PowerPoint 或 WPS 打开。
插入后：眉标改「家长需求」、页脚改「老约翰 · 2026.10 宣讲会」、页码重编；
两张卡片的文字精简（阅读、写作两条线各说各的），删掉底部「小古文」提示条，两张卡片拉长填满。
"""
import os
import sys

import win32com.client

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '1-国庆后宣讲-主宣讲.pptx'))
SRC = os.path.abspath(os.path.join(HERE, '..', '四至六年级教材换新全面梳理-20260907 .pptx'))
LOGO = os.path.abspath(os.path.join(HERE, '..', '..', '..', '品牌资产', 'logo.png'))
SRC_NO = 21
ANCHOR = '对我们这类读写机构，这是结构性利好'  # 插在含这句标题的页之后

KICKER = '家长需求'
NEW_FOOTER = '老约翰 · 2026.10 宣讲会'
CARDS = {  # 卡片底框名 → (正文框名, 现状, 怎么做)
    'Shape 2': ('Text 5', '整本书阅读要求提高，快乐读书吧分量加重。只读节选、只做题，已经跟不上新教材。',
                '读完、读透一本书，把读到的东西想清楚、说出来。'),
    'Shape 6': ('Text 9', '新习作题目贴近真实生活，套模板、背范文的收益在下降。',
                '写真实的事、真实的感受，把一篇作文写清楚、写具体。'),
}
HEADS = ['Text 4', 'Text 8']  # 「阅读主线」「写作主线」
DROP = ['Shape 10', 'Shape 11', 'Image 3', 'Text 12']  # 底部「小古文」提示条
HOW = '怎么做：'
RED = 0x2C44C0  # #C0442C，COM 颜色是 BGR
NOTES = '阅读和写作两条线分开讲：读书会回应「读得深」，同步写作回应「写得出」。单元习作与作文仍是家长最直接的衡量标准。'


def texts(slide):
    for sh in slide.Shapes:
        if sh.HasTextFrame and sh.TextFrame.HasText:
            yield sh, sh.TextFrame.TextRange.Text


def find_slide(pres, needle):
    hits = [i for i in range(1, pres.Slides.Count + 1) if any(needle in t for _, t in texts(pres.Slides(i)))]
    assert len(hits) == 1, (needle, hits)
    return hits[0]


def is_page_no(sh, t, pres):
    return t.strip().isdigit() and len(t.strip()) == 2 and sh.Top > pres.PageSetup.SlideHeight * 0.9


app = win32com.client.DispatchEx('PowerPoint.Application')
pres = app.Presentations.Open(MAIN, False, False, False)
try:
    at = find_slide(pres, ANCHOR)
    pres.Slides.InsertFromFile(SRC, at, SRC_NO, SRC_NO)
    sl = pres.Slides(at + 1)
    shapes = {sh.Name: sh for sh in sl.Shapes}

    # 源页右上角 logo 是 7237px 宽的大图（单张 2.4MB），换成主宣讲用的品牌 logo，位置高度不变
    old = shapes['Image 0']
    sl.Shapes.AddPicture(LOGO, False, True, old.Left, old.Top, old.Height * 1200 / 414, old.Height)
    old.Delete()

    bar_bottom = shapes['Shape 10'].Top + shapes['Shape 10'].Height
    for name in DROP:
        shapes[name].Delete()

    for card, (body, now, how) in CARDS.items():
        c, b = shapes[card], shapes[body]
        c.Height = bar_bottom - c.Top
        b.Top = c.Top + c.Height * 0.24
        b.Height = c.Top + c.Height - b.Top - 30
        tf = b.TextFrame
        tf.VerticalAnchor = 3  # 垂直居中，卡片拉长后不留下半截空白
        tr = tf.TextRange
        size = tr.Characters(1, 1).Font.Size
        tr.Text = now + '\r' + HOW + how
        tr.Font.Size = round(size * 1.6)
        tr.Font.Bold = False
        tr.ParagraphFormat.SpaceAfter = 30
        h = tr.Paragraphs(2).Characters(1, len(HOW))
        h.Font.Bold = True
        h.Font.Color.RGB = RED

    for name in HEADS:  # 正文放大后，卡片小标题同比放大，保持主次
        f = shapes[name].TextFrame.TextRange.Font
        f.Size = round(f.Size * 1.5)

    for sh, t in texts(sl):
        tr = sh.TextFrame.TextRange
        if t.strip().startswith('PART 2'):
            tr.Text = KICKER
        elif t.strip() == '老约翰 · 2026秋新教材解读':
            tr.Text = NEW_FOOTER
        elif is_page_no(sh, t, pres):
            tr.Text = f'{sl.SlideIndex:02d}'
    sl.NotesPage.Shapes.Placeholders(2).TextFrame.TextRange.Text = NOTES

    bad = [(i, t) for i in range(1, pres.Slides.Count + 1)
           for sh, t in texts(pres.Slides(i)) if is_page_no(sh, t, pres) and int(t) != i]
    assert not bad, f'页码与页序不符：{bad}'
    pres.Save()
    print('inserted source', SRC_NO, 'at', sl.SlideIndex, 'total', pres.Slides.Count)
finally:
    pres.Close()
    if app.Presentations.Count == 0:
        app.Quit()
