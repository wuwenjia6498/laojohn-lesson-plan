# -*- coding: utf-8 -*-
"""写作课 profile 的页型渲染（校内同步习作课）。

视觉沿用读书会（深灰蓝 anchor bar、红强调、微软雅黑）；写作课专属页型在此新增，
全部是加法、不回头碰 layouts_reading。公共件来自 layouts_common（课型无关），
新增视觉常量走 theme_writing，绝不往 layouts_reading 或 helpers 里塞 `if 写作`。

写作课页型诉求的实现（全部是加法、不回头碰 layouts_reading）：
- 构思表填空变体 → 复用读书会「填空表格」（render_table），本模块不另写。
- 逐句批注 / 评改对照 / 审题辨析 → 「双栏对照」render_compare（行/块两模式）。
- 写作任务定格 → 「写作任务」render_writing_task（计时/字数提为显要 chip）。
- 情境任务（设定情境/发布任务/课尾寄语）→ 「情境任务」render_task_intro（整段陈述、不拆编号）。
- 写法讲解（讲写法/归纳要点）→ 「写法讲解」render_teach（克制描边序号、去 Q 水印、保留参考答案红字）。
- 活动指令（组织学生动手做）→ 「活动指令」render_activity（步骤条：深灰蓝方块+竖连接线）。
写作 profile 下「引导问题/要点小结」重定向到 render_teach（去水印兜底），不再画 Q 水印/红方块。
封面、环节标题、原文齐读复用读书会/公共版式。
"""
import math
import os
import re
from pptx.util import Pt, Emu
from pptx.enum.shapes import MSO_SHAPE
from helpers import (
    add_textbox, add_rect, add_table, add_rich_textbox,
    add_numbered_bullets, add_qa_textbox, add_click_reveal,
    add_image_placeholder, add_image_cover, rgb as _rgb,
    _disable_shape_effects as _disable_effects,
)
from theme import (
    FONT_TITLE, FONT_BODY, FONT_QUOTE, COLOR_TITLE, COLOR_BODY, COLOR_RED_ACCENT,
    COLOR_BG_QUOTE, SZ_HEADING, SZ_BODY,
)
import theme_writing as tw
from layouts_common import (
    _render_cover_base, render_end,
    draw_anchor, draw_logo_inner, draw_page_num, maybe_placeholder,
    bullets_text, _split_title_keywords, _real_suggestions,
    legend_to_colors,
    resolve_image,
)
from layouts_reading import (
    render_section, render_quote, render_table,
)


# ---------- 封面 ----------
def render_cover(slide, page, ctx):
    # 写作课：标题是习作题目（如"这儿真美"），不是书名，不加《》
    _render_cover_base(slide, page, ctx, wrap_brackets=False)


_EMU_PER_PT = 12700.0


def _fit_font_size(text, width_emu, height_emu, base, line_spacing, min_size=13,
                   char_w_factor=1.15, height_factor=1.1):
    """按字符数估算能塞进给定矩形的最大字号，确定性缩字（不依赖 PowerPoint 重算 autofit）。
    仅写作课双栏正文用。char_w_factor/height_factor 是保守系数（中文实测每字约 1.15
    倍字号宽、行距略大于标称），宁可缩多一点也不出血。"""
    width_pt = width_emu / _EMU_PER_PT
    avail_pt = height_emu / _EMU_PER_PT
    src = (text or "").split("\n")
    size = base
    while size > min_size:
        cpl = max(1, int(width_pt / (size * char_w_factor)))
        total = sum(max(1, math.ceil(len(ln) / cpl)) for ln in src)
        if total * size * line_spacing * height_factor <= avail_pt:
            break
        size -= 1
    return size


# 标题「纯文字」opt-out 值：不画色块（回到旧的纯文字标题）。
_TITLE_PLAIN_STYLES = {"纯文字", "无"}


def _title_boxed(style):
    """判定该标题样式是否画粉底色块（供渲染器决定是否再补标题下红短线，避免双重强调）。
    v8 起色块是**默认**：除 竖条 / 纯文字 外都画块（含 ""、"强调"、"默认"）。"""
    return style not in _TITLE_PLAIN_STYLES and style != "竖条"


