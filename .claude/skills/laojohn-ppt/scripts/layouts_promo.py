# -*- coding: utf-8 -*-
"""宣讲 profile 的页型渲染（对外产品宣讲件，非课堂课件）。

每个函数签名：render_<type>(slide, page, ctx)，与 reading / writing 两 profile 一致。

定位：面向加盟商 / 校区负责人讲「同步习作」这条产品线，不是给学生上课。
因此不复用课件的深灰蓝色系，改用已发布招生海报的品牌色板（见 theme_promo）。

三条与架构有关的自持约定（改本文件前先读，踩中不报错）：
  1. **`封面` 与 `环节标题` 两个页型名不可改**。build_ppt 里"首页不是封面就自动补
     一页""按环节标题自动编章节序号"是课型无关逻辑，判据就是这两个字符串。改名
     会同时丢掉自动封面判定与章节编号，**且完全静默**。
  2. **`_END` 由本模块自己接管**（RENDERERS_PROMO["_END"] = render_promo_end）。
     layouts_common.render_end 硬编码「THE END / 下一次再见」，对宣讲件是观感事故。
     这是架构原本就设计好的换法——两个既有 profile 也各自显式写了这一行，
     不要反过来去参数化 layouts_common。
  3. **不 import layouts_writing 的私有件**（_heading / _bullets_cards / _resolve_image）。
     它们直读 theme_writing 的模块级常量（不是参数），import 过来会静默继承写作课的
     浅粉配色。本模块自持同形状、读 theme_promo；_resolve_image 那 8 行照抄不共享。

另有一个引擎限制必须绕开：`配图建议：图=…` 一页只保留**第一条**路径（parser 侧既有行为）。
所以一页多图一律走 `场景：图=…｜名=…｜问=…` 重复行，见 render_gallery。
"""
import os
import re

from pptx.util import Emu, Pt
from pptx.enum.shapes import MSO_SHAPE

from helpers import (
    add_textbox, add_rich_textbox, add_rect, add_gradient_rect,
    add_numbered_bullets, add_click_reveal, add_logo, add_table,
    rgb as _rgb, set_ascii_font,
    _disable_shape_effects as _no_fx,
)
from theme import FONT_TITLE, FONT_BODY, pct_x, pct_y, SLIDE_W, SLIDE_H
import theme_promo as tp
from layouts_common import _split_title_keywords


# ============================================================
# 内部小工具（本 profile 自持）
# ============================================================
def _resolve_image(ctx, path):
    """把中间稿里的相对图片路径解析为绝对路径（相对中间稿 .md 所在目录）。
    绝对路径原样返回。与 layouts_writing 同款 8 行，刻意不共享——避免
    promo → writing 的横向依赖（那会让宣讲线故障依赖写作课文件树）。"""
    if not path:
        return path
    if os.path.isabs(path):
        return path
    base = ctx.get("input_dir") or ""
    return os.path.normpath(os.path.join(base, path))


def _img_size(path):
    """读图片像素尺寸。PIL 不可用或读失败时返回 None（调用方退回占位）。"""
    try:
        from PIL import Image
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def add_image_contain(slide, x, y, w, h, image_path, *,
                      card=True, border=True):
    """按原比例完整放入给定框（contain 语义），居中，可选白卡托底。

    **不要用 helpers.add_image_cover 放文档截图**——那是 cover 语义（等比放大铺满
    再裁掉溢出），A4 竖版的学习单/详案页塞进横框会被裁掉大半页正文。宣讲件展示的
    正是"这份材料长什么样"，裁掉就没意义了。

    找不到图时画一个浅色空卡 + 说明，不报错、不留白洞。
    返回 (shape_ids, 实际图片区域 (ix, iy, iw, ih))。
    """
    ids = []
    path = image_path
    have = bool(path and os.path.isfile(path))
    size = _img_size(path) if have else None

    # 先按 contain 算出图的实际显示尺寸，卡再按它收窄——不然 A4 竖版图放进横框，
    # 两侧会留出大片空白卡面，看着像图没加载出来。
    pad = Emu(int(min(w, h) * 0.030)) if card else Emu(0)
    aw, ah = w - 2 * pad, h - 2 * pad
    if size:
        iw0, ih0 = size
        scale = min(aw / iw0, ah / ih0)
        dw, dh = int(iw0 * scale), int(ih0 * scale)
    else:
        dw, dh = int(aw), int(ah)

    cw, ch = dw + 2 * pad, dh + 2 * pad
    cx = x + (w - cw) // 2
    cy = y + (h - ch) // 2

    if card:
        bg = add_rect(slide, cx, cy, Emu(cw), Emu(ch), tp.COLOR_SHOT_CARD,
                      line=border, line_color=tp.COLOR_SHOT_BORDER)
        _no_fx(bg)
        ids.append(bg.shape_id)

    if not have:
        t = add_textbox(slide, cx, cy, Emu(cw), Emu(ch), "待贴图",
                        font=FONT_BODY, size=tp.SZ_SHOT_NOTE,
                        color=tp.COLOR_INK_SOFT, align="center", anchor="middle")
        ids.append(t.shape_id)
        return ids, (cx, cy, Emu(cw), Emu(ch))

    pic = slide.shapes.add_picture(path, cx + pad, cy + pad,
                                   width=Emu(dw), height=Emu(dh))
    ids.append(pic.shape_id)
    return ids, (cx + pad, cy + pad, Emu(dw), Emu(dh))


