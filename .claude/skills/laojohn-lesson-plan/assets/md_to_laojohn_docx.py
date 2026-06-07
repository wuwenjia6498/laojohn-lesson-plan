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
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT, WD_BREAK
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

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


# ===================== 各块渲染器 =====================

def render_doc_title(doc, text):
    p = doc.add_paragraph(); _fmt(p); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(text), size=DOC_TITLE_SZ, bold=True)


def render_subtitle(doc, text):
    p = doc.add_paragraph(); _fmt(p, space_after=6); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    set_font(p.add_run(text), size=BASE_SIZE, bold=False)


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
    r = p.add_run(text); set_font(r, size=LESSON_SZ, bold=True)
    r.font.color.rgb = TITLE_COLOR


def render_section_title(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run(text), size=BASE_SIZE, bold=True)


def render_bold_label(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run(text), size=BASE_SIZE, bold=True)


def render_teacher(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run('师：'), size=BASE_SIZE, bold=True)
    set_font(p.add_run(text), size=BASE_SIZE, bold=True)


def render_ref(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run('参考：'), size=BASE_SIZE, bold=True)
    set_font(p.add_run(text), size=BASE_SIZE, bold=False)


def render_share(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run(text), size=BASE_SIZE, bold=False)


def render_objective(doc, label, content):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run(f'【{label}】'), size=BASE_SIZE, bold=True)
    set_font(p.add_run(content), size=BASE_SIZE, bold=False)


def render_ppt(doc, text):
    p = doc.add_paragraph(); _fmt(p)
    r = p.add_run(text); set_font(r, size=BASE_SIZE, bold=False)
    r.font.color.rgb = PPT_COLOR


def render_quote(doc, text):
    p = doc.add_paragraph(); _fmt(p, left_indent=0.84, right_indent=0.84)
    set_font(p.add_run(text), size=BASE_SIZE, bold=False)


def render_para(doc, text, bold=False):
    p = doc.add_paragraph(); _fmt(p)
    set_font(p.add_run(text), size=BASE_SIZE, bold=bold)


def render_end(doc, text):
    p = doc.add_paragraph(); _fmt(p, space_before=6)
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    set_font(p.add_run(text), size=BASE_SIZE, bold=True)


def render_table(doc, header_cells, body_rows):
    ncol = len(header_cells)
    table = doc.add_table(rows=1 + len(body_rows), cols=ncol)
    table.style = 'Table Grid'
    table.autofit = True
    for i, h in enumerate(header_cells):
        cell = table.rows[0].cells[i]; cell.text = ''
        p = cell.paragraphs[0]; _fmt(p)
        set_font(p.add_run(h), size=TABLE_SZ, bold=True)
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
                set_font(p.add_run(seg), size=TABLE_SZ, bold=False)
            set_cell_shading(cell, CELL_FILL)
    return table


# ===================== 页面 / 页眉页脚 =====================

def setup_page(doc):
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

    for sec in doc.sections:
        sec.page_height = Cm(29.7); sec.page_width = Cm(21.0)
        sec.left_margin = sec.right_margin = Cm(2.5)
        sec.top_margin = Cm(3.2); sec.bottom_margin = Cm(2.5)
        sec.header_distance = Cm(1.5); sec.footer_distance = Cm(1.0)

    sec = doc.sections[0]
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

PPT_RE   = re.compile(r'^【?\s*PPT\s*换页\s*[-—:：]?\s*P', re.I)
OBJ_RE   = re.compile(r'^【(知识技能|过程方法|情感价值|知识与技能|过程与方法|情感态度价值观)】\s*(.*)$')
TABLE_SEP_RE = re.compile(r'^\|?\s*:?-{2,}.*$')  # |---|---| 分隔行
# 列表标记：无序 - / * / +，有序 1. 1) （仅行首，且后面有空格+内容）
LIST_RE  = re.compile(r'^\s*(?:[-*+]|\d+[.)])\s+(.*\S.*)$')
# 四级及以下标题 #### / ##### …（规范只定义到 ###，更深的剥掉 # 当正文）
DEEP_H_RE = re.compile(r'^#{4,}\s+(.*\S.*)$')


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

    doc = Document()
    setup_page(doc)

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
            render_doc_title(doc, stripped[2:].strip()); seen_doc_title = True; i += 1
            # 紧跟的非空非标记行当副标题
            if i < n and raw[i].strip() and not raw[i].strip().startswith('#') \
               and not raw[i].strip().startswith('师') and not is_table_line(raw[i]):
                render_subtitle(doc, raw[i].strip()); i += 1
            continue
        if stripped.startswith('## '):
            render_lesson_title(doc, stripped[3:].strip(), page_break=seen_lesson)
            seen_lesson = True
            i += 1; continue
        if stripped.startswith('### '):
            render_section_title(doc, stripped[4:].strip()); i += 1; continue

        # PPT 锚点
        if PPT_RE.match(stripped):
            txt = stripped.strip('【】').strip()
            render_ppt(doc, txt); i += 1; continue

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
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(1).strip())
            render_para(doc, text); i += 1; continue

        # 列表行：规范要求避免，但若 AI 误写，剥掉 -/数字. 标记当正文渲染
        # （注意：表格行已在前面 is_table_line 拦截；水平线 --- 不含内容不匹配）
        m = LIST_RE.match(stripped)
        if m:
            text = re.sub(r'\*\*(.+?)\*\*', r'\1', m.group(1).strip())
            render_para(doc, text); i += 1; continue

        # 默认正文（去掉行内 ** 强调标记，保留文字）
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', stripped)
        render_para(doc, text); i += 1

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
