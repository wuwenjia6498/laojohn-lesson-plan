# -*- coding: utf-8 -*-
"""老约翰深度阅读读书会 - 投屏 PPT 主题常量

字号 / 颜色 / 坐标 / 字体集中在此。投屏 5 米外可看清为底线。
"""
from pptx.util import Emu, Pt

# ============ 页面尺寸（与参考 PPT 一致，16:9）============
SLIDE_W = Emu(12192000)   # 13.333"
SLIDE_H = Emu(6858000)    # 7.5"

# ============ 字体 ============
FONT_TITLE = "微软雅黑"
FONT_BODY = "微软雅黑"   # 全套正文统一微软雅黑（投屏更清晰）
FONT_QUOTE = "宋体"      # 仅原文齐读页正文保留宋体（书卷感）
FONT_ASCII = "Calibri"

# ============ 颜色（RGB hex 字符串，无 #）============
COLOR_ANCHOR_BAR = "44546A"   # 左上章节栏色条（取自参考 PPT）
COLOR_TITLE      = "222222"
COLOR_BODY       = "404040"
COLOR_MUTED      = "8C8C8C"   # 出处 / 页码 / 占位
COLOR_ACCENT     = "C0392B"   # 强调（取自 LOGO 红）
COLOR_BG_QUOTE   = "F5F1EA"   # 原文齐读浅米色
COLOR_BG_PLACE   = "FAFAFA"   # 配图占位浅灰底
COLOR_DASH       = "BFBFBF"   # 占位虚线 / 表格线
COLOR_TABLE_HEAD_BG = "44546A"
COLOR_TABLE_HEAD_FG = "FFFFFF"

# END 页青绿渐变（左上 → 右下：略亮 → 略深）
COLOR_END_BG_FROM = "6FB4AF"
COLOR_END_BG_TO   = "3A7F7A"

# === 方案 A：三类页型差异化 ===
# 环节标题：整面深灰蓝底 + 大序号 + 白字
COLOR_SECTION_BG  = "44546A"
COLOR_SECTION_FG  = "FFFFFF"
COLOR_SECTION_SUB = "DDDDDD"
COLOR_SECTION_NUM = "8FA5C5"   # 巨大章节序号（浅蓝灰，略淡）
COLOR_SECTION_PG  = "B8C4D6"   # 深底页码

# 引导问题：问号水印 + 红色引导竖线
COLOR_QMARK_WATER = "F0EFEC"   # 极淡灰，问号水印
COLOR_RED_ACCENT  = "C0392B"   # 红色强调（沿用 LOGO 红）

# 要点小结：红方块编号 + 细分隔线
COLOR_NUMBOX_BG   = "C0392B"
COLOR_NUMBOX_FG   = "FFFFFF"
COLOR_BULLET_SEP  = "E5E5E5"
# 方案 B：要点小结结论卡
COLOR_CARD_BG     = "FBF6EE"
COLOR_CARD_BORDER = "E8DDC8"

# ============ 字号（pt）============
SZ_COVER_TITLE     = 66
SZ_COVER_SUB       = 32
SZ_COVER_META      = 18     # 作者 / 译者
SZ_ANCHOR_LABEL    = 20     # 左上章节铭牌（眉标）
SZ_PAGE_EYEBROW    = 14     # 页内眉标小字
SZ_HEADING         = 32     # 内页大标题
SZ_BODY            = 20     # 正文 / 要点
SZ_GUIDE_BULLET    = 24     # 引导问题页要点（①②③，用微软雅黑）
SZ_QUOTE           = 24     # 原文齐读
SZ_SUBTITLE        = 16     # 副标题（填空表格用）
SZ_TABLE_HEAD      = 18
SZ_TABLE_BODY      = 16
SZ_FOOTNOTE        = 12
SZ_PAGE_NUM        = 12
SZ_PLACEHOLDER     = 14     # 配图占位说明

# ============ 关键坐标（百分比 → 内部转换 EMU）============
def pct_x(p):
    return Emu(int(SLIDE_W * p))


def pct_y(p):
    return Emu(int(SLIDE_H * p))


# 左上色条（仅内页）
ANCHOR_BAR_X = pct_x(0.000)
ANCHOR_BAR_Y = pct_y(0.073)
ANCHOR_BAR_W = pct_x(0.059)
ANCHOR_BAR_H = pct_y(0.105)

# 左上章节铭牌文字（位于色条右侧，避免重叠）
ANCHOR_LABEL_X = pct_x(0.070)
ANCHOR_LABEL_Y = pct_y(0.073)
ANCHOR_LABEL_W = pct_x(0.250)
ANCHOR_LABEL_H = pct_y(0.105)

# 右上 LOGO（封面）— 在横幅内部右上角；仅指定宽度，高度按图片原比例自动缩放
LOGO_COVER_X = pct_x(0.855)
LOGO_COVER_Y = pct_y(0.055)
LOGO_COVER_W = pct_x(0.100)

# 右上 LOGO（内页）
LOGO_INNER_X = pct_x(0.860)
LOGO_INNER_Y = pct_y(0.040)
LOGO_INNER_W = pct_x(0.110)

# 右下页码常量（页码角标已取消、draw_page_num 现为空操作；常量保留备用，便于将来恢复）
PAGE_NUM_X = pct_x(0.900)
PAGE_NUM_Y = pct_y(0.940)
PAGE_NUM_W = pct_x(0.080)
PAGE_NUM_H = pct_y(0.040)