def _split_segs(text):
    """把一条要点按全角/半角竖线拆段：`63｜个任务｜三上到六下全覆盖` → 三段。

    这是**呈现层对已有字符串的解读**，不是新语法——parser 只把整行当一条 bullet
    存进 page.bullets，它不知情也不需要知情。
    """
    return [s.strip() for s in re.split(r"\s*[｜|]\s*", str(text)) if s.strip()]


def _has_todo(text):
    """是否含【待填】占位。仓内查无事实源的栏位一律留它，渲染成红字提醒。"""
    return tp.TODO_MARK in str(text)


def _logo(slide, ctx, white=False):
    p = ctx.get("logo_white_path") if white else ctx.get("logo_path")
    p = p or ctx.get("logo_path")
    if p:
        add_logo(slide, p, tp.LOGO_X, tp.LOGO_Y, tp.LOGO_W)


def _head(slide, page, ctx, *, lead=True, logo=True):
    """内页统一页头：眉标 + 标题（「」内自动飘品牌红）+ 红短线 + 可选小注。
    返回主体区顶边 y（有小注时下移）。"""
    if logo:
        _logo(slide, ctx)
    if page.eyebrow:
        add_textbox(slide, tp.EYEBROW_X, tp.EYEBROW_Y, tp.EYEBROW_W, tp.EYEBROW_H,
                    page.eyebrow, font=FONT_BODY, size=tp.SZ_EYEBROW,
                    color=tp.COLOR_INK_SOFT, align="left", anchor="middle")
    title = page.title or ""
    # 22 字是 34pt 单行的上限；再长就降档，否则标题折成两行会压住下面的红短线。
    size = tp.SZ_TITLE if len(title) <= 22 else tp.SZ_TITLE_SM
    segs = [(t, {"color": tp.COLOR_BRAND_RED if kw else tp.COLOR_INK, "bold": True})
            for t, kw in _split_title_keywords(title)]
    if segs:
        add_rich_textbox(slide, tp.TITLE_X, tp.TITLE_Y, tp.TITLE_W, tp.TITLE_H,
                         segs, font=FONT_TITLE, size=size,
                         align="left", anchor="middle", line_spacing=1.25)
    r = add_rect(slide, tp.TITLE_RULE_X, tp.TITLE_RULE_Y,
                 tp.TITLE_RULE_W, tp.TITLE_RULE_H, tp.COLOR_BRAND_RED)
    _no_fx(r)

    top = tp.BODY_TOP
    if lead and page.body:
        add_textbox(slide, tp.LEAD_X, tp.LEAD_Y, tp.LEAD_W, tp.LEAD_H,
                    page.body, font=FONT_BODY, size=tp.SZ_LEAD,
                    color=tp.COLOR_INK_SOFT, align="left", anchor="top",
                    line_spacing=1.5)
    else:
        top = tp.LEAD_Y
    return top


def _footnote(slide, text):
    if not text:
        return
    add_textbox(slide, tp.FOOTNOTE_X, tp.FOOTNOTE_Y, tp.FOOTNOTE_W, tp.FOOTNOTE_H,
                text, font=FONT_BODY, size=tp.SZ_FOOTNOTE,
                color=tp.COLOR_INK_SOFT, align="left", anchor="middle")


def _dark_ground(slide):
    """深色满幅底（封面 / 章节页 / 收尾 / END 共用）。"""
    add_gradient_rect(slide, Emu(0), Emu(0), SLIDE_W, SLIDE_H,
                      tp.COLOR_DARK_FROM, tp.COLOR_DARK_TO, angle_deg=135)


# ============================================================
# 1 · 封面
# ============================================================
def render_cover(slide, page, ctx):
    """宣讲封面：深色满幅 + 左侧红竖条 + 大主标 + 副标 + 左下主讲信息。

    刻意不走 layouts_common._render_cover_base——那套是课件封面（横幅图 + 斜体
    书名 + 装饰三角），观感是"要上课了"，宣讲场合要的是一张沉稳的产品扉页。
    """
    _dark_ground(slide)

    bar_x, bar_y = pct_x(0.065), pct_y(0.300)
    bar = add_rect(slide, bar_x, bar_y, pct_x(0.006), pct_y(0.230),
                   tp.COLOR_BRAND_RED)
    _no_fx(bar)

    tx = pct_x(0.095)
    tw_ = pct_x(0.760)
    title = (page.title or ctx.get("book_title", "")).strip()
    segs = [(t, {"color": tp.COLOR_BRAND_RED if kw else tp.COLOR_DARK_FG,
                 "bold": True})
            for t, kw in _split_title_keywords(title)]
    if segs:
        # 按字数降档：文字区约 10.1in 宽，50pt 只装得下 12 字，再长就会折行，
        # 而封面折出一个三字的尾巴很难看。
        n = len(title)
        csize = (tp.SZ_COVER_TITLE if n <= 12
                 else tp.SZ_COVER_TITLE_MD if n <= 17
                 else tp.SZ_COVER_TITLE_SM)
        add_rich_textbox(slide, tx, pct_y(0.295), tw_, pct_y(0.240), segs,
                         font=FONT_TITLE, size=csize,
                         align="left", anchor="middle", line_spacing=1.30)

    sub = page.subtitle or ctx.get("course_name", "")
    if sub:
        add_textbox(slide, tx, pct_y(0.560), tw_, pct_y(0.080), sub,
                    font=FONT_TITLE, size=tp.SZ_COVER_SUB,
                    color=tp.COLOR_DARK_SUB, align="left", anchor="middle",
                    line_spacing=1.4)

    meta = page.body or ctx.get("meta", "")
    if meta:
        add_textbox(slide, tx, pct_y(0.760), tw_, pct_y(0.150), meta,
                    font=FONT_BODY, size=tp.SZ_COVER_META,
                    color=tp.COLOR_DARK_SUB, align="left", anchor="top",
                    line_spacing=1.8)

    _logo(slide, ctx, white=True)