def _heading(slide, x, y, w, h, title, size=SZ_HEADING, *, style=""):
    """带「」红字关键词高亮的内页大标题（沿用读书会引导问题页观感）。

    style（v8 · 纯样式、无课型分支）：
      - ""（默认）/"强调"/"默认"：标题坐在粉底圆角块上（无描边、无下短线、无阴影）。
        v8.1 起色块是**写作内页默认标题款**、铺到大部分页；"强调" 保留为同款别名（向后兼容）。
      - "竖条"：标题左侧红竖条（密集讲解页可选）。
      - "纯文字"/"无"：不画色块，回到纯文字标题（个别页想要素净时用）。
    """
    text_x = x
    text_w = w
    if style == "竖条":
        # 左红竖条 + 文字右移让位
        bar_h = Emu(int(h * 0.62))
        bar_y = y + (h - bar_h) // 2
        add_rect(slide, x, bar_y, tw.TITLE_BAR_W, bar_h, COLOR_RED_ACCENT)
        text_x = x + tw.TITLE_BAR_W + tw.TITLE_BAR_INSET
        text_w = w - (tw.TITLE_BAR_W + tw.TITLE_BAR_INSET)
    elif style not in _TITLE_PLAIN_STYLES:
        # 默认（含 "强调"/"默认"）：粉底圆角块托住标题（无描边、无下短线、无阴影）。
        # 估算文字实际宽度，色块只包住文字（不铺满整行）——用字符数×字号近似。
        plain = title or ""
        est_w = min(w, Emu(int(len(plain) * size * 12700 * 1.05)) + 2 * tw.TITLE_BOX_PAD_X)
        box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, y, est_w, h)
        try:
            box.adjustments[0] = tw.TITLE_BOX_RADIUS
        except Exception:
            pass
        box.fill.solid()
        box.fill.fore_color.rgb = _rgb(tw.COLOR_TITLE_BOX_BG)
        box.line.fill.background()          # 无描边
        _disable_effects(box)               # 无阴影
        text_x = x + tw.TITLE_BOX_PAD_X
        text_w = est_w - 2 * tw.TITLE_BOX_PAD_X
    # 纯文字/无：不画色块，纯文字标题（旧默认观感）

    segs = []
    for txt, is_kw in _split_title_keywords(title or ""):
        color = COLOR_RED_ACCENT if is_kw else COLOR_TITLE
        segs.append((txt, {"color": color, "bold": True}))
    add_rich_textbox(slide, text_x, y, text_w, h, segs,
                     font=FONT_TITLE, size=size,
                     align="left", anchor="middle", line_spacing=1.3)


# ---------- 双栏对照（逐句批注 / 评改对照 / 审题辨析）----------
def render_compare(slide, page, ctx):
    """左右并置一屏双看。两种模式按内容自动判：
    - 块模式：page.left_body / right_body（各一大段）——评改对照、审题辨析。
    - 行模式：page.table_headers / table_rows（2 列：句子↔批注）——示范文逐句批注。
    底部可选「判断依据/对比点」要点条（page.bullets）。
    """
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    _heading(slide, tw.COMPARE_TITLE_X, tw.COMPARE_TITLE_Y,
             tw.COMPARE_TITLE_W, tw.COMPARE_TITLE_H, page.title)

    is_rows = bool(page.table_headers)

    if is_rows:
        # 行模式：2 列对照表（纯展示、不挖空），复用读书会自适应表格引擎。
        # 分类上色（可选）：给了 `图例` 时，单元格 `[码:片段]` 按码上色（如旁批表右列
        # 的"打比方/看得见的颜色/听得见的声音"），颜色与示范文/五感表同源。
        cell_colors = legend_to_colors(page.legend) or None
        add_table(slide, tw.ROWS_TABLE_X, tw.ROWS_TABLE_Y,
                  tw.ROWS_TABLE_W, tw.ROWS_TABLE_H,
                  page.table_headers, page.table_rows, reveal_cells={},
                  cell_colors=cell_colors)
        return

    # 块模式：左右两栏（栏头 tab + 正文卡）+ 中缝分隔
    has_notes = bool(page.bullets)
    body_bottom = (tw.COMPARE_BODY_BOTTOM_WITHNOTES if has_notes
                   else tw.COMPARE_BODY_BOTTOM_FULL)
    body_h = body_bottom - tw.COMPARE_BODY_TOP

    # 中缝（常显，不入点击动画）
    add_rect(slide, tw.COMPARE_DIVIDER_X, tw.COMPARE_COL_TOP,
             tw.COMPARE_DIVIDER_W, body_bottom - tw.COMPARE_COL_TOP, tw.COLOR_DIVIDER)

    # 左右两栏取同一适配字号（取较长一栏的缩字结果），保持视觉平衡、杜绝出血
    pad = tw.COMPARE_COL_W // 24
    inner_w = tw.COMPARE_COL_W - 2 * pad
    inner_h = body_h - 2 * pad
    body_size = min(
        _fit_font_size(b, inner_w, inner_h, tw.SZ_COMPARE_BODY, 1.6)
        for b in (page.left_body, page.right_body) if b
    ) if (page.left_body or page.right_body) else tw.SZ_COMPARE_BODY

    # 逐步揭示顺序：先出一栏正文卡（让学生先读内容思考）、再亮该栏判断标签，左栏后右栏，
    # 最后底部「判断依据」逐条。教学逻辑：先看内容、再揭结论、后讲原因。
    reveal_seq = []
    for col_x, col_title, col_body in (
        (tw.COMPARE_LEFT_X, page.left_title, page.left_body),
        (tw.COMPARE_RIGHT_X, page.right_title, page.right_body),
    ):
        # 正文卡（卡背景 + 正文）——先揭示
        body_grp = []
        card = add_rect(slide, col_x, tw.COMPARE_BODY_TOP,
                        tw.COMPARE_COL_W, body_h, tw.COLOR_COMPARE_CARD_BG)
        body_grp.append(card.shape_id)
        if col_body:
            tb = add_textbox(slide, col_x + pad, tw.COMPARE_BODY_TOP + pad,
                             inner_w, inner_h, col_body,
                             font=FONT_BODY, size=body_size, color=COLOR_BODY,
                             align="left", anchor="top", line_spacing=1.6,
                             first_line_indent_chars=2)
            body_grp.append(tb.shape_id)
        reveal_seq.append(body_grp)
        # 栏头 tab（深灰蓝底白字）——后揭示（先读内容再亮"能贴/不能贴"的判断）
        if col_title:
            tab_bg = add_rect(slide, col_x, tw.COMPARE_COL_TOP,
                              tw.COMPARE_COL_W, tw.COMPARE_TAB_H, tw.COLOR_COMPARE_TAB_BG)
            tab_t = add_textbox(slide, col_x, tw.COMPARE_COL_TOP,
                                tw.COMPARE_COL_W, tw.COMPARE_TAB_H, col_title,
                                font=FONT_TITLE, size=tw.SZ_COMPARE_TAB,
                                color=tw.COLOR_COMPARE_TAB_FG, bold=True,
                                align="center", anchor="middle")
            reveal_seq.append([tab_bg.shape_id, tab_t.shape_id])

    # 底部「判断依据/对比点」要点：逐条揭示（一句一句出）
    if has_notes:
        _circle = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨"]
        n = len(page.bullets)
        line_h = tw.COMPARE_NOTES_H // max(1, n)
        for i, b in enumerate(page.bullets):
            marker = _circle[i] if i < len(_circle) else f"{i + 1}."
            nb = add_textbox(slide, tw.COMPARE_NOTES_X, tw.COMPARE_NOTES_Y + i * line_h,
                             tw.COMPARE_NOTES_W, line_h, f"{marker}  {b}",
                             font=FONT_BODY, size=tw.SZ_COMPARE_NOTES, color=COLOR_BODY,
                             align="left", anchor="middle")
            reveal_seq.append([nb.shape_id])

    # 点击逐步淡入（关动画/线上系统不支持时全部静态直出）
    if ctx.get("anim") and len(reveal_seq) >= 2:
        add_click_reveal(slide, reveal_seq)


