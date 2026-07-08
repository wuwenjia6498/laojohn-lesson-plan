# -*- coding: utf-8 -*-
"""老约翰 · 阅读单「原生可编辑 PPTX」渲染引擎（与 render.py 平行，读同一份 manifest）。

render.py 出 PDF/HTML（定版打印件，改不动）；本脚本把每张阅读单**重建成 PPT 原生
表格 / 文本框 / 线条 / 形状**，老师可在 PowerPoint/WPS 里直接改字、加行、挪元素。

用法（Windows，先确认盘符）：
    set PYTHONUTF8=1
    python render_pptx.py <manifest.json> <输出目录>

输出：每本书一份 `<书名>-阅读单.pptx`，一张单子一页、按 manifest（=教学先后）次序排。
不出 zip；不改 render.py、不改任何 HTML 模板。

保真策略：直接搬用各 `template_<键>.html` 的 render() 像素坐标常量，按固定比例 px→EMU
映射到 A4 竖版。几何类（venn/ladder/logic/voyage/story_mountain/fishbone/timeline/
bubble）为近似还原；timeline / story_mountain 原为横版，这里缩放横铺进竖版页（唯一已知
近似点，交付时显式上报）。

加模板：在 RENDERERS 注册一个 render_<键>(slide, d) 即可，引擎不动（同 render.py 的扩展性）。
"""
import os, sys, json, base64, pathlib, math, unicodedata

from pptx import Presentation
from pptx.util import Emu, Pt, Mm
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE, MSO_CONNECTOR
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

# ── 路径（移动硬盘：盘符可能变，全部相对本文件解析）──
HERE = pathlib.Path(__file__).resolve().parent
SKILL_ROOT = HERE.parent
PROJECT_ROOT = SKILL_ROOT.parents[2]            # .../.claude/skills/<skill> → 项目根
LOGO_PATH = PROJECT_ROOT / "品牌资产" / "logo.png"

# ── 坐标映射：HTML #page 宽 794px = A4 宽（竖版）。SCALE 同时适用 x/y（A4 长宽比≈一致）──
PAGE_W_PX = 794
A4_W_EMU = Mm(210)                              # 7,560,000
A4_H_EMU = Mm(297)                              # 10,692,000
SCALE = A4_W_EMU / PAGE_W_PX
FONT = "微软雅黑"
ASCII_FONT = "Calibri"

# 字体：CSS px @96dpi → pt = px * 0.75（page.pdf 把 1 CSS px 当 1/96 inch，与此一致）
def fs_pt(px):
    return max(1.0, px * 0.75)


def E(px):
    return Emu(int(round(px * SCALE)))


def rgb(hex_str):
    return RGBColor.from_string(hex_str.lstrip("#"))


# ── 仿射变换：竖版模板用恒等；横版模板(timeline/story_mountain)缩放横铺进竖版页 ──
class TF:
    def __init__(self, sx=1.0, sy=1.0, tx=0.0, ty=0.0):
        self.sx, self.sy, self.tx, self.ty = sx, sy, tx, ty

    def X(self, px):
        return E(px * self.sx + self.tx)

    def Y(self, px):
        return E(px * self.sy + self.ty)

    def W(self, px):
        return E(px * self.sx)

    def H(self, px):
        return E(px * self.sy)

    def F(self, px):
        return fs_pt(px * self.sx)               # 字号随横铺缩放同步

    def L(self, px):
        return max(0.5, px * 0.75 * self.sx)     # 线宽(pt)随缩放


ID = TF()


# ─────────────────────────── 通用低层绘制原语 ───────────────────────────
def _set_ea_font(run, font_name=FONT):
    """OOXML 要求 a:latin 在 a:ea 前，否则中文回退成 Calibri（见 laojohn-ppt helpers）。"""
    rPr = run._r.get_or_add_rPr()
    for latin in rPr.findall(qn("a:latin")):
        rPr.remove(latin)
    latin = etree.SubElement(rPr, qn("a:latin"))
    latin.set("typeface", ASCII_FONT)
    for ea in rPr.findall(qn("a:ea")):
        rPr.remove(ea)
    ea = etree.SubElement(rPr, qn("a:ea"))
    ea.set("typeface", font_name)


def add_text(slide, x, y, w, h, text, *, size=14, color="333333", bold=False,
             align="left", anchor="top", line_spacing=1.2, font=FONT, tf=ID):
    """文本框（px 坐标 + px 字号；经 tf 变换）。text 内 \\n 换段。"""
    box = slide.shapes.add_textbox(tf.X(x), tf.Y(y), tf.W(w), tf.H(h))
    frame = box.text_frame
    frame.word_wrap = True
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(frame, m, Emu(0))
    frame.vertical_anchor = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE,
                             "bottom": MSO_ANCHOR.BOTTOM}[anchor]
    al = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}[align]
    for i, line in enumerate(str(text).split("\n")):
        p = frame.paragraphs[0] if i == 0 else frame.add_paragraph()
        p.alignment = al
        p.line_spacing = line_spacing
        run = p.add_run()
        run.text = line
        run.font.name = font
        run.font.size = Pt(tf.F(size))
        run.font.bold = bold
        run.font.color.rgb = rgb(color)
        _set_ea_font(run, font)
    return box


def _no_shadow(shape):
    spPr = shape._element.spPr
    for tag in ("a:effectLst", "a:effectDag"):
        for el in spPr.findall(qn(tag)):
            spPr.remove(el)
    etree.SubElement(spPr, qn("a:effectLst"))


def _fill_alpha(shape, alpha_pct):
    """给已 solid 填充的形状加透明度（OOXML alpha 单位=千分之一百分点）。"""
    spPr = shape._element.spPr
    sf = spPr.find(qn("a:solidFill"))
    if sf is None:
        return
    srgb = sf.find(qn("a:srgbClr"))
    if srgb is None:
        return
    for a in srgb.findall(qn("a:alpha")):
        srgb.remove(a)
    a = etree.SubElement(srgb, qn("a:alpha"))
    a.set("val", str(int(alpha_pct * 1000)))