# ============================================================
# 2 · 环节标题（章节大间隔页）
# ============================================================
def render_section(slide, page, ctx):
    """章节大间隔页：深色满幅 + 左上巨型序号 + 红短线 + 章名 + 引子。

    序号来自 build_ppt 自动编号（_section_no / _section_total），课型无关。
    结构照抄 layouts_reading.render_section 的骨架，配色换成宣讲深墨——刻意不
    直接 import 那个函数，因为它的色值是模块级常量、不是参数（见文件头约定 3）。
    """
    _dark_ground(slide)
    no = getattr(page, "_section_no", 1)
    total = getattr(page, "_section_total", 1)

    if total > 1:
        num = add_textbox(slide, pct_x(0.065), pct_y(0.150), pct_x(0.40), pct_y(0.300),
                          f"{no:02d}", font=FONT_TITLE, size=tp.SZ_SECTION_NUM,
                          color=tp.COLOR_DARK_NUM, bold=True, italic=False,
                          align="left", anchor="middle")
        set_ascii_font(num, "Bahnschrift")

    r = add_rect(slide, pct_x(0.065), pct_y(0.520), pct_x(0.052), Emu(34000),
                 tp.COLOR_BRAND_RED)
    _no_fx(r)
    add_textbox(slide, pct_x(0.065), pct_y(0.560), pct_x(0.840), pct_y(0.150),
                page.title, font=FONT_TITLE, size=tp.SZ_SECTION_TITLE,
                color=tp.COLOR_DARK_FG, bold=True, align="left",
                anchor="middle", line_spacing=1.3)
    if page.body:
        add_textbox(slide, pct_x(0.065), pct_y(0.730), pct_x(0.840), pct_y(0.150),
                    page.body, font=FONT_BODY, size=tp.SZ_SECTION_LEAD,
                    color=tp.COLOR_DARK_SUB, align="left", anchor="top",
                    line_spacing=1.6)
    _logo(slide, ctx, white=True)


# ============================================================
# 3 · 主张（整页只有一句话）
# ============================================================
def render_claim(slide, page, ctx):
    """一句话主张页：大字号主张句（「」内飘红）+ 红短线 + 一行小注。

    整页只放一句，是宣讲的节奏停顿——不要往这个页型塞要点。
    """
    _logo(slide, ctx)
    if page.eyebrow:
        add_textbox(slide, tp.EYEBROW_X, tp.EYEBROW_Y, tp.EYEBROW_W, tp.EYEBROW_H,
                    page.eyebrow, font=FONT_BODY, size=tp.SZ_EYEBROW,
                    color=tp.COLOR_INK_SOFT, align="left", anchor="middle")

    claim = page.title or ""
    size = tp.SZ_CLAIM if len(claim) <= 24 else tp.SZ_CLAIM_SM
    segs = [(t, {"color": tp.COLOR_BRAND_RED if kw else tp.COLOR_INK, "bold": True})
            for t, kw in _split_title_keywords(claim)]
    add_rich_textbox(slide, tp.MARGIN_X, pct_y(0.280), tp.CONTENT_W, pct_y(0.300),
                     segs, font=FONT_TITLE, size=size,
                     align="left", anchor="middle", line_spacing=1.45)

    r = add_rect(slide, tp.MARGIN_X, pct_y(0.615), pct_x(0.070), Emu(34000),
                 tp.COLOR_BRAND_RED)
    _no_fx(r)
    if page.body:
        add_textbox(slide, tp.MARGIN_X, pct_y(0.660), tp.CONTENT_W, pct_y(0.180),
                    page.body, font=FONT_BODY, size=tp.SZ_CLAIM_NOTE,
                    color=tp.COLOR_INK_SOFT, align="left", anchor="top",
                    line_spacing=1.7)


