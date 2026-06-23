# -*- coding: utf-8 -*-
"""
md_to_laojohn_docx.py
固定排版引擎：读取按《课案 Markdown 约定规范》写好的 .md 课案详案，
自动套用老约翰官方样式，输出 .docx。

用法：
    python md_to_laojohn_docx.py 输入.md [输出.docx]
    # 不给输出名时，输出到同目录同名 .docx

样式对齐官方成品（《我家没有英雄》教学设计）：
- 全文宋体 12pt / 行距 1.5，层级仅靠加粗与居中区分；
- 主标题 16pt 居中；课时标题 14pt 居中黑色；
- 师话整段加粗；参考“参考：”领起；PPT 锚点橙色 ED7D31；
- 表格 Table Grid + 米色表头 F5E6C6；
- 页眉左右双栏 + 下边框线；页脚居中页码；A4 四边 2.5cm。

行内标记安全网（所有文字统一经 add_md_text 进 docx，覆盖师话/参考/
引用块/表格/三维目标/标题等全部位置）：
- 成对 **…** / __…__ → 真实加粗 run，星号绝不原样进文；
- 未配对的残余 ** / __ 标记一律剥除。
引号规范化在 convert() 入口对**整篇** .md 一次性执行（不可逐行/逐段，
否则跨行引号的开闭状态会重置）；成对 " → “”，成对 ' → ‘’（英文撇号如
don't 不动）。奇数个 ASCII 引号时方向可能判反，脚本会额外警告——源 .md
仍应写全角弯引号，不依赖安全网。
"""
import sys
import os
import re
import subprocess


def _ensure_docx():
    """确保 python-docx 已安装；缺失时自动 pip 安装一次。"""
    try:
        import docx  # noqa: F401
        return
    except ImportError:
        pass
    print('[md_to_laojohn_docx] 未检测到 python-docx，正在自动安装……')
    for args in (
        [sys.executable, '-m', 'pip', 'install', 'python-docx', '--quiet'],
        [sys.executable, '-m', 'pip', 'install', 'python-docx', '--quiet',
         '--break-system-packages'],
        [sys.executable, '-m', 'pip', 'install', 'python-docx', '--quiet',
         '--user'],
    ):
        try:
            subprocess.check_call(args)
            import docx  # noqa: F401
            print('[md_to_laojohn_docx] python-docx 安装成功。')
            return
        except Exception:
            continue
    sys.exit('[md_to_laojohn_docx] 自动安装 python-docx 失败，请手动运行：'
             'pip install python-docx')


_ensure_docx()

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ROW_HEIGHT_RULE, WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement, parse_xml

# ===================== 官方样式常量（集中可调） =====================
CN_FONT      = '宋体'
BASE_SIZE    = 12
LINE_SPACING = 1.5
DOC_TITLE_SZ = 16
LESSON_SZ    = 14
HEADER_SZ    = 10.5
TABLE_SZ     = 12
HEADER_FILL  = 'F5E6C6'   # 表头米色
CELL_FILL    = 'FEFEFE'   # 单元格底色
PPT_COLOR    = RGBColor(0xED, 0x7D, 0x31)
PAGETAG_COLOR = RGBColor(0xE9, 0x97, 0x43)   # 〖PPT Pxx〗备课页标·色标 #E99743
TITLE_COLOR  = RGBColor(0x00, 0x00, 0x00)
HEADER_GREY  = RGBColor(0x59, 0x59, 0x59)   # 页眉右侧深灰

# 识别为“学生分享提示”的整行（可扩充）
SHARE_LINES = ('学生互动分享', '学生自由分享', '学生分享', '学生分组汇报',
               '学生互动', '学生安静阅读', '学生自读', '学生总结，自由分享')

# ===================== 样式底层工具 =====================

def set_cell_shading(cell, color_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), color_hex)
    tcPr.append(shd)


def set_font(run, name=CN_FONT, size=BASE_SIZE, bold=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.bold = bold
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts')
        rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), name)
    rFonts.set(qn('w:ascii'), name)
    rFonts.set(qn('w:hAnsi'), name)


def _fmt(p, space_after=0, space_before=0, line_spacing=LINE_SPACING,
         first_indent=None, left_indent=None, right_indent=None):
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    pf.line_spacing = line_spacing
    if first_indent is not None:
        pf.first_line_indent = Cm(first_indent)
    if left_indent is not None:
        pf.left_indent = Cm(left_indent)
    if right_indent is not None:
        pf.right_indent = Cm(right_indent)
    return p


# ===================== 引号规范化 =====================

