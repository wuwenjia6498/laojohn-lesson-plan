# -*- coding: utf-8 -*-
"""6 种页型渲染函数。

每个函数签名：render_<type>(slide, page, ctx)
ctx 提供：course_name, page_index, page_total, logo_path, banner_path
"""
from pptx.util import Emu, Pt
from pptx.enum.shapes import MSO_SHAPE
from helpers import (
    add_textbox, add_rect, add_logo, add_image_or_skip,
    add_image_placeholder, add_table, rgb,
    add_gradient_rect, _disable_shape_effects,
)
from theme import (
    FONT_TITLE, FONT_BODY,
    COLOR_ANCHOR_BAR, COLOR_TITLE, COLOR_BODY, COLOR_MUTED, COLOR_ACCENT,
    COLOR_BG_QUOTE, COLOR_END_BG_FROM, COLOR_END_BG_TO,
    SZ_COVER_TITLE, SZ_COVER_SUB, SZ_COVER_META,
    SZ_ANCHOR_LABEL, SZ_PAGE_EYEBROW, SZ_HEADING, SZ_BODY, SZ_QUOTE,
    SZ_SUBTITLE, SZ_TABLE_HEAD, SZ_TABLE_BODY, SZ_PAGE_NUM,
    # 坐标
    ANCHOR_BAR_X, ANCHOR_BAR_Y, ANCHOR_BAR_W, ANCHOR_BAR_H,
    ANCHOR_LABEL_X, ANCHOR_LABEL_Y, ANCHOR_LABEL_W, ANCHOR_LABEL_H,
    LOGO_COVER_X, LOGO_COVER_Y, LOGO_COVER_W,
    LOGO_INNER_X, LOGO_INNER_Y, LOGO_INNER_W,
    PAGE_NUM_X, PAGE_NUM_Y, PAGE_NUM_W, PAGE_NUM_H,
    PLACEHOLDER_REGIONS,
    GUIDE_TITLE_X, GUIDE_TITLE_Y, GUIDE_TITLE_W, GUIDE_TITLE_H,
    GUIDE_BULLETS_X, GUIDE_BULLETS_Y, GUIDE_BULLETS_W, GUIDE_BULLETS_H,
    SECTION_TITLE_X, SECTION_TITLE_Y, SECTION_TITLE_W, SECTION_TITLE_H,
    SECTION_LEAD_X, SECTION_LEAD_Y, SECTION_LEAD_W, SECTION_LEAD_H,
    QUOTE_BG_X, QUOTE_BG_Y, QUOTE_BG_W, QUOTE_BG_H,
    QUOTE_TITLE_X, QUOTE_TITLE_Y, QUOTE_TITLE_W, QUOTE_TITLE_H,
    QUOTE_BODY_X, QUOTE_BODY_Y, QUOTE_BODY_W, QUOTE_BODY_H,
    SUMMARY_TITLE_X, SUMMARY_TITLE_Y, SUMMARY_TITLE_W, SUMMARY_TITLE_H,
    SUMMARY_BULLETS_X, SUMMARY_BULLETS_Y, SUMMARY_BULLETS_W, SUMMARY_BULLETS_H,
    TABLE_TITLE_X, TABLE_TITLE_Y, TABLE_TITLE_W, TABLE_TITLE_H,
    TABLE_SUBTITLE_X, TABLE_SUBTITLE_Y, TABLE_SUBTITLE_W, TABLE_SUBTITLE_H,
    TABLE_AREA_X, TABLE_AREA_Y, TABLE_AREA_W, TABLE_AREA_H,
    COVER_TITLE_X, COVER_TITLE_Y, COVER_TITLE_W, COVER_TITLE_H,
    COVER_SUB_X, COVER_SUB_Y, COVER_SUB_W, COVER_SUB_H,
    COVER_META_X, COVER_META_Y, COVER_META_W, COVER_META_H,
    COVER_BANNER_X, COVER_BANNER_Y, COVER_BANNER_W, COVER_BANNER_H,
    COVER_TRI_X, COVER_TRI_Y, COVER_TRI_W, COVER_TRI_H,
    SLIDE_W, SLIDE_H, pct_x, pct_y,
)