# ============================================================
# 4 · 数据面板
# ============================================================
def render_stats(slide, page, ctx):
    """大数字卡横排。每条要点写 `数字｜单位｜一行注解`（2–4 条）。

    数字用 Bahnschrift（拉丁槽），微软雅黑的数字在 78pt 上显笨。
    """
    top = _head(slide, page, ctx)
    items = [_split_segs(b) for b in (page.bullets or [])]
    n = len(items)
    if n == 0:
        return
    n = min(n, 4)
    items = items[:n]
    gap = tp.STAT_GAP
    cw = (tp.CONTENT_W - gap * (n - 1)) // n
    h = tp.STAT_CARD_H
    num_size = tp.SZ_STAT_NUM if n <= 3 else tp.SZ_STAT_NUM_SM

    groups = []
    for i, segs in enumerate(items):
        cx = tp.MARGIN_X + i * (cw + gap)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, top, cw, h)
        try:
            card.adjustments[0] = tp.STAT_RADIUS
        except Exception:
            pass
        card.fill.solid()
        card.fill.fore_color.rgb = _rgb(tp.COLOR_ZEBRA)
        card.line.color.rgb = _rgb(tp.COLOR_LINE)
        card.line.width = Pt(0.75)
        _no_fx(card)

        pad = Emu(int(cw * 0.09))
        big = segs[0] if segs else ""
        unit = segs[1] if len(segs) > 1 else ""
        note = segs[2] if len(segs) > 2 else ""

        nb = add_textbox(slide, cx + pad, top + Emu(int(h * 0.10)),
                         cw - 2 * pad, Emu(int(h * 0.38)), big,
                         font=FONT_TITLE, size=num_size,
                         color=tp.COLOR_BRAND_RED, bold=True,
                         align="left", anchor="middle")
        set_ascii_font(nb, "Bahnschrift")
        ids = [card.shape_id, nb.shape_id]
        if unit:
            ub = add_textbox(slide, cx + pad, top + Emu(int(h * 0.50)),
                             cw - 2 * pad, Emu(int(h * 0.15)), unit,
                             font=FONT_TITLE, size=tp.SZ_STAT_UNIT,
                             color=tp.COLOR_INK, bold=True,
                             align="left", anchor="middle")
            ids.append(ub.shape_id)
        if note:
            tb = add_textbox(slide, cx + pad, top + Emu(int(h * 0.645)),
                             cw - 2 * pad, Emu(int(h * 0.335)), note,
                             font=FONT_BODY, size=tp.SZ_STAT_NOTE,
                             color=tp.COLOR_INK_SOFT if not _has_todo(note)
                             else tp.COLOR_BRAND_RED,
                             align="left", anchor="top", line_spacing=1.45)
            ids.append(tb.shape_id)
        groups.append(ids)
    _footnote(slide, page.subtitle)


# ============================================================
# 5 · 体系全景（六阶轴 + 能力线矩阵）
# ============================================================
def render_overview(slide, page, ctx):
    """上：能力阶梯横轴（要点每条 `阶名｜学段`，条首加 `~` = 淡显、不属本产品线）。
    下：能力线矩阵（表格：首列=线名，其余列按阶对位）。

    两部分都可单独出现：只写要点＝只画轴；只写表格＝只画矩阵。
    格子左侧的竖色条按列取 theme_promo.COLOR_STAGE，**颜色即口径**，与海报逐格同色。
    """
    top = _head(slide, page, ctx)

    stages = [_split_segs(b) for b in (page.bullets or [])]
    grid_top = top
    if stages:
        n = len(stages)
        gap = tp.AXIS_GAP
        sw = (tp.CONTENT_W - gap * (n - 1)) // n
        h = tp.AXIS_H
        active = 0
        for i, segs in enumerate(stages):
            raw = segs[0] if segs else ""
            muted = raw.startswith("~")
            name = raw.lstrip("~").strip()
            sub = segs[1] if len(segs) > 1 else ""
            if muted:
                color = tp.COLOR_STAGE_MUTED
            else:
                color = tp.COLOR_STAGE[min(active, len(tp.COLOR_STAGE) - 1)]
                active += 1
            sx = tp.MARGIN_X + i * (sw + gap)
            shp = slide.shapes.add_shape(MSO_SHAPE.CHEVRON, sx, top, sw, h)
            shp.fill.solid()
            shp.fill.fore_color.rgb = _rgb(color)
            shp.line.fill.background()
            _no_fx(shp)
            # 阶名与学段分两行、两档字号——单行放不下「五年级下—六年级下」这种长学段，
            # 挤成三行会顶破 chevron。
            # 淡显段（不属本产品线的低段）降一号字：阶名更长，且本就该弱化。
            nsz = tp.SZ_AXIS_STAGE_MUTED if muted else tp.SZ_AXIS_STAGE
            segs2 = [(name, {"size": nsz, "bold": True})]
            if sub:
                segs2.append((chr(10) + sub, {"size": tp.SZ_AXIS_SUB, "bold": False}))
            # 左边距比右边距大：chevron 的左尖尾是凹进去的，会压住起首那个字。
            add_rich_textbox(slide, sx + Emu(int(sw * 0.115)), top,
                             sw - Emu(int(sw * 0.205)), h, segs2,
                             font=FONT_TITLE, default_color="FFFFFF",
                             align="center", anchor="middle", line_spacing=1.2)
        grid_top = tp.GRID_TOP

    rows = page.table_rows or []
    if rows:
        ncol = max(len(r) for r in rows) - 1
        ncol = max(ncol, 1)
        nrow = len(rows)
        rgap = tp.GRID_ROW_GAP
        rh = (tp.GRID_H - rgap * (nrow - 1)) // nrow
        lw = tp.GRID_LABEL_W
        cgap = Emu(20000)
        cw = (tp.CONTENT_W - lw - cgap * ncol) // ncol
        for ri, row in enumerate(rows):
            ry = grid_top + ri * (rh + rgap)
            lab = add_rect(slide, tp.MARGIN_X, ry, lw, rh, tp.COLOR_BROWN_CELL)
            _no_fx(lab)
            add_textbox(slide, tp.MARGIN_X + Emu(int(lw * 0.08)), ry,
                        lw - Emu(int(lw * 0.16)), rh, row[0],
                        font=FONT_TITLE, size=tp.SZ_AXIS_ROW, color=tp.COLOR_INK,
                        bold=True, align="left", anchor="middle")
            for ci in range(ncol):
                cell = row[ci + 1] if ci + 1 < len(row) else ""
                cx = tp.MARGIN_X + lw + cgap + ci * (cw + cgap)
                bg = add_rect(slide, cx, ry, cw, rh, tp.COLOR_ZEBRA)
                _no_fx(bg)
                bar = add_rect(slide, cx, ry, Emu(28000), rh,
                               tp.COLOR_STAGE[min(ci, len(tp.COLOR_STAGE) - 1)])
                _no_fx(bar)
                if cell:
                    add_textbox(slide, cx + Emu(int(cw * 0.07)), ry,
                                cw - Emu(int(cw * 0.12)), rh, cell,
                                font=FONT_BODY, size=tp.SZ_AXIS_CELL,
                                color=tp.COLOR_INK, align="left", anchor="middle",
                                line_spacing=1.25)
    _footnote(slide, page.subtitle)