def smart_quotes(text: str) -> str:
    """把 ASCII 直引号成对转换为中文弯引号。
    双引号 " → “ / ” 交替；单引号 ' → ‘ / ’ 交替（均以“左引号”起步）。
    例外：夹在两个英文字母之间的 ' 视为英文撇号（如 don't），保持原样。
    若总数为奇数（配对本身有歧义），落单的那个会落在“左引号”一侧，
    方向可能与原意相反——此时由调用方另行提示用户核对，本函数不自行猜测收尾方向。
    注意：应对整篇文本一次性调用，使开/闭状态跨行连贯；逐行调用会在换行处
    重置状态，导致跨行引号（如跨行引用块/长台词）的闭引号被误判为开引号。
    """
    result = []
    d_open = True  # 下一个双引号是左引号
    s_open = True  # 下一个单引号是左引号
    for k, ch in enumerate(text):
        if ch == '"':
            result.append('\u201c' if d_open else '\u201d')
            d_open = not d_open
        elif ch == "'":
            prev_alpha = k > 0 and text[k - 1].isascii() and text[k - 1].isalpha()
            next_alpha = k + 1 < len(text) and text[k + 1].isascii() and text[k + 1].isalpha()
            if prev_alpha and next_alpha:      # 英文撇号，不动
                result.append(ch)
            else:
                result.append('\u2018' if s_open else '\u2019')
                s_open = not s_open
        else:
            result.append(ch)
    return ''.join(result)


# ===================== 统一文本入口（行内标记安全网） =====================

# 成对的行内加粗标记 **…** 或 __…__
_INLINE_BOLD_RE = re.compile(r'(\*\*.+?\*\*|__.+?__)')


def add_md_text(p, text, size=BASE_SIZE, bold=False, color=None):
    """所有正文文字进 docx 的唯一入口。
    1. 成对 **…** / __…__ 转为真实加粗 run（基底已加粗的语境下效果不变，标记照样吃掉）；
    2. 未配对的残余 ** / __ 标记剥除，绝不让星号原样印进 docx；
    3. color 给定时套用到本段所有 run（如 PPT 锚点橙色）。
    引号已在 convert() 整篇预处理，此处不再重复调用 smart_quotes，
    避免分段渲染时开/闭状态重置导致跨 ** 边界的引号判错。
    """
    wrote = False
    for seg in _INLINE_BOLD_RE.split(text):
        if len(seg) > 4 and ((seg.startswith('**') and seg.endswith('**'))
                             or (seg.startswith('__') and seg.endswith('__'))):
            r = p.add_run(seg[2:-2])
            set_font(r, size=size, bold=True)
        else:
            seg = seg.replace('**', '').replace('__', '')  # 残余未配对标记剥除
            if not seg:
                continue
            r = p.add_run(seg)
            set_font(r, size=size, bold=bold)
        if color is not None:
            r.font.color.rgb = color
        wrote = True
    if not wrote:  # 全空时仍补一个空 run，保持段落字体设置
        r = p.add_run('')
        set_font(r, size=size, bold=bold)
        if color is not None:
            r.font.color.rgb = color


# ===================== 各块渲染器 =====================

def render_doc_title(doc, text):
    # space_after 让主标题与紧随其后的「教案提纲」表格之间空出一行
    p = doc.add_paragraph(); _fmt(p, space_after=16); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_md_text(p, text, size=DOC_TITLE_SZ, bold=True)


def render_subtitle(doc, text):
    p = doc.add_paragraph(); _fmt(p, space_after=6); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_md_text(p, text, size=BASE_SIZE, bold=False)


def render_lesson_title(doc, text, page_break=False):
    if page_break:
        # 分页：标题段设“段前分页”，并在其前插一个有高度的空行段，
        # 制造页眉与标题之间的视觉留白（空行段不分页，跟随标题翻到新页顶部）
        spacer = doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(0)
        spacer.paragraph_format.space_after = Pt(0)
        spacer.paragraph_format.line_spacing = 1.0
        spacer.paragraph_format.page_break_before = True
        set_font(spacer.add_run(' '), size=BASE_SIZE, bold=False)
    p = doc.add_paragraph()
    _fmt(p, space_before=(6 if page_break else 12), space_after=6)
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    add_md_text(p, text, size=LESSON_SZ, bold=True, color=TITLE_COLOR)


def render_section_title(doc, text, space_before=0):
    p = doc.add_paragraph(); _fmt(p, space_before=space_before)
    add_md_text(p, text, size=BASE_SIZE, bold=True)