# ---------- 通用元素 ----------
def draw_anchor(slide, label_text: str):
    """左上色条 + 章节铭牌（仅内页用）。

    label_text: 显示在色条右侧，通常是 page.eyebrow（如"情境导入""猜书名""作者的话"）。
    """
    add_rect(slide, ANCHOR_BAR_X, ANCHOR_BAR_Y, ANCHOR_BAR_W, ANCHOR_BAR_H,
             COLOR_ANCHOR_BAR)
    add_textbox(
        slide, ANCHOR_LABEL_X, ANCHOR_LABEL_Y, ANCHOR_LABEL_W, ANCHOR_LABEL_H,
        label_text or "",
        font=FONT_TITLE, size=SZ_ANCHOR_LABEL,
        color=COLOR_TITLE, bold=True, anchor="middle", align="left",
    )


def draw_logo_inner(slide, logo_path):
    # 高度按图片原比例自动缩放
    add_logo(slide, logo_path, LOGO_INNER_X, LOGO_INNER_Y, LOGO_INNER_W)


def draw_logo_cover(slide, logo_path):
    add_logo(slide, logo_path, LOGO_COVER_X, LOGO_COVER_Y, LOGO_COVER_W)


def draw_page_num(slide, idx: int, total: int):
    add_textbox(
        slide, PAGE_NUM_X, PAGE_NUM_Y, PAGE_NUM_W, PAGE_NUM_H,
        f"{idx} / {total}",
        font=FONT_BODY, size=SZ_PAGE_NUM, color=COLOR_MUTED, align="right",
    )


def draw_cover_triangle(slide):
    """封面左侧的深灰蓝朝右三角形装饰（▷），从横幅左边缘伸出。"""
    x = COVER_TRI_X
    y = COVER_TRI_Y
    w = COVER_TRI_W
    h = COVER_TRI_H

    # FreeformBuilder：起点 (x, y) = 左上角
    # 路径：左上 → 右中 → 左下 → 闭合回左上
    builder = slide.shapes.build_freeform(x, y, scale=1.0)
    builder.add_line_segments([
        (x + w, y + h // 2),  # 右中（三角尖端）
        (x, y + h),           # 左下
    ], close=True)
    shape = builder.convert_to_shape()
    shape.fill.solid()
    shape.fill.fore_color.rgb = rgb(COLOR_ANCHOR_BAR)
    shape.line.fill.background()


def draw_eyebrow(slide, page):
    """已废弃：眉标内容现在放在左上 anchor label 中。此函数保留为空。"""
    return


def maybe_placeholder(slide, page):
    sug = (page.image_suggestion or "").strip()
    if not sug or sug in {"无", "无（页面已满）", "—", "无配图"}:
        return
    region = PLACEHOLDER_REGIONS.get(page.page_type)
    if not region:
        return
    add_image_placeholder(slide, *region, suggestion=sug)


def bullets_text(bullets):
    """要点列表 → 带数字圆圈的多行文本。"""
    circle = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]
    out = []
    for i, b in enumerate(bullets):
        marker = circle[i] if i < len(circle) else f"{i+1}."
        out.append(f"{marker}  {b}")
    return "\n".join(out)


# ---------- 6 种页型 ----------
def render_cover(slide, page, ctx):
    # 顶部横幅（四周留白边）
    add_image_or_skip(
        slide, ctx.get("banner_path"),
        COVER_BANNER_X, COVER_BANNER_Y,
        COVER_BANNER_W, COVER_BANNER_H,
    )
    # 左侧装饰五边形（横幅左边缘伸出）
    draw_cover_triangle(slide)
    # LOGO（位于横幅内部右上角，仅宽度，保持原比例）
    draw_logo_cover(slide, ctx.get("logo_path"))

    # 大标题：自动包书名号、斜体（叠在横幅中央）；不加粗
    title_text = (page.title or ctx.get("book_title", "")).strip()
    if title_text and not (title_text.startswith("《") and title_text.endswith("》")):
        title_text = f"《{title_text}》"
    add_textbox(
        slide, COVER_TITLE_X, COVER_TITLE_Y, COVER_TITLE_W, COVER_TITLE_H,
        title_text,
        font=FONT_TITLE, size=SZ_COVER_TITLE, color=COLOR_TITLE,
        bold=False, italic=True, align="center", anchor="middle",
    )
    # 副标题/课时（叠在横幅，标题下方）；斜体
    sub = page.subtitle or ctx.get("course_name", "")
    if sub:
        add_textbox(
            slide, COVER_SUB_X, COVER_SUB_Y, COVER_SUB_W, COVER_SUB_H,
            sub,
            font=FONT_TITLE, size=SZ_COVER_SUB, color=COLOR_TITLE,
            italic=True, align="center", anchor="middle",
        )
    # 作者元信息（左下角，左对齐；支持正文多行）
    meta_text = page.body or ctx.get("meta", "")
    if meta_text:
        add_textbox(
            slide, COVER_META_X, COVER_META_Y, COVER_META_W, COVER_META_H,
            meta_text,
            font=FONT_BODY, size=SZ_COVER_META, color=COLOR_BODY,
            align="left", anchor="top", line_spacing=1.8,
        )