# ============================================================
# 6 · 流程时间轴
# ============================================================
def render_flow(slide, page, ctx):
    """横向流程轴：要点每条 `环节名｜时长`；单独一条 `---` 表示分段（如第 1 节 / 第 2 节）。

    分段用两种深浅的轴色区分，段标签写在轴下方（取 `副标题：第 1 节｜第 2 节`）。
    """
    _head(slide, page, ctx)

    raw = page.bullets or []
    items, split_at = [], None
    for b in raw:
        if str(b).strip() in {"---", "——", "—"}:
            split_at = len(items)
            continue
        items.append(_split_segs(b))
    n = len(items)
    if n == 0:
        return

    seg_w = tp.CONTENT_W // n
    line_y = tp.FLOW_LINE_Y
    d = tp.FLOW_NODE_D
    # 7 字环节名在 14pt 下正好撑破格宽、断成两行，所以 8 格时降到 13pt。
    name_size = (tp.SZ_STEP_NAME if n <= 6
                 else tp.SZ_STEP_NAME - 1 if n == 7
                 else tp.SZ_STEP_NAME - 2)

    # 轴线：按分段分两截着色
    if split_at is None or split_at <= 0 or split_at >= n:
        add_rect(slide, tp.MARGIN_X, line_y, tp.CONTENT_W, tp.FLOW_LINE_H,
                 tp.COLOR_LINE)
    else:
        w1 = seg_w * split_at
        a = add_rect(slide, tp.MARGIN_X, line_y, w1, tp.FLOW_LINE_H,
                     tp.COLOR_STAGE[1])
        b_ = add_rect(slide, tp.MARGIN_X + w1, line_y, tp.CONTENT_W - w1,
                      tp.FLOW_LINE_H, tp.COLOR_STAGE[3])
        _no_fx(a)
        _no_fx(b_)

    for i, segs in enumerate(items):
        cx = tp.MARGIN_X + i * seg_w
        mid = cx + seg_w // 2
        color = (tp.COLOR_STAGE[1] if (split_at is not None and i < split_at)
                 else tp.COLOR_STAGE[3] if split_at is not None
                 else tp.COLOR_BRAND_RED)
        # 环节名（轴上方）
        name = segs[0] if segs else ""
        add_textbox(slide, cx + Emu(int(seg_w * 0.02)), tp.FLOW_TOP,
                    seg_w - Emu(int(seg_w * 0.04)), tp.FLOW_NAME_H, name,
                    font=FONT_TITLE, size=name_size, color=tp.COLOR_INK,
                    bold=True, align="center", anchor="bottom", line_spacing=1.25)
        # 节点圆 + 序号
        node = slide.shapes.add_shape(MSO_SHAPE.OVAL, mid - d // 2,
                                      line_y + tp.FLOW_LINE_H // 2 - d // 2, d, d)
        node.fill.solid()
        node.fill.fore_color.rgb = _rgb(color)
        node.line.color.rgb = _rgb("FFFFFF")
        node.line.width = Pt(1.5)
        _no_fx(node)
        add_textbox(slide, mid - d // 2, line_y + tp.FLOW_LINE_H // 2 - d // 2,
                    d, d, str(i + 1), font=FONT_TITLE, size=tp.SZ_STEP_NUM,
                    color="FFFFFF", bold=True, align="center", anchor="middle")
        # 时长（轴下方）
        if len(segs) > 1:
            add_textbox(slide, cx, tp.FLOW_TIME_Y, seg_w, tp.FLOW_TIME_H, segs[1],
                        font=FONT_BODY, size=tp.SZ_STEP_TIME,
                        color=tp.COLOR_INK_SOFT, align="center", anchor="middle")

    # 分段标签
    if page.subtitle and split_at:
        labels = _split_segs(page.subtitle)
        if len(labels) >= 2:
            w1 = seg_w * split_at
            add_textbox(slide, tp.MARGIN_X, tp.FLOW_SEG_LABEL_Y, w1, pct_y(0.06),
                        labels[0], font=FONT_TITLE, size=tp.SZ_STEP_NAME,
                        color=tp.COLOR_STAGE[1], bold=True,
                        align="center", anchor="middle")
            add_textbox(slide, tp.MARGIN_X + w1, tp.FLOW_SEG_LABEL_Y,
                        tp.CONTENT_W - w1, pct_y(0.06), labels[1],
                        font=FONT_TITLE, size=tp.SZ_STEP_NAME,
                        color=tp.COLOR_STAGE[3], bold=True,
                        align="center", anchor="middle")


# ============================================================
# 7 · 并列卡片
# ============================================================
def render_cards(slide, page, ctx):
    """卡片横排：每条要点 `卡名｜说明`（2–4 条）。含【待填】的说明渲染成红字。"""
    top = _head(slide, page, ctx)
    items = [_split_segs(b) for b in (page.bullets or [])]
    n = min(len(items), 4)
    if n == 0:
        return
    items = items[:n]
    gap = tp.CARDS_GAP
    cw = (tp.CONTENT_W - gap * (n - 1)) // n
    h = pct_y(0.470)

    for i, segs in enumerate(items):
        cx = tp.MARGIN_X + i * (cw + gap)
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, top, cw, h)
        try:
            card.adjustments[0] = tp.CARD_RADIUS
        except Exception:
            pass
        card.fill.solid()
        card.fill.fore_color.rgb = _rgb(tp.COLOR_ZEBRA)
        card.line.color.rgb = _rgb(tp.COLOR_LINE)
        card.line.width = Pt(0.75)
        _no_fx(card)

        d = tp.CARD_NUM_D
        nx = cx + Emu(int(cw * 0.075))
        ny = top + Emu(int(h * 0.075))
        chip = slide.shapes.add_shape(MSO_SHAPE.OVAL, nx, ny, d, d)
        chip.fill.solid()
        chip.fill.fore_color.rgb = _rgb(tp.COLOR_BRAND_RED)
        chip.line.fill.background()
        _no_fx(chip)
        add_textbox(slide, nx, ny, d, d, str(i + 1), font=FONT_TITLE,
                    size=tp.SZ_CARD_NUM, color="FFFFFF", bold=True,
                    align="center", anchor="middle")

        pad = Emu(int(cw * 0.085))
        name = segs[0] if segs else ""
        add_textbox(slide, cx + pad, ny + d + Emu(int(h * 0.045)),
                    cw - 2 * pad, Emu(int(h * 0.155)), name,
                    font=FONT_TITLE, size=tp.SZ_CARD_TITLE, color=tp.COLOR_INK,
                    bold=True, align="left", anchor="top", line_spacing=1.3)
        if len(segs) > 1:
            # 第一段是卡的主说明，其后各段是补充——降一号字、再淡一档，
            # 否则两行贴在一起，读起来像一句话被硬断了行。
            body = chr(10).join(segs[1:])
            todo = _has_todo(body)
            rich = [(segs[1], {"size": tp.SZ_CARD_BODY,
                               "color": tp.COLOR_BRAND_RED if todo
                               else tp.COLOR_INK_SOFT})]
            for extra in segs[2:]:
                rich.append((chr(10) + extra,
                             {"size": tp.SZ_CARD_BODY - 2,
                              "color": tp.COLOR_BRAND_RED if todo
                              else tp.COLOR_BROWN_DEEP}))
            add_rich_textbox(slide, cx + pad, ny + d + Emu(int(h * 0.225)),
                             cw - 2 * pad, h - d - Emu(int(h * 0.34)), rich,
                             font=FONT_BODY, align="left", anchor="top",
                             line_spacing=1.5)
    _footnote(slide, page.subtitle)