def add_shape(slide, kind, x, y, w, h, *, fill=None, alpha=None, line=None,
              line_w=1.0, dash=None, radius=None, tf=ID):
    shp = slide.shapes.add_shape(kind, tf.X(x), tf.Y(y), tf.W(w), tf.H(h))
    if radius is not None and kind == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            shp.adjustments[0] = radius
        except Exception:
            pass
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = rgb(fill)
        if alpha is not None:
            _fill_alpha(shp, alpha)
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = rgb(line)
        shp.line.width = Pt(tf.L(line_w))
        if dash:
            ln = shp.line._get_or_add_ln()
            for d in ln.findall(qn("a:prstDash")):
                ln.remove(d)
            etree.SubElement(ln, qn("a:prstDash")).set("val", dash)
    _no_shadow(shp)
    return shp


def add_rect(slide, x, y, w, h, **kw):
    return add_shape(slide, MSO_SHAPE.RECTANGLE, x, y, w, h, **kw)


def add_round_rect(slide, x, y, w, h, radius=0.08, **kw):
    return add_shape(slide, MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h, radius=radius, **kw)


def add_oval(slide, x, y, w, h, **kw):
    return add_shape(slide, MSO_SHAPE.OVAL, x, y, w, h, **kw)


def add_line(slide, x1, y1, x2, y2, color, w=1.4, dash=None, tf=ID):
    conn = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT,
                                      tf.X(x1), tf.Y(y1), tf.X(x2), tf.Y(y2))
    conn.line.color.rgb = rgb(color)
    conn.line.width = Pt(tf.L(w))
    if dash:
        ln = conn.line._get_or_add_ln()
        etree.SubElement(ln, qn("a:prstDash")).set("val", dash)
    # 连接线默认继承主题投影（气泡连线/维恩书写线会带阴影）——空 effectLst 覆盖掉
    _no_shadow(conn)
    return conn


def add_triangle(slide, x, y, w, h, fill, rotation=0, tf=ID):
    shp = slide.shapes.add_shape(MSO_SHAPE.ISOSCELES_TRIANGLE, tf.X(x), tf.Y(y),
                                 tf.W(w), tf.H(h))
    shp.rotation = rotation
    shp.fill.solid()
    shp.fill.fore_color.rgb = rgb(fill)
    shp.line.fill.background()
    _no_shadow(shp)
    return shp


def add_logo(slide):
    if LOGO_PATH.exists():
        slide.shapes.add_picture(str(LOGO_PATH), E(628), E(36), width=E(118))


# ─────────────────────────── 公共页眉 ───────────────────────────
def clean_variant(v):
    """空白版/派发版不盖左上版本角标（复合标签剥前缀保后半）。同 render.py。"""
    if not isinstance(v, str):
        return ""
    s = v.strip()
    for tag in ("空白版", "派发版"):
        if s == tag:
            return ""
        if s.startswith(tag):
            return s[len(tag):].lstrip(" ·・•|—-、\t")
    return s


def _wrap_lines(text, width_px, size_px):
    """估算一段文字在给定宽度/字号下的换行行数（含显式 \\n）。
    PPTX 是绝对定位、无浏览器流式排版，长副标题会压到下方正文，故正文起点须按此下推。
    宽度按东亚全角=1em、其余≈0.55em 估算，模糊向上取整（宁可多留空、不撞版）。"""
    per_line = max(1.0, width_px / float(size_px))       # 每行可容纳的 em 单位数
    total = 0
    for seg in str(text).split("\n"):
        units = 0.0
        for ch in seg:
            units += 1.0 if unicodedata.east_asian_width(ch) in ("W", "F", "A") else 0.55
        total += max(1, math.ceil(units / per_line))
    return max(1, total)


def header(slide, d, *, title_align="center", title_px=72, title_size=23,
           sub_px=112, title_color="333333", sub_color="8A8268",
           variant_color="B3A98F", title=None):
    """通用页眉：logo + 版本角标 + 标题 + 副标题。返回正文起始 y(px)（副标题多行时随之下推）。"""
    add_logo(slide)
    var = clean_variant(d.get("variant", ""))
    if var:
        add_text(slide, 52, 40, 320, 24, var, size=13, color=variant_color)
    t = title if title is not None else d.get("title", "")
    if title_align == "left":
        add_text(slide, 64, title_px, 600, 40, t, size=title_size, bold=True,
                 color=title_color, align="left", line_spacing=1.4)
    else:
        add_text(slide, 40, title_px, 714, 60, t, size=title_size, bold=True,
                 color=title_color, align="center", line_spacing=1.4)
    y = title_px + 40
    sub = d.get("subtitle", "")
    if sub:
        sa = "left" if title_align == "left" else "center"
        sx, sw = (64, 640) if title_align == "left" else (48, 698)
        add_text(slide, sx, sub_px, sw, 50, sub, size=15, color=sub_color,
                 align=sa, line_spacing=1.5)
        # 15px 行高 ×1.5 ≈ 23px/行；末行下留 16px 间隔
        lines = _wrap_lines(sub, sw, 15)
        y = max(y, sub_px + lines * 23 + 16)
    return y


def footer(slide, d, key="footer", color="9A937F", y=1075):
    # PDF 模板的 note/foot 一律左对齐（padding 40px）——PPTX 对齐之
    txt = d.get(key, "")
    if txt:
        add_text(slide, 40, y, 714, 30, txt, size=14, color=color, align="left")


# ─────────────────────────── 表格内边框 ───────────────────────────
def _cell_borders(cell, color="D6CEC0", w_px=1.0):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for side in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        for ln in tcPr.findall(qn(side)):
            tcPr.remove(ln)
    for side in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
        ln = etree.SubElement(tcPr, qn(side))
        ln.set("w", str(int(E(w_px))))
        ln.set("cap", "flat")
        sf = etree.SubElement(ln, qn("a:solidFill"))
        etree.SubElement(sf, qn("a:srgbClr")).set("val", color.lstrip("#"))


