# -*- coding: utf-8 -*-
"""写作课 profile 的视觉变体常量（profile 接缝 · 写作课覆盖层）。

视觉沿用读书会（深灰蓝 anchor bar、红强调、微软雅黑）——本模块只补写作课新页型
（双栏对照 / 写作任务 / 情境任务 / 写法讲解 / 活动指令）需要的坐标与少量配色，
相同的仍直接用 theme.py。约定：只放写作课**与读书会不同**的那部分；不另起色系。

三个讲解页型的序号视觉互相区分（都在读书会基色内）：
    要点小结（读书会）= 红实心方块；写法讲解 = 白底深灰蓝描边序号（克制）；
    活动指令 = 深灰蓝实心方块 + 竖连接线（步骤流）。
"""
from theme import (
    COLOR_ANCHOR_BAR, COLOR_RED_ACCENT, COLOR_BODY, COLOR_TITLE,
    COLOR_BG_PLACE, COLOR_DASH,
    pct_x, pct_y,
)

# ============ 复用读书会基色（语义别名，便于 layouts_writing 引用）============
COLOR_COMPARE_TAB_BG = COLOR_ANCHOR_BAR    # 双栏栏头底色（深灰蓝）
COLOR_COMPARE_TAB_FG = "FFFFFF"
COLOR_COMPARE_CARD_BG = COLOR_BG_PLACE     # 双栏正文卡底（极浅灰）
COLOR_DIVIDER = COLOR_DASH                 # 中缝分隔线
COLOR_CHIP_TIMER_BG = COLOR_RED_ACCENT     # 计时 chip（红，最醒目）
COLOR_CHIP_WORD_BG = COLOR_ANCHOR_BAR      # 字数 chip（深灰蓝）
COLOR_CHIP_FG = "FFFFFF"

# ============ 双栏对照页（render_compare）============
# 标题带（与要点小结标题同高区）
COMPARE_TITLE_X = pct_x(0.07)
COMPARE_TITLE_Y = pct_y(0.20)
COMPARE_TITLE_W = pct_x(0.86)
COMPARE_TITLE_H = pct_y(0.12)

# 左右两栏（中缝在 0.50）：栏头 tab + 正文卡
COMPARE_COL_TOP = pct_y(0.35)             # 两栏顶部
COMPARE_TAB_H = pct_y(0.075)              # 栏头 tab 高
COMPARE_LEFT_X = pct_x(0.07)
COMPARE_RIGHT_X = pct_x(0.515)
COMPARE_COL_W = pct_x(0.415)             # 单栏宽（左右各一）
COMPARE_DIVIDER_X = pct_x(0.498)
COMPARE_DIVIDER_W = pct_x(0.004)

# 正文卡（tab 下方到底部；若有底部要点条则上抬）
COMPARE_BODY_TOP = pct_y(0.435)          # = COL_TOP + TAB_H + 间隙
COMPARE_BODY_BOTTOM_FULL = pct_y(0.91)   # 无要点条时正文卡底边
COMPARE_BODY_BOTTOM_WITHNOTES = pct_y(0.74)  # 有要点条时正文卡底边

# 底部「判断依据/对比点」要点条
COMPARE_NOTES_X = pct_x(0.07)
COMPARE_NOTES_Y = pct_y(0.77)
COMPARE_NOTES_W = pct_x(0.86)
COMPARE_NOTES_H = pct_y(0.15)

SZ_COMPARE_TAB = 22       # 栏头小标题
SZ_COMPARE_BODY = 20      # 栏内正文
SZ_COMPARE_NOTES = 20     # 底部要点

# 行模式（逐句批注）：复用读书会 add_table（2 列：句子↔批注），表区与填空表同位
ROWS_TABLE_X = pct_x(0.07)
ROWS_TABLE_Y = pct_y(0.36)
ROWS_TABLE_W = pct_x(0.86)
ROWS_TABLE_H = pct_y(0.56)

# ============ 写作任务定格页（render_writing_task）============
TASK_TITLE_X = pct_x(0.07)
TASK_TITLE_Y = pct_y(0.20)
TASK_TITLE_W = pct_x(0.60)        # 右侧给 chip 让位
TASK_TITLE_H = pct_y(0.16)

TASK_BULLETS_X = pct_x(0.07)
TASK_BULLETS_Y = pct_y(0.40)
TASK_BULLETS_W = pct_x(0.60)
TASK_BULLETS_H = pct_y(0.50)