# ============================================================
# 8 · 双栏对照
# ============================================================
def render_versus(slide, page, ctx):
    """左右对比：左＝对照组（灰、弱），右＝我们（品牌红、强）。
    底部可选一行要点（`要点：` 每条一句），随右栏结论一起点击后出。
    """
    _head(slide, page, ctx, lead=True)

    notes = page.bullets or []
    bottom = tp.VS_BODY_BOTTOM if not notes else tp.VS_BODY_BOTTOM_WITHNOTES

    # 栏内正文按字数降档。栏宽约 24 字/行、栏高约 6 行，超了就压字号——
    # 溢出的表现是正文冲出栏底压住下面的要点，机检查不出来，只有看图才发现。
    def _eff(txt):
        # 等效长度 = 字数 + 段落分隔占的行。段落数也吃高度，只数字数会漏判：
        # 60 字分三段，比 90 字一段还高。
        t = (txt or "").strip()
        paras = [p for p in t.split(chr(10) + chr(10)) if p.strip()]
        return len(t) + 24 * max(0, len(paras) - 1)

    _eff_len = max(_eff(page.left_body), _eff(page.right_body))
    body_size = (tp.SZ_COMPARE_BODY - 1 if _eff_len <= 90
                 else tp.SZ_COMPARE_BODY - 3 if _eff_len <= 130
                 else tp.SZ_COMPARE_BODY - 5)

    def col(x, tab_text, tab_bg, body_text, body_bg, fg):
        t = add_rect(slide, x, tp.VS_TOP, tp.VS_COL_W, tp.VS_TAB_H, tab_bg)
        _no_fx(t)
        add_textbox(slide, x + pct_x(0.018), tp.VS_TOP,
                    tp.VS_COL_W - pct_x(0.036), tp.VS_TAB_H, tab_text,
                    font=FONT_TITLE, size=tp.SZ_COMPARE_TAB, color="FFFFFF",
                    bold=True, align="left", anchor="middle")
        b = add_rect(slide, x, tp.VS_BODY_TOP, tp.VS_COL_W,
                     bottom - tp.VS_BODY_TOP, body_bg)
        _no_fx(b)
        ids = [t.shape_id, b.shape_id]
        if body_text:
            tb = add_textbox(slide, x + pct_x(0.020), tp.VS_BODY_TOP + pct_y(0.018),
                             tp.VS_COL_W - pct_x(0.040),
                             bottom - tp.VS_BODY_TOP - pct_y(0.036), body_text,
                             font=FONT_BODY, size=body_size, color=fg,
                             align="left", anchor="top", line_spacing=1.62)
            ids.append(tb.shape_id)
        return ids

    col(tp.VS_LEFT_X, page.left_title or "常见做法", tp.COLOR_VS_LEFT_TAB,
        page.left_body, tp.COLOR_VS_LEFT_BG, tp.COLOR_INK_SOFT)
    right_ids = col(tp.VS_RIGHT_X, page.right_title or "老约翰",
                    tp.COLOR_VS_RIGHT_TAB, page.right_body,
                    tp.COLOR_VS_RIGHT_BG, tp.COLOR_INK)

    groups = []
    if notes:
        ids = add_numbered_bullets(
            slide, tp.MARGIN_X, tp.VS_NOTES_Y, tp.CONTENT_W, tp.VS_NOTES_H,
            notes, text_size=tp.SZ_COMPARE_BODY - 2, columns=min(len(notes), 3),
            num_bg=tp.COLOR_BRAND_RED, num_fg="FFFFFF",
            text_color=tp.COLOR_INK, text_font=FONT_BODY, num_style="dot")
        groups = [right_ids] + list(ids)
    if ctx.get("anim") and groups:
        add_click_reveal(slide, groups)