def _style_cell(cell, text, *, fill, fg, size, bold, align="left", anchor="top"):
    _cell_borders(cell)
    cell.fill.solid()
    cell.fill.fore_color.rgb = rgb(fill)
    cell.vertical_anchor = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE}[anchor]
    cell.margin_left = E(12)
    cell.margin_right = E(12)
    cell.margin_top = E(8)
    cell.margin_bottom = E(8)
    tf = cell.text_frame
    tf.word_wrap = True
    al = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER}[align]
    for i, seg in enumerate(str(text).split("\n")):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = al
        p.line_spacing = 1.4
        run = p.add_run()
        run.text = seg
        run.font.name = FONT
        run.font.size = Pt(fs_pt(size))
        run.font.bold = bold
        run.font.color.rgb = rgb(fg)
        _set_ea_font(run, FONT)


# =====================================================================
#  各模板 renderer —— 直接搬对应 template_<键>.html 的 render() 坐标/字段
# =====================================================================
CONTENT_X, CONTENT_W = 56, 682           # #page padding 56 两侧 → 正文区


def render_table(slide, d):
    body_y = header(slide, d, title_align="left", title_px=108, title_size=21,
                    sub_px=146, title_color="2B2B2B", sub_color="8A8175",
                    variant_color="A89B8A")
    cols = d.get("columns", [])
    rows = d.get("rows", [])
    ncol = len(cols)
    label_first = d.get("label_first_col", False)
    hi = d.get("highlight_col", -1)
    if not isinstance(hi, int):
        hi = -1
    row_min_h = d.get("row_min_h", 64)

    y0 = max(168, int(round(body_y))) if d.get("subtitle") else 168
    # 表头高度随表头换行数
    hd_lines = max((str(c.get("name", "")).count("\n") + 1) for c in cols) if cols else 1
    head_h = 30 + 20 * hd_lines

    # 竖版页固定高，行多/行高大的表（如 9 行自读检测表）会挂出页底——按可用高度把行高
    # 等比压到入页，设可书写下限 84px（低于此宁可挂底也不再压，保住书写空间）。
    PAGE_H, BOT_MARGIN, ROW_FLOOR = 1123, 28, 84
    if rows:
        avail_rows = PAGE_H - BOT_MARGIN - y0 - head_h
        fit_h = avail_rows / len(rows)
        row_h = row_min_h if row_min_h * len(rows) <= avail_rows else max(ROW_FLOOR, int(fit_h))
    else:
        row_h = row_min_h

    shape = slide.shapes.add_table(len(rows) + 1, ncol, E(CONTENT_X), E(y0),
                                   E(CONTENT_W), E(head_h + row_h * len(rows)))
    table = shape.table
    table.first_row = False
    table.horz_banding = False
    # 列宽（百分比）
    widths = [int(c.get("width", 100 / ncol)) for c in cols]
    wsum = sum(widths) or 100
    acc = 0
    for c in range(ncol):
        w = int(CONTENT_W * widths[c] / wsum) if c < ncol - 1 else (CONTENT_W - acc)
        table.columns[c].width = E(w)
        acc += w
    table.rows[0].height = E(head_h)
    for r in range(len(rows)):
        table.rows[r + 1].height = E(row_h)

    # 表头
    for c in range(ncol):
        is_label = label_first and c == 0
        is_hi = c == hi
        bg = "7D7468" if is_label else ("6E9457" if is_hi else "A89B8A")
        _style_cell(table.cell(0, c), cols[c].get("name", ""), fill=bg, fg="FFFFFF",
                    size=15, bold=True, align="center", anchor="middle")
    # 数据行
    for r, row in enumerate(rows):
        zebra = (r % 2 == 1)
        for c in range(ncol):
            txt = row[c] if c < len(row) and row[c] is not None else ""
            is_label = label_first and c == 0
            is_hi = c == hi
            if is_label:
                fill, fg, bold = "EFEBE3", "5A5048", True
            elif is_hi:
                fill, fg, bold = "EAF1E2", "3C5232", True
            else:
                fill, fg, bold = ("F6F4EF" if zebra else "FFFFFF"), "333333", False
            _style_cell(table.cell(r + 1, c), txt, fill=fill, fg=fg, size=14, bold=bold)

    # note 放页底固定位（表格实际高度受 PowerPoint 自动撑行影响、难精确预估）
    footer(slide, d, key="note", color="8A8175", y=1085)


def render_venn(slide, d):
    header(slide, d, title_px=72, title_size=26, sub_px=120, title_color="4A4A42")
    OFF = 170                                       # svg top:170
    CX1, CX2, CY, R = 272, 522, 440, 212
    add_oval(slide, CX1 - R, CY - R + OFF, 2 * R, 2 * R, fill="7FA86A", alpha=28,
             line="6E9457", line_w=1.5)
    add_oval(slide, CX2 - R, CY - R + OFF, 2 * R, 2 * R, fill="D8B24E", alpha=26,
             line="C29A38", line_w=1.5)
    labY = CY - R - 34 + OFF
    add_text(slide, CX1 - 40 - 80, labY - 18, 160, 30, d.get("left_label", ""),
             size=22, bold=True, color="5C7A47", align="center")
    add_text(slide, 397 - 80, labY - 18, 160, 30, d.get("center_label", "共同"),
             size=22, bold=True, color="7A6B3A", align="center")
    add_text(slide, CX2 + 40 - 80, labY - 18, 160, 30, d.get("right_label", ""),
             size=22, bold=True, color="A07E2A", align="center")
    slots = {"left": (188, [368, 448, 528], "6E9457", 158),
             "center": (397, [410, 490], "9A8A4A", 120),
             "right": (606, [368, 448, 528], "C29A38", 158)}
    for key in ("left", "center", "right"):
        x, ys, color, lw = slots[key]
        items = d.get(key, [])
        for i, yy in enumerate(ys):
            txt = items[i] if i < len(items) else ""
            if isinstance(txt, str) and txt.strip():
                add_text(slide, x - 90, yy - 12 + OFF, 180, 40, txt, size=16,
                         color="3A3A33", align="center")
            else:
                add_line(slide, x - lw / 2, yy + OFF, x + lw / 2, yy + OFF, color, 1.5)
    footer(slide, d, key="footer")