# 右侧两枚显要 chip（计时在上、字数在下）
TASK_CHIP_X = pct_x(0.70)
TASK_CHIP_W = pct_x(0.25)
TASK_CHIP_H = pct_y(0.16)
TASK_CHIP_TIMER_Y = pct_y(0.40)
TASK_CHIP_WORD_Y = pct_y(0.60)

SZ_TASK_TITLE = 34
SZ_TASK_BULLET = 24
SZ_CHIP_LABEL = 16        # chip 上行小标签（"计时""字数"）
SZ_CHIP_VALUE = 34        # chip 下行大值

# ============ 讲解三页型共用 ============
COLOR_ACCENT_RULE = COLOR_RED_ACCENT      # 标题下红短线
COLOR_TEACH_NUM = COLOR_ANCHOR_BAR        # 写法讲解描边序号（边+数字，深灰蓝）
COLOR_ACTIVITY_NUM = COLOR_ANCHOR_BAR     # 活动指令步骤方块底（深灰蓝）
COLOR_STEP_CONNECTOR = COLOR_ANCHOR_BAR   # 活动指令步骤间竖连接线

# ============ 情境任务页（render_task_intro）============
# 老师设定情境 / 发布任务 / 课尾寄语——整段陈述，连贯话不拆编号。
TASKINTRO_TITLE_X = pct_x(0.07)
TASKINTRO_TITLE_Y = pct_y(0.185)
TASKINTRO_TITLE_W = pct_x(0.86)
TASKINTRO_TITLE_H = pct_y(0.13)
TASKINTRO_RULE_X = pct_x(0.075)
TASKINTRO_RULE_Y = pct_y(0.330)
TASKINTRO_RULE_W = pct_x(0.055)
TASKINTRO_RULE_H = pct_y(0.010)
TASKINTRO_BODY_X = pct_x(0.07)
TASKINTRO_BODY_Y = pct_y(0.385)
TASKINTRO_BODY_W = pct_x(0.86)
TASKINTRO_BODY_H_FULL = pct_y(0.50)        # 无要点时正文占大区（连贯口令/寄语）
TASKINTRO_BODY_H_WITHNOTES = pct_y(0.15)   # 有要点时正文=一句总起（引子）
TASKINTRO_NOTES_X = pct_x(0.07)
TASKINTRO_NOTES_Y = pct_y(0.55)
TASKINTRO_NOTES_W = pct_x(0.86)
TASKINTRO_NOTES_H = pct_y(0.36)
SZ_TASKINTRO_BODY = 26     # 陈述正文（比常规正文大，突出"这是一个任务/情境"）
SZ_TASKINTRO_LEAD = 22     # 有要点时的总起句（引子，略小）
SZ_TASKINTRO_NOTE = 22     # 任务要素圆点

# ============ 写法讲解页（render_teach）============
# 讲写法 / 归纳要点——克制描边序号，保留参考答案红字揭示。无 Q 水印。
TEACH_TITLE_X = pct_x(0.07)
TEACH_TITLE_Y = pct_y(0.185)
TEACH_TITLE_W = pct_x(0.86)
TEACH_TITLE_H = pct_y(0.12)
TEACH_RULE_X = pct_x(0.075)
TEACH_RULE_Y = pct_y(0.315)
TEACH_RULE_W = pct_x(0.055)
TEACH_RULE_H = pct_y(0.010)
TEACH_BODY_X = pct_x(0.07)          # 可选中心句/引文小字
TEACH_BODY_Y = pct_y(0.350)
TEACH_BODY_W = pct_x(0.86)
TEACH_BODY_H = pct_y(0.10)
TEACH_BULLETS_X = pct_x(0.07)
TEACH_BULLETS_W = pct_x(0.86)
TEACH_BULLETS_Y_FULL = pct_y(0.47)     # 上方有正文时要点下压
TEACH_BULLETS_H_FULL = pct_y(0.44)
TEACH_BULLETS_Y_NOBODY = pct_y(0.375)  # 无正文时要点上抬
TEACH_BULLETS_H_NOBODY = pct_y(0.535)
SZ_TEACH_BODY = 18
SZ_TEACH_BULLET = 22

