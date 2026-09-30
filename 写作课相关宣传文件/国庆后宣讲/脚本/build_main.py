# -*- coding: utf-8 -*-
"""主宣讲重做版（2026-09-30）：整份从零生成，版式不再沿用同步写作完整介绍。

用法：PYTHONUTF8=1 python build_main.py [输出路径]
缺省输出到上级目录的 1-国庆后宣讲-主宣讲.pptx（文件被 PowerPoint 打开时会写失败，先关掉）。
第一部分的按钮超链接到同目录的 2-同步写作课程完整介绍.pptx，两份文件须放在同一文件夹。
"""
import os
import sys

from lxml import etree
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.dml import MSO_LINE
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))  # 按相对位置定位项目根，不写死盘符
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', '1-国庆后宣讲-主宣讲.pptx')
LOGO = os.path.join(ROOT, '品牌资产', 'logo.png')
LOGO_WHITE = os.path.join(HERE, '_logo_white.png')  # 深底用的反白 logo，脚本现做，不入库
LINK = '2-同步写作课程完整介绍.pptx'

FONT = '微软雅黑'
INK = RGBColor(0x1E, 0x2B, 0x3A)      # 深墨蓝：分隔页、深色块
RED = RGBColor(0xC8, 0x35, 0x2B)      # 品牌红
PAPER = RGBColor(0xF7, 0xF3, 0xEC)    # 页面底色
SAND = RGBColor(0xED, 0xE4, 0xD6)     # 浅沙：次级色块
CARD = RGBColor(0xFF, 0xFF, 0xFF)
TEXT = RGBColor(0x2B, 0x29, 0x26)
MUTED = RGBColor(0x7A, 0x74, 0x68)
LINE = RGBColor(0xDD, 0xD3, 0xC4)
PALE = RGBColor(0xC9, 0xD2, 0xDC)     # 深底上的次级文字
TINT = RGBColor(0xFB, 0xEB, 0xE8)     # 浅红

W, H = 20.0, 11.25


def make_white_logo():
    im = Image.open(LOGO).convert('RGBA')
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if a:
                k = max(0.0, min(1.0, (255 - g) / 190.0))  # 红→不透明白，白→透明（字从色块里镂空）
                px[x, y] = (255, 255, 255, int(a * k))
    im.save(LOGO_WHITE)


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]


# ---------- 原语 ----------
def rect(s, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, line=None, radius=None):
    sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1.25)
    sp.shadow.inherit = False
    if radius is not None and shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        sp.adjustments[0] = radius
    return sp


def _font(run, size, color, bold):
    f = run.font
    f.size = Pt(size)
    f.bold = bold
    f.color.rgb = color
    f.name = FONT
    rpr = run._r.get_or_add_rPr()
    latin = rpr.find(qn('a:latin'))
    ea = rpr.find(qn('a:ea'))
    if ea is None:
        ea = etree.SubElement(rpr, qn('a:ea'))
        latin.addnext(ea)  # ea 必须紧跟 latin 之后，顺序错了中文会掉成 Calibri
    ea.set('typeface', FONT)


def text(s, x, y, w, h, paras, size=22, color=TEXT, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.3, after=0):
    """paras：字符串（\n 分段）或段落列表；段落可以是字符串或 [(文字, {size,color,bold}), …]。"""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    if isinstance(paras, str):
        paras = paras.split('\n')
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        if after and i < len(paras) - 1:
            p.space_after = Pt(after)
        runs = [(para, {})] if isinstance(para, str) else para
        for t, st in runs:
            r = p.add_run()
            r.text = t
            _font(r, st.get('size', size), st.get('color', color), st.get('bold', bold))
    return tb


def logo(s, dark=False, x=None, y=0.55, h=0.62):
    w = h * 1200 / 414
    s.shapes.add_picture(LOGO_WHITE if dark else LOGO, Inches(W - 0.9 - w if x is None else x),
                         Inches(y), height=Inches(h))


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


def bg(s, color):
    f = s.background.fill
    f.solid()
    f.fore_color.rgb = color