def render_ladder(slide, d):
    header(slide, d, title_px=74, title_size=24, sub_px=116)
    OFF = 150                                       # svg top:150
    steps = d.get("steps", [])
    n = len(steps)
    PALETTE = ["#D9883A", "#A8504F", "#5B7FA6", "#C49B3E", "#4E8C7D", "#8268A0"]
    X_LEFT, X_TOP_MAX, Y_BOTTOM, Y_TOP, LINE_LEN, LINE_GAP = 72, 392, 815, 170, 358, 58
    rise = (Y_BOTTOM - Y_TOP) / (n - 1) if n > 1 else 0
    run = (X_TOP_MAX - X_LEFT) / (n - 1) if n > 1 else 0
    ST = [{"X": round(X_LEFT + run * i), "Y": round(Y_BOTTOM - rise * i),
           "color": PALETTE[i % len(PALETTE)]} for i in range(n)]
    # 楼梯折线
    pts = [(22, ST[0]["Y"])]
    for s in ST:
        pts.append((s["X"], s["Y"]))
        pts.append((s["X"], s["Y"] - rise))
        pts.append((s["X"] + run, s["Y"] - rise))
    for a, b in zip(pts, pts[1:]):
        add_line(slide, a[0], a[1] + OFF, b[0], b[1] + OFF, "CBC4B6", 2)
    # 各阶标签 + 书写线
    for i, st in enumerate(steps):
        s = ST[i]
        lx, ly = s["X"] + 18, s["Y"]
        add_line(slide, lx - 6, ly - 38 + OFF, lx - 6, ly - 14 + OFF, s["color"], 4)
        add_text(slide, lx + 2, ly - 36 + OFF, LINE_LEN, 26, st.get("header", ""),
                 size=16, bold=True, color=s["color"])
        items = st.get("items", ["", ""])
        rowY = ly + 6
        for it in items[:2]:
            if isinstance(it, str) and it.strip():
                add_text(slide, lx + 6, rowY - 16 + OFF, LINE_LEN, 40, it, size=14,
                         color="3A3A33", line_spacing=1.5)
                add_line(slide, lx + 2, rowY + 44 + OFF, lx + 2 + LINE_LEN,
                         rowY + 44 + OFF, "D8D2C5", 1.3)
                rowY += 60
            else:
                add_line(slide, lx + 2, rowY + OFF, lx + 2 + LINE_LEN, rowY + OFF,
                         s["color"], 1.4)
                rowY += LINE_GAP
    footer(slide, d, key="footer", y=1080)


def render_logic(slide, d):
    header(slide, d, title_px=104, title_size=24, sub_px=140, title_color="1F3864",
           sub_color="6B7180", variant_color="9FA3B0")
    layers = d.get("layers", [])
    x, w = 64, 666
    y0 = 178 if d.get("subtitle") else 158
    lh = 175
    natural = len(layers) * lh + max(0, len(layers) - 1) * 60
    tf = _fit_tf(y0, natural)
    y = y0
    for i, ly in enumerate(layers):
        add_round_rect(slide, x, y, w, lh, radius=0.04, fill="DADDE4",
                       line="1F3864", line_w=2.5, tf=tf)
        add_text(slide, x + 30, y + 22, w - 60, 30, ly.get("label", ""), size=19,
                 bold=True, color="1F3864", align="center", tf=tf)
        txt = ly.get("text", "")
        if isinstance(txt, str) and txt.strip():
            add_text(slide, x + 34, y + 64, w - 68, lh - 80, txt, size=18,
                     color="2B2B2B", align="center", anchor="middle",
                     line_spacing=1.7, tf=tf)
        y += lh
        if i < len(layers) - 1:                     # 层间下箭头
            add_line(slide, x + w / 2, y + 14, x + w / 2, y + 44, "1F3864", 3.5, tf=tf)
            add_triangle(slide, x + w / 2 - 11, y + 44, 22, 16, "1F3864",
                         rotation=180, tf=tf)
            y += 60
    footer(slide, d, key="footer", color="8A90A0", y=min(1080, tf.sy * y + tf.ty + 16))


