# -*- coding: utf-8 -*-
"""通用绘制工具：文本框、矩形、占位框、表格。"""
import os
import math
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
    COLOR_NUMBOX_BG, COLOR_NUMBOX_FG, COLOR_BULLET_SEP,
    COLOR_RED_ACCENT, COLOR_CARD_BG, COLOR_CARD_BORDER,
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


def add_rich_textbox(slide, x, y, w, h, segments, *,
                    font=FONT_BODY, size=20, default_color="404040",
                    default_bold=False, default_italic=False,
                    align="left", anchor="top", line_spacing=1.2):
    """富文本框：segments = [(text, {color,bold,italic,size}), ...]。
    text 内 \n 自动换段；style 缺省回退到 default_*。"""
    box = slide.shapes.add_textbox(x, y, w, h)
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = Emu(0); tf.margin_right = Emu(0)
    tf.margin_top = Emu(0);  tf.margin_bottom = Emu(0)
    anchor_map = {"top": MSO_ANCHOR.TOP, "middle": MSO_ANCHOR.MIDDLE, "bottom": MSO_ANCHOR.BOTTOM}
    tf.vertical_anchor = anchor_map.get(anchor, MSO_ANCHOR.TOP)
    align_map = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER, "right": PP_ALIGN.RIGHT}

    p = tf.paragraphs[0]
    p.alignment = align_map.get(align, PP_ALIGN.LEFT)
    p.line_spacing = line_spacing

    for text, style in segments:
        for j, part in enumerate(str(text).split("\n")):
            if j > 0:
                p = tf.add_paragraph()
                p.alignment = align_map.get(align, PP_ALIGN.LEFT)
                p.line_spacing = line_spacing
            run = p.add_run()
            run.text = part
            f = run.font
            f.name = font
            f.size = Pt(style.get("size", size))
            f.bold = style.get("bold", default_bold)
            f.italic = style.get("italic", default_italic)
            f.color.rgb = rgb(style.get("color", default_color))
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


def add_image_grid(slide, x, y, w, h, suggestions, *, gap=None):
    """四图网格占位：把 2–4 条配图建议排成 2 列网格，每条一个占位框。

    用于"给你们看 N 幅画面"这类引导问题页（每幅一图，逐格各配一题）。
    suggestions：已过滤掉"无"的配图建议字符串列表（每条仍是三段式）。
    """
    sugs = [s for s in suggestions if s and s.strip() not in
            {"无", "无（页面已满）", "—", "无配图"}]
    n = len(sugs)
    if n == 0:
        return
    if gap is None:
        gap = Emu(int(w * 0.02))
    cols = 1 if n == 1 else 2
    rows = (n + cols - 1) // cols
    cell_w = (w - gap * (cols - 1)) // cols
    cell_h = (h - gap * (rows - 1)) // rows
    for i, sug in enumerate(sugs):
        r, c = divmod(i, cols)
        # 末行不足 cols 个时整行居中
        in_row = cols if (r + 1) * cols <= n else (n - r * cols)
        row_w = cell_w * in_row + gap * (in_row - 1)
        x_off = x + (w - row_w) // 2
        cx = x_off + c * (cell_w + gap)
        cy = y + r * (cell_h + gap)
        add_image_placeholder(slide, cx, cy, cell_w, cell_h, sug)


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


def add_conclusion_card(slide, x, y, w, h, text, *,
                        bg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER,
                        text_color=COLOR_RED_ACCENT, text_size=22):
    """要点小结首条结论卡：浅奶油圆角矩形 + 红字加粗。"""
    shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, w, h)
    try:
        shape.adjustments[0] = 0.18
    except Exception:
        pass
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(bg_color)
    shape.line.color.rgb = rgb(border_color)
    shape.line.width = Pt(1)
    _disable_shape_effects(shape)

    pad = Pt(20)
    add_textbox(
        slide, x + pad, y, w - 2 * pad, h, text,
        font=FONT_TITLE, size=text_size, color=text_color,
        bold=True, align="left", anchor="middle", line_spacing=1.4,
    )