def render_section(slide, page, ctx):
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    # 居中大标题
    add_textbox(
        slide, SECTION_TITLE_X, SECTION_TITLE_Y, SECTION_TITLE_W, SECTION_TITLE_H,
        page.title,
        font=FONT_TITLE, size=SZ_HEADING + 4,   # 环节标题略大
        color=COLOR_TITLE, bold=True,
        align="left", anchor="middle", line_spacing=1.3,
    )
    if page.body:
        add_textbox(
            slide, SECTION_LEAD_X, SECTION_LEAD_Y, SECTION_LEAD_W, SECTION_LEAD_H,
            page.body,
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            align="left", anchor="top", line_spacing=1.6,
        )
    maybe_placeholder(slide, page)


def render_guide(slide, page, ctx):
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    add_textbox(
        slide, GUIDE_TITLE_X, GUIDE_TITLE_Y, GUIDE_TITLE_W, GUIDE_TITLE_H,
        page.title,
        font=FONT_TITLE, size=SZ_HEADING, color=COLOR_TITLE, bold=True,
        align="left", anchor="middle", line_spacing=1.3,
    )

    if page.bullets:
        add_textbox(
            slide, GUIDE_BULLETS_X, GUIDE_BULLETS_Y, GUIDE_BULLETS_W, GUIDE_BULLETS_H,
            bullets_text(page.bullets),
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.8, align="left", anchor="top",
        )
    elif page.body:
        add_textbox(
            slide, GUIDE_BULLETS_X, GUIDE_BULLETS_Y, GUIDE_BULLETS_W, GUIDE_BULLETS_H,
            page.body,
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.8, align="left", anchor="top",
        )

    maybe_placeholder(slide, page)


def render_quote(slide, page, ctx):
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    # 书页底
    add_rect(slide, QUOTE_BG_X, QUOTE_BG_Y, QUOTE_BG_W, QUOTE_BG_H, COLOR_BG_QUOTE)

    if page.title:
        add_textbox(
            slide, QUOTE_TITLE_X, QUOTE_TITLE_Y, QUOTE_TITLE_W, QUOTE_TITLE_H,
            page.title,
            font=FONT_TITLE, size=SZ_HEADING - 4, color=COLOR_TITLE, bold=True,
            align="left", anchor="middle",
        )
    if page.body:
        add_textbox(
            slide, QUOTE_BODY_X, QUOTE_BODY_Y, QUOTE_BODY_W, QUOTE_BODY_H,
            page.body,
            font=FONT_BODY, size=SZ_QUOTE, color=COLOR_TITLE,
            line_spacing=1.8, first_line_indent_chars=2,
            align="left", anchor="top",
        )


def render_summary(slide, page, ctx):
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    add_textbox(
        slide, SUMMARY_TITLE_X, SUMMARY_TITLE_Y, SUMMARY_TITLE_W, SUMMARY_TITLE_H,
        page.title,
        font=FONT_TITLE, size=SZ_HEADING, color=COLOR_TITLE, bold=True,
        align="left", anchor="middle", line_spacing=1.3,
    )
    if page.bullets:
        add_textbox(
            slide, SUMMARY_BULLETS_X, SUMMARY_BULLETS_Y, SUMMARY_BULLETS_W, SUMMARY_BULLETS_H,
            bullets_text(page.bullets),
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.8, align="left", anchor="top",
        )
    elif page.body:
        add_textbox(
            slide, SUMMARY_BULLETS_X, SUMMARY_BULLETS_Y, SUMMARY_BULLETS_W, SUMMARY_BULLETS_H,
            page.body,
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.8, align="left", anchor="top",
        )
    maybe_placeholder(slide, page)