# ============================================================
# 9 · 清单页（复用「要点小结」页型名）
# ============================================================
def render_list(slide, page, ctx):
    """竖排清单：有序要点＝大号数字 + 红竖线；无序＝实心圆点。
    含【待填】的条目整条渲染成品牌红，提醒宣讲人上台前必须填。
    """
    top = _head(slide, page, ctx)
    bullets = page.bullets or []
    if not bullets:
        return
    style = "bar" if page.bullets_ordered else "dot"
    size = tp.SZ_LIST if len(bullets) <= 5 else tp.SZ_LIST - 2

    todo = any(_has_todo(b) for b in bullets)
    # 行高 = 区高 / 条数，所以区高不能固定：两三条要点会被拉开半页，
    # 中间空出一大截，看着像漏了内容。按条数收紧、封顶到主体区。
    h_use = min(pct_y(0.480), Emu(int(pct_y(0.118) * max(len(bullets), 1))))
    groups = add_numbered_bullets(
        slide, tp.MARGIN_X, top, tp.CONTENT_W, h_use, bullets,
        text_size=size, columns=1,
        num_bg=tp.COLOR_BRAND_RED, num_fg="FFFFFF",
        text_color=tp.COLOR_BRAND_RED if todo else tp.COLOR_INK,
        text_font=FONT_BODY, num_style=style)
    _footnote(slide, page.subtitle)
    if ctx.get("anim") and len(groups) > 1 and page.bullets_ordered:
        add_click_reveal(slide, groups)


# ============================================================
# 10 · 图集（一页 2–4 张实物截图）
# ============================================================
def render_gallery(slide, page, ctx):
    """多张实物截图并排。每张写一行：
        场景：图=<路径>｜名=<图注>｜问=<一行说明>

    **必须用 `场景：` 而不是多条 `配图建议：`**——parser 侧一页只保留第一条
    `配图建议：图=` 的路径（既有行为），多写只会静默丢图。
    图一律 contain 放入白卡（不是 cover），文档截图裁掉正文就失去展示意义。
    """
    _head(slide, page, ctx)
    scenes = page.scenes or []
    n = min(len(scenes), 4)
    if n == 0:
        return
    scenes = scenes[:n]
    gap = tp.SHOT_GAP
    cw = (tp.CONTENT_W - gap * (n - 1)) // n

    for i, sc in enumerate(scenes):
        cx = tp.MARGIN_X + i * (cw + gap)
        path = _resolve_image(ctx, sc.get("image_path", ""))
        add_image_contain(slide, cx, tp.SHOT_TOP, cw, tp.SHOT_H, path)
        cap = sc.get("name", "")
        if cap:
            add_textbox(slide, cx, tp.SHOT_TOP + tp.SHOT_H + Emu(40000),
                        cw, tp.SHOT_CAP_H, cap, font=FONT_TITLE,
                        size=tp.SZ_SHOT_CAP, color=tp.COLOR_INK, bold=True,
                        align="left", anchor="middle")
        note = sc.get("question", "")
        if note:
            add_textbox(slide, cx,
                        tp.SHOT_TOP + tp.SHOT_H + tp.SHOT_CAP_H + Emu(40000),
                        cw, tp.SHOT_NOTE_H, note, font=FONT_BODY,
                        size=tp.SZ_SHOT_NOTE, color=tp.COLOR_INK_SOFT,
                        align="left", anchor="top", line_spacing=1.45)


