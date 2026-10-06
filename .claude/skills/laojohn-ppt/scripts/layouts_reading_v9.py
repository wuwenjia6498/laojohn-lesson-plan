# -*- coding: utf-8 -*-
"""读书会 profile · v9 新样式（按书主题色 + 图感知版式）。

只在中间稿元信息声明了 `主题色：<色名>` 时启用；不声明时 layouts_reading 原样走现行版式，
存量书重烘逐形状不变。样式来源＝用户 2026-10 对三本书 12 份课件的人工优化版：

- 一本书一个主题色：眉标色块 / 分节页底 / 编号方块 / 表头 / 封面三角 / 答案字色都取色板；
  红色只留给 LOGO 与标题关键词。
- 内容页一张大图：抠图（带透明通道）贴右下出血、底边落在页底（有依托不飘）；
  场景图（矩形）等比放右栏、圆角。分节页 / 表格页 / END 不放图。
- 引导问题 / 要点小结：去红竖条，标题下铺通栏浅色底带，主题色方块编号，
  问题与答案各自独立文本框（答案＝主题色深色档）。
- 原文齐读：楷体；有图时书页底收窄让出右栏。
- 缺图不画虚线占位框，直接按无图（全宽）版式出；缺图清单由 build_ppt 汇报。
- 文字放不下时先降字号，降到下限仍放不下就放弃配图、改全宽（宁可无图不溢出）。

签名与 layouts_reading 一致外加 th（theme.ReadingTheme）：render_<type>(slide, page, ctx, th)。
"""
import math

from pptx.enum.shapes import MSO_SHAPE
from pptx.util import Emu, Pt

from helpers import (
    add_textbox, add_rich_textbox, add_rect, add_picture_fit, image_has_alpha,
    add_image_cover,
    add_click_reveal, add_logo, rgb, set_ascii_font, _disable_shape_effects,
)
from theme import (
    FONT_TITLE, FONT_BODY, FONT_QUOTE_V9,
    COLOR_TITLE, COLOR_BODY, COLOR_RED_ACCENT, COLOR_BG_QUOTE,
    SLIDE_W, SLIDE_H,
    LOGO_INNER_X, LOGO_INNER_Y, LOGO_INNER_W,
    pct_x, pct_y,
)
from layouts_common import (
    draw_anchor, draw_logo_inner, resolve_image,
    _real_suggestions, _split_title_keywords, _render_cover_base,
)

_EMU_PER_PT = 12700.0

# ---------- 版面几何（占页宽/页高比例）----------
TITLE_Y, TITLE_H = 0.200, 0.140
BAND_Y, BAND_B = 0.365, 0.945          # 通栏底带上下沿
BODY_X = 0.07
BODY_Y = 0.400                          # 底带内正文起点
BODY_B = 0.920                          # 正文下限
COL_W_IMG = 0.50                        # 有图时文字栏宽
COL_W_FULL = 0.86                       # 无图时文字栏宽
# 抠图：右下贴页边出血；场景图：右栏等比圆角
CUT_BOX = (0.585, 0.215, 0.415, 0.785)
SCENE_BOX = (0.605, 0.395, 0.355, 0.510)

Q_LADDER = (24, 22, 20, 18)             # 问题字号梯；答案比问题小 2pt
MIN_SIZE_WITH_IMAGE = 18


def _P(v):
    return Emu(int(v))


def _theme_ctx(slide, page, ctx, th):
    draw_anchor(slide, page.eyebrow, bar_color=th.main)
    draw_logo_inner(slide, ctx.get("logo_path"))


def _title(slide, text, x=BODY_X, w=0.86, size=30):
    if not text:
        return None
    segs = [(t, {"color": COLOR_RED_ACCENT if kw else COLOR_TITLE, "bold": True})
            for t, kw in _split_title_keywords(text)]
    if len(text) > 30:
        size -= 2
    return add_rich_textbox(slide, pct_x(x), pct_y(TITLE_Y), pct_x(w), pct_y(TITLE_H),
                            segs, font=FONT_TITLE, size=size,
                            align="left", anchor="middle", line_spacing=1.25)


def _band(slide, th, top=BAND_Y, bottom=BAND_B):
    r = add_rect(slide, 0, pct_y(top), SLIDE_W, pct_y(bottom - top), th.band)
    _disable_shape_effects(r)
    return r