# ============ 活动指令页（render_activity）============
# 组织学生动手做——步骤条（深灰蓝方块序号 + 竖连接线），可挂情境配图占位。
ACTIVITY_TITLE_X = pct_x(0.07)
ACTIVITY_TITLE_Y = pct_y(0.185)
ACTIVITY_TITLE_W = pct_x(0.86)
ACTIVITY_TITLE_H = pct_y(0.12)
ACTIVITY_STEPS_X = pct_x(0.07)
ACTIVITY_STEPS_Y = pct_y(0.375)
ACTIVITY_STEPS_W = pct_x(0.86)            # 无配图时步骤条全宽
ACTIVITY_STEPS_W_WITHIMG = pct_x(0.55)    # 有配图时让位右侧
ACTIVITY_STEPS_H = pct_y(0.525)
ACTIVITY_IMG_X = pct_x(0.66)
ACTIVITY_IMG_Y = pct_y(0.375)
ACTIVITY_IMG_W = pct_x(0.28)
ACTIVITY_IMG_H = pct_y(0.42)
SZ_ACTIVITY_STEP = 22
# 步骤竖连接线宽（细）
STEP_CONNECTOR_W = pct_x(0.003)

# ============ 教师示范文整页（render_model_essay）============
# 整篇范文塞进一页、字号按字数自适应缩放（不拆页）；米色书页观感。
MODELESSAY_BG_X = pct_x(0.05)
MODELESSAY_BG_Y = pct_y(0.155)
MODELESSAY_BG_W = pct_x(0.90)
MODELESSAY_BG_H = pct_y(0.785)
MODELESSAY_TITLE_X = pct_x(0.09)
MODELESSAY_TITLE_Y = pct_y(0.185)
MODELESSAY_TITLE_W = pct_x(0.82)
MODELESSAY_TITLE_H = pct_y(0.075)
MODELESSAY_BODY_X = pct_x(0.09)
MODELESSAY_BODY_Y = pct_y(0.275)
MODELESSAY_BODY_W = pct_x(0.82)
MODELESSAY_BODY_H = pct_y(0.655)
SZ_MODELESSAY_TITLE = 26
SZ_MODELESSAY_BODY_MAX = 26   # 自适应上限；字多则往下缩（_fit_font_size，min 13）

# 分句上色：图例行坐标（调色板见 layouts_common.CATEGORY_PALETTE，全课统一单一源——
# 示范文/五感表/旁批表共用，颜色按 `图例` 声明顺序取）
MODELESSAY_LEGEND_X = pct_x(0.09)
MODELESSAY_LEGEND_Y = pct_y(0.272)
MODELESSAY_LEGEND_H = pct_y(0.042)
MODELESSAY_LEGEND_SWATCH = pct_x(0.010)   # 图例色块边长
MODELESSAY_LEGEND_GAP = pct_x(0.022)      # 图例项之间的间隔
SZ_MODELESSAY_LEGEND = 15
# 有图例时正文下移让出图例行（无图例用上面的 BODY_Y/H 占满）
MODELESSAY_BODY_Y_LEGEND = pct_y(0.322)
MODELESSAY_BODY_H_LEGEND = pct_y(0.608)


# ============ v8 标题样式（_heading 的 boxed/bar 分支）============
# 样式"强调"：粉底圆角框 + 红描边 + 标题下红短线（抓注意力页用，如情境任务/环节起始）。
# 样式"竖条"：标题左侧红竖条（克制，密集讲解页用）。不声明＝纯文字（默认）。
COLOR_TITLE_BOX_BG = "FBEEF0"          # 标题强调粉底
COLOR_TITLE_BOX_BORDER = COLOR_RED_ACCENT
TITLE_BOX_PAD_X = pct_x(0.012)         # 粉底框比文字左右各外扩
TITLE_BOX_RADIUS = 0.28                # 圆角比例（roundRect adj）
TITLE_BOX_RULE_W = pct_x(0.055)        # 框下红短线宽
TITLE_BOX_RULE_H = pct_y(0.008)
TITLE_BOX_RULE_GAP = pct_y(0.012)      # 框底到红短线的间隙
TITLE_BAR_W = pct_x(0.006)             # 竖条样式：左红竖条宽
TITLE_BAR_INSET = pct_x(0.006)         # 竖条与文字的间隙（竖条在文字左侧）

# ============ v8 要点·卡片版式（render_bullets_cards）============
# 每条要点一张浅底圆角卡横排；序号圆章；末条可红底强调。3 条稳、4 条缩。
CARDS_Y = pct_y(0.40)
CARDS_H = pct_y(0.45)
CARDS_X = pct_x(0.07)
CARDS_W = pct_x(0.86)
CARDS_GAP = pct_x(0.02)
COLOR_CARD_FILL = "F1EFE8"             # 卡底（浅灰米）
COLOR_CARD_FILL_HL = "FBEEF0"          # 强调卡底（浅粉）
COLOR_CARD_NUM = COLOR_ANCHOR_BAR      # 序号章底（深灰蓝）
COLOR_CARD_NUM_HL = COLOR_RED_ACCENT   # 强调卡序号章底（红）
CARD_RADIUS = 0.08
CARD_NUM_D = pct_y(0.075)              # 序号圆章直径
SZ_CARD_TEXT = 17
SZ_CARD_NUM = 18