# ---------- 写作任务定格页 ----------
def render_writing_task(slide, page, ctx):
    """静默写作时投屏定格：标题 + 任务要点 + 显要计时/字数 chip。

    定格页全程可见、不做点击动画（学生持续看任务锚点）。计时/字数缺则隐藏对应 chip
    （真实性红线：详案没给字数就不编）。
    """
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    _heading(slide, tw.TASK_TITLE_X, tw.TASK_TITLE_Y,
             tw.TASK_TITLE_W, tw.TASK_TITLE_H, page.title, size=tw.SZ_TASK_TITLE)

    # 任务要点（圈号①②③ 自然流式，静态全显）
    # 不用 add_numbered_bullets 的等距分布——任务要点长短不一会换行，等距会让长条重叠；
    # 流式文本框按 line_spacing 顺排，换行也不挤。
    if page.bullets:
        add_textbox(slide, tw.TASK_BULLETS_X, tw.TASK_BULLETS_Y,
                    tw.TASK_BULLETS_W, tw.TASK_BULLETS_H,
                    bullets_text(page.bullets),
                    font=FONT_TITLE, size=tw.SZ_TASK_BULLET, color=COLOR_BODY,
                    align="left", anchor="top", line_spacing=1.8)

    # 右侧 chip：计时（红）在上、字数（深灰蓝）在下；缺则隐藏
    def _chip(y, bg, label, value):
        add_rect(slide, tw.TASK_CHIP_X, y, tw.TASK_CHIP_W, tw.TASK_CHIP_H, bg)
        add_textbox(slide, tw.TASK_CHIP_X, y + tw.TASK_CHIP_H // 8,
                    tw.TASK_CHIP_W, tw.TASK_CHIP_H // 3, label,
                    font=FONT_BODY, size=tw.SZ_CHIP_LABEL, color=tw.COLOR_CHIP_FG,
                    align="center", anchor="middle")
        add_textbox(slide, tw.TASK_CHIP_X, y + tw.TASK_CHIP_H // 3,
                    tw.TASK_CHIP_W, tw.TASK_CHIP_H * 2 // 3, value,
                    font=FONT_TITLE, size=tw.SZ_CHIP_VALUE, color=tw.COLOR_CHIP_FG,
                    bold=True, align="center", anchor="middle")

    if page.timer:
        _chip(tw.TASK_CHIP_TIMER_Y, tw.COLOR_CHIP_TIMER_BG, "计时", page.timer)
    if page.word_count:
        _chip(tw.TASK_CHIP_WORD_Y, tw.COLOR_CHIP_WORD_BG, "字数", page.word_count)

    maybe_placeholder(slide, page)


