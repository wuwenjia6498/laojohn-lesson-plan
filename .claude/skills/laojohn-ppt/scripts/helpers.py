# -*- coding: utf-8 -*-
"""通用绘制工具：文本框、矩形、占位框、表格。"""
import os
from pptx.util import Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import qn
from lxml import etree

from theme import (
    FONT_TITLE, FONT_BODY, FONT_ASCII,
    COLOR_DASH, COLOR_BG_PLACE, COLOR_MUTED, COLOR_BODY,
    SZ_PLACEHOLDER,
)


def rgb(hex_str):
    return RGBColor.from_string(hex_str.lstrip("#"))


def add_textbox(slide, x, y, w, h, text, *,
                font=FONT_BODY, size=20, color="404040",
                bold=False, italic=False, align="left", anchor="top",
                line_spacing=1.2, first_line_indent_chars=0):
    """添加一个文本框。

    align: "left" | "center" | "right"
    anchor: "top" | "middle" | "bottom"
    """
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0)
    tf.margin_right = Emu(0)
    tf.margin_top = Emu(0)
    tf.margin_bottom = Emu(0)
    anchor_map = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
    tf.vertical_anchor = anchor_map.get(anchor, MSO_ANCHOR.TOP)

    align_map = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}

    lines = text.split("\n") if isinstance(text, str) else list(text)
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align_map.get(align, PP_ALIGN.LEFT)
        p.line_spacing = line_spacing
        if first_line_indent_chars:
            # 用全角空格模拟首行缩进
            line = "\u3000" * first_line_indent_chars + line
        run = p.add_run()
        run.text = line
        f = run.font
        f.name = font
        f.size = Pt(size)
        f.bold = bold
        f.italic = italic
        f.color.rgb = rgb(color)
        # 显式设置东亚字体
        _set_east_asia_font(run, font)
    return box


def _set_east_asia_font(run, font_name):
    """python-pptx 默认不设 eastAsia 字体，中文会回退到主题字体。手动注入。"""
    rPr = run._r.get_or_add_rPr()
    # 移除已有 eastAsia
    for ea in rPr.findall(qn("a:ea")):
        rPr.remove(ea)
    ea = etree.SubElement(rPr, qn("a:ea"))
    ea.set("typeface", font_name)
    # latin 设为 Calibri，避免中文字体应用到英文/数字时显丑
    for latin in rPr.findall(qn("a:latin")):
        rPr.remove(latin)
    latin = etree.SubElement(rPr, qn("a:latin"))
    latin.set("typeface", FONT_ASCII)


def add_rect(slide, x, y, w, h, fill_color, line=False, line_color=None):
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill_color)
    if line:
        shape.line.color.rgb = rgb(line_color or fill_color)
        shape.line.width = Pt(0.5)
    else:
        shape.line.fill.background()
    return shape


def add_gradient_rect(slide, x, y, w, h, color_from, color_to, angle_deg=135):
    """添加线性渐变矩形（无边框）。

    angle_deg：渐变方向角度。0=从左到右；90=从上到下；135=从左上到右下。
    OpenXML 用 60000 单位 = 1 度。
    """
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    spPr = shape.fill._xPr
    # 移除现有 fill 元素（必须放在 ln 之前；先清空避免冲突）
    for tag in ("a:noFill", "a:solidFill", "a:gradFill", "a:blipFill", "a:pattFill"):
        for el in spPr.findall(qn(tag)):
            spPr.remove(el)

    # 渐变填充：在 ln 元素之前插入
    ln_elem = spPr.find(qn("a:ln"))
    gradFill = etree.Element(qn("a:gradFill"))
    gradFill.set("flip", "none")
    gradFill.set("rotWithShape", "1")

    gsLst = etree.SubElement(gradFill, qn("a:gsLst"))
    for pos, color in [("0", color_from), ("100000", color_to)]:
        gs = etree.SubElement(gsLst, qn("a:gs"))
        gs.set("pos", pos)
        srgb = etree.SubElement(gs, qn("a:srgbClr"))
        srgb.set("val", color.lstrip("#"))

    lin = etree.SubElement(gradFill, qn("a:lin"))
    lin.set("ang", str(int(angle_deg * 60000)))
    lin.set("scaled", "0")
    etree.SubElement(gradFill, qn("a:tileRect"))

    if ln_elem is not None:
        ln_elem.addprevious(gradFill)
    else:
        spPr.append(gradFill)

    # 去边框
    shape.line.fill.background()
    return shape


def add_dashed_rect(slide, x, y, w, h, fill_color=COLOR_BG_PLACE, line_color=COLOR_DASH):
    """虚线矩形（用于配图占位框）。"""
    shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, x, y, w, h)
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(fill_color)
    shape.line.color.rgb = rgb(line_color)
    shape.line.width = Pt(1.25)
    # 设置虚线：操作底层 XML
    spPr = shape.line._get_or_add_ln()
    # 移除已有 prstDash
    for d in spPr.findall(qn("a:prstDash")):
        spPr.remove(d)
    dash = etree.SubElement(spPr, qn("a:prstDash"))
    dash.set("val", "dash")
    return shape