# 配图占位框（按页型分区）
# 注：环节标题为满屏深灰蓝实心卡片，render_section 不调用 maybe_placeholder，
# 故此处不为其留区域（与 image-suggestion.md「环节标题不配图」一致）。
PLACEHOLDER_REGIONS = {
    "引导问题": (pct_x(0.60), pct_y(0.35), pct_x(0.35), pct_y(0.50)),
    "要点小结": (pct_x(0.65), pct_y(0.45), pct_x(0.30), pct_y(0.45)),
}

# 四图网格区域（引导问题页带 ≥2 条配图建议时启用）：标题下整幅主体区
# 2×2 排布，每幅一个占位框；详见 helpers.add_image_grid / layouts.render_guide。
IMAGE_GRID_REGION = (pct_x(0.07), pct_y(0.42), pct_x(0.86), pct_y(0.50))
IMAGE_GRID_GAP = pct_x(0.018)

# 主内容区（避开左上铭牌、右上 LOGO、右下页码）
CONTENT_LEFT_X   = pct_x(0.07)
CONTENT_TOP_Y    = pct_y(0.22)
CONTENT_WIDTH    = pct_x(0.86)
CONTENT_HEIGHT   = pct_y(0.70)

# 引导问题：主标题居中、要点在下方左半
GUIDE_TITLE_X = pct_x(0.07)
GUIDE_TITLE_Y = pct_y(0.22)
GUIDE_TITLE_W = pct_x(0.86)
GUIDE_TITLE_H = pct_y(0.18)

GUIDE_BULLETS_X = pct_x(0.07)
GUIDE_BULLETS_Y = pct_y(0.45)
GUIDE_BULLETS_W = pct_x(0.50)
GUIDE_BULLETS_H = pct_y(0.45)

# 环节标题：居中
SECTION_TITLE_X = pct_x(0.10)
SECTION_TITLE_Y = pct_y(0.30)
SECTION_TITLE_W = pct_x(0.50)
SECTION_TITLE_H = pct_y(0.20)

SECTION_LEAD_X = pct_x(0.10)
SECTION_LEAD_Y = pct_y(0.55)
SECTION_LEAD_W = pct_x(0.50)
SECTION_LEAD_H = pct_y(0.30)

# 原文齐读：整页书页底（避开顶部 LOGO/铭牌区域）
QUOTE_BG_X = pct_x(0.06)
QUOTE_BG_Y = pct_y(0.22)
QUOTE_BG_W = pct_x(0.88)
QUOTE_BG_H = pct_y(0.70)

QUOTE_TITLE_X = pct_x(0.10)
QUOTE_TITLE_Y = pct_y(0.25)
QUOTE_TITLE_W = pct_x(0.80)
QUOTE_TITLE_H = pct_y(0.10)

QUOTE_BODY_X = pct_x(0.12)
QUOTE_BODY_Y = pct_y(0.38)
QUOTE_BODY_W = pct_x(0.76)
QUOTE_BODY_H = pct_y(0.50)

# 要点小结
SUMMARY_TITLE_X = pct_x(0.07)
SUMMARY_TITLE_Y = pct_y(0.22)
SUMMARY_TITLE_W = pct_x(0.86)
SUMMARY_TITLE_H = pct_y(0.15)

SUMMARY_BULLETS_X = pct_x(0.07)
SUMMARY_BULLETS_Y = pct_y(0.42)
SUMMARY_BULLETS_W = pct_x(0.55)
SUMMARY_BULLETS_H = pct_y(0.50)

# 填空表格
TABLE_TITLE_X = pct_x(0.07)
TABLE_TITLE_Y = pct_y(0.22)
TABLE_TITLE_W = pct_x(0.86)
TABLE_TITLE_H = pct_y(0.08)

TABLE_SUBTITLE_X = pct_x(0.07)
TABLE_SUBTITLE_Y = pct_y(0.32)
TABLE_SUBTITLE_W = pct_x(0.86)
TABLE_SUBTITLE_H = pct_y(0.06)

TABLE_AREA_X = pct_x(0.07)
TABLE_AREA_Y = pct_y(0.385)
TABLE_AREA_W = pct_x(0.86)
TABLE_AREA_H = pct_y(0.555)   # 上移加高，给多行表更多纵向空间（底边 ~0.94H）

# 封面
# 横幅：四周留白边，覆盖上半页
COVER_BANNER_X = pct_x(0.025)
COVER_BANNER_Y = pct_y(0.040)
COVER_BANNER_W = pct_x(0.950)
COVER_BANNER_H = pct_y(0.650)

# 左侧三角装饰：从横幅左边缘往外伸出（朝右 ▷）
COVER_TRI_X = pct_x(0.000)
COVER_TRI_Y = pct_y(0.190)
COVER_TRI_W = pct_x(0.075)
COVER_TRI_H = pct_y(0.180)

# 书名（叠在横幅中央）
COVER_TITLE_X = pct_x(0.100)
COVER_TITLE_Y = pct_y(0.190)
COVER_TITLE_W = pct_x(0.800)
COVER_TITLE_H = pct_y(0.200)

# 副标题（如"导读课"，叠在横幅中央下方）
COVER_SUB_X = pct_x(0.100)
COVER_SUB_Y = pct_y(0.430)
COVER_SUB_W = pct_x(0.800)
COVER_SUB_H = pct_y(0.110)

# 作者/译者元信息：左下角，左对齐
COVER_META_X = pct_x(0.060)
COVER_META_Y = pct_y(0.800)
COVER_META_W = pct_x(0.700)
COVER_META_H = pct_y(0.140)