# ---------- 情境任务页（设定情境 / 发布任务 / 课尾寄语）----------
def render_task_intro(slide, page, ctx):
    """老师设定情境、发布写作任务、课尾情境寄语。正文=整段陈述（连贯话不拆编号，
    首行缩进、字号略大、行距 1.7），底部可选 1–2 条圆点补充说明。无 Q 水印、无编号方块。"""
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    _heading(slide, tw.TASKINTRO_TITLE_X, tw.TASKINTRO_TITLE_Y,
             tw.TASKINTRO_TITLE_W, tw.TASKINTRO_TITLE_H, page.title, style=page.title_style)
    # 标题下红短线：仅纯文字标题才补（画了色块的默认/强调样式自带衬托，避免双重强调）
    if not _title_boxed(page.title_style):
        add_rect(slide, tw.TASKINTRO_RULE_X, tw.TASKINTRO_RULE_Y,
                 tw.TASKINTRO_RULE_W, tw.TASKINTRO_RULE_H, tw.COLOR_ACCENT_RULE)

    has_notes = bool(page.bullets)
    body_h = (tw.TASKINTRO_BODY_H_WITHNOTES if has_notes
              else tw.TASKINTRO_BODY_H_FULL)
    if page.body:
        # 有要点时正文=一句总起（引子）；无要点时正文=整段连贯陈述占大区
        body_size = (tw.SZ_TASKINTRO_LEAD if has_notes else tw.SZ_TASKINTRO_BODY)
        add_textbox(slide, tw.TASKINTRO_BODY_X, tw.TASKINTRO_BODY_Y,
                    tw.TASKINTRO_BODY_W, body_h, page.body,
                    font=FONT_BODY, size=body_size, color=COLOR_BODY,
                    align="left", anchor="top", line_spacing=1.7,
                    first_line_indent_chars=2)
    # 要点=任务的并列要素，用圆点符号列成主体（并列内容不套 1/2/3，与写法讲解无序一致）
    if has_notes:
        add_numbered_bullets(slide, tw.TASKINTRO_NOTES_X, tw.TASKINTRO_NOTES_Y,
                             tw.TASKINTRO_NOTES_W, tw.TASKINTRO_NOTES_H, page.bullets,
                             columns=1, text_size=tw.SZ_TASKINTRO_NOTE,
                             text_font=FONT_TITLE,
                             num_bg=tw.COLOR_TEACH_NUM, num_style="dot")

    maybe_placeholder(slide, page)


# ---------- 写法讲解页（讲写法 / 归纳要点）----------
def render_teach(slide, page, ctx):
    """讲写法、归纳要点。克制描边序号（白底深灰蓝边）、无 Q 水印。有参考答案时走
    "问题+红字答案"交错逐段揭示（承载真正的开放问句，如读样稿两问）。
    亦作写作 profile 下「引导问题/要点小结」的去水印兜底渲染器。"""
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    _heading(slide, tw.TEACH_TITLE_X, tw.TEACH_TITLE_Y,
             tw.TEACH_TITLE_W, tw.TEACH_TITLE_H, page.title, style=page.title_style)
    # 标题下红短线：仅纯文字标题才补（画了色块的默认/强调样式自带衬托，避免双重强调）
    if not _title_boxed(page.title_style):
        add_rect(slide, tw.TEACH_RULE_X, tw.TEACH_RULE_Y,
                 tw.TEACH_RULE_W, tw.TEACH_RULE_H, tw.COLOR_ACCENT_RULE)

    has_body = bool(page.body)
    if has_body:
        add_textbox(slide, tw.TEACH_BODY_X, tw.TEACH_BODY_Y,
                    tw.TEACH_BODY_W, tw.TEACH_BODY_H, page.body,
                    font=FONT_BODY, size=tw.SZ_TEACH_BODY, color=COLOR_BODY,
                    align="left", anchor="top", line_spacing=1.5)

    bx, bw = tw.TEACH_BULLETS_X, tw.TEACH_BULLETS_W
    by = tw.TEACH_BULLETS_Y_FULL if has_body else tw.TEACH_BULLETS_Y_NOBODY
    bh = tw.TEACH_BULLETS_H_FULL if has_body else tw.TEACH_BULLETS_H_NOBODY

    answers = getattr(page, "bullet_answers", None) or []
    has_ans = any(a for a in answers)
    qa_groups = bullet_groups = None
    if page.bullets:
        if has_ans:
            # 有参考答案→问答交错优先（教学正确性高于版式花样，卡片/菱形不承载红答案）
            _box, qa_groups = add_qa_textbox(
                slide, bx, by, bw, bh, page.bullets, answers,
                text_size=tw.SZ_TEACH_BULLET, font=FONT_TITLE,
            )
        else:
            # 无答案→按 bullet_style 选版式（竖排/卡片/步骤/图文/节点），默认竖排
            bullet_groups = _render_bullets(
                slide, page, ctx, bx, by, bw, bh,
                text_size=tw.SZ_TEACH_BULLET, text_font=FONT_TITLE,
            )

    if ctx.get("anim"):
        if qa_groups is not None and len(qa_groups) >= 2:
            add_click_reveal(slide, qa_groups)
        elif bullet_groups and len(bullet_groups) >= 2:
            add_click_reveal(slide, bullet_groups)

    maybe_placeholder(slide, page)