def add_numbered_bullets(slide, x, y, w, h, bullets, *,
                          text_size=20, columns=1,
                          num_bg=COLOR_NUMBOX_BG, num_fg=COLOR_NUMBOX_FG,
                          text_color=COLOR_BODY,
                          line_spacing=1.45, start_index=1):
    """要点列表：红方块编号 + 文字。

    红方块去除主题阴影；要点之间不画分隔线。
    columns=1 默认；调用方可传 columns=2 改双列。
    """
    n = len(bullets)
    if n == 0:
        return
    cols = max(1, columns)
    rows_per_col = (n + cols - 1) // cols
    col_w = w // cols
    row_h = h // rows_per_col

    # 方块尺寸：随字号缩放
    box_side = Pt(text_size + 8)
    text_gap = Pt(14)   # 方块到文字的横向间隙

    for i, b in enumerate(bullets):
        col = i // rows_per_col
        row = i % rows_per_col
        cx = x + col * col_w
        cy = y + row * row_h
        box_top = cy + Pt(2)

        # 红方块（去阴影）
        box_shape = add_rect(slide, cx, box_top, box_side, box_side, num_bg)
        _disable_shape_effects(box_shape)

        # 数字
        add_textbox(
            slide, cx, box_top, box_side, box_side,
            str(i + start_index),
            font=FONT_TITLE, size=text_size - 2, color=num_fg,
            bold=True, align="center", anchor="middle",
        )
        # 内容文字
        text_x = cx + box_side + text_gap
        text_w = col_w - box_side - text_gap - Pt(8)
        add_textbox(
            slide, text_x, cy, text_w, row_h,
            b,
            font=FONT_BODY, size=text_size, color=text_color,
            align="left", anchor="top", line_spacing=line_spacing,
        )


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


def _cell_segments(text):
    """单元格文本 → 行段列表（`<br>` 与 `\n` 均视为换行）。"""
    return str(text).replace("<br>", "\n").split("\n")


def _cell_maxlen(text):
    """单元格最长一行的字符数（按换行拆分后取最长段）。"""
    return max((len(s) for s in _cell_segments(text)), default=0)


def _content_col_widths(headers, rows, total_w):
    """按各列"最长一行内容"自适应列宽：短列窄、长列宽。

    用 len^0.7 软化极端差异，避免某一长列吃掉几乎全部宽度；每列设字符数下限 3。
    返回 EMU 整数列表，合计 == total_w。
    """
    ncols = len(headers)
    maxlen = [max(3, _cell_maxlen(headers[c])) for c in range(ncols)]
    for row in rows:
        for c in range(ncols):
            if c < len(row):
                maxlen[c] = max(maxlen[c], _cell_maxlen(row[c]))
    weights = [m ** 0.7 for m in maxlen]
    tot = sum(weights) or 1.0
    widths = [int(int(total_w) * wt / tot) for wt in weights]
    widths[-1] = int(total_w) - sum(widths[:-1])   # 余数归末列，保证合计精确
    return widths


def _fit_table_font(headers, rows, widths_emu, area_h_emu, marg_pt,
                    size_hi=16, size_lo=10):
    """自适应字号：从 size_hi 往下试，找到"全表估算高度 ≤ 区域高度"的最大字号。

    估算逐行：每个单元格按列宽换算每行可容字符数（中文按 1 em≈字号宽），
    对每个换行段做 ceil(段长/每行字符数) 累加得该格行数，取本行各格最大行数。
    返回 (字号, [每行高度EMU]).
    """
    widths_pt = [wd / 914400 * 72 for wd in widths_emu]
    area_h_pt = area_h_emu / 914400 * 72
    all_rows = [headers] + list(rows)
    ncols = len(headers)

    best = None
    for fs in range(size_hi, size_lo - 1, -1):
        line_h = fs * 1.32           # 行距（含 1.1 行间）
        row_heights_pt = []
        total = 0.0
        for row in all_rows:
            row_lines = 1
            for c in range(ncols):
                txt = row[c] if c < len(row) else ""
                avail_pt = max(8.0, widths_pt[c] - 2 * marg_pt)
                cpl = max(1, int(avail_pt / (fs * 1.02)))   # 每行可容字符数（中文为主）
                cell_lines = 0
                for seg in _cell_segments(txt):
                    cell_lines += max(1, math.ceil(len(seg) / cpl))
                row_lines = max(row_lines, cell_lines)
            rh = row_lines * line_h + 2 * marg_pt
            row_heights_pt.append(rh)
            total += rh
        if total <= area_h_pt:
            best = (fs, row_heights_pt)
            break
    if best is None:
        # 连最小字号也放不下：用最小字号，并把行高等比压进区域（宁可挤，不可出界）
        fs = size_lo
        line_h = fs * 1.32
        row_heights_pt = []
        total = 0.0
        for row in all_rows:
            row_lines = 1
            for c in range(ncols):
                txt = row[c] if c < len(row) else ""
                avail_pt = max(8.0, widths_pt[c] - 2 * marg_pt)
                cpl = max(1, int(avail_pt / (fs * 1.02)))
                cell_lines = sum(max(1, math.ceil(len(s) / cpl)) for s in _cell_segments(txt))
                row_lines = max(row_lines, cell_lines)
            rh = row_lines * line_h + 2 * marg_pt
            row_heights_pt.append(rh); total += rh
        scale = area_h_pt / total if total else 1.0
        row_heights_pt = [rh * scale for rh in row_heights_pt]
        best = (fs, row_heights_pt)

    fs, row_heights_pt = best
    row_heights_emu = [Emu(int(rh / 72 * 914400)) for rh in row_heights_pt]
    return fs, row_heights_emu