def button(s, x, y, w, h, label, fill, color):
    b = rect(s, x, y, w, h, fill, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    tf = b.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = label
    _font(r, 20, color, True)
    b.click_action.hyperlink.address = LINK
    return b


PAGE = [0]


def content(kicker, title, sub=None, title_size=40):
    """内容页骨架：左上红色眉标 + 大标题 + 可选导语；右上 logo；底部页脚。"""
    s = prs.slides.add_slide(BLANK)
    bg(s, PAPER)
    PAGE[0] = len(prs.slides)
    rect(s, 0, 0, 0.22, H, RED)
    if kicker.startswith('开发任务'):  # 开发任务页：眉标做成红底白字徽标，一眼认出是第几项任务
        head, _, rest = kicker.partition(' · ')
        bw = len(head) * 0.3 + 0.7
        rect(s, 0.9, 0.42, bw, 0.58, RED, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
        text(s, 0.9, 0.42, bw, 0.58, head, size=21, color=CARD, bold=True, align=PP_ALIGN.CENTER,
             anchor=MSO_ANCHOR.MIDDLE)
        if rest:
            text(s, 0.9 + bw + 0.25, 0.42, 10, 0.58, rest, size=21, color=RED, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    else:
        text(s, 0.9, 0.62, 12, 0.4, kicker, size=17, color=RED, bold=True)
    text(s, 0.9, 1.08, 16.2, 0.9, title, size=title_size, color=INK, bold=True, spacing=1.1)
    if sub:
        text(s, 0.9, 2.12, 17.5, 0.5, sub, size=21, color=MUTED)
    logo(s)
    rect(s, 0.9, H - 0.62, W - 1.8, 0.012, LINE)
    text(s, 0.9, H - 0.5, 10, 0.3, '老约翰 · 2026.10 宣讲会', size=12, color=MUTED)
    text(s, W - 2.9, H - 0.5, 2, 0.3, f'{PAGE[0]:02d}', size=12, color=MUTED, bold=True, align=PP_ALIGN.RIGHT)
    return s


def divider(num, label, title, desc, steps=None):
    s = prs.slides.add_slide(BLANK)
    bg(s, INK)
    logo(s, dark=True)
    text(s, 0.9, 1.3, 9, 3.4, num, size=230, color=RED, bold=True, spacing=0.9)
    text(s, 1.0, 5.0, 12, 0.5, label, size=24, color=PALE, bold=True)
    text(s, 1.0, 5.65, 17, 1.3, title, size=64, color=CARD, bold=True, spacing=1.05)
    text(s, 1.0, 7.1, 16, 0.6, desc, size=23, color=PALE)
    if steps:  # 本部分的进度条：已讲完的灰、当前的亮
        x = 1.0
        for name, state in steps:
            on = state == 'now'
            dot = rect(s, x, 8.62, 0.26, 0.26, RED if on else None, MSO_SHAPE.OVAL,
                       line=None if on else PALE)
            text(s, x + 0.45, 8.5, 5, 0.5, name + ('（已讲完）' if state == 'done' else ''),
                 size=21, color=CARD if on else PALE, bold=on)
            x += 6.2
    return s


# ---------- 1 封面 ----------
make_white_logo()
s = prs.slides.add_slide(BLANK)
bg(s, PAPER)
rect(s, 0, 0, 12.2, H, INK)
logo(s, dark=True, x=0.95, y=0.85, h=0.8)
rect(s, 1.0, 3.35, 0.9, 0.09, RED)
text(s, 1.0, 3.75, 10.5, 0.5, '2026.10 宣讲', size=26, color=PALE, bold=True)
text(s, 0.95, 4.45, 11, 1.8, '读写并重，正当其时', size=84, color=CARD, bold=True, spacing=1.0)
text(s, 1.0, 6.45, 10.5, 1.0, '新课标、新教材把阅读和写作推到台前，\n读书会与同步写作，两条线正当其时。',
     size=22, color=PALE, spacing=1.45)
for i, (n, a, b) in enumerate([('01', '新课程', '同步写作正式发布'),
                               ('02', '新计划', '总部近期重点工作'),
                               ('03', '新变化', '小学语文教育与市场变化')]):
    y = 2.1 + i * 2.55
    text(s, 13.2, y, 2, 1.2, n, size=66, color=RED, bold=True, spacing=1.0)
    text(s, 15.3, y + 0.12, 4.2, 0.5, a, size=19, color=MUTED, bold=True)
    text(s, 15.3, y + 0.6, 4.4, 0.9, b, size=27, color=INK, bold=True, spacing=1.15)
    if i < 2:
        rect(s, 13.25, y + 1.9, 6.0, 0.012, LINE)
notes(s, '标题「读写并重，正当其时」：新课标新教材把阅读和写作推到台前，读书会与同步写作两条课程线正赶上这一轮。'
         '“读写并重”取自新教材解读的总结口径（阅读为本、读写并重、文化为魂）。')

# ---------- 2 目录 ----------
s = content('今天的安排', '今天讲三件事')
items = [('01', '同步写作正式发布', '课程定位、写作教学方法、课堂上法、课程文件与批改、用法。'),
         ('02', '总部近期重点工作', '上半：后续开发任务\n下半：自媒体运营思路'),
         ('03', '小学语文教育与市场变化', '新课标、新教材的重点，以及为什么这对读写机构是结构性利好。')]
for i, (n, t, d) in enumerate(items):
    x = 0.9 + i * 6.15
    rect(s, x, 2.75, 5.75, 6.95, CARD, line=LINE)
    rect(s, x, 2.75, 5.75, 0.12, RED if i == 0 else INK)
    text(s, x + 0.55, 3.35, 3, 1.2, n, size=64, color=RED if i == 0 else INK, bold=True, spacing=1.0)
    text(s, x + 0.55, 4.85, 4.8, 1.3, t, size=31, color=INK, bold=True, spacing=1.15)
    text(s, x + 0.55, 6.35, 4.75, 2.0, d, size=20, color=MUTED, spacing=1.5)
    if i == 0:
        button(s, x + 0.55, 8.55, 4.65, 0.72, '进入同步写作课程介绍  →', RED, CARD)
notes(s, '第一部分点左侧卡片里的按钮进入完整介绍，讲完按 Esc 回到这一页，再讲第二、三部分。')

# ---------- 3 第一部分 ----------
s = divider('01', '第一部分', '同步写作正式发布', '课程定位、写作教学方法、课堂上法、课程文件与批改、用法。')
button(s, 1.0, 8.4, 5.6, 0.85, '进入同步写作课程介绍  →', CARD, INK)
notes(s, '点下方按钮进入《同步写作课程完整介绍》放映，讲完按 Esc 回到这一页，接着讲第二部分。'
         '两份文件要放在同一个文件夹里，按钮才打得开。')

# ---------- 4 第二部分 ----------
s = divider('02', '第二部分', '总部近期重点工作', '分上下两半：先讲后续开发任务，再讲自媒体运营思路。',
            steps=[('后续开发任务', 'now'), ('自媒体运营思路', 'next')])
notes(s, '第二部分讲总部下一阶段的两项重点工作：后续开发与自媒体运营。先讲开发。')

# ---------- 5 开发总览 ----------
s = content('后续开发 · 总览', '下一阶段开发：四项任务', '按推进顺序排列，后面逐项展开。')
dirs = [('任务一', '同步写作后续单元', '跟着更新后的统编教材，完成后续单元课案', '春季教材 12 月后定稿'),
        ('任务二', '低段快乐读书吧', '一至三年级快乐读书吧，共 10 本书', '11 月左右完成'),
        ('任务三', '整套看图写话', '补上一、二年级，写作课贯通一至六年级', '已规划，开发中'),
        ('任务四', '读书会课件迭代', '买不到的书、难上的课，按反馈做替换', '不定期')]
for i, (k, t, d, when) in enumerate(dirs):
    x = 0.9 + i * 4.62
    rect(s, x, 2.95, 4.32, 3.95, CARD, line=LINE)
    text(s, x + 0.4, 3.3, 3.5, 0.4, k, size=18, color=RED, bold=True)
    text(s, x + 0.4, 3.8, 3.6, 0.6, t, size=27, color=INK, bold=True)
    text(s, x + 0.4, 4.6, 3.55, 1.3, d, size=19, color=TEXT, spacing=1.45)
    pill = rect(s, x + 0.4, 6.0, 3.5, 0.55, SAND, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
    text(s, x + 0.4, 6.0, 3.5, 0.55, when, size=17, color=INK, bold=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
rect(s, 0.9, 7.25, W - 1.8, 2.95, INK)
text(s, 1.4, 7.55, 17, 0.5, '后续设想', size=24, color=CARD, bold=True)
text(s, 1.4, 8.3, 8.2, 1.4, [[('小古文　', {'color': CARD, 'bold': True}),
                              ('统编教材从三年级起选入文言文，孩子初读常卡在读不顺、读不懂。可围绕教材篇目和同类短文，练朗读、断句和理解，打好文言基础。', {})]],
     size=18, color=PALE, spacing=1.45)
text(s, 10.3, 8.3, 8.4, 1.4, [[('主题阅读　', {'color': CARD, 'bold': True}),
                               ('寒暑假安排连续几天，只读一本大部头，如《苏东坡传》、四大名著、《儒林外史》等。平时课时读不完的经典，用一整段时间读透。', {})]],
     size=18, color=PALE, spacing=1.45)
notes(s, '先用一页把四件事和时间讲清，后面逐项展开。已定的时间：低段快乐读书吧 11 月左右完成；'
         '同步写作春季用的新教材预计 12 月出来，出来后做最后一轮更新。'
         '底部两类课程还没有立项，讲清方向和价值即可，不承诺时间，可以现场请伙伴们说说自己加盟馆的需求。')

# ---------- 6 任务一 ----------
s = content('开发任务一', '同步写作后续单元：跟着新教材走')
rect(s, 0.9, 3.35, 0.1, 3.75, RED)
text(s, 1.55, 3.2, 17.0, 6.0, [[
    ('2026 年秋起，统编教材四、五、六年级换用新版，春季用的下册新教材预计 12 月出来。', {}),
    ('总部按新版教材逐单元核对课文、语文要素与习作题目，新教材换了题目的单元，按新题开发。', {}),
    ('教材版次调整由总部统一核对修订、推送更新。', {'color': RED, 'bold': True})]],
    size=32, color=TEXT, spacing=1.75)
notes(s, '重点说清楚两件事：秋季班已按新教材走；春季班要等 12 月新教材出来再做最后更新，'
         '加盟馆拿到的始终是对应新教材的版本。')

# ---------- 7 任务二 ----------
s = content('开发任务二', '低段快乐读书吧：一至三年级 10 本书，11 月左右完成',
            '完成一至三年级快乐读书吧的剩余全部书目，按读书会深度阅读课的标准开发。', title_size=38)
grades = [('一年级', '4 本', ['《和大人一起读（一）》', '《和大人一起读（二）》', '《和大人一起读（三）》', '《和大人一起读（四）》']),
          ('二年级', '4 本', ['《孤独的小螃蟹》', '《小狗的小房子》', '《神笔马良》', '《大头儿子和小头爸爸》']),
          ('三年级', '2 本', ['《稻草人》', '《克雷洛夫寓言》'])]
for i, (g, n, books) in enumerate(grades):
    x = 0.9 + i * 6.15
    rect(s, x, 2.95, 5.75, 5.0, CARD, line=LINE)
    rect(s, x, 2.95, 5.75, 1.15, INK)
    text(s, x + 0.45, 2.95, 3, 1.15, g, size=28, color=CARD, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 2.8, 2.95, 2.5, 1.15, n, size=28, color=RED, bold=True, anchor=MSO_ANCHOR.MIDDLE,
         align=PP_ALIGN.RIGHT)
    text(s, x + 0.45, 4.45, 5.0, 3.3, '\n'.join(books), size=23, color=TEXT, spacing=1.6)
rect(s, 0.9, 8.3, W - 1.8, 1.9, SAND)
rect(s, 0.9, 8.3, 0.1, 1.9, RED)
text(s, 1.45, 8.55, 3, 0.5, '怎么用', size=24, color=RED, bold=True)
text(s, 1.45, 9.15, 17, 0.8, '与同步写作组合排课：每学期 16 次课，8 次同步写作、8 次快乐读书吧，均依据统编教材。',
     size=23, color=INK)
notes(s, '一至三年级快乐读书吧共 10 本：一年级《和大人一起读》四册，二年级四本，三年级两本。'
         '组合排课的方式在完整介绍的「三种用法」里讲过。')

# ---------- 8 看图写话 · 补上一二年级 ----------
s = content('开发任务三 · 整套看图写话', '补上一二年级，写作课贯通一至六年级')
GRADES = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级']
GW = (W - 1.8 - 5 * 0.08) / 6
for g, name in enumerate(GRADES):
    gx = 0.9 + g * (GW + 0.08)
    rect(s, gx, 2.45, GW, 0.62, SAND)
    text(s, gx, 2.45, GW, 0.62, name, size=19, color=INK, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
for g0, g1, label, col in [(0, 1, '看图写话 · 这次补上', RED), (2, 5, '同步写作 · 已上线', INK)]:
    gx = 0.9 + g0 * (GW + 0.08)
    gw = (g1 - g0 + 1) * GW + (g1 - g0) * 0.08
    rect(s, gx, 3.15, gw, 0.85, col)
    text(s, gx, 3.15, gw, 0.85, label, size=24, color=CARD, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, 0.9, 4.3, 18.2, 1.1, [[('同步写作从三年级起步，而一二年级正是孩子第一次拿笔写话的时候。', {}),
                              ('补上看图写话，写作课就从一年级贯通到六年级——同一套能力线，一级一级往上走。', {'color': RED, 'bold': True})]],
     size=21, color=TEXT, spacing=1.5)
stages = [('第一阶 · 一年级', '说清楚，写完整', '看懂一幅图，大方讲清楚，写出完整通顺的一两句话。', INK,
           ['会看图会讲图', '写完整的一句话', '把句子写“胖”', '标点会说话']),
          ('第二阶 · 二年级', '写连贯，讲成故事', '把一组图写成有细节、有波澜的小故事。', RED,
           ['把画面写具体', '四图连成故事', '故事有“没想到”', '句子会“变身”'])]
for i, (k, t, d, col, ms) in enumerate(stages):
    x = 0.9 + i * 9.25
    rect(s, x, 5.65, 8.85, 3.45, CARD, line=LINE)
    rect(s, x, 5.65, 8.85, 1.0, col)
    text(s, x + 0.5, 5.65, 8, 1.0, [[(k + '　', {'size': 18, 'color': CARD if col == INK else TINT}),
                                     (t, {'size': 28})]], color=CARD, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, x + 0.5, 6.85, 7.9, 0.5, d, size=18, color=TEXT)
    for j, a in enumerate(ms):
        cx, cy = x + 0.5 + (j % 2) * 4.0, 7.45 + (j // 2) * 0.82
        rect(s, cx, cy, 3.8, 0.7, PAPER)
        text(s, cx + 0.3, cy, 3.4, 0.7, a, size=19, color=col, bold=True, anchor=MSO_ANCHOR.MIDDLE)
rect(s, 0.9, 9.35, W - 1.8, 0.85, SAND)
for j, (n, u) in enumerate([('4', '个学期'), ('64', '次课'), ('24', '个方法主题'), ('5', '条能力线')]):
    text(s, 1.4 + j * 4.5, 9.35, 4.3, 0.85, [[(n, {'size': 32, 'color': RED}), ('  ' + u, {'size': 20, 'color': INK})]],
         bold=True, anchor=MSO_ANCHOR.MIDDLE)
notes(s, '先讲为什么要做看图写话：同步写作从三年级开始，一二年级是空着的。补上这两年，'
         '写作课就是一至六年级一条线，孩子从一年级进来可以一直学到六年级。'
         '看图写话是全六阶写作体系的第一、二阶：一年级重点是敢说敢写、不怕动笔，二年级开始像小作家一样讲故事。'
         '每学期 16 次课，四个学期共 64 次，每次课两节连排 90 分钟。')

# ---------- 9 看图写话 · 接上三年级 ----------
s = content('开发任务三 · 整套看图写话', '一二年级练的本领，三年级写作文直接用上',
            '看图写话不是单独一门课：它的四条能力线，一条条接进三年级同步写作的单元习作。')
text(s, 3.35, 2.85, 10, 0.4, '看图写话 · 一二年级', size=17, color=RED, bold=True)
text(s, 14.0, 2.85, 5.1, 0.4, '同步写作 · 三年级接上', size=17, color=INK, bold=True)
lines = [('会观察', ['看懂图', '写清楚一句话', '抓住细节', '有顺序地看'], '《我们眼中的缤纷世界》'),
         ('会讲故事', ['讲清一件事', '前因后果', '完整情节', '写出波澜'], '《那次玩得真高兴》'),
         ('会想象', ['补对话', '写心里话', '补全情节', '写出新故事'], '《续写故事》《我来编童话》'),
         ('会用词', ['标点语气', '叠词拟声', '比喻拟人', '好词入句'], '《这儿真美》')]
for i, (name, steps, tgt) in enumerate(lines):
    y = 3.35 + i * 1.3
    rect(s, 0.9, y, 2.2, 1.0, RED, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.15)
    text(s, 0.9, y, 2.2, 1.0, name, size=22, color=CARD, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    for j, st in enumerate(steps):
        x = 3.35 + j * 2.6
        rect(s, x, y + 0.08, 2.15, 0.84, CARD, line=LINE)
        text(s, x, y + 0.08, 2.15, 0.84, st, size=18, color=TEXT, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
        if j < 3:
            text(s, x + 2.15, y + 0.08, 0.45, 0.84, '›', size=28, color=RED, bold=True,
                 align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 13.72, y + 0.08, 0.3, 0.84, '→', size=24, color=RED, bold=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE)
    rect(s, 14.0, y + 0.08, 5.1, 0.84, INK)
    text(s, 14.25, y + 0.08, 4.7, 0.84, tgt, size=18, color=CARD, bold=True, anchor=MSO_ANCHOR.MIDDLE)
rect(s, 0.9, 8.75, W - 1.8, 1.45, SAND)
rect(s, 0.9, 8.75, 0.1, 1.45, RED)
text(s, 1.5, 8.85, 17.4, 0.6, '一年级进来，同一套能力线、同一套教法，一路写到六年级。', size=24, color=INK, bold=True)
text(s, 1.5, 9.5, 17.4, 0.5, '中途加入也接得上：入班前有小测评和衔接课，把前面的关键方法补齐，再并入当前进度。',
     size=18, color=MUTED)
notes(s, '这一页讲衔接：左边是看图写话两年练的四条能力线，右边是三年级同步写作里直接接上的单元习作。'
         '对加盟馆来说，一二年级的学员升到三年级，可以自然转进同步写作，不用重新招生。')

# ---------- 12 任务四 ----------
s = content('开发任务四', '读书会课件迭代：买不到的书、难上的课，做替换',
            '按加盟商在使用中的反馈，替换原有读书会课程里的两类，改过的版本统一推送更新。', title_size=38)
cards = [('买不到的书', '书已绝版或长期断货。', '换成主题相近、买得到的书'),
         ('难上的课', '老师讲起来吃力、学生接不住，课堂效果打折扣。', '换成更好上的书目与课案')]
for i, (t, why, how) in enumerate(cards):
    x = 0.9 + i * 9.25
    rect(s, x, 2.95, 8.85, 5.55, CARD, line=LINE)
    rect(s, x, 2.95, 0.14, 5.55, RED if i == 0 else INK)
    text(s, x + 0.7, 3.4, 7.8, 0.8, t, size=40, color=RED if i == 0 else INK, bold=True)
    text(s, x + 0.7, 4.55, 7.6, 1.5, why, size=23, color=TEXT, spacing=1.55)
    rect(s, x + 0.7, 6.45, 7.5, 1.35, PAPER)
    text(s, x + 1.0, 6.45, 7.0, 1.35, [[('替换　', {'color': RED, 'bold': True}), (how, {'bold': True})]],
         size=24, color=INK, anchor=MSO_ANCHOR.MIDDLE)
notes(s, '这一项是改已有的，不是新开发。可以现场请伙伴们报一报：哪些书在本地买不到、哪些课上起来难。')

# ---------- 课程体系全景 ----------
s = content('开发计划讲完 · 看全貌', '一至六年级，阅读课、写作课都已完整')
GRADES = ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级']
X0, GW = 4.3, (W - 0.9 - 4.3 - 5 * 0.08) / 6


def span(g0, g1, y, h, label, fill, color=CARD, dash=False, size=22):
    gx = X0 + g0 * (GW + 0.08)
    gw = (g1 - g0 + 1) * GW + (g1 - g0) * 0.08
    b = rect(s, gx, y, gw, h, fill, line=RED if dash else None)
    if dash:
        b.line.dash_style = MSO_LINE.DASH
        b.line.width = Pt(2)
    text(s, gx + 0.2, y, gw - 0.4, h, label, size=size, color=color, bold=True, align=PP_ALIGN.CENTER,
         anchor=MSO_ANCHOR.MIDDLE, spacing=1.25)


for g, name in enumerate(GRADES):
    gx = X0 + g * (GW + 0.08)
    rect(s, gx, 2.45, GW, 0.62, SAND)
    text(s, gx, 2.45, GW, 0.62, name, size=19, color=INK, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
rows = [('阅读课', '早几年推出', 3.3), ('写作课', '一至六年级贯通', 4.95), ('后续设想', '让体系更完善', 6.6)]
for name, sub, y in rows:
    text(s, 0.9, y, 3.2, 0.9, name, size=28, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
    text(s, 0.9, y + 0.85, 3.2, 0.5, sub, size=16, color=MUTED)
span(0, 5, 3.3, 1.4, [[('读书会深度阅读', {}), ('　整本书阅读，一至六年级全覆盖', {'size': 18, 'color': PALE})]], INK, size=26)
span(0, 1, 4.95, 1.4, [[('看图写话', {})], [('一、二年级', {'size': 17, 'color': TINT})]], RED, size=26)
span(2, 5, 4.95, 1.4, [[('同步写作', {}), ('　三至六年级，跟着统编教材单元走', {'size': 18, 'color': PALE})]], INK, size=26)
half = 2
span(0, half, 6.6, 1.4, [[('小古文', {})], [('从教材文言篇目起步，练朗读、断句、理解', {'size': 16, 'color': MUTED})]],
     CARD, color=RED, dash=True, size=24)
span(half + 1, 5, 6.6, 1.4, [[('主题阅读', {})], [('寒暑假集中几天，精读一本大部头', {'size': 16, 'color': MUTED})]],
     CARD, color=RED, dash=True, size=24)
rect(s, 0.9, 8.55, W - 1.8, 1.65, INK)
text(s, 1.5, 8.55, 17.4, 1.65, [[('阅读课、写作课，一至六年级都已贯通；', {}),
                                ('再加上小古文和主题阅读，就是一套完整的读写课程体系。', {'color': RGBColor(0xF2, 0x8B, 0x7F)})]],
     size=25, color=CARD, bold=True, anchor=MSO_ANCHOR.MIDDLE, spacing=1.4)
notes(s, '开发计划讲完，用这一页收一下：公司之前已有一至六年级的读书会阅读课；写作课这边，'
         '三至六年级同步写作已上线，一二年级看图写话补上之后，一至六年级的写作课也完整了。'
         '也就是说，阅读、写作两条线一至六年级都已完整。后续再加上小古文、寒暑假主题阅读，'
         '就是一个很完善的课程体系。虚线框是后续设想，还没有排期。')

# ---------- 13 分隔：自媒体 ----------
s = divider('02', '第二部分 · 下半', '自媒体运营思路', '开发计划讲完，接下来讲宣传：先看现状，再定思路，最后落到总部与加盟馆各做什么。',
            steps=[('后续开发任务', 'done'), ('自媒体运营思路', 'now')])
notes(s, '开发计划到这里讲完。下面换一个话题，讲自媒体运营。')

# ---------- 14 现状 ----------
s = content('自媒体运营 · 现状', '先看现状：我们和同行', '做法之前，先把现状看清楚。')
cols = [('总部目前', INK, '【待填：已有账号与平台、主要内容、更新频率、关注与互动情况】'),
        ('同行现状', RED, '不少同行把直播当作主要的引流手段：直播公开课、直播带课，再配合短视频投放。\n'
                        '这种做法要有稳定的主播、持续的投放和专门的运营团队。【待填：总部掌握的具体情况】')]
for i, (t, col, d) in enumerate(cols):
    x = 0.9 + i * 9.25
    rect(s, x, 2.95, 8.85, 5.1, CARD, line=LINE)
    rect(s, x, 2.95, 8.85, 0.12, col)
    text(s, x + 0.6, 3.4, 7, 0.6, t, size=30, color=col, bold=True)
    text(s, x + 0.6, 4.35, 7.7, 3.5, d, size=21, color=TEXT, spacing=1.55, after=10)
rect(s, 0.9, 8.45, W - 1.8, 1.4, SAND)
rect(s, 0.9, 8.45, 0.1, 1.4, RED)
text(s, 1.5, 8.45, 17, 1.4, '同行做得热闹，不等于适合我们。关键看投入和回报。', size=26, color=INK, bold=True,
     anchor=MSO_ANCHOR.MIDDLE)
notes(s, '左边总部现状由总部补数据；右边同行现状是总体情况，具体例子现场可以补充。')

# ---------- 15 思路 ----------
s = content('自媒体运营 · 思路', '以做好内容为主，做好服务、做好口碑', title_size=46)
for i, (t, col) in enumerate([('内容', RED), ('服务', INK), ('口碑', INK)]):
    x = 0.9 + i * 3.3
    rect(s, x, 3.0, 2.9, 2.9, col, MSO_SHAPE.OVAL)
    text(s, x, 3.0, 2.9, 2.9, t, size=44, color=CARD, bold=True, align=PP_ALIGN.CENTER, anchor=MSO_ANCHOR.MIDDLE)
text(s, 11.2, 3.0, 7.9, 3.2, '总部目前不具备做直播引流的条件，投入大、性价比不高，现阶段不做。', size=26, color=INK,
     bold=True, spacing=1.5, anchor=MSO_ANCHOR.MIDDLE)
rect(s, 0.9, 6.6, W - 1.8, 0.012, LINE)
text(s, 0.9, 7.0, 18.2, 2.5, '把力气放在内容上：读书会深度阅读课、同步写作课本身做扎实，每次课后的服务做到位，家长认可了，口碑自然会传开。',
     size=27, color=TEXT, spacing=1.6)
notes(s, '这一页是本节的核心，讲慢一点。直播不做，不是不重视宣传，是现阶段性价比不高。')

# ---------- 16 落点 ----------
s = content('自媒体运营 · 落点', '内容、服务、口碑，分别落在哪里', '总部出内容，加盟馆在本地用好；读书会与同步写作两条课程线都覆盖。')
land = [('做好内容', '读书会、同步写作两条课程线都做扎实。'),
        ('做好服务', '每次课后有东西交到家长手上：读书会有阅读单与课后反馈，写作课有孩子的成稿、点评卡、家长一页纸。'),
        ('做好口碑', '家长看到孩子读得更深、写得更好，愿意向身边人推荐。'),
        ('总部与加盟馆', '总部为两条课程线统一出品素材，加盟馆在本地家长群与账号使用。')]
for i, (t, d) in enumerate(land):
    x, y = 0.9 + (i % 2) * 9.25, 2.9 + (i // 2) * 3.1
    rect(s, x, y, 8.85, 2.75, CARD, line=LINE)
    text(s, x + 0.6, y + 0.4, 3, 0.4, f'0{i + 1}', size=20, color=RED, bold=True)
    text(s, x + 1.5, y + 0.3, 6.5, 0.6, t, size=28, color=INK, bold=True)
    text(s, x + 1.5, y + 1.1, 7.0, 1.5, d, size=20, color=TEXT, spacing=1.5)
pill = rect(s, 0.9, 9.3, 5.0, 0.7, INK, MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.5)
text(s, 0.9, 9.3, 5.0, 0.7, '直播引流：现阶段不做', size=20, color=CARD, bold=True, align=PP_ALIGN.CENTER,
     anchor=MSO_ANCHOR.MIDDLE)
notes(s, '四块都要把读书会和同步写作一起说到，不只讲写作课。写作课海报和宣传短视频的样例在完整介绍的「招生支持」一页；读书会的书目卡、海报、阅读单沿用已有做法。')

# ---------- 第三部分 ----------
s = divider('03', '第三部分', '小学语文教育与市场变化', '新课标、新教材把阅读和写作推到台前——对我们这类读写机构，是结构性利好。')
notes(s, '第三部分先讲课标和教材怎么变，再讲变化落在阅读和写作上，最后讲为什么这是我们的机会、要做好哪三件事。')

# ---------- 课标与教材 ----------
s = content('课标与教材', '这几年，小学语文发生了什么', '课标先更新，教材跟着换，最后落到每一个单元的课堂上。')
tl = [('2022 年', '《义务教育语文课程标准（2022 年版）》颁布'), ('2024 年秋起', '统编教材依据新课标修订，一年级率先启用，逐年换新'),
      ('2026 年秋', '四、五、六年级换用新教材，义务教育全学段完成替换'), ('接下来', '下册新版目录待发布，四至六年级下册已确定多个单元有变')]
rect(s, 1.3, 4.05, 17.4, 0.06, LINE)
for i, (t, d) in enumerate(tl):
    x = 0.9 + i * 4.62
    last = i == 3  # 末项尚未发生，空心点
    rect(s, x + 0.2, 3.83, 0.5, 0.5, CARD if last else RED, MSO_SHAPE.OVAL, line=RED if last else None)
    text(s, x, 4.75, 4.2, 0.7, t, size=32, color=RED if not last else MUTED, bold=True)
    text(s, x, 5.6, 4.35, 2.2, d, size=21, color=TEXT, spacing=1.5)
rect(s, 0.9, 8.45, W - 1.8, 1.4, INK)
text(s, 1.5, 8.45, 17, 1.4, '统编教材使用以来的首次大修：不是换几篇课文，而是单元、篇目、习作与学习任务的系统调整。',
     size=24, color=CARD, bold=True, anchor=MSO_ANCHOR.MIDDLE)
notes(s, '这一页只讲事实脉络，不展开评论。依据是《四至六年级教材换新全面梳理》（0907）：'
         '此次修订经 550 多所学校、10 万余名学生试教试用；下册以出版社正式发布为准。')

# ---------- 新教材的重点 ----------
s = content('新教材的方向', '新教材的重点，落在阅读和写作上', '这一轮改版的几条趋势，几乎都指向读和写。')
trends = [('阅读地位提升', '整本书阅读要求提高，快乐读书吧分量加重；高年级更多训练信息整合、逻辑和思辨。'),
          ('习作回到真实表达', '多个习作换题或移位，新题贴近真实生活，套模板、背范文的收益在下降。'),
          ('传统文化加强', '新建“中国的世界文化遗产”单元，文言文篇目调整，从孩子熟悉的故事入门。'),
          ('科学与想象', '航天、科技题材进入课本，科普与说明性文本应当纳入课外阅读。')]
for i, (t, d) in enumerate(trends):
    x = 0.9 + i * 4.62
    rect(s, x, 2.95, 4.32, 5.05, CARD, line=LINE)
    rect(s, x, 2.95, 4.32, 0.12, RED if i < 2 else INK)
    text(s, x + 0.4, 3.35, 3.5, 0.6, f'0{i + 1}', size=30, color=RED if i < 2 else INK, bold=True)
    text(s, x + 0.4, 4.1, 3.6, 0.6, t, size=25, color=INK, bold=True)
    text(s, x + 0.4, 4.95, 3.55, 2.9, d, size=19, color=TEXT, spacing=1.55)
rect(s, 0.9, 8.45, W - 1.8, 1.4, INK)
text(s, 1.5, 8.45, 17, 1.4, [[('从“教课文”走向“育素养”：', {'color': PALE}), ('阅读为本、读写并重、文化为魂。', {})]],
     size=26, color=CARD, bold=True, anchor=MSO_ANCHOR.MIDDLE)
notes(s, '前两条（阅读、写作）标红，是和我们两条课程线直接相关的；后两条是阅读面的拓宽。'
         '口径与《四至六年级教材换新全面梳理》的「五大改版趋势」一致。')

# ---------- 结构性利好 ----------
s = content('对我们意味着什么', '对我们这类读写机构，这是结构性利好')
goods = [('读书会深度阅读', '整本书阅读被推到台前', '整本书阅读要求提高、快乐读书吧持续强化，读书会与教材导向正面重合，这是“为什么要上阅读课”最有力的官方依据。'),
         ('同步写作', '习作跟着新教材重排', '新题没有历年范文可背，写真实的事、真实的感受才拉得开差距；跟着单元、当堂写成一篇，正对这个需求。'),
         ('后续课程', '文言文与传统文化需求上升', '文言篇目调整、世界文化遗产单元新建，小古文、文化主题读写有了明确的教材抓手。'),
         ('竞品格局', '素养导向下，竞品在分化', '机械刷题类产品与新教材的错位越来越明显，以读促写、素养培养类机构的价值相应提升。')]
for i, (tag, t, d) in enumerate(goods):
    x, y = 0.9 + (i % 2) * 9.25, 2.45 + (i // 2) * 3.2
    rect(s, x, y, 8.85, 2.95, CARD, line=LINE)
    rect(s, x, y, 0.14, 2.95, RED if i < 2 else INK)
    text(s, x + 0.6, y + 0.3, 7.8, 0.4, tag, size=17, color=RED if i < 2 else MUTED, bold=True)
    text(s, x + 0.6, y + 0.72, 7.8, 0.6, t, size=27, color=INK, bold=True)
    text(s, x + 0.6, y + 1.45, 7.85, 1.4, d, size=18, color=TEXT, spacing=1.5)
rect(s, 0.9, 9.0, W - 1.8, 1.2, SAND)
rect(s, 0.9, 9.0, 0.1, 1.2, RED)
text(s, 1.5, 9.0, 17.4, 1.2, '对外表达从“补差提分”转向“与新教材同频的读写素养培养”，用教材变化本身说明课程的价值。',
     size=21, color=INK, bold=True, anchor=MSO_ANCHOR.MIDDLE)
notes(s, '这一页是第三部分的核心：新课标新教材要的，正是我们一直在做的读和写。'
         '读书会是早几年就推出的产品，这一轮改版等于给它补上了官方依据；同步写作则正好接住习作换新。')


# ---------- 家长需求 ----------
def statement(kicker, head, body):
    s = content(kicker, '')
    text(s, 0.9, 3.1, 18, 1.4, head, size=50, color=INK, bold=True, spacing=1.15)
    rect(s, 0.9, 4.85, 1.2, 0.09, RED)
    text(s, 0.9, 5.4, 17.6, 3.8, body, size=27, color=TEXT, spacing=1.65)
    return s


s = statement('家长需求', '家长要的，是读得深、写得出',
              '只读节选、只做题的方式，已经跟不上新教材。家长开始关心：孩子能不能读完、读透一本书，读到的东西能不能变成自己笔下的文字。'
              '在校内习作与升学压力之下，单元习作与作文仍是最直接的衡量标准。')
notes(s, '阅读和写作两头都要讲：读书会回应「读得深」，同步写作回应「写得出」。')

# ---------- 三件事 ----------
s = content('对我们意味着什么', '变化之下，我们要做好的三件事')
three = [('招生', '读书会和同步写作都能在新教材里找到依据：整本书阅读、单元习作，家长一听就懂'),
         ('推广', '从“补差提分”转向“与新教材同频的读写素养”，用教材变化说明课程价值'),
         ('教学', '读书会读透一本书，同步写作当堂写好一篇，两条线都跟着新教材走')]
for i, (t, d) in enumerate(three):
    x = 0.9 + i * 6.15
    rect(s, x, 3.0, 5.75, 6.3, INK if i == 0 else CARD, line=None if i == 0 else LINE)
    text(s, x + 0.55, 3.45, 3, 1.6, str(i + 1), size=96, color=RED, bold=True, spacing=1.0)
    text(s, x + 0.55, 5.3, 4.8, 0.8, t, size=40, color=CARD if i == 0 else INK, bold=True)
    rect(s, x + 0.55, 6.3, 0.8, 0.07, RED)
    text(s, x + 0.55, 6.7, 4.7, 2.4, d, size=24, color=PALE if i == 0 else TEXT, spacing=1.6)
notes(s, '这三条是已有口径；总部如有进一步判断，可以在这里补充。讲完直接进收尾。')

# ---------- 22 封底 ----------
s = prs.slides.add_slide(BLANK)
bg(s, INK)
lw = 5.2
s.shapes.add_picture(LOGO_WHITE, Inches((W - lw) / 2), Inches(3.0), width=Inches(lw))
rect(s, W / 2 - 0.5, 5.35, 1.0, 0.08, RED)
text(s, 0, 5.85, W, 0.8, '读写并重，正当其时', size=40, color=CARD, bold=True, align=PP_ALIGN.CENTER)
text(s, 0, 6.85, W, 0.6, '阅读 · 思辨 · 表达', size=24, color=PALE, align=PP_ALIGN.CENTER)
text(s, 0, 8.6, W, 0.6, '谢谢各位伙伴', size=24, color=PALE, align=PP_ALIGN.CENTER)

prs.save(OUT)
os.remove(LOGO_WHITE)
print('saved', len(prs.slides), 'slides ->', os.path.abspath(OUT))