# ============================================================
# 11 · 满屏图（单张实物大图 + 右侧指点）
# ============================================================
def render_showcase(slide, page, ctx):
    """左侧一张大图（contain + 白卡），右侧竖排 2–3 条红字指点（要点字段）。
    图走 `配图建议：图=<路径>｜说明`（单图，用 page.image_path）。
    """
    _head(slide, page, ctx, lead=False)
    path = _resolve_image(ctx, page.image_path)
    add_image_contain(slide, tp.SHOW_IMG_X, tp.SHOW_IMG_Y,
                      tp.SHOW_IMG_W, tp.SHOW_IMG_H, path)

    bullets = page.bullets or []
    if not bullets:
        return
    n = len(bullets)
    h = tp.SHOW_NOTE_H // max(n, 1)
    groups = []
    for i, b in enumerate(bullets):
        y = tp.SHOW_NOTE_Y + i * h
        bar = add_rect(slide, tp.SHOW_NOTE_X, y + Emu(20000),
                       Emu(30000), h - Emu(80000), tp.COLOR_BRAND_RED)
        _no_fx(bar)
        tb = add_textbox(slide, tp.SHOW_NOTE_X + pct_x(0.018), y,
                         tp.SHOW_NOTE_W - pct_x(0.018), h - Emu(60000), b,
                         font=FONT_BODY, size=tp.SZ_POINTER, color=tp.COLOR_INK,
                         align="left", anchor="middle", line_spacing=1.5)
        groups.append([bar.shape_id, tb.shape_id])
    if ctx.get("anim") and len(groups) > 1:
        add_click_reveal(slide, groups)


# ============================================================
# 12 · 收尾（行动号召，是内容页，与自动 _END 不是一回事）
# ============================================================
def render_closing(slide, page, ctx):
    _dark_ground(slide)
    title = page.title or ""
    segs = [(t, {"color": tp.COLOR_BRAND_RED if kw else tp.COLOR_DARK_FG,
                 "bold": True})
            for t, kw in _split_title_keywords(title)]
    add_rich_textbox(slide, pct_x(0.10), pct_y(0.240), pct_x(0.80), pct_y(0.180),
                     segs, font=FONT_TITLE, size=tp.SZ_SECTION_TITLE,
                     align="center", anchor="middle", line_spacing=1.35)
    if page.body:
        add_textbox(slide, pct_x(0.15), pct_y(0.430), pct_x(0.70), pct_y(0.100),
                    page.body, font=FONT_BODY, size=tp.SZ_SECTION_LEAD,
                    color=tp.COLOR_DARK_SUB, align="center", anchor="middle",
                    line_spacing=1.6)

    chips = page.bullets or []
    n = min(len(chips), 4)
    if n:
        gap = tp.CLOSE_CHIP_GAP
        total_w = pct_x(0.80)
        cw = (total_w - gap * (n - 1)) // n
        x0 = pct_x(0.10)
        for i, c in enumerate(chips[:n]):
            cx = x0 + i * (cw + gap)
            shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx,
                                         pct_y(0.590), cw, tp.CLOSE_CHIP_H)
            try:
                shp.adjustments[0] = tp.CLOSE_CHIP_RADIUS
            except Exception:
                pass
            shp.fill.solid()
            shp.fill.fore_color.rgb = _rgb(tp.COLOR_DARK_FROM)
            shp.line.color.rgb = _rgb(tp.COLOR_BRAND_RED)
            shp.line.width = Pt(1.25)
            _no_fx(shp)
            add_textbox(slide, cx + Emu(int(cw * 0.06)), pct_y(0.590),
                        cw - Emu(int(cw * 0.12)), tp.CLOSE_CHIP_H, c,
                        font=FONT_BODY, size=tp.SZ_CARD_BODY,
                        color=tp.COLOR_DARK_FG, align="center", anchor="middle",
                        line_spacing=1.4)
    _logo(slide, ctx, white=True)


# ============================================================
# _END · 宣讲件自己的收尾页
# ============================================================
def render_promo_end(slide, page, ctx):
    """品牌收尾页。**绝不出现「THE END」「下一次再见」**——那是课件文案，
    对着加盟商放出来是观感事故。layouts_common.render_end 把这两句硬编码在
    函数体里，所以宣讲 profile 自带一个，而不是去参数化共享层。

    page 参数仅占位，本函数不读取其内容（与 render_end 同约定）。
    """
    _dark_ground(slide)
    add_textbox(slide, pct_x(0.10), pct_y(0.380), pct_x(0.80), pct_y(0.120),
                "老约翰 · 校内同步写作", font=FONT_TITLE, size=tp.SZ_END_TITLE,
                color=tp.COLOR_DARK_FG, bold=True, align="center", anchor="middle")
    r = add_rect(slide, pct_x(0.465), pct_y(0.520), pct_x(0.070), Emu(30000),
                 tp.COLOR_BRAND_RED)
    _no_fx(r)
    add_textbox(slide, pct_x(0.15), pct_y(0.560), pct_x(0.70), pct_y(0.090),
                "写清楚 · 写生动 · 有章法", font=FONT_BODY, size=tp.SZ_END_SUB,
                color=tp.COLOR_DARK_SUB, align="center", anchor="middle")
    logo_white = ctx.get("logo_white_path") or ctx.get("logo_path")
    if logo_white:
        add_logo(slide, logo_white, pct_x(0.45), pct_y(0.760), pct_x(0.10))


RENDERERS_PROMO = {
    # —— 名字必须沿用（build_ppt 的课型无关逻辑靠它判定，改名静默出错）——
    "封面": render_cover,
    "环节标题": render_section,
    # —— 宣讲专属页型 ——
    "主张": render_claim,
    "数据面板": render_stats,
    "体系全景": render_overview,
    "流程时间轴": render_flow,
    "并列卡片": render_cards,
    "双栏对照": render_versus,
    "图集": render_gallery,
    "满屏图": render_showcase,
    "收尾": render_closing,
    # —— 复用既有页型名 ——
    "要点小结": render_list,
    "填空表格": render_overview,   # 纯表格页走全景版式（只画矩阵、不画轴）
    "_END": render_promo_end,
}