# ---------- 活动指令页（组织学生动手做）----------
def render_activity(slide, page, ctx):
    """组织学生动手做（感官活动、小解说员、说一说写一写、互评）。步骤条：深灰蓝实心
    方块序号 + 串联竖连接线（突出"照步骤做"的流程感，区别于写法讲解的静态罗列）；
    有情境场景配图建议时右侧挂占位。全程静态可见、不做点击动画。无 Q 水印。"""
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    _heading(slide, tw.ACTIVITY_TITLE_X, tw.ACTIVITY_TITLE_Y,
             tw.ACTIVITY_TITLE_W, tw.ACTIVITY_TITLE_H, page.title)

    sugs = _real_suggestions(page)
    has_img = bool(sugs)
    steps_w = tw.ACTIVITY_STEPS_W_WITHIMG if has_img else tw.ACTIVITY_STEPS_W

    n = len(page.bullets) if page.bullets else 0
    if n:
        # 先画串联竖连接线（在方块之下，两端被首末方块盖住、只在方块之间露出）
        if n >= 2:
            box_side = Pt(tw.SZ_ACTIVITY_STEP + 8)
            row_h = tw.ACTIVITY_STEPS_H // n
            first_c = tw.ACTIVITY_STEPS_Y + Pt(2) + box_side // 2
            last_c = tw.ACTIVITY_STEPS_Y + (n - 1) * row_h + Pt(2) + box_side // 2
            conn_x = tw.ACTIVITY_STEPS_X + box_side // 2 - tw.STEP_CONNECTOR_W // 2
            add_rect(slide, conn_x, first_c, tw.STEP_CONNECTOR_W,
                     last_c - first_c, tw.COLOR_STEP_CONNECTOR)
        add_numbered_bullets(
            slide, tw.ACTIVITY_STEPS_X, tw.ACTIVITY_STEPS_Y, steps_w,
            tw.ACTIVITY_STEPS_H, page.bullets, columns=1,
            text_size=tw.SZ_ACTIVITY_STEP, text_font=FONT_TITLE,
            num_bg=tw.COLOR_ACTIVITY_NUM, num_style="box",
        )

    if has_img:
        add_image_placeholder(slide, tw.ACTIVITY_IMG_X, tw.ACTIVITY_IMG_Y,
                              tw.ACTIVITY_IMG_W, tw.ACTIVITY_IMG_H, sugs[0])


# ---------- 教师示范文整页（整篇一页 + 字号按字数自适应 + 分句上色）----------
# 正文标注语法 `[码:片段]`：把该片段渲染成 `图例` 里此码对应的颜色（分句上色）。
_ANNOT_RE = re.compile(r"\[([^:：\]]+)[:：]([^\]]+)\]")


def _essay_color_segments(body, code_color, default_color):
    """把含 `[码:片段]` 标注的正文拆成 add_rich_textbox 的 segments，
    标注片段上对应色并加粗、其余用默认色。保留 \\n 供换段。"""
    segs = []
    pos = 0
    for m in _ANNOT_RE.finditer(body):
        if m.start() > pos:
            segs.append((body[pos:m.start()], {}))
        code, txt = m.group(1).strip(), m.group(2)
        segs.append((txt, {"color": code_color.get(code, default_color), "bold": True}))
        pos = m.end()
    if pos < len(body):
        segs.append((body[pos:], {}))
    return segs