# ============ v8 要点·菱形节点版式（render_bullets_diamond）============
# 双层菱形序号节点（不放语义图标）+ 折线引导 + 文字带。3–4 条竖排。
DIAMOND_X = pct_x(0.055)               # 节点中心 X
DIAMOND_TOP = pct_y(0.40)              # 第一个节点中心 Y
DIAMOND_STEP = pct_y(0.155)            # 节点垂直间距（4 条约到 0.86）
DIAMOND_OUTER = pct_x(0.030)           # 外层菱形对角半宽（缩小：0.040→0.030）
DIAMOND_INNER = pct_x(0.021)           # 内层菱形对角半宽（缩小：0.029→0.021）
COLOR_DIAMOND_OUTER = "C7D3DE"         # 外层雾霾蓝（低饱和）
COLOR_DIAMOND_INNER = "7B93A8"         # 内层雾霾蓝（低饱和）
COLOR_DIAMOND_OUTER_HL = "F4C0D1"      # 强调外层浅粉
COLOR_DIAMOND_INNER_HL = COLOR_RED_ACCENT
COLOR_DIAMOND_LINE = "B4B2A9"          # 折线引导（浅灰）
DIAMOND_TEXT_X = pct_x(0.115)          # 文字左界（菱形缩小后左移：0.135→0.115）
DIAMOND_TEXT_W = pct_x(0.82)
SZ_DIAMOND_TEXT = 18
SZ_DIAMOND_NUM = 13                     # 序号字号（随菱形缩小：16→13）

# ============ v8 要点·图文版式（render_bullets_media）============
# 左真图（image_path，走 add_image_cover）+ 右要点竖排。
MEDIA_IMG_X = pct_x(0.07)
MEDIA_IMG_Y = pct_y(0.40)
MEDIA_IMG_W = pct_x(0.36)
MEDIA_IMG_H = pct_y(0.46)
MEDIA_BULLETS_X = pct_x(0.48)
MEDIA_BULLETS_Y = pct_y(0.40)
MEDIA_BULLETS_W = pct_x(0.45)
MEDIA_BULLETS_H = pct_y(0.46)

# ============ v8 实景观察页（render_scene_observe）============
# 图在上、绿色半透明说明条压图底沿、问答文字在图外下方、绿线收尾。
# 1 景→单景（图占右上、问答在左）；2 景→双景并排。对齐文件4老槐树S5/荷塘石头S6。
SCENE_TITLE_X = pct_x(0.07)
SCENE_TITLE_Y = pct_y(0.185)
SCENE_TITLE_W = pct_x(0.86)
SCENE_TITLE_H = pct_y(0.12)
COLOR_SCENE_BAND = "6F9F5B"            # 场景说明条（绿，还原文件4）
COLOR_SCENE_RULE = "8FB877"            # 卡片底部绿细线
COLOR_SCENE_ANSWER = COLOR_RED_ACCENT  # 答案红字
COLOR_SCENE_QUESTION = COLOR_TITLE     # 问题黑字
# —— 双景并排：两张卡左右分列 ——
SCENE2_CARD_TOP = pct_y(0.33)
SCENE2_LEFT_X = pct_x(0.055)
SCENE2_RIGHT_X = pct_x(0.515)
SCENE2_CARD_W = pct_x(0.43)
SCENE2_IMG_H = pct_y(0.30)             # 卡内图高
SCENE2_TEXT_Y = pct_y(0.65)            # 图下问答文字起点
SCENE2_TEXT_H = pct_y(0.22)
SCENE2_RULE_Y = pct_y(0.90)
# —— 单景：图占右侧、问答卡在左 ——
SCENE1_IMG_X = pct_x(0.60)
SCENE1_IMG_Y = pct_y(0.33)
SCENE1_IMG_W = pct_x(0.34)
SCENE1_IMG_H = pct_y(0.55)
SCENE1_QA_X = pct_x(0.07)
SCENE1_QA_Y = pct_y(0.35)
SCENE1_QA_W = pct_x(0.48)
SCENE1_QA_H = pct_y(0.55)
SZ_SCENE_NAME = 15                     # 说明条场景名
SZ_SCENE_Q = 17                        # 问题
SZ_SCENE_A = 17                        # 答案