def render_voyage(slide, d):
    add_logo(slide)
    var = clean_variant(d.get("variant", ""))
    if var:
        add_text(slide, 46, 38, 320, 24, var, size=13, color="B3A98F")
    # 顶部棕框（中心节点）
    tb_w = 320
    tbx = (PAGE_W_PX - tb_w) / 2
    tby = 116
    th = 64
    add_round_rect(slide, tbx, tby, tb_w, th, radius=0.18, fill="6B5644")
    add_text(slide, tbx, tby + 10, tb_w, 30, d.get("title_main", ""), size=23,
             bold=True, color="FFFFFF", align="center")
    if d.get("title_sub"):
        add_text(slide, tbx, tby + 38, tb_w, 22, d.get("title_sub"), size=15,
                 color="FFFFFF", align="center")
    add_line(slide, PAGE_W_PX / 2, tby + th, PAGE_W_PX / 2, tby + th + 28, "B89A6E", 2)

    branches = d.get("branches", [])

    def card_h(br):
        rows_h = 0
        for f in br.get("fields", []):
            if _has_val(f.get("value")):
                arr = f["value"] if isinstance(f["value"], list) else [f["value"]]
                rows_h += 14 + 26 * len(arr)
            else:
                rows_h += 14 + 36 * f.get("lines", 1)
        return 24 + 38 + rows_h + 16

    cy0 = tby + th + 36
    natural = sum(card_h(br) + 16 for br in branches)
    tf = _fit_tf(cy0, natural)                       # 分支卡区按需纵向压缩入页
    x, w = 56, 682
    y = cy0
    for br in branches:
        ch = card_h(br)
        add_round_rect(slide, x, y, w, ch, radius=0.03, line="C9B89A", line_w=1.5,
                       fill="FFFFFF", tf=tf)
        add_text(slide, x + 22, y + 14, w - 44, 24, br.get("header", ""), size=17,
                 bold=True, color="6B5644", tf=tf)
        add_line(slide, x + 22, y + 44, x + w - 22, y + 44, "E3D8C2", 1, tf=tf)
        fy = y + 54
        for f in br.get("fields", []):
            add_text(slide, x + 22, fy, 76, 30, f.get("label", ""), size=14,
                     bold=True, color="8A6F4E", tf=tf)
            vx, vw = x + 110, w - 132
            if _has_val(f.get("value")):
                arr = f["value"] if isinstance(f["value"], list) else [f["value"]]
                for item in arr:
                    add_text(slide, vx, fy, vw, 24, item, size=14, color="3A3A33", tf=tf)
                    add_line(slide, vx, fy + 24, vx + vw, fy + 24, "E0D6C2", 1,
                             dash="dash", tf=tf)
                    fy += 26
                fy += 14
            else:
                for _ in range(f.get("lines", 1)):
                    add_line(slide, vx, fy + 30, vx + vw, fy + 30, "D8CBB0", 1.3, tf=tf)
                    fy += 36
                fy += 14
        y += ch + 16
    footer(slide, d, key="footer", y=min(1085, tf.sy * y + tf.ty + 6))