def _page_image(page, ctx):
    """本页可用真图的绝对路径（无/不存在 → None）。"""
    p = resolve_image(ctx, getattr(page, "image_path", ""))
    import os
    return p if (p and os.path.isfile(p)) else None


def _place_image(slide, path, box=None, anchor=None, rounded=True):
    """按图的类型放图：抠图贴右下出血、场景图按 box 等比 contain（不裁切）。"""
    if image_has_alpha(path):
        x, y, w, h = box or CUT_BOX
        return add_picture_fit(slide, path, pct_x(x), pct_y(y), pct_x(w), pct_y(h),
                               anchor=anchor or "br")
    x, y, w, h = box or SCENE_BOX
    return add_picture_fit(slide, path, pct_x(x), pct_y(y), pct_x(w), pct_y(h),
                           anchor=anchor or "c", trim_alpha=False,
                           rounded=rounded, radius_frac=0.04)


# ---------- 构图轮换（2026-10-06/07 用户两轮反馈：底带页太统一、原书插图关在色块里局促；
# 底带不必都缩、位置不必统一、可穿插灰色）----------
# 底带四种形态：通栏（文字区）、标题横带（只衬标题，正文落白底）、短底带（只铺文字栏）、无底带
# （白底＋主题色竖线）；颜色在主题浅色与中性浅灰间穿插。
# · 场景图（矩形，含原书插图）：一律站在白底上、放大；奇数页在右（短主题色底带）、偶数页在左
#   （短灰底带）；横图在右侧贴右下出血。contain 不裁切——原书插图要让学生数东西、找细节。
# · 抠图：页码 mod 4 轮换「通栏主题色、人物站在底带上」/「标题横带」/「灰通栏、图在左」/「白底竖线」。
# · 无图问答页：页码 mod 4 轮换「通栏主题色」/「标题横带」/「灰通栏」/「白底竖线」。
# 按页码定而不按计数（build_ppt 每页新建 ctx、存不住状态）；相邻页余数必不同，不会重样。
LANDSCAPE_RATIO = 1.15
GRAY_BAND = "EFEFEF"
FULL = (0.0, 1.0, BAND_Y, BAND_B)          # 通栏底带 (x0, x1, y0, y1)
STRIP = (0.0, 1.0, 0.185, 0.365)           # 标题横带


def _aspect(path):
    from PIL import Image
    with Image.open(path) as im:
        w, h = im.size
    return w / float(h or 1)


def _lay(kind, band=None, gray=False, line=False, text_x=BODY_X, img_box=None,
         img_anchor=None, rounded=True, title_x=BODY_X, title_w=0.86):
    return dict(kind=kind, band=band, gray=gray, line=line, text_x=text_x, img_box=img_box,
                img_anchor=img_anchor, rounded=rounded, title_x=title_x, title_w=title_w)


def _layout_for(page, img):
    """返回本页构图（见上方注释）。img 为 None＝无图页。"""
    k = page.num % 4
    if img is None:
        return (_lay("band", band=FULL), _lay("strip", band=STRIP),
                _lay("gray", band=FULL, gray=True), _lay("line", line=True))[k]
    if image_has_alpha(img):
        if k == 0:
            return _lay("cut_band", band=FULL, img_box=CUT_BOX, img_anchor="br",
                        rounded=False, title_w=0.55)
        if k == 1:
            return _lay("cut_strip", band=STRIP, img_box=CUT_BOX, img_anchor="br",
                        rounded=False, title_w=0.55)
        if k == 2:
            return _lay("cut_left", band=FULL, gray=True, text_x=0.43,
                        img_box=(0.0, 0.38, 0.40, 0.62), img_anchor="bl", rounded=False)
        return _lay("cut_line", line=True, img_box=CUT_BOX, img_anchor="br",
                    rounded=False, title_w=0.55)
    land = _aspect(img) >= LANDSCAPE_RATIO
    if page.num % 2 == 1:               # 奇数页图在右，偶数页图在左
        if land:
            return _lay("right_bleed", band=(0.0, 0.60, BAND_Y, BAND_B),
                        img_box=(0.60, 0.30, 0.40, 0.70), img_anchor="br", rounded=False,
                        title_w=0.55)
        return _lay("right", band=(0.0, 0.61, BAND_Y, BAND_B),
                    img_box=(0.635, 0.19, 0.335, 0.765), img_anchor="c", title_w=0.55)
    if land:                            # 横图在左：与右侧对称，贴左下出血
        return _lay("left_bleed", band=(0.40, 1.0, BAND_Y, BAND_B), gray=True, text_x=0.43,
                    img_box=(0.0, 0.30, 0.40, 0.70), img_anchor="bl", rounded=False,
                    title_x=0.43, title_w=0.54)
    return _lay("left", band=(0.40, 1.0, BAND_Y, BAND_B), gray=True, text_x=0.43,
                img_box=(0.03, 0.19, 0.335, 0.765), img_anchor="c", title_x=0.43, title_w=0.54)


