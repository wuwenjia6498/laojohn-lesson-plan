# -*- coding: utf-8 -*-
"""课型无关的公共渲染元素（profile 接缝 · 共享层）。

本模块只放**读书会 / 写作课都用得到、且与课型无关**的渲染件：
左上铭牌、LOGO、封面三角、占位图、要点编号、标题关键词拆分、
参数化封面基函数 `_render_cover_base`、END 结束页。

课型专属的页型渲染分别在 `layouts_reading.py` / `layouts_writing.py`，
它们 import 本模块复用这些公共件。**本模块禁止出现 `doc_kind` 分支**——
两类课型的差异由各自的 layouts 模块、或经 ctx/参数传入决定，不在共享层判课型。
"""
import re
from pptx.util import Emu, Pt
from pptx.enum.shapes import MSO_SHAPE
from helpers import (
    add_textbox, add_rect, add_logo, add_image_or_skip,
    add_image_placeholder, rgb,
    add_gradient_rect, _disable_shape_effects,
)
from theme import (
    FONT_TITLE, FONT_BODY,
    COLOR_ANCHOR_BAR, COLOR_TITLE, COLOR_BODY, COLOR_RED_ACCENT,
    SZ_COVER_TITLE, SZ_COVER_SUB, SZ_COVER_META,
    SZ_ANCHOR_LABEL,
    ANCHOR_BAR_X, ANCHOR_BAR_Y, ANCHOR_BAR_W, ANCHOR_BAR_H,
    ANCHOR_LABEL_X, ANCHOR_LABEL_Y, ANCHOR_LABEL_W, ANCHOR_LABEL_H,
    LOGO_COVER_X, LOGO_COVER_Y, LOGO_COVER_W,
    LOGO_INNER_X, LOGO_INNER_Y, LOGO_INNER_W,
    PLACEHOLDER_REGIONS,
    COVER_TITLE_X, COVER_TITLE_Y, COVER_TITLE_W, COVER_TITLE_H,
    COVER_SUB_X, COVER_SUB_Y, COVER_SUB_W, COVER_SUB_H,
    COVER_META_X, COVER_META_Y, COVER_META_W, COVER_META_H,
    COVER_BANNER_X, COVER_BANNER_Y, COVER_BANNER_W, COVER_BANNER_H,
    COVER_TRI_X, COVER_TRI_Y, COVER_TRI_W, COVER_TRI_H,
    pct_x, pct_y,
)


# ---------- 分类上色（图例→颜色，全课统一的"颜色=手法/感官"）----------
# 示范文分句上色、五感观察表、旁批表三处共用同一调色板同一取色顺序 → 同一个 `图例`
# 声明（同码同序）在三页得到一致的颜色，学生形成稳定的"某色=某类手法/感官"认知。
CATEGORY_PALETTE = [
    COLOR_RED_ACCENT,   # 1 红——中心句 / 关键句
    "D98A3D",           # 2 橙——看得见的颜色
    "2E6DA4",           # 3 蓝——听到·摸到的感觉
    "3A8A5F",           # 4 绿——打比方
    "7E57C2",           # 5 紫——闻到的气味
    "C2185B",           # 6 品红——备用
]


def legend_to_colors(legend, palette=CATEGORY_PALETTE):
    """`图例`（[(码, 名), ...]）→ {码: 颜色}，颜色按声明顺序取调色板。"""
    return {code: palette[i % len(palette)]
            for i, (code, _name) in enumerate(legend or [])}


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


def _real_suggestions(page):
    """返回该页有效配图建议列表（过滤"无"等占位写法）。"""
    raw = getattr(page, "image_suggestions", None) or (
        [page.image_suggestion] if page.image_suggestion else [])
    return [s for s in raw if s and s.strip() not in
            {"无", "无（页面已满）", "—", "无配图"}]


_KEYWORD_RE = re.compile(r'(「[^」]+」|“[^”]+”|"[^"]+")')


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


# ---------- 封面基函数（参数化书名号，不判 doc_kind）----------
def _render_cover_base(slide, page, ctx, *, wrap_brackets: bool):
    """封面渲染公共体。

    wrap_brackets: 标题是否自动补《》——读书会传 True（标题是书名）、
    写作课传 False（标题是习作题目）。本函数不嗅探 doc_kind，决策权交给
    调用它的 reading / writing cover。
    """
    # 顶部横幅（四周留白边）
    add_image_or_skip(
        slide, ctx.get("banner_path"),
        COVER_BANNER_X, COVER_BANNER_Y,
        COVER_BANNER_W, COVER_BANNER_H,
    )
    # 左侧装饰三角（横幅左边缘伸出）
    draw_cover_triangle(slide)
    # LOGO（位于横幅内部右上角，仅宽度，保持原比例）
    draw_logo_cover(slide, ctx.get("logo_path"))

    # 大标题（叠在横幅中央）；不加粗、斜体
    title_text = (page.title or ctx.get("book_title", "")).strip()
    if wrap_brackets and title_text \
            and not (title_text.startswith("《") and title_text.endswith("》")):
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
    # 作者/元信息（左下角，左对齐；支持正文多行）
    meta_text = page.body or ctx.get("meta", "")
    if meta_text:
        add_textbox(
            slide, COVER_META_X, COVER_META_Y, COVER_META_W, COVER_META_H,
            meta_text,
            font=FONT_BODY, size=SZ_COVER_META, color=COLOR_BODY,
            align="left", anchor="top", line_spacing=1.8,
        )


# ---------- END 结束页 ----------
def render_end(slide, page, ctx):
    """每节课 PPT 末页：青绿渐变 + 居中 END + 老约翰白 LOGO + 右下"下一次再见 ▶"。

    不参与页码计数；page 参数仅占位，本函数不读取其内容。课型无关，两 profile 共用。
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
