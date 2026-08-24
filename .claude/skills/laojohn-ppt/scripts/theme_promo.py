# -*- coding: utf-8 -*-
"""宣讲 profile 的视觉常量（profile 接缝 · 对外宣讲覆盖层）。

用途：面向加盟商/校区负责人的产品宣讲件，不是课堂课件。因此配色不沿用
读书会的深灰蓝课件色，改用「同步习作」已发布招生物料的色板，让宣讲件与
已经发出去的招生海报同源：
    唯一源 = 写作课相关宣传文件\\招生海报.html 的 CSS 变量（品牌红 + 四阶色）。

约定同 theme_writing：只放**与 theme.py 不同**的那部分，尺寸/字体/pct_x/pct_y
仍直接用 theme.py。本模块不含任何逻辑，纯常量。
"""
from pptx.util import Emu, Pt

from theme import pct_x, pct_y

# ============ 品牌色板（取自已发布招生海报，勿自行调色）============
COLOR_BRAND_RED = "C8352B"   # 品牌红：强调、关键词、点缀
COLOR_INK = "3A3A38"         # 正文墨
COLOR_INK_SOFT = "7A7568"    # 次级墨（说明、图注）
COLOR_PAPER = "FFFFFF"       # 纸面
COLOR_ZEBRA = "F7F5F0"       # 斑马纹 / 浅卡底
COLOR_LINE = "C9C0B0"        # 分隔线 / 描边
COLOR_BROWN_DEEP = "7D7468"  # 深褐（次级标签）
COLOR_BROWN_CELL = "EFEBE3"  # 褐调格底
COLOR_GROUND = "EDEAE3"      # 页面外底色（暖灰）

# 四阶色：第三阶 → 第六阶（与海报能力阶梯逐格同色，改这里等于改口径）
COLOR_STAGE = ["6BA368", "4E8FA6", "C08A3E", "A05A4E"]
# 前两阶（看图写话，本产品线不含）淡显用
COLOR_STAGE_MUTED = "B3ACA0"

# 深色页（封面 / 章节大间隔 / 收尾）：暖调深墨，与纸面同族、不撞课件的深灰蓝
COLOR_DARK_FROM = "413C35"
COLOR_DARK_TO = "26231F"
COLOR_DARK_FG = "FFFFFF"
COLOR_DARK_SUB = "D6CFC2"
COLOR_DARK_NUM = "6E655A"     # 章节页巨型序号（低对比，压在底层）

# ============ 通用版心 ============
MARGIN_X = pct_x(0.065)
CONTENT_W = pct_x(0.870)

EYEBROW_X = MARGIN_X
EYEBROW_Y = pct_y(0.075)
EYEBROW_W = CONTENT_W
EYEBROW_H = pct_y(0.055)

TITLE_X = MARGIN_X
TITLE_Y = pct_y(0.145)
TITLE_W = CONTENT_W
TITLE_H = pct_y(0.125)

# 标题下的红短线
TITLE_RULE_X = MARGIN_X
TITLE_RULE_Y = pct_y(0.278)
TITLE_RULE_W = pct_x(0.052)
TITLE_RULE_H = Emu(34000)

# 标题下一行小注（可选）
LEAD_X = MARGIN_X
LEAD_Y = pct_y(0.300)
LEAD_W = CONTENT_W
LEAD_H = pct_y(0.093)   # 容得下两行 19pt；上限抵住 BODY_TOP(0.395)

# 主体区（有小注时从 BODY_TOP 起，无小注时可上提到 LEAD_Y）
BODY_TOP = pct_y(0.395)
BODY_H = pct_y(0.505)

# 底部图注 / 脚注
FOOTNOTE_X = MARGIN_X
FOOTNOTE_Y = pct_y(0.905)
FOOTNOTE_W = CONTENT_W
FOOTNOTE_H = pct_y(0.060)

# 右上 LOGO（内页；比课件略小、更靠边）
LOGO_X = pct_x(0.868)
LOGO_Y = pct_y(0.062)
LOGO_W = pct_x(0.098)

# ============ 字号 ============
SZ_EYEBROW = 15
SZ_TITLE = 34
SZ_TITLE_SM = 28       # 标题过长时的降档
SZ_LEAD = 19
SZ_BODY = 19
SZ_FOOTNOTE = 14

SZ_COVER_TITLE = 50
SZ_COVER_TITLE_MD = 44   # 13–17 字：仍单行
SZ_COVER_TITLE_SM = 38   # 更长：允许折两行，但每行都够长
SZ_COVER_SUB = 24
SZ_COVER_META = 16

SZ_SECTION_NUM = 190   # 章节页巨型序号
SZ_SECTION_TITLE = 46
SZ_SECTION_LEAD = 21

SZ_CLAIM = 42          # 主张页大句
SZ_CLAIM_SM = 34       # 主张句较长时降档
SZ_CLAIM_NOTE = 18

SZ_STAT_NUM = 78       # 数据面板大数字
SZ_STAT_NUM_SM = 60
SZ_STAT_UNIT = 19
SZ_STAT_NOTE = 15

SZ_CARD_TITLE = 20
SZ_CARD_BODY = 16
SZ_CARD_NUM = 17