def render_story_mountain(slide, d):
    # 横版内容：缩放横铺进竖版页（近似）。标题/页脚用竖版正常排。
    header(slide, d, title_px=74, title_size=23, sub_px=116)
    steps = d.get("steps", [])
    n = len(steps)
    X_L, X_R, Y_BASE, AMP = 110, 1013, 580, 360
    k = (PAGE_W_PX - 28) / 1123.0
    # 峰顶框顶 native≈52(=Y_BASE-AMP-18-150)；让它落到标题下方 page y≈150
    tf = TF(sx=k, sy=k, tx=14, ty=150 - k * 52)
    PALETTE = ["#A8504F", "#D9883A", "#C49B3E", "#4E8C7D", "#5B7FA6", "#8268A0", "#7A8C3A"]
    BOX_W = min(176, (X_R - X_L) // max(1, n - 1) - 12)
    peak = d.get("peak")
    if not isinstance(peak, int):
        peak = next((i for i, s in enumerate(steps)
                     if "高潮" in str(s.get("header", ""))), -1)
        if peak < 0:
            peak = round((n - 1) * 0.6)
    peak = max(0, min(n - 1, peak))
    import math
    pos = []
    for i in range(n):
        t = i / (n - 1) if n > 1 else 0.5
        x = X_L + (X_R - X_L) * t
        if i <= peak:
            frac = i / peak if peak > 0 else 1
        else:
            frac = (n - 1 - i) / (n - 1 - peak) if (n - 1 - peak) > 0 else 1
        y = Y_BASE - AMP * math.sin(frac * math.pi / 2)
        pos.append((round(x), round(y)))
    # 山形折线（分段近似平滑曲线）+ 地平线
    for a, b in zip(pos, pos[1:]):
        add_line(slide, a[0], a[1], b[0], b[1], "5B86A6", 3, tf=tf)
    if n >= 2:
        add_line(slide, 80, Y_BASE + 4, 1043, Y_BASE + 4, "D8D2C5", 1.5, tf=tf)
    for i, st in enumerate(steps):
        px, py = pos[i]
        color = PALETTE[i % len(PALETTE)]
        boxH = 150
        bx = max(8, min(1123 - 8 - BOX_W, px - BOX_W / 2))
        by = py - 18 - boxH
        add_oval(slide, px - 6, py - 6, 12, 12, fill="FFFFFF", line=color, line_w=3, tf=tf)
        add_line(slide, px, py - 6, px, by + boxH, color, 1.6, tf=tf)
        add_round_rect(slide, bx, by, BOX_W, boxH, radius=0.06, fill="FFFFFF",
                       line=color, line_w=1.6, tf=tf)
        add_rect(slide, bx, by, BOX_W, 24, fill=color, tf=tf)
        add_text(slide, bx, by + 3, BOX_W, 20, st.get("header", ""), size=14,
                 bold=True, color="FFFFFF", align="center", tf=tf)
        items = st.get("items", ["", ""])
        txt = next((x for x in items if isinstance(x, str) and x.strip()), "")
        if txt:
            add_text(slide, bx + 8, by + 34, BOX_W - 16, boxH - 40, txt, size=13,
                     color="3A3A33", line_spacing=1.4, tf=tf)
        else:
            for kk in range(3):
                ly = by + 52 + kk * 34
                add_line(slide, bx + 8, ly, bx + BOX_W - 8, ly, "CFC8BA", 1.2, tf=tf)
    footer(slide, d, key="footer", y=1080)


def render_fishbone(slide, d):
    header(slide, d, title_px=74, title_size=23, sub_px=116)
    OFF = 150
    ribs = d.get("ribs", [])
    n = len(ribs)
    PALETTE = ["#5B8C7B", "#C18A3A", "#7A8C3A", "#5B7FA6", "#A8634F", "#8268A0"]
    SPINE_Y, X_TAIL, X_HEAD, BOX_W, BOX_H = 470, 150, 596, 150, 80
    # 主干 + 鱼头/鱼尾(三角近似)
    add_line(slide, X_TAIL, SPINE_Y + OFF, X_HEAD, SPINE_Y + OFF, "C9A24A", 5)
    add_triangle(slide, X_HEAD, SPINE_Y - 44 + OFF, 84, 88, "E7C46A", rotation=90)
    add_triangle(slide, X_TAIL - 58, SPINE_Y - 40 + OFF, 40, 80, "E7C46A", rotation=270)
    add_text(slide, X_HEAD + 90, SPINE_Y - 12 + OFF, 150, 30, d.get("head_label", ""),
             size=16, bold=True, color="5A5048")
    add_text(slide, X_TAIL - 216, SPINE_Y - 12 + OFF, 150, 30, d.get("tail_label", ""),
             size=16, bold=True, color="5A5048", align="right")
    segL, segR = X_TAIL + 30, X_HEAD - 20
    for i, rb in enumerate(ribs):
        t = i / (n - 1) if n > 1 else 0.5
        sx = round(segL + (segR - segL) * t)
        up = (rb["side"] == "up") if rb.get("side") else (i % 2 == 0)
        color = PALETTE[i % len(PALETTE)]
        ex, ey = sx + 66, SPINE_Y + (-150 if up else 150)
        add_line(slide, sx, SPINE_Y + OFF, ex, ey + OFF, "B7AE9C", 2)
        bx = max(6, min(794 - 6 - BOX_W, ex - BOX_W / 2))
        by = (ey - BOX_H) if up else ey
        add_round_rect(slide, bx, by + OFF, BOX_W, BOX_H, radius=0.08, fill="FFFFFF",
                       line=color, line_w=1.6)
        add_rect(slide, bx, by + OFF, BOX_W, 22, fill=color)
        add_text(slide, bx + 10, by + 3 + OFF, BOX_W - 16, 18,
                 rb.get("header", f"第{i+1}件"), size=13, bold=True, color="FFFFFF")
        txt = rb.get("text", "")
        if isinstance(txt, str) and txt.strip():
            add_text(slide, bx + 10, by + 30 + OFF, BOX_W - 18, BOX_H - 30, txt,
                     size=13, color="3A3A33", line_spacing=1.3)
        else:
            add_line(slide, bx + 10, by + 44 + OFF, bx + BOX_W - 10, by + 44 + OFF,
                     "CFC8BA", 1.2)
            add_line(slide, bx + 10, by + 66 + OFF, bx + BOX_W - 10, by + 66 + OFF,
                     "CFC8BA", 1.2)
    footer(slide, d, key="footer", y=1080)


def render_timeline(slide, d):
    # 横版内容：缩放横铺进竖版页（近似）。标题/页脚竖版正常排。
    header(slide, d, title_px=64, title_size=24, sub_px=98)
    nodes = d.get("nodes", [])
    n = len(nodes)
    AX_Y, X0, X1 = 200, 64, 1059
    k = (PAGE_W_PX - 24) / 1123.0
    tf = TF(sx=k, sy=k, tx=12, ty=210 - k * 142)
    PALETTE = ["#4F86C6", "#D9883A", "#C49B3E", "#6FA85A", "#4E8C7D", "#5B7FA6", "#A8504F"]
    add_line(slide, X0, AX_Y, X1, AX_Y, "9A937F", 2.5, tf=tf)
    add_triangle(slide, X1, AX_Y - 9, 18, 18, "9A937F", rotation=90, tf=tf)
    colW = (X1 - X0) / n if n else 0
    for i, nd in enumerate(nodes):
        cx = round(X0 + colW * (i + 0.5))
        color = PALETTE[i % len(PALETTE)]
        cw = min(colW - 16, 210)
        add_oval(slide, cx - 7, AX_Y - 7, 14, 14, fill="FFFFFF", line=color, line_w=3, tf=tf)
        add_round_rect(slide, cx - cw / 2, AX_Y - 58, cw, 30, radius=0.2, fill=color, tf=tf)
        add_text(slide, cx - cw / 2, AX_Y - 54, cw, 22, nd.get("header", ""), size=14,
                 bold=True, color="FFFFFF", align="center", tf=tf)
        val = nd.get("value")
        val = val if isinstance(val, list) else ([val] if val else [])
        bx, by = cx - cw / 2, AX_Y + 28
        if val:
            add_text(slide, bx, by + 6, cw, 200, "\n".join(val), size=14,
                     color="3A3A33", align="center", line_spacing=1.3, tf=tf)
        else:
            rows = nd.get("lines", 7)
            for kk in range(rows):
                ly = by + 22 + kk * 46
                add_line(slide, bx, ly, bx + cw, ly, "CFC8BA", 1.2, tf=tf)
    footer(slide, d, key="footer", y=1080)


def render_bubble(slide, d):
    header(slide, d, title_px=74, title_size=23, sub_px=116)
    OFF = 150
    import math
    bubbles = d.get("bubbles", [])
    n = len(bubbles)
    color = (d.get("color") or "#7FA86A").lstrip("#")
    center = d.get("center")
    center = (center.get("label") if isinstance(center, dict) else center) or ""
    CX, CY, CR, RX, RY, BX, BY = 397, 470, 74, 296, 268, 90, 64
    pos = []
    for i in range(n):
        ang = -math.pi / 2 + (2 * math.pi * i) / n
        pos.append((CX + RX * math.cos(ang), CY + RY * math.sin(ang)))
    for px, py in pos:
        add_line(slide, CX, CY + OFF, round(px), round(py) + OFF, "C9C2B4", 1.6)
    for i, b in enumerate(bubbles):
        px, py = pos[i]
        add_oval(slide, round(px) - BX, round(py) - BY + OFF, 2 * BX, 2 * BY,
                 fill="EEF3E6", line=color, line_w=1.8)
        txt = b if isinstance(b, str) else (b.get("text", "") if isinstance(b, dict) else "")
        if isinstance(txt, str) and txt.strip():
            add_text(slide, round(px) - BX + 8, round(py) - BY + 8 + OFF, 2 * BX - 16,
                     2 * BY - 16, txt, size=13, color="3A3A33", align="center",
                     anchor="middle", line_spacing=1.25)
    add_oval(slide, CX - CR, CY - CR + OFF, 2 * CR, 2 * CR, fill=color)
    add_text(slide, CX - CR, CY - CR + OFF, 2 * CR, 2 * CR, center, size=17, bold=True,
             color="FFFFFF", align="center", anchor="middle", line_spacing=1.2)
    footer(slide, d, key="footer", y=1080)


def render_writing(slide, d):
    body_y = header(slide, d, title_align="left", title_px=108, title_size=21, sub_px=142,
                    title_color="2B2B2B", sub_color="8A8175", variant_color="A89B8A")
    n = d.get("lines", 13)
    pre = d.get("value", [])
    pre = pre if isinstance(pre, list) else ([pre] if pre else [])
    # 长副标题（如创作任务单的任务 A/B 大段说明）会换多行，书写框起点须随之下推
    fy = max(182, int(round(body_y)))
    fh = max(800, 74 + n * 48 + 26)
    fh = min(fh, 1075 - fy)
    add_round_rect(slide, CONTENT_X, fy, CONTENT_W, fh, radius=0.04, line="9BBF84",
                   line_w=2, dash="dash", fill="FFFFFF")
    if d.get("icon") is not False:
        add_text(slide, CONTENT_X + 34, fy + 22, 60, 40, "✏️", size=28)
    ly = fy + 88
    for i in range(n):
        if i < len(pre) and isinstance(pre[i], str) and pre[i].strip():
            add_text(slide, CONTENT_X + 36, ly - 22, CONTENT_W - 68, 28, pre[i],
                     size=15, color="3A4A45")
        add_line(slide, CONTENT_X + 34, ly, CONTENT_X + CONTENT_W - 34, ly,
                 "B9B2A2", 1.4, dash="sysDot")
        ly += 48


def render_draw(slide, d):
    header(slide, d, title_align="left", title_px=108, title_size=21, sub_px=142,
           title_color="2B2B2B", sub_color="8A8175", variant_color="A89B8A")
    cap_n = d.get("caption_lines", 0)
    box_h = d.get("box_min_h", 640 if cap_n else 820)
    by = 182
    box_h = min(box_h, 1060 - by - (cap_n * 44 + 22 if cap_n else 0))
    add_round_rect(slide, CONTENT_X, by, CONTENT_W, box_h, radius=0.03, line="C7A86A",
                   line_w=2, dash="dash", fill="FFFFFF")
    if d.get("prompt"):
        add_text(slide, CONTENT_X + 20, by + 16, CONTENT_W - 40, 30, d.get("prompt"),
                 size=15, bold=True, color="9A7B45")
    elif d.get("icon") is not False:
        add_text(slide, CONTENT_X + 18, by + 14, 60, 40, "🎨", size=24)
    if cap_n:
        cy = by + box_h + 22
        for i in range(cap_n):
            add_line(slide, CONTENT_X + 4, cy + 30, CONTENT_X + CONTENT_W - 4,
                     cy + 30, "B9B2A2", 1.4, dash="sysDot")
            cy += 44


def render_comic(slide, d):
    header(slide, d, title_align="left", title_px=108, title_size=21, sub_px=142,
           title_color="2B2B2B", sub_color="8A8175", variant_color="A89B8A")
    y = 178
    if d.get("banner"):
        bw = 300
        bx = (PAGE_W_PX - bw) / 2
        add_line(slide, bx, y, bx + bw, y, "C9B89A", 2)
        add_text(slide, bx, y + 8, bw, 26, d.get("banner"), size=18, bold=True,
                 color="6B5644", align="center")
        add_line(slide, bx, y + 44, bx + bw, y + 44, "C9B89A", 2)
        y += 70
    cells = d.get("cells", 3)
    if isinstance(cells, int):
        cells = [{} for _ in range(cells)]
    desc_w, gap = 300, 22
    draw_x = CONTENT_X + desc_w + gap
    draw_w = CONTENT_W - desc_w - gap

    def cell_h_of(c):
        lines = c.get("lines", 4)
        return max(c.get("h", lines * 46 + 10), lines * 46)

    natural = sum(cell_h_of(c) + 22 for c in cells)
    tf = _fit_tf(y, natural)
    for c in cells:
        lines = c.get("lines", 4)
        pre = c.get("value", [])
        pre = pre if isinstance(pre, list) else ([pre] if pre else [])
        cell_h = cell_h_of(c)
        ly = y + 6
        for i in range(lines):
            if i < len(pre) and isinstance(pre[i], str) and pre[i].strip():
                add_text(slide, CONTENT_X + 2, ly + 14, desc_w - 4, 26, pre[i],
                         size=14, color="3A4A45", tf=tf)
            add_line(slide, CONTENT_X, ly + 40, CONTENT_X + desc_w, ly + 40,
                     "B9B2A2", 1.4, dash="sysDot", tf=tf)
            ly += 46
        add_round_rect(slide, draw_x, y, draw_w, cell_h, radius=0.05, line="B9C9A6",
                       line_w=2, dash="dash", fill="FFFFFF", tf=tf)
        add_text(slide, draw_x + 14, y + 12, 50, 30, "🎨", size=20, tf=tf)
        y += cell_h + 22


def render_profile(slide, d):
    header(slide, d, title_align="left", title_px=108, title_size=21, sub_px=142,
           title_color="2B2B2B", sub_color="8A8175", variant_color="A89B8A")
    y = 178
    if d.get("banner"):
        bw = 300
        bx = (PAGE_W_PX - bw) / 2
        add_line(slide, bx, y, bx + bw, y, "C9B89A", 2)
        add_text(slide, bx, y + 8, bw, 26, d.get("banner"), size=18, bold=True,
                 color="6B5644", align="center")
        add_line(slide, bx, y + 44, bx + bw, y + 44, "C9B89A", 2)
        y += 70

    cards = d.get("cards", [])

    def card_h_of(c):
        fh = 0
        for f in c.get("fields", []):
            if _has_val(f.get("value")):
                arr = f["value"] if isinstance(f["value"], list) else [f["value"]]
                fh += 22 + 38 * len(arr) + 12
            else:
                fh += 22 + 38 * f.get("lines", 1) + 12
        box_h = (c["box"].get("h", 150) if c.get("box") else 0)
        return max(fh, box_h) + 40

    natural = sum(card_h_of(c) + 20 for c in cards)
    tf = _fit_tf(y, natural)
    for c in cards:
        box = c.get("box")
        card_h = card_h_of(c)
        add_round_rect(slide, CONTENT_X, y, CONTENT_W, card_h, radius=0.04,
                       fill="EEF3E6", tf=tf)
        fx = CONTENT_X + 22
        if box:
            bw, bh = box.get("w", 150), box.get("h", 150)
            add_round_rect(slide, CONTENT_X + 22, y + 20, bw, bh, radius=0.06,
                           line="A9BE8C", line_w=1.6, dash="dash", fill="FBFCF8", tf=tf)
            add_text(slide, CONTENT_X + 22, y + 20, bw, bh, box.get("label", "画像 / 贴图"),
                     size=13, color="A9A18C", align="center", anchor="middle", tf=tf)
            fx = CONTENT_X + 22 + bw + 22
        fw = CONTENT_X + CONTENT_W - 22 - fx
        fy = y + 20
        for f in c.get("fields", []):
            add_text(slide, fx, fy, fw, 22, f.get("label", ""), size=14, bold=True,
                     color="5C6E48", tf=tf)
            fy += 24
            if _has_val(f.get("value")):
                arr = f["value"] if isinstance(f["value"], list) else [f["value"]]
                for item in arr:
                    add_text(slide, fx + 2, fy + 8, fw - 4, 26, item, size=14,
                             color="3A4A45", tf=tf)
                    add_line(slide, fx, fy + 34, fx + fw, fy + 34, "ADB79C", 1.3,
                             dash="sysDot", tf=tf)
                    fy += 38
            else:
                for _ in range(f.get("lines", 1)):
                    add_line(slide, fx, fy + 30, fx + fw, fy + 30, "ADB79C", 1.3,
                             dash="sysDot", tf=tf)
                    fy += 38
            fy += 12
        y += card_h + 20


def _has_val(v):
    if isinstance(v, list):
        return len(v) > 0
    return isinstance(v, str) and v.strip() != ""


def _fit_tf(start_y, natural_h, bottom=1075):
    """流式模板防溢出：内容自 start_y 起、自然高 natural_h，若超出页面可用高度，
    则仅压缩纵向（sx=1 保持字号/横向不变）。返回 TF。"""
    avail = bottom - start_y
    vk = min(1.0, avail / natural_h) if natural_h > 0 else 1.0
    return TF(sx=1.0, sy=vk, tx=0.0, ty=start_y * (1 - vk))


RENDERERS = {
    "table": render_table, "venn": render_venn, "ladder": render_ladder,
    "logic": render_logic, "voyage": render_voyage,
    "story_mountain": render_story_mountain, "fishbone": render_fishbone,
    "timeline": render_timeline, "bubble": render_bubble,
    "writing": render_writing, "draw": render_draw, "comic": render_comic,
    "profile": render_profile,
}


# ─────────────────────────── 引擎 ───────────────────────────
_QUOTE_MAP = str.maketrans({"「": "“", "」": "”", "『": "‘", "』": "’"})


def normalize_quotes(obj):
    if isinstance(obj, str):
        return obj.translate(_QUOTE_MAP)
    if isinstance(obj, list):
        return [normalize_quotes(x) for x in obj]
    if isinstance(obj, dict):
        return {k: normalize_quotes(v) for k, v in obj.items()}
    return obj


def _is_demo(fname):
    return fname.endswith("-示范")


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    manifest_path = pathlib.Path(sys.argv[1]).resolve()
    out_dir = pathlib.Path(sys.argv[2]).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    book = manifest.get("book", "阅读单")
    sheets = manifest.get("sheets", [])

    prs = Presentation()
    prs.slide_width = A4_W_EMU
    prs.slide_height = A4_H_EMU
    blank = prs.slide_layouts[6]

    unknown = []
    count = 0
    for s in sheets:
        if _is_demo(s["file"]):                     # 示范版已停产，自动跳过
            print("跳过(示范版已停产):", s["file"])
            continue
        key = s["template"]
        renderer = RENDERERS.get(key)
        slide = prs.slides.add_slide(blank)
        if renderer is None:
            unknown.append((s["file"], key))
            add_text(slide, 56, 400, 682, 200,
                     f"【缺少 PPTX renderer：模板「{key}」】\n请在 render_pptx.py 的 "
                     f"RENDERERS 注册 render_{key}，或以 PDF 版为准。",
                     size=18, color="B00020", align="center", anchor="middle")
            continue
        data = normalize_quotes(dict(s["data"]))
        renderer(slide, data)
        count += 1
        print("OK:", s["file"])

    out_path = out_dir / f"{book}-阅读单.pptx"
    try:
        prs.save(str(out_path))
    except OSError:
        out_path = out_path.with_name(f"{book}-阅读单.new.pptx")
        prs.save(str(out_path))
        sys.stderr.write(f"[warn] 目标被占用，已改写 {out_path.name}\n")
    print(f"\n完成 {count} 页 → {out_path}")
    if unknown:
        sys.stderr.write("[warn] 以下模板无 PPTX renderer（已占位提示，需补）：\n")
        for f, k in unknown:
            sys.stderr.write(f"   - {f}（template={k}）\n")


if __name__ == "__main__":
    main()