def _draw_essay_legend(slide, legend, code_color):
    """顶部一行颜色图例：每项＝小色块 + 彩色图例名，横排。"""
    x = tw.MODELESSAY_LEGEND_X
    y = tw.MODELESSAY_LEGEND_Y
    h = tw.MODELESSAY_LEGEND_H
    sw = tw.MODELESSAY_LEGEND_SWATCH
    for code, name in legend:
        color = code_color[code]
        add_rect(slide, x, y + (h - sw) // 2, sw, sw, color)
        name_w = Pt(len(name) * tw.SZ_MODELESSAY_LEGEND * 1.2)
        add_textbox(slide, x + sw + Pt(5), y, name_w, h, name,
                    font=FONT_BODY, size=tw.SZ_MODELESSAY_LEGEND, color=color,
                    bold=True, align="left", anchor="middle")
        x += sw + Pt(5) + name_w + tw.MODELESSAY_LEGEND_GAP


def render_model_essay(slide, page, ctx):
    """教师示范文整篇塞进一页，正文字号按实际字数确定性缩放（不拆页）。米色书页观感、宋体。
    区别于读书会「原文齐读」的大字满屏、每段独立成页——示范文要让学生一眼看到整篇谋篇结构。
    **分句上色**：若给了 `图例`（码=名），正文里 `[码:片段]` 的片段按码上色、顶部画颜色图例，
    让"哪句写颜色/声音/比喻"在文字上直接跳出来（无图例时=纯灰底整篇，向后兼容）。"""
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    # 米色书页底
    add_rect(slide, tw.MODELESSAY_BG_X, tw.MODELESSAY_BG_Y,
             tw.MODELESSAY_BG_W, tw.MODELESSAY_BG_H, COLOR_BG_QUOTE)

    if page.title:
        add_textbox(slide, tw.MODELESSAY_TITLE_X, tw.MODELESSAY_TITLE_Y,
                    tw.MODELESSAY_TITLE_W, tw.MODELESSAY_TITLE_H, page.title,
                    font=FONT_TITLE, size=tw.SZ_MODELESSAY_TITLE, color=COLOR_TITLE,
                    bold=True, align="left", anchor="middle")

    # 图例（可选）：码 → 颜色（按声明顺序取全课统一调色板；与五感表/旁批表同源）
    legend = getattr(page, "legend", None) or []
    code_color = legend_to_colors(legend)
    if legend:
        _draw_essay_legend(slide, legend, code_color)
        body_x, body_y = tw.MODELESSAY_BODY_X, tw.MODELESSAY_BODY_Y_LEGEND
        body_w, body_h = tw.MODELESSAY_BODY_W, tw.MODELESSAY_BODY_H_LEGEND
    else:
        body_x, body_y = tw.MODELESSAY_BODY_X, tw.MODELESSAY_BODY_Y
        body_w, body_h = tw.MODELESSAY_BODY_W, tw.MODELESSAY_BODY_H

    if page.body:
        # 保守缩字（下限 12pt）：整篇范文段落多、中文真实行高比字号×行距更大，默认系数会低估
        # 行数致末段溢出——宁可缩小一点保证整篇塞得下。字号按**剥掉标注后**的纯文本算。
        _ls = 1.45
        plain = _ANNOT_RE.sub(lambda m: m.group(2), page.body)
        size = _fit_font_size(plain, body_w, body_h, tw.SZ_MODELESSAY_BODY_MAX, _ls,
                              char_w_factor=1.2, height_factor=1.55, min_size=12)
        if code_color:
            segs = _essay_color_segments(page.body, code_color, COLOR_TITLE)
            add_rich_textbox(slide, body_x, body_y, body_w, body_h, segs,
                             font=FONT_QUOTE, size=size, default_color=COLOR_TITLE,
                             align="left", anchor="top", line_spacing=_ls)
        else:
            add_textbox(slide, body_x, body_y, body_w, body_h, page.body,
                        font=FONT_QUOTE, size=size, color=COLOR_TITLE,
                        line_spacing=_ls, first_line_indent_chars=2,
                        align="left", anchor="top")


# ============ v8 图片路径解析 ============
# 单一源已提到 layouts_common.resolve_image（读书会 v9 同用）；此处保留旧名供本模块调用。
_resolve_image = resolve_image


# ============ v8 要点多版式分派 ============
def _render_bullets(slide, page, ctx, x, y, w, h, *,
                    text_size=tw.SZ_TEACH_BULLET, text_font=FONT_TITLE):
    """按 page.bullet_style 选版式渲染要点，统一返回逐条点击分组（供 add_click_reveal）。
    竖排＝复用 add_numbered_bullets（现有行为，默认）。其余走本模块新版式。
    有参考答案(bullet_answers)时优先走问答交错（add_qa_textbox），版式选择器让位教学正确性。
    """
    bullets = page.bullets or []
    if not bullets:
        return []
    style = page.bullet_style or "竖排"

    if style == "卡片":
        return _bullets_cards(slide, bullets, page, x, y, w, h, text_size)
    if style == "节点":
        return _bullets_diamond(slide, bullets, x, y, w, h, text_size)
    if style == "图文":
        return _bullets_media(slide, page, ctx, bullets, y, text_size)
    if style == "步骤":
        return add_numbered_bullets(slide, x, y, w, h, bullets, columns=1,
                                    text_size=text_size, text_font=text_font,
                                    num_bg=tw.COLOR_ACTIVITY_NUM, num_style="box")
    # 竖排（默认）：有序→bar、无序→dot，沿用讲解页观感
    num_style = "bar" if page.bullets_ordered else "dot"
    return add_numbered_bullets(slide, x, y, w, h, bullets, columns=1,
                                text_size=text_size, text_font=text_font,
                                num_bg=tw.COLOR_TEACH_NUM, num_style=num_style)


def _bullets_cards(slide, bullets, page, x, y, w, h, text_size):
    """要点卡片横排：每条一张浅底圆角卡 + 序号圆章。末条可红底强调（bullets_highlight_last）。
    3 条稳、4 条自动缩窄。返回每卡的形状分组（卡+章+字一次点击同出）。"""
    n = len(bullets)
    cols = min(n, 4)
    gap = tw.CARDS_GAP
    card_w = (w - gap * (cols - 1)) // cols
    groups = []
    hl_last = getattr(page, "bullets_highlight_last", False)
    for i, b in enumerate(bullets):
        cx = x + i * (card_w + gap)
        is_hl = hl_last and i == n - 1
        fill = tw.COLOR_CARD_FILL_HL if is_hl else tw.COLOR_CARD_FILL
        num_bg = tw.COLOR_CARD_NUM_HL if is_hl else tw.COLOR_CARD_NUM
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, cx, y, card_w, h)
        try:
            card.adjustments[0] = tw.CARD_RADIUS
        except Exception:
            pass
        card.fill.solid(); card.fill.fore_color.rgb = _rgb(fill)
        card.line.fill.background()
        _disable_effects(card)
        # 序号圆章
        num_d = tw.CARD_NUM_D
        num_x = cx + Emu(int(card_w * 0.08))
        num_y = y + Emu(int(h * 0.08))
        chip = slide.shapes.add_shape(MSO_SHAPE.OVAL, num_x, num_y, num_d, num_d)
        chip.fill.solid(); chip.fill.fore_color.rgb = _rgb(num_bg)
        chip.line.fill.background(); _disable_effects(chip)
        num_t = add_textbox(slide, num_x, num_y, num_d, num_d, str(i + 1),
                            font=FONT_TITLE, size=tw.SZ_CARD_NUM, color="FFFFFF",
                            bold=True, align="center", anchor="middle")
        # 卡内正文
        pad = Emu(int(card_w * 0.09))
        txt = add_textbox(slide, cx + pad, num_y + num_d + Emu(int(h * 0.04)),
                          card_w - 2 * pad, h - num_d - Emu(int(h * 0.16)), b,
                          font=FONT_BODY, size=text_size, color=COLOR_BODY,
                          align="left", anchor="top", line_spacing=1.35)
        groups.append([card.shape_id, chip.shape_id, num_t.shape_id, txt.shape_id])
    return groups