# ---------- 文字估高 ----------
def _lines(text, width_emu, size):
    cpl = max(1, int((width_emu / _EMU_PER_PT) / (size * 1.04)))
    return sum(max(1, math.ceil(len(ln) / cpl)) for ln in (text or "").split("\n"))


def _text_h(text, width_emu, size, spacing):
    return int(_lines(text, width_emu, size) * size * spacing * 1.18 * _EMU_PER_PT)


def _plan_items(items, width_emu, size, has_body_text=None):
    """items：[(问题, 答案)]；返回总高（EMU）。"""
    side = Pt(size + 8)
    tw = width_emu - side - Pt(12)
    total = 0
    for q, a in items:
        total += max(_text_h(q, tw, size, 1.3), side) + Pt(4)
        if a:
            total += _text_h(a, tw, size - 2, 1.35)
        total += Pt(14)
    return total


def _fit_size(items, width_emu, avail_emu, ladder=Q_LADDER):
    for sz in ladder:
        if _plan_items(items, width_emu, sz) <= avail_emu:
            return sz
    return None


# ---------- 问答块：主题色方块编号 + 问题框 + 答案框（各自独立）----------
def _qa_blocks(slide, items, x, y, w, size, th, numbered=True):
    """items：[(问题, 答案)]。返回点击分组：问题一组（方块+数字+问题），答案一组。"""
    side = Pt(size + 8)
    gap = Pt(12)
    tx = x + side + gap if numbered else x
    tw = w - (side + gap if numbered else 0)
    cy = y
    groups = []
    for i, (q, a) in enumerate(items):
        grp = []
        if numbered:
            sq = add_rect(slide, x, cy + Pt(3), side, side, th.main)
            _disable_shape_effects(sq)
            num = add_textbox(slide, x, cy + Pt(3), side, side, str(i + 1),
                              font=FONT_TITLE, size=size - 4, color="FFFFFF",
                              bold=True, align="center", anchor="middle")
            set_ascii_font(num, "Bahnschrift")
            grp += [sq.shape_id, num.shape_id]
        qh = max(_text_h(q, tw, size, 1.3), side)
        qb = add_textbox(slide, tx, cy, tw, qh, q, font=FONT_TITLE, size=size,
                         color=COLOR_TITLE, bold=bool(a), align="left", anchor="top",
                         line_spacing=1.3)
        grp.append(qb.shape_id)
        groups.append(grp)
        cy += qh + Pt(4)
        if a:
            ah = _text_h(a, tw, size - 2, 1.35)
            ab = add_textbox(slide, tx, cy, tw, ah, a, font=FONT_BODY, size=size - 2,
                             color=th.answer, align="left", anchor="top", line_spacing=1.35)
            groups.append([ab.shape_id])
            cy += ah
        cy += Pt(14)
    return groups