def add_table(slide, x, y, w, h, headers, rows,
              head_bg="44546A", head_fg="FFFFFF",
              head_size=None, body_size=None,
              zebra_bg="F5F5F5"):
    """添加表格：无边框 + 表头深色 + 斑马纹，并**自适应塞进给定区域**。

    - `<br>` / `\n` 渲染为单元格内真实换行（多段落），不再印出字面量；
    - 列宽按内容长短分配（短列窄、长列宽）；
    - 字号按行数/内容自动下调（投屏可读下限 10pt），行高均分以不超出区域 h；
    - head_size/body_size 传 None 时自动定档；显式传入则作为上限基准。
    样式：表头深灰蓝粗体白字居中；正文行白/浅灰交替、左对齐、垂直居中；无可见边框。
    """
    n_cols = len(headers)
    n_rows = len(rows) + 1
    dense = n_rows >= 7

    # 边距（密集表收紧）
    marg_l = Emu(45720) if dense else Emu(82296)   # 0.05" / 0.09"
    marg_t = Emu(13716) if dense else Emu(27432)   # 0.015" / 0.03"
    marg_pt = (marg_l / 914400 * 72)

    # 列宽（内容自适应）
    widths = _content_col_widths(headers, rows, w)

    # 自适应字号 + 逐行行高（确保合计 ≤ 区域高度 h）
    size_hi = body_size if body_size else 16
    auto_fs, row_heights = _fit_table_font(headers, rows, widths, h, marg_pt, size_hi=size_hi)
    body_fs = auto_fs
    head_fs = head_size if head_size else min(auto_fs + 2, 18)

    shape = slide.shapes.add_table(n_rows, n_cols, x, y, w, h)
    table = shape.table

    for c in range(n_cols):
        table.columns[c].width = widths[c]
    for r in range(n_rows):
        table.rows[r].height = row_heights[r]

    def style_cell(cell, text, *, fill_color, font_color, size, bold, align):
        _remove_cell_borders(cell)
        cell.fill.solid()
        cell.fill.fore_color.rgb = rgb(fill_color)
        cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        cell.text = ""
        tf = cell.text_frame
        tf.word_wrap = True
        tf.margin_left = marg_l
        tf.margin_right = marg_l
        tf.margin_top = marg_t
        tf.margin_bottom = marg_t
        align_map = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER}
        for j, seg in enumerate(_cell_segments(text)):
            p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
            p.alignment = align_map.get(align, PP_ALIGN.LEFT)
            p.line_spacing = 1.1
            run = p.add_run()
            run.text = seg
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
            size=head_fs, bold=True, align="center",
        )

    # 数据行（斑马纹：奇数行白，偶数行浅灰）
    for r, row in enumerate(rows, start=1):
        bg = "FFFFFF" if r % 2 == 1 else zebra_bg
        for c in range(n_cols):
            text = row[c] if c < len(row) else ""
            style_cell(
                table.cell(r, c), text,
                fill_color=bg, font_color=COLOR_BODY,
                size=body_fs, bold=False, align="left",
            )

    return table


def set_ascii_font(textbox, font_name):
    """覆盖 textbox 内所有 run 的 latin 字体。
    用于纯数字/英文场景换装饰字体（如章节序号用 Bahnschrift）。"""
    for p in textbox.text_frame.paragraphs:
        for run in p.runs:
            rPr = run._r.get_or_add_rPr()
            for latin in rPr.findall(qn("a:latin")):
                rPr.remove(latin)
            latin = etree.SubElement(rPr, qn("a:latin"))
            latin.set("typeface", font_name)