def _bullets_diamond(slide, bullets, x, y, w, h, text_size):
    """要点菱形节点竖排：双层菱形序号节点（不放图标）+ 折线引导 + 文字。3–4 条。
    折线：节点右尖 → 短横 → 斜折 → 文字带。返回每条分组（菱形组+折线+字一次点击）。"""
    n = len(bullets)
    step = tw.DIAMOND_STEP if n <= 4 else Emu(int((h) / n))
    cx = tw.DIAMOND_X
    groups = []
    for i, b in enumerate(bullets):
        cy = tw.DIAMOND_TOP + i * step
        # 外层浅蓝菱形（旋转45°的方块用菱形自选图形 MSO_SHAPE.DIAMOND）
        o = tw.DIAMOND_OUTER
        outer = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, cx - o, cy - o, 2 * o, 2 * o)
        outer.fill.solid(); outer.fill.fore_color.rgb = _rgb(tw.COLOR_DIAMOND_OUTER)
        outer.line.fill.background(); _disable_effects(outer)
        ii = tw.DIAMOND_INNER
        inner = slide.shapes.add_shape(MSO_SHAPE.DIAMOND, cx - ii, cy - ii, 2 * ii, 2 * ii)
        inner.fill.solid(); inner.fill.fore_color.rgb = _rgb(tw.COLOR_DIAMOND_INNER)
        inner.line.fill.background(); _disable_effects(inner)
        num_t = add_textbox(slide, cx - ii, cy - ii, 2 * ii, 2 * ii, str(i + 1),
                            font=FONT_TITLE, size=tw.SZ_DIAMOND_NUM, color="FFFFFF",
                            bold=True, align="center", anchor="middle")
        # 折线引导：节点右尖 → 文字带左侧（细灰折线，用两段矩形近似避免自定义几何）
        line_y = cy
        seg1_x = cx + o
        seg1_w = tw.DIAMOND_TEXT_X - seg1_x
        conn = add_rect(slide, seg1_x, line_y - Emu(6000), max(Emu(1), seg1_w), Emu(12000),
                        tw.COLOR_DIAMOND_LINE)
        _disable_effects(conn)
        # 文字
        txt = add_textbox(slide, tw.DIAMOND_TEXT_X, cy - Emu(int(step * 0.32)),
                          tw.DIAMOND_TEXT_W, Emu(int(step * 0.64)), b,
                          font=FONT_BODY, size=tw.SZ_DIAMOND_TEXT, color=COLOR_BODY,
                          align="left", anchor="middle", line_spacing=1.3)
        groups.append([outer.shape_id, inner.shape_id, num_t.shape_id,
                       conn.shape_id, txt.shape_id])
    return groups