SZ_AXIS_STAGE = 14     # 六阶轴段内 · 阶名（16pt 会撑破 chevron，实测过）
SZ_AXIS_SUB = 11       # 六阶轴段内 · 学段（第二行，小一档）
SZ_AXIS_STAGE_MUTED = 12  # 淡显段阶名（低段，不属本线，弱化处理）
SZ_AXIS_ROW = 16       # 能力线行标签
SZ_AXIS_CELL = 13      # 能力线格内文字

SZ_STEP_NAME = 15      # 流程时间轴环节名
SZ_STEP_TIME = 13      # 流程时间轴时长
SZ_STEP_NUM = 15

SZ_COMPARE_TAB = 21
SZ_COMPARE_BODY = 17
SZ_LIST = 20

SZ_SHOT_CAP = 16       # 图集图注
SZ_SHOT_NOTE = 14      # 图集说明
SZ_POINTER = 17        # 满屏图右侧指点

SZ_END_TITLE = 34
SZ_END_SUB = 19

# ============ 数据面板（render_stats）============
STAT_GAP = pct_x(0.022)
STAT_CARD_H = pct_y(0.360)
STAT_RADIUS = 0.10

# ============ 并列卡片（render_cards）============
CARDS_GAP = pct_x(0.020)
CARD_RADIUS = 0.08
CARD_NUM_D = pct_x(0.030)

# ============ 体系全景（render_overview）============
AXIS_Y = pct_y(0.360)          # 六阶轴带 y
AXIS_H = pct_y(0.105)
AXIS_GAP = Emu(26000)
GRID_TOP = pct_y(0.515)        # 能力线矩阵顶
GRID_H = pct_y(0.365)          # 底边须留在 FOOTNOTE_Y(0.905) 之上
GRID_LABEL_W = pct_x(0.150)    # 左侧行标签宽
GRID_ROW_GAP = Emu(24000)

# ============ 流程时间轴（render_flow）============
FLOW_LINE_Y = pct_y(0.545)     # 轴线 y
FLOW_LINE_H = Emu(26000)
FLOW_NODE_D = pct_x(0.036)     # 节点圆直径
FLOW_TOP = pct_y(0.330)        # 上方环节名区顶
FLOW_NAME_H = pct_y(0.170)
FLOW_TIME_Y = pct_y(0.625)     # 下方时长区
FLOW_TIME_H = pct_y(0.070)
FLOW_SEG_LABEL_Y = pct_y(0.745)  # 「第 1 节 / 第 2 节」分段标签

# ============ 双栏对照（render_versus）============
VS_TOP = pct_y(0.330)
VS_TAB_H = pct_y(0.072)
VS_LEFT_X = MARGIN_X
VS_RIGHT_X = pct_x(0.505)
VS_COL_W = pct_x(0.430)
VS_BODY_TOP = pct_y(0.412)
VS_BODY_BOTTOM = pct_y(0.900)
VS_BODY_BOTTOM_WITHNOTES = pct_y(0.735)   # 底部有要点条时，正文卡要提前收住
VS_NOTES_Y = pct_y(0.772)
VS_NOTES_H = pct_y(0.155)
COLOR_VS_LEFT_TAB = "9A948A"   # 左栏（对照组）：灰，弱
COLOR_VS_RIGHT_TAB = COLOR_BRAND_RED  # 右栏（我们）：品牌红，强
COLOR_VS_LEFT_BG = "F2F0EC"
COLOR_VS_RIGHT_BG = "FBF3F1"

# ============ 图集 / 满屏图（render_gallery / render_showcase）============
SHOT_GAP = pct_x(0.024)
SHOT_TOP = pct_y(0.360)
SHOT_H = pct_y(0.430)          # 图卡高（图注在其下）
SHOT_CAP_H = pct_y(0.055)
SHOT_NOTE_H = pct_y(0.075)
COLOR_SHOT_CARD = "FFFFFF"     # 纸张托底
COLOR_SHOT_BORDER = "D8D2C6"

SHOW_IMG_X = MARGIN_X
SHOW_IMG_Y = pct_y(0.262)
SHOW_IMG_W = pct_x(0.320)   # 竖版文档 contain 后只占窄窄一条，框不必留那么宽
SHOW_IMG_H = pct_y(0.700)
SHOW_NOTE_X = pct_x(0.430)
SHOW_NOTE_Y = pct_y(0.330)
SHOW_NOTE_W = pct_x(0.505)
SHOW_NOTE_H = pct_y(0.560)

# ============ 收尾页（render_closing）============
CLOSE_CHIP_H = pct_y(0.110)
CLOSE_CHIP_GAP = pct_x(0.022)
CLOSE_CHIP_RADIUS = 0.22

# ============ 待填占位（仓内无事实源的栏位）============
# 宣讲稿里凡「师训安排/班型人数/排课频次」这类仓内查无事实源的字段，
# 一律写成本标记；渲染端画成红框空槽，提醒宣讲人上台前必须填。
# 绝不许模型用行业惯例把它填上（真实性红线）。
TODO_MARK = "【待填】"
COLOR_TODO_BORDER = COLOR_BRAND_RED
COLOR_TODO_BG = "FBF3F1"
SZ_TODO = 17