def render_bold_label(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    add_md_text(p, text, size=BASE_SIZE, bold=True)


def render_teacher(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run('师：'), size=BASE_SIZE, bold=True)
    add_md_text(p, text, size=BASE_SIZE, bold=True)


def render_ref(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run('参考：'), size=BASE_SIZE, bold=True)
    add_md_text(p, text, size=BASE_SIZE, bold=False)


def render_share(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    add_md_text(p, text, size=BASE_SIZE, bold=False)


def render_objective(doc, label, content):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run(f'【{label}】'), size=BASE_SIZE, bold=True)
    add_md_text(p, content, size=BASE_SIZE, bold=False)


def render_ppt(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    add_md_text(p, text, size=BASE_SIZE, bold=False, color=PPT_COLOR)


def render_pagetag(doc, text):
    """〖PPT Pxx · 页型〗备课页标——青绿加粗，醒目但克制（备课交叉对照用）。"""
    p = doc.add_paragraph(); _fmt(p)
    add_md_text(p, text, size=BASE_SIZE, bold=True, color=PAGETAG_COLOR)


def render_quote(doc, text):
    p = doc.add_paragraph(); _fmt(p, left_indent=0.84, right_indent=0.84)
    add_md_text(p, text, size=BASE_SIZE, bold=False)


def render_para(doc, text, bold=False, space_before=0):
    p = doc.add_paragraph(); _fmt(p, space_before=space_before)
    add_md_text(p, text, size=BASE_SIZE, bold=bold)


def render_end(doc, text):
    p = doc.add_paragraph(); _fmt(p, space_before=6)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_md_text(p, text, size=BASE_SIZE, bold=True)


# 共享资产唯一源（见 CLAUDE.md §3）。引擎位于
# <项目根>/.claude/skills/laojohn-lesson-plan/assets/，上溯 4 层到项目根。
PROJECT_ROOT = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', '..'))
COVER_DIR   = os.path.join(PROJECT_ROOT, '书籍封面')
PROFILE_DIR = os.path.join(PROJECT_ROOT, '书籍档案')
# 封面 logo：圆形徽标「老约翰·引领儿童阅读与成长」(不含「阅读·思辨·表达」，
# 后者由封面文本框单独渲染)。优先 logo-01.jpg，缺失回退。
LOGO_PATH = os.path.join(PROJECT_ROOT, '品牌资产', 'logo-01.jpg')
for _alt in ('logo-emblem.png', 'logo.png'):
    if not os.path.isfile(LOGO_PATH):
        LOGO_PATH = os.path.join(PROJECT_ROOT, '品牌资产', _alt)

def find_cover(book_name):
    if not book_name:
        return None
    for ext in ('png', 'jpg', 'jpeg', 'webp'):
        path = os.path.join(COVER_DIR, f'{book_name}.{ext}')
        if os.path.isfile(path):
            return path
    return None


def find_book_meta(book_name):
    """从 <项目根>/书籍档案/<书名>书籍档案.md 机读块取 等级 / 获奖（短字段）。
    取不到/档案不存在 → 返回 (None, None)；写作课等无档案时静默跳过封面页元信息。"""
    level = award = None
    path = os.path.join(PROFILE_DIR, f'{book_name}书籍档案.md')
    if not os.path.isfile(path):
        return level, award
    try:
        with open(path, encoding='utf-8') as fh:
            txt = fh.read()
    except Exception:
        return level, award
    # [ \t]* 仅吃同行空格，不用 \s*（\s 含换行，空字段会跨行误抓下一行/子条目）
    m = re.search(r'^\s*-\s*等级[:：][ \t]*(L\d)', txt, re.M)
    if m:
        level = m.group(1)
    m = re.search(r'^\s*-\s*获奖[:：][ \t]*(.+)$', txt, re.M)
    if m and m.group(1).strip():
        award = m.group(1).strip()
    return level, award


def render_cover(doc, book_name):
    """「一、文本介绍」标题下方插入书籍封面；找不到封面文件则静默跳过。"""
    path = find_cover(book_name)
    if not path:
        return False
    doc.add_picture(path, width=Cm(6.5))
    pf = doc.paragraphs[-1].paragraph_format
    pf.space_before = Pt(6); pf.space_after = Pt(6)
    return True


# ---- 封面页（导出 docx 时作为第 1 页，原生可编辑元素：浮动图片 + 文本框 + 形状）----
# 全部锚定到「页面」，正文另起一节。各元素可在 Word 里单独点选、移动、改字、换图。
EMU_CM = 360000
COVER_FONT = '微软雅黑'
_DOCPR = [2000]
# 浮动绘图所需命名空间（含微软 wps，不在 python-docx nsmap 内，须手写）
_NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
       'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
       'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
       'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
       'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"')


def _next_id():
    _DOCPR[0] += 1
    return _DOCPR[0]


def _xesc(s):
    return (s or '').replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def _run_xml(text, size_pt, bold=False, color='2D2D2D', font=COVER_FONT):
    sz = int(round(size_pt * 2))
    b = '<w:b/><w:bCs/>' if bold else ''
    return ('<w:r><w:rPr><w:rFonts w:ascii="%s" w:eastAsia="%s" w:hAnsi="%s"/>%s'
            '<w:color w:val="%s"/><w:sz w:val="%d"/><w:szCs w:val="%d"/></w:rPr>'
            '<w:t xml:space="preserve">%s</w:t></w:r>'
            % (font, font, font, b, color, sz, sz, _xesc(text)))


def _para_xml(runs_xml, jc='center'):
    return ('<w:p><w:pPr><w:jc w:val="%s"/>'
            '<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
            '</w:pPr>%s</w:p>' % (jc, runs_xml))


def _anchor_open(x_cm, y_cm, w_cm, h_cm, name, z):
    return ('<wp:anchor %s behindDoc="0" distT="0" distB="0" distL="0" distR="0" '
            'simplePos="0" locked="0" layoutInCell="1" allowOverlap="1" relativeHeight="%d">'
            '<wp:simplePos x="0" y="0"/>'
            '<wp:positionH relativeFrom="page"><wp:posOffset>%d</wp:posOffset></wp:positionH>'
            '<wp:positionV relativeFrom="page"><wp:posOffset>%d</wp:posOffset></wp:positionV>'
            '<wp:extent cx="%d" cy="%d"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
            '<wp:wrapNone/><wp:docPr id="%d" name="%s"/><wp:cNvGraphicFramePr/>'
            % (_NS, z,
               int(round(x_cm * EMU_CM)), int(round(y_cm * EMU_CM)),
               int(round(w_cm * EMU_CM)), int(round(h_cm * EMU_CM)), _next_id(), name))


def _add_textbox(run, x_cm, y_cm, w_cm, h_cm, content_xml, vert='horz',
                 anchor='t', name='tb', z=20):
    """wps DrawingML 文本框（锚定页面）。与浮动图片同机制，交互式 Word 定位可靠
    （VML 文本框在交互式 Word 里会错位到左上角，故不用）。"""
    cx = int(round(w_cm * EMU_CM)); cy = int(round(h_cm * EMU_CM))
    xml = ('<w:drawing %s>%s'
           '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
           '<wps:wsp><wps:cNvSpPr txBox="1"/>'
           '<wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
           '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/><a:ln><a:noFill/></a:ln></wps:spPr>'
           '<wps:txbx><w:txbxContent>%s</w:txbxContent></wps:txbx>'
           '<wps:bodyPr rot="0" vert="%s" wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" '
           'anchor="%s" anchorCtr="0"><a:noAutofit/></wps:bodyPr>'
           '</wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing>'
           % (_NS, _anchor_open(x_cm, y_cm, w_cm, h_cm, name, z), cx, cy, content_xml, vert, anchor))
    run._r.append(parse_xml(xml))


def _add_pie(run, x_cm, y_cm, d_cm, fill, name='badge', z=11):
    """珊瑚粉整圆（椭圆）。调用方把圆心放在纸张右下角，整圆被页边自然裁成「贴角 1/4 圆」
    （直角在纸角、弧线朝页内）——比 pie 角度可靠。"""
    dd = int(round(d_cm * EMU_CM))
    xml = ('<w:drawing %s>%s'
           '<a:graphic><a:graphicData uri="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">'
           '<wps:wsp><wps:cNvSpPr/>'
           '<wps:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%d" cy="%d"/></a:xfrm>'
           '<a:prstGeom prst="ellipse"><a:avLst/></a:prstGeom>'
           '<a:solidFill><a:srgbClr val="%s"/></a:solidFill><a:ln><a:noFill/></a:ln></wps:spPr>'
           '<wps:bodyPr/></wps:wsp></a:graphicData></a:graphic></wp:anchor></w:drawing>'
           % (_NS,
              _anchor_open(x_cm, y_cm, d_cm, d_cm, name, z), dd, dd, fill))
    run._r.append(parse_xml(xml))


def _add_float_picture(run, image_path, x_cm, y_cm, w_cm, name='pic', z=5):
    """加浮动(锚定页面)图片：先 inline 建立 blip 关系，再就地换成 anchor。"""
    run.add_picture(image_path, width=Cm(w_cm))
    drawing = run._r.findall(qn('w:drawing'))[-1]
    inline = drawing.find(qn('wp:inline'))
    ext = inline.find(qn('wp:extent'))
    cx, cy = ext.get('cx'), ext.get('cy')
    rid = None
    for el in inline.iter(qn('a:blip')):
        rid = el.get(qn('r:embed'))
        break
    drawing.remove(inline)
    w_cm, h_cm = float(cx) / EMU_CM, float(cy) / EMU_CM
    anchor = parse_xml(
        '%s'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="%d" name="%s"/><pic:cNvPicPr/></pic:nvPicPr>'
        '<pic:blipFill><a:blip r:embed="%s"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="%s" cy="%s"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
        '</pic:pic></a:graphicData></a:graphic></wp:anchor>'
        % (_anchor_open(x_cm, y_cm, w_cm, h_cm, name, z), _next_id(), name, rid, cx, cy))
    drawing.append(anchor)
    return w_cm, h_cm


def render_cover_page(doc, book_name):
    """正文前插入原生可编辑封面页。各元素均锚定到「页面」(无视页边距、可贴边)，
    Word 里可单独点选/移动/改字/换图。无书封文件则整页跳过（如写作课）。
    采用「单节 + 首页独立页眉 + 页面分页符」，由 setup_page 统一配置——
    避免分节导致正文页眉串到封面页。"""
    cpath = find_cover(book_name)
    if not book_name or not cpath:
        return False
    level, award = find_book_meta(book_name)
    if award:
        award = award.strip().lstrip('★*-•·–—  ').strip()

    # 封面节：A4 整页、零页边距——元素本就锚定到页面、与边距无关；零边距让
    # Word「显示文字边界」的四角标记被挤到纸张极角、几乎不可见（角标本是视图辅助、不打印）。
    cov = doc.sections[0]
    cov.page_height = Cm(29.7); cov.page_width = Cm(21.0)
    cov.top_margin = cov.bottom_margin = Cm(0)
    cov.left_margin = cov.right_margin = Cm(0)
    cov.header_distance = Cm(0); cov.footer_distance = Cm(0)

    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(0); pf.space_after = Pt(0); pf.line_spacing = 1.0
    r = p.add_run()

    INK = '2D2D2D'; NAVY = '4A5274'; CORAL = 'F2A0A0'; GRAY = '595959'

    # 1) logo（右上）
    if os.path.isfile(LOGO_PATH):
        _add_float_picture(r, LOGO_PATH, 13.65, 2.0, 4.7, name='logo', z=6)
    # 2) navy 副标「阅读·思辨·表达」（右对齐到 logo 右边缘 18.35cm）
    _add_textbox(r, 13.65, 3.7, 4.7, 0.7,
                 _para_xml(_run_xml('阅读 · 思辨 · 表达', 13, bold=False, color=NAVY), jc='right'),
                 vert='horz', name='sub', z=21)
    # 3) 竖排大标题「老约翰深度阅读」（深灰；上移贴近副标）。竖排框高度保持原样（13cm）；
    #    加大「宽度」(横向 4cm)防止 wps 竖排框把末字「读」截断。加宽后竖排列靠框右，
    #    故 x 设 14.85 使列右缘回到 logo 右缘 18.35。
    _add_textbox(r, 14.85, 3.85, 4.0, 13.0,
                 _para_xml(_run_xml('老约翰深度阅读', 40, bold=True, color=GRAY)),
                 vert='eaVert', name='title', z=20)
    # 4) 左列《书名》+「教学设计」（深灰·同色；紧挨无空格；统一二号=22pt）
    col = (_run_xml(f'《{book_name}》', 22, bold=False, color=GRAY)
           + _run_xml('教学设计', 22, bold=False, color=GRAY))
    _add_textbox(r, 14.9, 4.9, 2.0, 16.5, _para_xml(col, jc='left'),
                 vert='eaVert', name='subtitle', z=20)
    # 5) 书封（左侧中下，略缩小；整体下移 1cm）
    _, bh = _add_float_picture(r, cpath, 2.9, 17.5, 6.0, name='cover', z=5)
    # 6) 获奖语（书封下方，随书封下移 1cm，不与书封重叠）
    if award:
        _add_textbox(r, 2.5, 17.5 + bh + 0.25, 14.5, 1.0,
                     _para_xml(_run_xml(f'★{award}', 14, bold=True, color=INK), jc='left'),
                     vert='horz', name='award', z=22)
    # 7) 右下角贴角 1/4 圆徽标 + 年级（整圆圆心置于纸张右下角，被页边裁出 1/4）
    if level:
        bd = 5.2  # 直径；圆心在页角(21,29.7)，可见的是左上 1/4
        _add_pie(r, 21.0 - bd / 2, 29.7 - bd / 2, bd, CORAL, name='badge', z=11)
        _add_textbox(r, 18.9, 28.0, 1.7, 1.1,
                     _para_xml(_run_xml(level, 20, bold=True, color='FFFFFF')),
                     vert='horz', anchor='ctr', name='level', z=23)

    # 正文另起一节（封面节独立，便于零页边距/无页眉，不影响正文版式）
    doc.add_section(WD_SECTION.NEW_PAGE)
    return True


def render_table(doc, header_cells, body_rows):
    ncol = len(header_cells)
    table = doc.add_table(rows=1 + len(body_rows), cols=ncol)
    table.style = 'Table Grid'
    table.autofit = True
    # 表头：若仅首格有内容、其余为空（如「教案提纲」表的 `| 教案提纲 |  |`），
    # 则把整行合并为一个居中表头单元格；否则按多列分别渲染（对比表/工具表等不受影响）。
    merge_header = ncol > 1 and header_cells[0].strip() and \
        all(not h.strip() for h in header_cells[1:])
    if merge_header:
        cell = table.rows[0].cells[0]
        for j in range(1, ncol):
            cell = cell.merge(table.rows[0].cells[j])
        cell.text = ''
        p = cell.paragraphs[0]; _fmt(p); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_md_text(p, header_cells[0], size=TABLE_SZ, bold=True)
        set_cell_shading(cell, HEADER_FILL)
        header_cells = []
    for i, h in enumerate(header_cells):
        cell = table.rows[0].cells[i]; cell.text = ''
        p = cell.paragraphs[0]; _fmt(p)
        add_md_text(p, h, size=TABLE_SZ, bold=True)
        set_cell_shading(cell, HEADER_FILL)
    for ri, row in enumerate(body_rows):
        for ci in range(ncol):
            val = row[ci] if ci < len(row) else ''
            cell = table.rows[ri + 1].cells[ci]; cell.text = ''
            p = cell.paragraphs[0]; _fmt(p)
            # 支持 <br> 换行
            parts = val.split('<br>')
            for k, seg in enumerate(parts):
                if k > 0:
                    p.add_run().add_break()
                add_md_text(p, seg, size=TABLE_SZ, bold=False)
            set_cell_shading(cell, CELL_FILL)
    # 「教案提纲」表（合并表头）专属版式：行高加大、第一列缩窄、整表居中、固定列宽。
    # 其余多列表格（对比表/工具表等）保持 autofit，不受影响。
    if merge_header and ncol == 2:
        sec = doc.sections[0]
        usable = sec.page_width - sec.left_margin - sec.right_margin
        col0 = Cm(1.6)            # 第一列(项目名)缩窄
        col1 = usable - col0
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.autofit = False
        table.allow_autofit = False
        for row in table.rows:
            row.height = Cm(1.05)   # 行高加大
            row.height_rule = WD_ROW_HEIGHT_RULE.AT_LEAST
            for cell in row.cells:
                cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER  # 文字垂直居中
        table.rows[0].cells[0].width = usable   # 合并表头跨满全表
        for row in table.rows[1:]:
            row.cells[0].width = col0
            row.cells[1].width = col1
    return table


# ===================== 页面 / 页眉页脚 =====================

def setup_page(doc, has_cover=False):
    style = doc.styles['Normal']
    style.font.name = CN_FONT
    style.font.size = Pt(BASE_SIZE)
    rPr = style.element.get_or_add_rPr()
    rFonts = rPr.find(qn('w:rFonts'))
    if rFonts is None:
        rFonts = OxmlElement('w:rFonts'); rPr.append(rFonts)
    rFonts.set(qn('w:eastAsia'), CN_FONT)
    rFonts.set(qn('w:ascii'), CN_FONT)
    rFonts.set(qn('w:hAnsi'), CN_FONT)
    style.paragraph_format.line_spacing = LINE_SPACING

    # 配置「正文节」(最后一节)。有封面时封面是独立的 sections[0](零边距,见
    # render_cover_page)，这里不动它，只把页眉/页脚/页码配到正文节，并把封面节页眉置空。
    sec = doc.sections[-1]
    sec.page_height = Cm(29.7); sec.page_width = Cm(21.0)
    sec.left_margin = sec.right_margin = Cm(2.5)
    sec.top_margin = Cm(3.2); sec.bottom_margin = Cm(2.5)
    sec.header_distance = Cm(1.5); sec.footer_distance = Cm(1.0)
    sec.different_first_page_header_footer = False
    if has_cover:
        sectPr = sec._sectPr
        pgnum = OxmlElement('w:pgNumType'); pgnum.set(qn('w:start'), '1')  # 正文页码从1(封面节不计)
        sectPr.append(pgnum)
        # 正文节独立页眉/页脚；封面节页眉/页脚置空，避免正文页眉串到封面页。
        sec.header.is_linked_to_previous = False
        sec.footer.is_linked_to_previous = False
        cov = doc.sections[0]
        cov.header.is_linked_to_previous = False
        cov.footer.is_linked_to_previous = False
    # 页眉：用无边框两列表格实现左右两端对齐（比制表位在各 Word 版本更稳）
    hp = sec.header.paragraphs[0]; hp.text = ''
    usable = sec.page_width - sec.left_margin - sec.right_margin
    htab = sec.header.add_table(rows=1, cols=2, width=usable)
    htab.autofit = False
    htab.allow_autofit = False
    lc, rc = htab.rows[0].cells
    lc.width = Cm(8.0); rc.width = Cm(8.0)
    # 左格
    lp = lc.paragraphs[0]; _fmt(lp, line_spacing=1.0); lp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    set_font(lp.add_run('老约翰深度阅读'), size=HEADER_SZ, bold=False)
    # 右格
    rp = rc.paragraphs[0]; _fmt(rp, line_spacing=1.0); rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    rr = rp.add_run('阅读·思辨·表达')
    set_font(rr, size=HEADER_SZ, bold=False)
    rr.font.color.rgb = HEADER_GREY
    # 表格整体无外框，只给两个单元格加“下边框”作分隔线（线紧贴文字下方）
    for cell in (lc, rc):
        tcPr = cell._tc.get_or_add_tcPr()
        tcB = OxmlElement('w:tcBorders')
        for edge in ('top', 'left', 'right', 'insideH', 'insideV'):
            e = OxmlElement(f'w:{edge}')
            e.set(qn('w:val'), 'none'); e.set(qn('w:sz'), '0')
            e.set(qn('w:space'), '0'); e.set(qn('w:color'), 'auto')
            tcB.append(e)
        b = OxmlElement('w:bottom')
        b.set(qn('w:val'), 'single'); b.set(qn('w:sz'), '6')
        b.set(qn('w:space'), '1'); b.set(qn('w:color'), '808080')
        tcB.append(b)
        tcPr.append(tcB)
    # 删除表格后面残留的空页眉段落（否则会在线下多出一行/把线推低）
    hp._p.getparent().remove(hp._p)
    # 页脚页码
    fp = sec.footer.paragraphs[0]; fp.text = ''
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = fp.add_run(); set_font(run, size=HEADER_SZ, bold=False)
    b = OxmlElement('w:fldChar'); b.set(qn('w:fldCharType'), 'begin')
    instr = OxmlElement('w:instrText'); instr.set(qn('xml:space'), 'preserve'); instr.text = ' PAGE '
    e = OxmlElement('w:fldChar'); e.set(qn('w:fldCharType'), 'end')
    run._r.append(b); run._r.append(instr); run._r.append(e)


# ===================== Markdown 解析 =====================

# 注：PPT 换页点已废弃，新详案不再产出。以下识别/橙色渲染逻辑仅作向后兼容，
# 用于正确排版历史 docx 里残留的换页点；新流程不依赖它。
PPT_RE   = re.compile(r'^【?\s*PPT\s*换页\s*[-—:：]?\s*P', re.I)
# 〖PPT 第N页 · 页型 · 眉标〗备课页标（laojohn-ppt-draft 回注产物）——独占行，渲染为青绿加粗。
PAGETAG_RE = re.compile(r'^〖\s*PPT\s+第\d+页.*〗\s*$')
OBJ_RE   = re.compile(r'^【(知识技能|过程方法|情感价值|知识与技能|过程与方法|情感态度价值观)】\s*(.*)$')
TABLE_SEP_RE = re.compile(r'^\|?\s*:?-{2,}.*$')  # |---|---| 分隔行
# 列表标记：无序 - / * / +，有序 1. 1) （仅行首，且后面有空格+内容）
LIST_RE  = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(.*\S.*)$')
# 四级及以下标题 #### / ##### …（规范只定义到 ###，更深的剥掉 # 当正文）
DEEP_H_RE = re.compile(r'^#{4,}\s+(.*\S.*)$')
# 测评题题号行（reading-assessment 专用）：行首「数字＋全角句点」如 `1．…`。
# 用于在题与题之间留出段前间距（详案/写作课均不用此写法，已核实零碰撞，故互不影响）。
QNUM_RE = re.compile(r'^\d+．')


def _split_table_row(line):
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [c.strip() for c in s.split('|')]


def is_table_line(line):
    return line.strip().startswith('|') and line.count('|') >= 2


def convert(md_path, docx_path):
    with open(md_path, encoding='utf-8') as f:
        raw = f.read().splitlines()

    # 引号预规范化（整篇一次性）：在进入逐行解析前，把全文 ASCII 直引号统一
    # 转为中文弯引号。**必须整篇一次处理、不可逐行**——逐行会在换行处重置
    # 开/闭状态，使跨行引号（跨行引用块、跨行长台词）的闭引号被误判为开引号。
    # 整篇处理后再 split 回行，行结构不变（smart_quotes 原样保留 '\n'）。
    ascii_dq_count = sum(line.count('\x22') for line in raw)
    ascii_sq_count = sum(line.count('\x27') for line in raw)
    if ascii_dq_count or ascii_sq_count:
        raw = smart_quotes('\n'.join(raw)).split('\n')
        # 奇数个引号 = 源文档配对本身有歧义，交替转换的左右方向可能判反，单独点名。
        odd_note = ''
        if ascii_dq_count % 2 or ascii_sq_count % 2:
            odd_note = (' [WARN] 其中存在奇数个引号，配对有歧义，左右方向可能判反，'
                        '请务必回到源 .md 核对。')
        print(f'[md_to_laojohn_docx] [WARN] 源文件含 ASCII 直引号'
              f'（双引号 {ascii_dq_count} 处，单引号 {ascii_sq_count} 处），'
              f'已整篇自动转换为中文弯引号。建议在源 .md 中修正。{odd_note}')

    doc = Document()

    # 预扫描主标题里的《书名》，在正文前插入原生封面页（单节·首页独立页眉）。
    # 必须先于 setup_page：封面建好后，setup_page 按 has_cover 配置首页独立页眉/页码。
    book_name = ''
    for ln in raw:
        s = ln.strip()
        if s.startswith('# '):
            mb = re.search(r'《(.+?)》', s)
            if mb:
                book_name = mb.group(1).strip()
            break
    has_cover = render_cover_page(doc, book_name)
    setup_page(doc, has_cover=has_cover)

    i = 0
    n = len(raw)
    seen_doc_title = False
    seen_lesson = False
    while i < n:
        line = raw[i]
        stripped = line.strip()

        # 空行
        if not stripped:
            i += 1
            continue

        # HTML 注释块 <!-- ... -->（含背景说明、交接备注），整块跳过不渲染
        if stripped.startswith('<!--'):
            if '-->' in stripped:
                i += 1
            else:
                i += 1
                while i < n and '-->' not in raw[i]:
                    i += 1
                i += 1  # 跳过含 --> 的那行
            continue

        # 表格块（连续的 | 行）
        if is_table_line(line):
            tbl_lines = []
            while i < n and is_table_line(raw[i]):
                tbl_lines.append(raw[i]); i += 1
            rows = [_split_table_row(l) for l in tbl_lines
                    if not TABLE_SEP_RE.match(l.strip())]
            if rows:
                header = rows[0]
                body = rows[1:]
                render_table(doc, header, body)
            continue

        # 标题层级
        if stripped.startswith('# ') and not seen_doc_title:
            title = stripped[2:].strip()
            m_book = re.search(r'《(.+?)》', title)
            if m_book:
                book_name = m_book.group(1).strip()
            render_doc_title(doc, title); seen_doc_title = True; i += 1
            # 紧跟的非空非标记行当副标题
            if i < n and raw[i].strip() and not raw[i].strip().startswith('#') \
               and not raw[i].strip().startswith('师') and not is_table_line(raw[i]):
                render_subtitle(doc, raw[i].strip()); i += 1
            continue
        if stripped.startswith('## '):
            title_text = stripped[3:].strip()
            # 课时标题(以"第"开头,如"第一课时")强制分页,即使是文档里第一个 ##;
            # 其他 ## 沿用旧逻辑:第一次不分页、后续分页。
            is_lesson = title_text.startswith('第')
            render_lesson_title(doc, title_text,
                                page_break=(seen_lesson or is_lesson))
            seen_lesson = True
            i += 1; continue
        if stripped.startswith('### '):
            sec_text = stripped[4:].strip()
            # 书级章节(文本介绍/教学目标/教学流程,出现在首个课时之前)上方空一行；
            # 课时内环节标题不加，避免全文每个 ### 前都留白。
            render_section_title(doc, sec_text,
                                 space_before=(14 if not seen_lesson else 0))
            # 「一、文本介绍」标题下方插入书籍封面
            if not seen_lesson and '文本介绍' in sec_text:
                render_cover(doc, book_name)
            i += 1; continue

        # PPT 锚点
        if PPT_RE.match(stripped):
            txt = stripped.strip('【】').strip()
            render_ppt(doc, txt); i += 1; continue

        # 〖PPT Pxx · 页型〗备课页标
        if PAGETAG_RE.match(stripped):
            render_pagetag(doc, stripped); i += 1; continue

        # 三维目标条
        m = OBJ_RE.match(stripped)
        if m:
            render_objective(doc, m.group(1), m.group(2)); i += 1; continue

        # 加粗小标题（**xxx** 单独成行）
        if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
            render_bold_label(doc, stripped[2:-2].strip()); i += 1; continue

        # 引用块（原文/宣传语）
        if stripped.startswith('>'):
            render_quote(doc, stripped.lstrip('>').strip()); i += 1; continue

        # 师话
        if stripped.startswith('师：') or stripped.startswith('师:'):
            render_teacher(doc, stripped[2:].lstrip('：:').strip()
                           if stripped[1] in '：:' else stripped[2:]); i += 1; continue

        # 参考
        if stripped.startswith('参考：') or stripped.startswith('参考:'):
            body = stripped[3:] if stripped[2] in '：:' else stripped[2:]
            render_ref(doc, body.strip()); i += 1; continue

        # 学生分享提示
        if stripped in SHARE_LINES or (stripped.startswith('学生') and len(stripped) <= 12):
            render_share(doc, stripped); i += 1; continue

        # 收尾
        if stripped in ('本课完。', '本课完', '全课完。', '全课完', '（全课完）'):
            render_end(doc, stripped); i += 1; continue

        # 四级及以下标题：规范未定义，剥掉 # 当正文，避免 #### 原样进文
        m = DEEP_H_RE.match(stripped)
        if m:
            render_para(doc, m.group(1).strip()); i += 1; continue

        # 列表行：规范要求避免，但若 AI 误写，剥掉 -/数字. 标记当正文渲染
        # （注意：表格行已在前面 is_table_line 拦截；水平线 --- 不含内容不匹配）
        m = LIST_RE.match(stripped)
        if m:
            render_para(doc, m.group(1).strip()); i += 1; continue

        # 测评题题号行：每题之间留出段前间距（reading-assessment 专用，详见 QNUM_RE 注释）
        if QNUM_RE.match(stripped):
            render_para(doc, stripped, space_before=12); i += 1; continue

        # 默认正文（行内标记由 add_md_text 统一处理）
        # 【作者介绍】上方空一行（与【内容简介】区隔）
        sb = 14 if stripped.startswith('【作者介绍】') else 0
        render_para(doc, stripped, space_before=sb); i += 1

    doc.save(docx_path)
    return docx_path


def main():
    if len(sys.argv) < 2:
        print('用法: python md_to_laojohn_docx.py 输入.md [输出.docx]')
        sys.exit(1)
    md_path = sys.argv[1]
    if len(sys.argv) >= 3:
        docx_path = sys.argv[2]
    else:
        base = os.path.splitext(md_path)[0]
        docx_path = base + '.docx'
    out = convert(md_path, docx_path)
    print(f'saved -> {out}')


if __name__ == '__main__':
    main()