def _bullets_media(slide, page, ctx, bullets, y, text_size):
    """图文版式：左真图（image_path→add_image_cover）+ 右要点竖排。
    图无路径时 add_image_cover 自兜底占位。返回右侧要点的逐条分组（图不入点击、首屏即在）。"""
    img_path = _resolve_image(ctx, getattr(page, "image_path", ""))
    add_image_cover(slide, tw.MEDIA_IMG_X, tw.MEDIA_IMG_Y, tw.MEDIA_IMG_W, tw.MEDIA_IMG_H,
                    img_path)
    return add_numbered_bullets(slide, tw.MEDIA_BULLETS_X, tw.MEDIA_BULLETS_Y,
                                tw.MEDIA_BULLETS_W, tw.MEDIA_BULLETS_H, bullets,
                                columns=1, text_size=text_size, text_font=FONT_TITLE,
                                num_bg=tw.COLOR_TEACH_NUM, num_style="dot")


# ============ v8 实景观察页（大图 + 感官问答，图外文字、不压图）============
def render_scene_observe(slide, page, ctx):
    """实景观察：给学生看真实场景图，问"看/听/闻/摸到什么"。图在上、绿色说明条压图底沿、
    问答文字在图外下方、绿线收尾（还原文件4老槐树S5/荷塘石头S6）。
    场景数自动切版面：1 景→图占右侧、问答在左；2 景→两卡并排。逐场景点击揭示答案。"""
    draw_anchor(slide, page.eyebrow)
    draw_logo_inner(slide, ctx.get("logo_path"))
    draw_page_num(slide, ctx["page_index"], ctx["page_total"])

    _heading(slide, tw.SCENE_TITLE_X, tw.SCENE_TITLE_Y, tw.SCENE_TITLE_W,
             tw.SCENE_TITLE_H, page.title, style=page.title_style or "强调")

    scenes = page.scenes or []
    if not scenes:
        # 没写场景就退化成占位提示，不报错
        add_image_placeholder(slide, tw.SCENE1_IMG_X, tw.SCENE1_IMG_Y,
                              tw.SCENE1_IMG_W, tw.SCENE1_IMG_H,
                              page.image_suggestion or "实景照片")
        return

    reveal = []
    if len(scenes) == 1:
        sc = scenes[0]
        img = _resolve_image(ctx, sc.get("image_path", ""))
        _pic, _caps = add_image_cover(
            slide, tw.SCENE1_IMG_X, tw.SCENE1_IMG_Y, tw.SCENE1_IMG_W, tw.SCENE1_IMG_H,
            img, caption=sc.get("name") or None,
            caption_band_color=tw.COLOR_SCENE_BAND, caption_size=tw.SZ_SCENE_NAME)
        # 左侧问答：问题黑字 + 答案红字，逐段点击
        q = sc.get("question", ""); a = sc.get("answer", "")
        _box, groups = add_qa_textbox(
            slide, tw.SCENE1_QA_X, tw.SCENE1_QA_Y, tw.SCENE1_QA_W, tw.SCENE1_QA_H,
            [q] if q else [], [a] if a else [],
            text_size=tw.SZ_SCENE_Q, font=FONT_TITLE,
            body_color=tw.COLOR_SCENE_QUESTION, answer_color=tw.COLOR_SCENE_ANSWER)
        reveal.extend(groups)
    else:
        for col_x, sc in zip((tw.SCENE2_LEFT_X, tw.SCENE2_RIGHT_X), scenes[:2]):
            img = _resolve_image(ctx, sc.get("image_path", ""))
            add_image_cover(
                slide, col_x, tw.SCENE2_CARD_TOP, tw.SCENE2_CARD_W, tw.SCENE2_IMG_H,
                img, caption=sc.get("name") or None,
                caption_band_color=tw.COLOR_SCENE_BAND, caption_size=tw.SZ_SCENE_NAME)
            q = sc.get("question", ""); a = sc.get("answer", "")
            _box, groups = add_qa_textbox(
                slide, col_x, tw.SCENE2_TEXT_Y, tw.SCENE2_CARD_W, tw.SCENE2_TEXT_H,
                [q] if q else [], [a] if a else [],
                text_size=tw.SZ_SCENE_Q, font=FONT_TITLE,
                body_color=tw.COLOR_SCENE_QUESTION, answer_color=tw.COLOR_SCENE_ANSWER)
            reveal.extend(groups)
            # 卡底绿细线
            add_rect(slide, col_x, tw.SCENE2_RULE_Y, tw.SCENE2_CARD_W, Emu(9000),
                     tw.COLOR_SCENE_RULE)

    if ctx.get("anim") and len(reveal) >= 2:
        add_click_reveal(slide, reveal)


RENDERERS_WRITING = {
    "封面": render_cover,
    # —— 写作课专属页型 ——
    "情境任务": render_task_intro,
    "写法讲解": render_teach,
    "活动指令": render_activity,
    "示范文": render_model_essay,
    "双栏对照": render_compare,
    "写作任务": render_writing_task,
    "实景观察": render_scene_observe,
    # —— 复用公共/读书会课型无关版式 ——
    "环节标题": render_section,
    "原文齐读": render_quote,
    "填空表格": render_table,
    # —— 去水印兜底：写作课不再主推这两页型，残留则用讲解版渲染（无 Q 水印/红方块）——
    "引导问题": render_teach,
    "要点小结": render_teach,
    "_END": render_end,
}
