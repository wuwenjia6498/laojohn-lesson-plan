# -*- coding: utf-8 -*-
"""6 种页型渲染函数。

每个函数签名：render_<type>(slide, page, ctx)
ctx 提供：course_name, page_index, page_total, logo_path, banner_path
"""
import re
from pptx.util import Emu, Pt
from pptx.enum.shapes import MSO_SHAPE
from helpers import (
    add_textbox, add_rect, add_logo, add_image_or_skip,
    add_image_placeholder, add_image_grid, add_table, cell_bg_color, rgb,
    add_gradient_rect, _disable_shape_effects,
    add_numbered_bullets, add_click_reveal,
    add_rich_textbox, add_conclusion_card,
    set_ascii_font,
)
from theme import (
    FONT_TITLE, FONT_BODY,
    COLOR_ANCHOR_BAR, COLOR_TITLE, COLOR_BODY, COLOR_MUTED, COLOR_ACCENT,
    COLOR_BG_QUOTE, COLOR_END_BG_FROM, COLOR_END_BG_TO,
    COLOR_SECTION_BG, COLOR_SECTION_FG, COLOR_SECTION_SUB,
    COLOR_SECTION_NUM, COLOR_SECTION_PG,
    COLOR_QMARK_WATER, COLOR_RED_ACCENT,
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
    IMAGE_GRID_REGION, IMAGE_GRID_GAP,
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
    # 已取消：课件不在右下角标注页码（页号以课件系统实际翻页为准）。
    # 保留函数签名与各页型调用，便于将来需要时一处恢复。
    return


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
    """环节标题：多环节显示巨型序号；单环节自动隐藏序号、居中标题。"""
    section_total = getattr(page, "_section_total", 1)
    is_solo = (section_total <= 1)

    # 深灰蓝色块（共用）
    add_rect(slide, pct_x(0.025), pct_y(0.040),
             pct_x(0.950), pct_y(0.920),
             COLOR_SECTION_BG)

    if not is_solo:
        # 多环节：保留巨型序号
        section_no = getattr(page, "_section_no", 1)
        section_box = add_textbox(
            slide, pct_x(0.08), pct_y(0.17), pct_x(0.35), pct_y(0.30),
            f"{section_no:02d}",
            font=FONT_TITLE, size=200, color=COLOR_SECTION_NUM,
            bold=False, italic=True, align="left", anchor="middle",
        )
        set_ascii_font(section_box, "Bahnschrift")
        add_rect(slide, pct_x(0.08), pct_y(0.51), pct_x(0.08), Emu(38000),
                 COLOR_RED_ACCENT)
        add_textbox(
            slide, pct_x(0.08), pct_y(0.55), pct_x(0.84), pct_y(0.16),
            page.title,
            font=FONT_TITLE, size=44, color=COLOR_SECTION_FG, bold=True,
            align="left", anchor="middle", line_spacing=1.3,
        )
        if page.body:
            add_textbox(
                slide, pct_x(0.08), pct_y(0.73), pct_x(0.84), pct_y(0.16),
                page.body,
                font=FONT_BODY, size=22, color=COLOR_SECTION_SUB,
                align="left", anchor="top", line_spacing=1.6,
            )
    else:
        # 单环节：去掉序号，居中大标题 + 红色短分隔 + 副本
        add_textbox(
            slide, pct_x(0.08), pct_y(0.34), pct_x(0.84), pct_y(0.14),
            page.title,
            font=FONT_TITLE, size=54, color=COLOR_SECTION_FG, bold=True,
            align="center", anchor="middle", line_spacing=1.3,
        )
        add_rect(slide, pct_x(0.46), pct_y(0.50), pct_x(0.08), Emu(38000),
                 COLOR_RED_ACCENT)
        if page.body:
            add_textbox(
                slide, pct_x(0.15), pct_y(0.55), pct_x(0.70), pct_y(0.20),
                page.body,
                font=FONT_BODY, size=22, color=COLOR_SECTION_SUB,
                align="center", anchor="top", line_spacing=1.6,
            )

    # LOGO（页码已取消：环节标题页也不再标注右下角页码）
    logo_white = ctx.get("logo_white_path") or ctx.get("logo_path")
    if logo_white:
        add_logo(slide, logo_white, LOGO_INNER_X, LOGO_INNER_Y, LOGO_INNER_W)


def _real_suggestions(page):
    """返回该页有效配图建议列表（过滤"无"等占位写法）。"""
    raw = getattr(page, "image_suggestions", None) or (
        [page.image_suggestion] if page.image_suggestion else [])
    return [s for s in raw if s and s.strip() not in
            {"无", "无（页面已满）", "—", "无配图"}]


def render_guide(slide, page, ctx):
    """引导问题（方案 A）：
    - 右半区一个超大半透明问号水印
    - 标题左侧加一根红色 ▎竖色条作为视觉引导
    - 其余排版（铭牌/要点/占位）沿用

    四图网格模式：当本页带 ≥2 条配图建议时，标题下整幅排 2×2 占位网格
    （"给你们看 N 幅画面"类页），此模式不画问号水印、不渲染要点文本。
    """
    grid_sugs = _real_suggestions(page)
    grid_mode = len(grid_sugs) >= 2

    # 水印优先画（被后续元素覆盖）；网格模式不画，避免从格缝透出
    if not grid_mode:
        guide_no = getattr(page, "_guide_no", 1)
        add_textbox(
            slide, pct_x(0.50), pct_y(0.20), pct_x(0.48), pct_y(0.55),
            f"Q{guide_no}",
            font=FONT_TITLE, size=240, color=COLOR_QMARK_WATER,
            bold=True, italic=True, align="center", anchor="middle",
        )

    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    # 标题左侧红色竖色条 ▎
    add_rect(slide, pct_x(0.070), pct_y(0.245), Emu(50000), pct_y(0.130),
             COLOR_RED_ACCENT)

    # 标题（整体右移给红色竖条让出位置）
    title_segments = []
    for txt, is_kw in _split_title_keywords(page.title):
        if is_kw:
            title_segments.append((txt, {"color": COLOR_RED_ACCENT, "bold": True}))
        else:
            title_segments.append((txt, {"color": COLOR_TITLE, "bold": True}))
    add_rich_textbox(
        slide, pct_x(0.090), GUIDE_TITLE_Y, pct_x(0.84), GUIDE_TITLE_H,
        title_segments,
        font=FONT_TITLE, size=SZ_HEADING,
        align="left", anchor="middle", line_spacing=1.3,
    )

    # 四图网格模式：标题下整幅排占位网格，不渲染要点/单图占位
    if grid_mode:
        add_image_grid(slide, *IMAGE_GRID_REGION, grid_sugs, gap=IMAGE_GRID_GAP)
        return

    # 正文(引文)与要点(追问)可同页共存：引文在上、追问在下
    # （契约 field-extraction「引文+追问」模式；旧版 if/elif 会静默丢弃正文）
    bullets_box = None
    if page.body and page.bullets:
        add_textbox(
            slide, GUIDE_BULLETS_X, GUIDE_BULLETS_Y, GUIDE_BULLETS_W, pct_y(0.20),
            page.body,
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.6, align="left", anchor="top",
        )
        bullets_box = add_textbox(
            slide, GUIDE_BULLETS_X, pct_y(0.66), GUIDE_BULLETS_W, pct_y(0.24),
            bullets_text(page.bullets),
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.8, align="left", anchor="top",
        )
    elif page.bullets:
        bullets_box = add_textbox(
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

    # 逐条点击：追问按段落构建，每点一次出一条（≥2 条才启用，单条直出）
    if ctx.get("anim") and bullets_box is not None and len(page.bullets) >= 2:
        spid = bullets_box.shape_id
        add_click_reveal(slide, [[(spid, i)] for i in range(len(page.bullets))])

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
    """要点小结（方案 A）：红方块编号 + 文字，永远单列。"""
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    add_textbox(
        slide, SUMMARY_TITLE_X, SUMMARY_TITLE_Y, SUMMARY_TITLE_W, SUMMARY_TITLE_H,
        page.title,
        font=FONT_TITLE, size=SZ_HEADING, color=COLOR_TITLE, bold=True,
        align="left", anchor="middle", line_spacing=1.3,
    )

    # 正文(引文)与要点可同页共存：引文在上、要点在下
    # （契约 field-extraction「引文+追问」模式；旧版 if/elif 会静默丢弃正文）
    bullet_groups = None
    if page.body and page.bullets:
        add_textbox(
            slide, SUMMARY_BULLETS_X, SUMMARY_BULLETS_Y, SUMMARY_BULLETS_W, pct_y(0.18),
            page.body,
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.6, align="left", anchor="top",
        )
        bullet_groups = add_numbered_bullets(
            slide,
            SUMMARY_BULLETS_X, pct_y(0.61), SUMMARY_BULLETS_W, pct_y(0.31),
            page.bullets, columns=1, text_size=SZ_BODY,
        )
    elif page.bullets:
        bullet_groups = add_numbered_bullets(
            slide,
            SUMMARY_BULLETS_X, SUMMARY_BULLETS_Y, SUMMARY_BULLETS_W, SUMMARY_BULLETS_H,
            page.bullets, columns=1, text_size=SZ_BODY,
        )
    elif page.body:
        add_textbox(
            slide, SUMMARY_BULLETS_X, SUMMARY_BULLETS_Y, SUMMARY_BULLETS_W, SUMMARY_BULLETS_H,
            page.body,
            font=FONT_BODY, size=SZ_BODY, color=COLOR_BODY,
            line_spacing=1.8, align="left", anchor="top",
        )

    # 逐条点击：每条要点的红方块+数字+文字成组，一次点击同出（≥2 条才启用）
    if ctx.get("anim") and bullet_groups and len(bullet_groups) >= 2:
        add_click_reveal(slide, bullet_groups)

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
    if not page.table_headers:
        return

    # 字号/行高/列宽由 add_table 按行数与内容自适应，确保整张表塞进区域。
    # 答案格（page.table_reveals）：底表渲占位、答案做成叠层逐格点击淡入。
    reveals = page.table_reveals or {}
    _table, geom = add_table(
        slide, TABLE_AREA_X, TABLE_AREA_Y, TABLE_AREA_W, TABLE_AREA_H,
        page.table_headers, page.table_rows, reveal_cells=reveals,
    )
    if not reveals:
        return

    # 为每个答案格叠"不透明底色矩形 + 完整答案文本框"，盖住底格占位
    bx, by = geom["x"], geom["y"]
    col_x, col_w = geom["col_x"], geom["col_w"]
    row_y, row_h = geom["row_y"], geom["row_h"]
    body_fs = geom["body_fs"]
    marg_l, marg_t = geom["marg_l"], geom["marg_t"]
    zebra = geom["zebra_bg"]

    groups = []
    for (d, c) in sorted(reveals.keys()):       # 阅读顺序：行优先、列内左→右
        tr = d + 1                               # 数据行 d 对应表行 d+1（表头占第 0 行）
        if tr >= len(row_y) or c >= len(col_x):
            continue
        cx = bx + col_x[c]
        cy = by + row_y[tr]
        cw, ch = col_w[c], row_h[tr]
        bg = cell_bg_color(d, zebra)

        rect = add_rect(slide, cx, cy, cw, ch, bg)
        _disable_shape_effects(rect)
        full = str(reveals[(d, c)]["full"]).replace("<br>", "\n")
        text_box = add_textbox(
            slide, cx + marg_l, cy + marg_t, cw - 2 * marg_l, ch - 2 * marg_t,
            full,
            font=FONT_BODY, size=body_fs, color=COLOR_BODY,
            align="left", anchor="middle", line_spacing=1.1,
        )
        groups.append([rect.shape_id, text_box.shape_id])

    # 逐格点击：每格一击（矩形+文字一起淡入）；关动画/系统不支持时全部直出=答案静态全显
    if ctx.get("anim") and groups:
        add_click_reveal(slide, groups)


_KEYWORD_RE = re.compile(r'(「[^」]+」|\u201c[^\u201d]+\u201d|"[^"]+")')


def _split_title_keywords(title: str):
    if not title:
        return [(title, False)]
    parts = _KEYWORD_RE.split(title)
    out = []
    for part in parts:
        if not part:
            continue
        is_kw = bool(_KEYWORD_RE.fullmatch(part))
        out.append((part, is_kw))
    return out


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

    # 中央 THE END（白色，120pt）
    add_textbox(
        slide, pct_x(0.10), pct_y(0.36), pct_x(0.80), pct_y(0.24),
        "THE END",
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