def render_table(slide, page, ctx):
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    add_textbox(
        slide, TABLE_TITLE_X, TABLE_TITLE_Y, TABLE_TITLE_W, TABLE_TITLE_H,
        page.title,
        font=FONT_TITLE, size=SZ_HEADING - 2, color=COLOR_TITLE, bold=True,
        align="left", anchor="middle",
    )
    if page.subtitle:
        add_textbox(
            slide, TABLE_SUBTITLE_X, TABLE_SUBTITLE_Y, TABLE_SUBTITLE_W, TABLE_SUBTITLE_H,
            page.subtitle,
            font=FONT_BODY, size=SZ_SUBTITLE, color=COLOR_MUTED,
            align="left", anchor="middle",
        )
    if page.table_headers:
        add_table(
            slide, TABLE_AREA_X, TABLE_AREA_Y, TABLE_AREA_W, TABLE_AREA_H,
            page.table_headers, page.table_rows,
            head_size=SZ_TABLE_HEAD, body_size=SZ_TABLE_BODY,
        )


RENDERERS = {
    "封面": render_cover,
    "环节标题": render_section,
    "引导问题": render_guide,
    "原文齐读": render_quote,
    "要点小结": render_summary,
    "填空表格": render_table,
    "_END": None,   # 占位，下文赋值
}


# ---------- END 结束页 ----------
def render_end(slide, page, ctx):
    """每节课 PPT 末页：青绿渐变 + 居中 END + 老约翰白 LOGO + 右下"下一次再见 ▶"。

    不参与页码计数；page 参数仅占位，本函数不读取其内容。
    """
    # 渐变底（四周留白，参考封面横幅留白比例）：右上 #1E7A79 → 左下 #8FBBBA
    # OpenXML 渐变线角度：顺时针，0°=左→右；从右上→左下 = 225°
    gx = pct_x(0.025)
    gy = pct_y(0.040)
    gw = pct_x(0.950)
    gh = pct_y(0.920)
    add_gradient_rect(slide, gx, gy, gw, gh,
                      "1E7A79", "8FBBBA", angle_deg=225)

    # 左上深灰蓝小色块（与内页 anchor bar 同位）
    add_rect(slide, ANCHOR_BAR_X, ANCHOR_BAR_Y, ANCHOR_BAR_W, ANCHOR_BAR_H,
             COLOR_ANCHOR_BAR)

    # 中央 END（白色，120pt）
    add_textbox(
        slide, pct_x(0.10), pct_y(0.36), pct_x(0.80), pct_y(0.24),
        "END",
        font=FONT_TITLE, size=120, color="FFFFFF",
        bold=False, italic=False, align="center", anchor="middle",
    )

    # 底部居中：白色 LOGO（宽度略大 → 10%）
    logo_white = ctx.get("logo_white_path") or ctx.get("logo_path")
    if logo_white:
        logo_w = pct_x(0.10)
        # 水平居中：x = (1 - 0.10) / 2 = 0.45
        add_logo(slide, logo_white, pct_x(0.45), pct_y(0.85), logo_w)

    # 右下："下一次再见"（字号 20，上移）
    # 文本框中心 y = 0.82 + 0.06/2 = 0.85
    add_textbox(
        slide, pct_x(0.62), pct_y(0.82), pct_x(0.26), pct_y(0.06),
        "下一次再见",
        font=FONT_TITLE, size=20, color="FFFFFF",
        bold=False, align="right", anchor="middle",
    )

    # 右下白色三角箭头 ▶（与"下一次再见"中线对齐：中心 y = 0.85）
    tri_x = pct_x(0.905)
    tri_y = pct_y(0.810)
    tri_w = pct_x(0.060)
    tri_h = pct_y(0.080)
    builder = slide.shapes.build_freeform(tri_x, tri_y, scale=1.0)
    builder.add_line_segments([
        (tri_x + tri_w, tri_y + tri_h // 2),  # 右中
        (tri_x, tri_y + tri_h),               # 左下
    ], close=True)
    arrow = builder.convert_to_shape()
    arrow.fill.solid()
    arrow.fill.fore_color.rgb = rgb("FFFFFF")
    arrow.line.fill.background()
    # 显式禁用 effectLst（去除默认主题阴影）
    _disable_shape_effects(arrow)


RENDERERS["_END"] = render_end