def add_image_placeholder(slide, x, y, w, h, suggestion: str):
    """配图占位框：浅灰底 + 虚线 + 📷 + 多行说明。

    suggestion 形如：苏七块·正骨场景｜书内P17–20｜建议元素：正骨大夫、银元、病患
    """
    add_dashed_rect(slide, x, y, w, h)

    # 占位框内文本
    parts = [p.strip() for p in suggestion.split("｜") if p.strip()]
    lines = ["📷 建议配图"]
    if parts:
        lines.append("")
        lines.extend(parts)

    add_textbox(
        slide, x, y, w, h,
        "\n".join(lines),
        font=FONT_BODY, size=SZ_PLACEHOLDER, color=COLOR_MUTED,
        align="center", anchor="middle", line_spacing=1.5,
    )


def add_logo(slide, logo_path, x, y, w, h=None):
    """添加 LOGO。h=None 时按图片原比例自动缩放（推荐，避免拉伸变形）。"""
    if logo_path and os.path.isfile(logo_path):
        if h is None:
            slide.shapes.add_picture(logo_path, x, y, width=w)
        else:
            slide.shapes.add_picture(logo_path, x, y, w, h)


def add_image_or_skip(slide, image_path, x, y, w, h):
    """安全添加图片：文件不存在时静默跳过。"""
    if image_path and os.path.isfile(image_path):
        slide.shapes.add_picture(image_path, x, y, w, h)


def _disable_shape_effects(shape):
    """禁用形状默认阴影等效果。注入空 <a:effectLst/> 元素覆盖主题 effect。"""
    spPr = shape.fill._xPr
    # 移除已有 effectLst / effectDag
    for tag in ("a:effectLst", "a:effectDag"):
        for el in spPr.findall(qn(tag)):
            spPr.remove(el)
    # 插入空 effectLst（必须在 scene3d/sp3d 之前，但放最后通常也兼容）
    etree.SubElement(spPr, qn("a:effectLst"))


def _remove_cell_borders(cell):
    """移除单元格四边边框（设为 noFill）。"""
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for side in ("lnL", "lnR", "lnT", "lnB"):
        # 移除已有
        for ln in tcPr.findall(qn(f"a:{side}")):
            tcPr.remove(ln)
        # 添加 noFill
        ln = etree.SubElement(tcPr, qn(f"a:{side}"))
        ln.set("w", "0")
        etree.SubElement(ln, qn("a:noFill"))


def add_table(slide, x, y, w, h, headers, rows,
              head_bg="44546A", head_fg="FFFFFF",
              head_size=18, body_size=16,
              zebra_bg="F5F5F5",
              min_row_h_pt=44):
    """添加表格：无边框 + 表头深色 + 斑马纹。

    样式参考：表头深灰蓝粗体白字居中；正文行白/浅灰交替、左对齐、垂直居中；无可见边框。
    """
    n_cols = len(headers)
    n_rows = len(rows) + 1
    shape = slide.shapes.add_table(n_rows, n_cols, x, y, w, h)
    table = shape.table

    # 行高
    row_h = Emu(int(Pt(min_row_h_pt)))
    for r in range(n_rows):
        table.rows[r].height = row_h

    def style_cell(cell, text, *, fill_color, font_color, size, bold, align):
        # 边框
        _remove_cell_borders(cell)
        # 填充
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(fill_color)
        # 垂直居中
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        # 文本
        cell.text = ""
        tf = cell.text_frame
        tf.margin_left = Emu(91440)   # 0.1"
        tf.margin_right = Emu(91440)
        tf.margin_top = Emu(36000)
        tf.margin_bottom = Emu(36000)
        p = tf.paragraphs[0]
        p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER}.get(align, PP_ALIGN.LEFT)
        run = p.add_run()
        run.text = text
        run.font.name = FONT_TITLE if bold else FONT_BODY
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.color.rgb = rgb(font_color)
        _set_east_asia_font(run, FONT_TITLE if bold else FONT_BODY)

    # 表头
    for c, header in enumerate(headers):
        style_cell(
            table.cell(0, c), header,
            fill_color=head_bg, font_color=head_fg,
            size=head_size, bold=True, align="center",
        )

    # 数据行（斑马纹：奇数行白，偶数行浅灰；r 从 1 开始，所以 r 奇=白，r 偶=灰）
    for r, row in enumerate(rows, start=1):
        bg = "FFFFFF" if r % 2 == 1 else zebra_bg
        for c in range(n_cols):
            text = row[c] if c < len(row) else ""
            style_cell(
                table.cell(r, c), text,
                fill_color=bg, font_color=COLOR_BODY,
                size=body_size, bold=False, align="left",
            )

    return table