# ---------- 并列项版式 ----------
def _pills(slide, bullets, x, y, w, h, th):
    n = len(bullets)
    ph = min(pct_y(0.095), (h - Pt(16) * (n - 1)) // n)
    total = ph * n + Pt(16) * (n - 1)
    cy = y + max(0, (h - total) // 2)
    groups = []
    for b in bullets:
        s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, cy, w, ph)
        s.adjustments[0] = 0.5
        s.fill.solid(); s.fill.fore_color.rgb = rgb(th.main)
        s.line.fill.background(); _disable_shape_effects(s)
        t = add_textbox(slide, x + Pt(28), cy, w - Pt(56), ph, b, font=FONT_TITLE,
                        size=22, color="FFFFFF", bold=True, align="center", anchor="middle")
        groups.append([s.shape_id, t.shape_id])
        cy += ph + Pt(16)
    return groups


def _cards(slide, bullets, x, y, w, h, th, flow=False):
    """3–4 项圆角卡：白底主题描边 + 主题色圆号；flow=True 卡间加箭头。窄栏自动改竖排。"""
    n = len(bullets)
    vertical = w < pct_x(0.6) and n >= 3
    groups = []
    if vertical:
        # 窄栏竖排：圆号在左、文字在右的紧凑横条，条高按文字收
        gap = Pt(12)
        tw = w - Pt(76)
        hs = [max(Pt(52), _text_h(t, tw, 22, 1.3) + Pt(24)) for t in bullets]
        cy = y
        for i, b in enumerate(bullets):
            ch = hs[i]
            s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, cy, w, ch)
            s.adjustments[0] = 0.2
            s.fill.solid(); s.fill.fore_color.rgb = rgb("FFFFFF")
            s.line.color.rgb = rgb(th.card); s.line.width = Pt(1.5)
            _disable_shape_effects(s)
            d = Pt(30)
            c = slide.shapes.add_shape(MSO_SHAPE.OVAL, x + Pt(16), cy + (ch - d) // 2, d, d)
            c.fill.solid(); c.fill.fore_color.rgb = rgb(th.main)
            c.line.fill.background(); _disable_shape_effects(c)
            nb = add_textbox(slide, x + Pt(16), cy + (ch - d) // 2, d, d, str(i + 1),
                             font=FONT_TITLE, size=16, color="FFFFFF", bold=True,
                             align="center", anchor="middle")
            t = add_textbox(slide, x + Pt(60), cy, tw, ch, b, font=FONT_TITLE, size=22,
                            color=COLOR_BODY, align="left", anchor="middle", line_spacing=1.3)
            groups.append([s.shape_id, c.shape_id, nb.shape_id, t.shape_id])
            cy += ch + gap
        return groups
    gap = Pt(34) if flow else Pt(18)
    cw = (w - gap * (n - 1)) // n
    longest = max(len(b) for b in bullets)
    size = 22 if longest <= 24 else (20 if longest <= 40 else 18)
    # 卡高按最长那张的文字收（不撑满整个底带，免得卡里大片空白）
    need = max(_text_h(t, cw - Pt(32), size, 1.35) for t in bullets) + Pt(76)
    h = min(h, max(need, pct_y(0.24)))
    for i, b in enumerate(bullets):
        cx = x + i * (cw + gap)
        groups.append(_card(slide, cx, y, cw, h, b, i + 1, th, size=size))
        if flow and i < n - 1:
            ar = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE,
                                        cx + cw + Pt(9), y + h // 2 - Pt(10), Pt(16), Pt(20))
            ar.rotation = 90
            ar.fill.solid(); ar.fill.fore_color.rgb = rgb(th.card)
            ar.line.fill.background(); _disable_shape_effects(ar)
            groups[-1].append(ar.shape_id)
    return groups


def _card(slide, x, y, w, h, text, no, th, size=20):
    s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    s.adjustments[0] = 0.08
    s.fill.solid(); s.fill.fore_color.rgb = rgb("FFFFFF")
    s.line.color.rgb = rgb(th.card); s.line.width = Pt(1.75)
    _disable_shape_effects(s)
    d = Pt(30)
    c = slide.shapes.add_shape(MSO_SHAPE.OVAL, x + Pt(14), y + Pt(14), d, d)
    c.fill.solid(); c.fill.fore_color.rgb = rgb(th.main)
    c.line.fill.background(); _disable_shape_effects(c)
    n = add_textbox(slide, x + Pt(14), y + Pt(14), d, d, str(no), font=FONT_TITLE,
                    size=16, color="FFFFFF", bold=True, align="center", anchor="middle")
    t = add_textbox(slide, x + Pt(16), y + Pt(52), w - Pt(32), h - Pt(64), text,
                    font=FONT_TITLE, size=size, color=COLOR_BODY, align="left",
                    anchor="top", line_spacing=1.35)
    return [s.shape_id, c.shape_id, n.shape_id, t.shape_id]


def _timeline(slide, bullets, x, y, w, h, th):
    n = len(bullets)
    line_y = y + h // 3
    ln = add_rect(slide, x, line_y - Pt(1.5), w, Pt(3), th.card)
    _disable_shape_effects(ln)
    step = w // n
    d = Pt(34)
    groups = []
    for i, b in enumerate(bullets):
        cx = x + step * i + step // 2
        c = slide.shapes.add_shape(MSO_SHAPE.OVAL, cx - d // 2, line_y - d // 2, d, d)
        c.fill.solid(); c.fill.fore_color.rgb = rgb(th.main)
        c.line.color.rgb = rgb("FFFFFF"); c.line.width = Pt(2.5)
        _disable_shape_effects(c)
        num = add_textbox(slide, cx - d // 2, line_y - d // 2, d, d, str(i + 1),
                          font=FONT_TITLE, size=16, color="FFFFFF", bold=True,
                          align="center", anchor="middle")
        # 标签一律放线下（自左向右读，不制造上下回跳）
        tw = step - Pt(12)
        ty = line_y + d // 2 + Pt(10)
        t = add_textbox(slide, cx - tw // 2, ty, tw, y + h - ty, b, font=FONT_TITLE, size=20,
                        color=COLOR_BODY, align="center", anchor="top", line_spacing=1.35)
        groups.append([c.shape_id, num.shape_id, t.shape_id])
    return groups


def _compare(slide, page, x, y, w, h, th):
    gap = Pt(24)
    bw = (w - gap) // 2
    groups = []
    for k, (title, body, col) in enumerate((
            (page.left_title, page.left_body, th.main),
            (page.right_title, page.right_body, COLOR_RED_ACCENT))):
        bx = x + k * (bw + gap)
        s = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, bx, y, bw, h)
        s.adjustments[0] = 0.06
        s.fill.solid(); s.fill.fore_color.rgb = rgb("FFFFFF")
        s.line.color.rgb = rgb(col); s.line.width = Pt(2)
        _disable_shape_effects(s)
        grp = [s.shape_id]
        if title:
            tt = add_textbox(slide, bx + Pt(20), y + Pt(14), bw - Pt(40), Pt(40), title,
                             font=FONT_TITLE, size=24, color=col, bold=True,
                             align="left", anchor="middle")
            grp.append(tt.shape_id)
        if body:
            bb = add_textbox(slide, bx + Pt(20), y + Pt(62), bw - Pt(40), h - Pt(76), body,
                             font=FONT_TITLE, size=20, color=COLOR_BODY,
                             align="left", anchor="top", line_spacing=1.45)
            grp.append(bb.shape_id)
        groups.append(grp)
    return groups


# ---------- 引导问题 / 要点小结（同一套图感知版式）----------
def _render_points(slide, page, ctx, th):
    _theme_ctx(slide, page, ctx, th)

    # 四图网格：≥2 条配图建议 → 2×2 真图（缺图格留底带色空位，不画虚线框）
    sugs = _real_suggestions(page)
    if len(sugs) >= 2:
        _title(slide, page.title)
        _grid(slide, page, ctx, th)     # 多图直接放白底，不铺底带
        return

    img = _page_image(page, ctx)
    answers = getattr(page, "bullet_answers", None) or []
    items = [(b, answers[i] if i < len(answers) else "") for i, b in enumerate(page.bullets)]
    has_ans = any(a for _q, a in items)
    style = "" if has_ans else (page.bullet_style or "")
    if style == "对比" and not (page.left_body or page.right_body):
        style = ""
    if style == "时间轴":
        img = None                      # 时间轴横贯全宽，不配图

    top = pct_y(BODY_Y)
    bottom = pct_y(BODY_B)

    def layout(with_img):
        col_w = pct_x(COL_W_IMG if with_img else COL_W_FULL)
        y0 = top
        body_h = 0
        if page.body and (page.bullets or style == "对比"):
            body_h = _text_h(page.body, col_w, 20, 1.5)
        avail = bottom - y0 - (body_h + Pt(14) if body_h else 0)
        if style or not page.bullets:
            return col_w, body_h, None, avail
        size = _fit_size(items, col_w, avail)
        return col_w, body_h, size, avail

    with_img = bool(img)
    col_w, body_h, size, avail = layout(with_img)
    if with_img and page.bullets and not style and (size is None or size < MIN_SIZE_WITH_IMAGE):
        with_img = False                # 文字放不下：弃图改全宽
        ctx.setdefault("_v9_dropped", []).append(page.num)
        col_w, body_h, size, avail = layout(False)
    if size is None:
        size = Q_LADDER[-1]

    lay = _layout_for(page, img if with_img else None)
    if lay["band"]:                     # 底带先画（标题横带要垫在标题下面）
        x0, x1, y0, y1 = lay["band"]
        r = add_rect(slide, pct_x(x0), pct_y(y0), pct_x(x1 - x0), pct_y(y1 - y0),
                     GRAY_BAND if lay["gray"] else th.band)
        _disable_shape_effects(r)
    if lay["line"]:
        ln = add_rect(slide, pct_x(BODY_X - 0.025), pct_y(BODY_Y), Pt(4),
                      pct_y(BODY_B - BODY_Y), th.main)
        _disable_shape_effects(ln)
    _title(slide, page.title, x=lay["title_x"], w=lay["title_w"])   # 图会伸到标题区，标题让位
    pic = (_place_image(slide, img, lay["img_box"], lay["img_anchor"], lay["rounded"])
           if with_img else None)

    x = pct_x(lay["text_x"])
    y = top
    groups = []
    if body_h:
        b = add_textbox(slide, x, y, col_w, body_h, page.body, font=FONT_BODY, size=20,
                        color=COLOR_BODY, align="left", anchor="top", line_spacing=1.5)
        y += body_h + Pt(14)
    elif page.body and not page.bullets:
        bsz = 24 if len(page.body) <= 90 else (22 if len(page.body) <= 150 else 20)
        add_textbox(slide, x, y, col_w, bottom - y, page.body, font=FONT_TITLE, size=bsz,
                    color=COLOR_BODY, align="left", anchor="top", line_spacing=1.6)

    area_h = bottom - y
    if style == "药丸" and page.bullets:
        groups = _pills(slide, page.bullets, x, y, col_w, area_h, th)
    elif style in ("卡片", "流程") and page.bullets:
        groups = _cards(slide, page.bullets, x, y, col_w, area_h, th, flow=(style == "流程"))
    elif style == "时间轴" and page.bullets:
        groups = _timeline(slide, page.bullets, x, y, col_w, area_h, th)
    elif style == "对比":
        groups = _compare(slide, page, x, y, col_w, area_h, th)
    elif page.bullets:
        groups = _qa_blocks(slide, items, x, y, col_w, size, th)

    if pic is not None and page.image_click and 1 <= page.image_click <= len(groups):
        groups[page.image_click - 1].append(pic.shape_id)

    if ctx.get("anim") and len(groups) >= 2:
        add_click_reveal(slide, groups)


def _grid(slide, page, ctx, th):
    import os
    sugs = _real_suggestions(page)[:4]
    paths = list(getattr(page, "image_paths", []) or [])
    n = len(sugs)
    cols = 2
    rows = 1 if n <= 2 else 2
    gx, gy, gw, gh = pct_x(0.07), pct_y(0.40), pct_x(0.86), pct_y(0.52)
    gap = pct_x(0.018)
    cw = (gw - gap * (cols - 1)) // cols
    ch = (gh - gap * (rows - 1)) // rows
    for i in range(n):
        r, c = divmod(i, cols)
        cx, cy = gx + c * (cw + gap), gy + r * (ch + gap)
        p = resolve_image(ctx, paths[i] if i < len(paths) else "")
        if p and os.path.isfile(p):
            add_image_cover(slide, cx, cy, cw, ch, p, rounded=True, radius_frac=0.04)


render_guide = _render_points
render_summary = _render_points


# ---------- 原文齐读 ----------
_QUOTE_LADDER = ((24, 1.8), (22, 1.65), (20, 1.5), (18, 1.4), (17, 1.35),
                 (16, 1.3), (15, 1.3), (14, 1.25))


def _quote_fit(text, w_emu, h_emu):
    width_pt, avail_pt = w_emu / _EMU_PER_PT, h_emu / _EMU_PER_PT
    lines = (text or "").split("\n")
    for size, spacing in _QUOTE_LADDER:
        cpl = max(1, int(width_pt / (size * 1.15)))
        total = sum(max(1, math.ceil((len(ln) + 2) / cpl)) for ln in lines)
        if total * size * spacing * 1.1 <= avail_pt:
            return size, spacing
    return _QUOTE_LADDER[-1]


def render_quote(slide, page, ctx, th):
    _theme_ctx(slide, page, ctx, th)
    img = _page_image(page, ctx)

    def geom(with_img):
        bg_w = 0.56 if with_img else 0.88
        return bg_w, pct_x(bg_w - 0.08), pct_y(0.50)

    with_img = bool(img)
    bg_w, body_w, body_h = geom(with_img)
    size, spacing = _quote_fit(page.body, body_w, body_h)
    if with_img and size < 20:
        with_img = False
        ctx.setdefault("_v9_dropped", []).append(page.num)
        bg_w, body_w, body_h = geom(False)
        size, spacing = _quote_fit(page.body, body_w, body_h)

    bg = add_rect(slide, pct_x(0.06), pct_y(0.22), pct_x(bg_w), pct_y(0.70), COLOR_BG_QUOTE)
    _disable_shape_effects(bg)
    if with_img:                        # 图移到书页底外的白底上、放大
        _place_image(slide, img, None if image_has_alpha(img) else (0.64, 0.22, 0.33, 0.70))
    if page.title:
        add_textbox(slide, pct_x(0.10), pct_y(0.25), pct_x(bg_w - 0.06), pct_y(0.10),
                    page.title, font=FONT_TITLE, size=26, color=COLOR_TITLE, bold=True,
                    align="left", anchor="middle")
    if page.body:
        add_textbox(slide, pct_x(0.10), pct_y(0.38), body_w, body_h, page.body,
                    font=FONT_QUOTE_V9, size=size, color=COLOR_TITLE,
                    line_spacing=spacing, first_line_indent_chars=2,
                    align="left", anchor="top")


# ---------- 环节标题 ----------
def render_section(slide, page, ctx, th):
    is_solo = getattr(page, "_section_total", 1) <= 1
    r = add_rect(slide, pct_x(0.025), pct_y(0.040), pct_x(0.950), pct_y(0.920), th.main)
    _disable_shape_effects(r)
    if not is_solo:
        box = add_textbox(slide, pct_x(0.08), pct_y(0.17), pct_x(0.35), pct_y(0.30),
                          f"{getattr(page, '_section_no', 1):02d}",
                          font=FONT_TITLE, size=200, color="FFFFFF",
                          italic=True, align="left", anchor="middle")
        set_ascii_font(box, "Bahnschrift")
        add_rect(slide, pct_x(0.08), pct_y(0.51), pct_x(0.08), Emu(38000), "FFFFFF")
        add_textbox(slide, pct_x(0.08), pct_y(0.55), pct_x(0.84), pct_y(0.16), page.title,
                    font=FONT_TITLE, size=44, color="FFFFFF", bold=True,
                    align="left", anchor="middle", line_spacing=1.3)
        if page.body:
            add_textbox(slide, pct_x(0.08), pct_y(0.73), pct_x(0.84), pct_y(0.16), page.body,
                        font=FONT_BODY, size=22, color="F2F2F2",
                        align="left", anchor="top", line_spacing=1.6)
    else:
        add_textbox(slide, pct_x(0.08), pct_y(0.34), pct_x(0.84), pct_y(0.14), page.title,
                    font=FONT_TITLE, size=54, color="FFFFFF", bold=True,
                    align="center", anchor="middle", line_spacing=1.3)
        add_rect(slide, pct_x(0.46), pct_y(0.50), pct_x(0.08), Emu(38000), "FFFFFF")
        if page.body:
            add_textbox(slide, pct_x(0.15), pct_y(0.55), pct_x(0.70), pct_y(0.20), page.body,
                        font=FONT_BODY, size=22, color="F2F2F2",
                        align="center", anchor="top", line_spacing=1.6)
    logo_white = ctx.get("logo_white_path") or ctx.get("logo_path")
    if logo_white:
        add_logo(slide, logo_white, LOGO_INNER_X, LOGO_INNER_Y, LOGO_INNER_W)


# ---------- 封面 / END ----------
def render_cover(slide, page, ctx, th):
    img = _page_image(page, ctx)

    def underlay(s):
        if img:
            add_picture_fit(s, img, pct_x(0.60), pct_y(0.20), pct_x(0.40), pct_y(0.80),
                            anchor="br")

    kw = {}
    if img:
        kw = dict(title_box=(pct_x(0.04), pct_y(0.19), pct_x(0.64), pct_y(0.20)),
                  meta_box=(pct_x(0.06), pct_y(0.78), pct_x(0.58), pct_y(0.17)))
    _render_cover_base(slide, page, ctx, wrap_brackets=True, tri_color=th.main,
                       underlay=underlay, **kw)


def render_end(slide, page, ctx, th):
    from layouts_common import render_end as _end
    _end(slide, page, ctx, anchor_color=th.main, bg=(th.main, th.main))
