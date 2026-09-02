#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""外部人工改过的详案 .docx → 仓内 .md 事实源「回贴器」。

背景（CLAUDE.md §8）：`写作课详案输出/*.docx` 是 gitignore 的渲染产物，事实源是 .md。
人工在 docx 上改了字，不回到 md，下一次重渲就静默冲掉。本仓此前没有任何 docx→md
反向工具，5 处 Document( 调用全是单向写入——本文件补上这一环。

做法＝**骨架继承 + 文本整体替换**（不是裸转，也不是逐条 diff 裁决）：
  影子解析(md) → Unit(lineno, md_pre, docx_pre, body, expect)
  抽取(外部 docx) → 块序列
  SequenceMatcher 对齐 → 对齐上的用 docx 新文本重建 md 行，md 前缀原样保留
  未被 Unit 覆盖的 md 行（注释块 / 空行 / --- / 首页授课提示）原样留在原位

*** 改 md_to_laojohn_docx.py 的解析分支，必须回归本文件的 shadow_units() ***
它是那个 while 循环文本分支的镜像。正则与 smart_quotes/fullwidth_punct 一律从
引擎 import、绝不重写；本文件只复刻「分派顺序」，不碰任何样式。
同理 front-page 通道镜像 style_front_page.py 的 parse_md/_render_value。

六个踩过的坑（改动本文件前先读）：
1. SequenceMatcher 必须 autojunk=False。骨架话术（`学生互动分享` 单篇 ×5）在
   b 长度 ≥200 时会被 autojunk 判为垃圾并全部拉黑，对齐直接崩。
2. 归一只 strip ASCII 空白，绝不折叠 U+3000——「9月15日　星期一　晴」的全角空格是内容。
3. 首页必须走独立通道：style_front_page._render_value 对值列做过文本级重排
   （`　│　` 重拼、剥 `**`、partition 后 strip），塞进正文序列必假报差异。
4. 表格必须手写 body 块迭代器：doc.paragraphs 漏单元格、doc.tables 丢顺序；
   合并单元格 row.cells 会返回重复对象，按 id(cell._tc) 去重。
5. Word 重存会把一个 run 拆成多个（拼写检查、语言标记都会拆），抽取后须合并相邻同 bold run。
6. `## 第N课时` 分页时引擎会先插一个内容为 ' ' 的 spacer 段；HR `---` 渲染成空段落。
   两者都要当噪声丢弃，但丢弃前保留索引映射。

自证闸门：backfill/verify 前先用引擎渲一份基线 docx，断言 extract(基线) ≡ shadow(md)。
不等即 exit 2 拒绝动手——把「影子解析器抄错引擎分支」从静默出错变成响亮罢工。

用法：
    python docx_backfill.py selfcheck <md>
    python docx_backfill.py backfill  <md> <外部docx> [--dry-run] [-o 新md]
    python docx_backfill.py verify    <md> <外部docx>
退出码：0 无差异 / 1 有差异 / 2 影子自证失败 / 3 参数或文件错
"""
import os
import re
import sys
import argparse
import difflib
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import md_to_laojohn_docx as E          # noqa: E402  影子解析器的镜像对象
import style_front_page as F            # noqa: E402  首页通道的镜像对象

from docx import Document               # noqa: E402
from docx.oxml.ns import qn             # noqa: E402
from docx.text.paragraph import Paragraph   # noqa: E402
from docx.table import Table            # noqa: E402


# ===================== 归一 =====================

_ASCII_WS = ' \t\r\n\x0b\x0c'


def norm(t):
    """比对用归一。只处理渲染层必然发生的变换，绝不碰内容层。"""
    t = t.replace('\x0b', '\n')
    t = re.sub(r'<br\s*/?>', '\n', t)
    t = t.replace('**', '').replace('__', '')
    return t.strip(_ASCII_WS)


def strip_bold(t):
    """剥掉成对/残余的 ** __ ——与引擎 add_md_text 的行为一致。"""
    out = []
    for seg in E._INLINE_BOLD_RE.split(t):
        if len(seg) > 4 and ((seg.startswith('**') and seg.endswith('**'))
                             or (seg.startswith('__') and seg.endswith('__'))):
            out.append(seg[2:-2])
        else:
            out.append(seg.replace('**', '').replace('__', ''))
    return ''.join(out)


# ===================== 影子解析器（镜像 E.convert 的文本分支）=====================

class Unit(object):
    """md 一行（或表格一格）与其在 docx 中对应块的映射。

    md_pre    md 行里正文之前的标记（'### ' / '> ' / '师：' / '- ' …），回写时原样保留
    docx_pre  docx 文本里正文之前的固定前缀（'' / '师：' / '参考：' / '【标签】'）
    body      md 侧正文（可能含 ** 标记）
    expect    期望的 docx 段落全文 = docx_pre + strip_bold(body)
    """

    __slots__ = ('lineno', 'kind', 'md_pre', 'docx_pre', 'body', 'expect',
                 'col', 'ncol', 'has_bold')

    def __init__(self, lineno, kind, md_pre, docx_pre, body, col=None, ncol=None):
        self.lineno = lineno
        self.kind = kind
        self.md_pre = md_pre
        self.docx_pre = docx_pre
        self.body = body
        self.col = col
        self.ncol = ncol
        self.has_bold = ('**' in body) or ('__' in body)
        self.expect = docx_pre + strip_bold(body)


def detect_eol(md_path):
    """探测原文件行尾符。写回时必须原样保持，否则 git diff 会把整篇标成改动。"""
    with open(md_path, 'rb') as f:
        data = f.read()
    return '\r\n' if data.count(b'\r\n') else '\n'


def preprocess(md_path):
    """复刻 E.convert 的整篇预处理（引号规范化 + 标点全角化）。行数不变。"""
    with open(md_path, encoding='utf-8') as f:
        orig = f.read().splitlines()
    raw = list(orig)
    if any('\x22' in l or '\x27' in l for l in raw):
        raw = E.smart_quotes('\n'.join(raw)).split('\n')
    raw, _ = E.fullwidth_punct('\n'.join(raw))
    raw = raw.split('\n')
    return orig, raw


def shadow_units(md_path):
    """把 md 解析成「anchor 之后的正文 Unit 序列」+ 首页提纲表行。

    anchor 与 style_front_page.restyle 同口径：第一个以「第N课时」开头的段落。
    anchor 之前的块会被 style_front_page 删掉重建，故不进正文序列。
    """
    orig, raw = preprocess(md_path)
    n = len(raw)
    units = []
    front_rows = []          # [(label, value, lineno, col1_lineno)]
    started = False          # 是否已越过 anchor
    seen_doc_title = False
    seen_lesson_title = False
    in_front_table = False   # 位于 `## 教案提纲表` 与下一个 `##` 之间

    def emit(lineno, md_pre, docx_pre, body):
        # 归一后为空的块不进序列：引擎对空引用块 `> ` 会渲成一个空段落，
        # 而 flatten_docx 把空段当噪声丢弃——两边口径必须一致，否则自证必失配。
        if started and norm(docx_pre + strip_bold(body)):
            units.append(Unit(lineno, 'P', md_pre, docx_pre, body))

    i = 0
    while i < n:
        line = raw[i]
        stripped = line.strip()
        lineno = i + 1

        if not stripped:
            i += 1
            continue

        # HTML 注释块：引擎整块跳过 → md 独有，原样保留、不进序列
        if stripped.startswith('<!--'):
            if '-->' in stripped:
                i += 1
            else:
                i += 1
                while i < n and '-->' not in raw[i]:
                    i += 1
                i += 1
            continue

        # 表格块
        if E.is_table_line(line):
            tbl = []
            while i < n and E.is_table_line(raw[i]):
                tbl.append((i + 1, raw[i]))
                i += 1
            rows = [(ln, E._split_table_row(l)) for ln, l in tbl
                    if not E.TABLE_SEP_RE.match(l.strip())]
            if not rows:
                continue
            if in_front_table and not started:
                for ln, cells in rows:
                    if len(cells) >= 2 and not set(cells[0]) <= {'-', ' ', ':'}:
                        front_rows.append((cells[0], cells[1], ln))
                continue
            ncol = len(rows[0][1])
            for ln, cells in rows:
                for ci in range(ncol):
                    val = cells[ci] if ci < len(cells) else ''
                    if started:
                        u = Unit(ln, 'T', '', '', val, col=ci, ncol=ncol)
                        u.expect = norm(strip_bold(val))
                        units.append(u)
            continue

        # H1 + 副标题（同段、软回车分行）
        if stripped.startswith('# ') and not seen_doc_title:
            title = stripped[2:].strip()
            nxt = raw[i + 1].strip() if i + 1 < n else ''
            sub = None
            if nxt.startswith('###### '):
                sub = nxt[7:].strip()
            elif nxt and not nxt.startswith('#') and not nxt.startswith('师') \
                    and not E.is_table_line(raw[i + 1]):
                sub = nxt
            seen_doc_title = True
            i += 2 if sub else 1
            continue

        if stripped.startswith('## '):
            t = stripped[3:].strip()
            is_lesson = t.startswith('第')
            in_front_table = bool(re.search(
                F.PROFILES['writing']['zones_anchor'], stripped)) or \
                bool(re.search(F.PROFILES['picture']['zones_anchor'], stripped))
            if is_lesson and not started:
                started = True          # anchor：从这一段起进正文序列
                seen_lesson_title = True
            emit(lineno, '## ', '', t)
            i += 1
            continue

        if stripped.startswith('### '):
            emit(lineno, '### ', '', stripped[4:].strip())
            i += 1
            continue

        if E.PPT_RE.match(stripped):
            emit(lineno, '', '', stripped.strip('【】').strip())
            i += 1
            continue

        if E.PAGETAG_RE.match(stripped):
            emit(lineno, '', '', stripped)
            i += 1
            continue

        m = E.OBJ_RE.match(stripped)
        if m:
            emit(lineno, '【%s】' % m.group(1), '【%s】' % m.group(1), m.group(2))
            i += 1
            continue

        # 整行 **加粗小标题**
        if stripped.startswith('**') and stripped.endswith('**') and len(stripped) > 4:
            emit(lineno, '**', '', stripped[2:-2].strip())
            i += 1
            continue

        # 引用块
        if stripped.startswith('>'):
            body = stripped.lstrip('>').strip()
            pre = line[:len(line) - len(line.lstrip())] + \
                stripped[:len(stripped) - len(stripped.lstrip('>'))]
            rest = stripped.lstrip('>')
            pre += rest[:len(rest) - len(rest.lstrip())]
            emit(lineno, pre, '', body)
            i += 1
            continue

        # 师话
        if stripped.startswith('师：') or stripped.startswith('师:'):
            body = stripped[2:].lstrip('：:').strip() if stripped[1] in '：:' \
                else stripped[2:]
            emit(lineno, stripped[:2], '师：', body)
            i += 1
            continue

        # 参考
        if stripped.startswith('参考：') or stripped.startswith('参考:'):
            body = (stripped[3:] if stripped[2] in '：:' else stripped[2:]).strip()
            emit(lineno, stripped[:3], '参考：', body)
            i += 1
            continue

        # 学生分享提示
        if stripped in E.SHARE_LINES or (stripped.startswith('学生') and len(stripped) <= 12):
            emit(lineno, '', '', stripped)
            i += 1
            continue

        # 收尾
        if stripped in ('本课完。', '本课完', '全课完。', '全课完', '（全课完）'):
            emit(lineno, '', '', stripped)
            i += 1
            continue

        # 四级及以下标题
        m = E.DEEP_H_RE.match(stripped)
        if m:
            pre = stripped[:len(stripped) - len(m.group(1))]
            emit(lineno, pre, '', m.group(1).strip())
            i += 1
            continue

        # HR：渲染成空段落 → 噪声，不进序列
        if E.HR_RE.match(stripped):
            i += 1
            continue

        # 列表行
        m = E.LIST_RE.match(stripped)
        if m:
            pre = stripped[:len(stripped) - len(m.group(1))]
            emit(lineno, pre, '', m.group(1).strip())
            i += 1
            continue

        if E.QNUM_RE.match(stripped):
            emit(lineno, '', '', stripped)
            i += 1
            continue

        emit(lineno, '', '', stripped)
        i += 1

    return orig, raw, front_rows, units


# ===================== docx 抽取 =====================

def iter_blocks(parent_elm, parent):
    """按文档流保序产出 ('P', Paragraph) / ('T', Table)。
    python-docx 没有保序块迭代器：doc.paragraphs 漏表格单元格、doc.tables 丢顺序。"""
    for child in parent_elm.iterchildren():
        if child.tag == qn('w:p'):
            yield 'P', Paragraph(child, parent)
        elif child.tag == qn('w:tbl'):
            yield 'T', Table(child, parent)


def para_text(p):
    """段落全文。python-docx 已把 <w:br/> 转成 '\\n'。"""
    return p.text.replace('\x0b', '\n')


def extract_docx(path):
    """抽成 [(kind, payload)]：('P', text) / ('T', [[cell, ...], ...])。"""
    doc = Document(path)
    out = []
    for kind, obj in iter_blocks(doc.element.body, doc):
        if kind == 'P':
            out.append(('P', para_text(obj)))
        else:
            rows = []
            for row in obj.rows:
                cells, seen = [], set()
                for c in row.cells:
                    if id(c._tc) in seen:       # 合并单元格会返回重复对象
                        continue
                    seen.add(id(c._tc))
                    cells.append('\n'.join(para_text(p) for p in c.paragraphs))
                rows.append(cells)
            out.append(('T', rows))
    return out


def flatten_docx(blocks, anchor_re=re.compile(r'^第\s*\d+\s*课时')):
    """把 docx 块序列拍平成与 shadow units 同构的文本序列（anchor 起）。

    返回 (front_table, body)：front_table 是 anchor 前的最后一张表（提纲表），
    body 是 [(text, kind, col, ncol)]。丢弃空段与 spacer(' ')。
    """
    front_table = None
    body = []
    started = False
    for kind, payload in blocks:
        if not started:
            if kind == 'T':
                front_table = payload
                continue
            if kind == 'P' and anchor_re.match(payload.strip()):
                started = True
            else:
                continue
        if kind == 'P':
            t = payload.strip(_ASCII_WS)
            if not t:
                continue
            body.append((t, 'P', None, None))
        else:
            ncol = max(len(r) for r in payload) if payload else 0
            for row in payload:
                for ci in range(ncol):
                    v = row[ci] if ci < len(row) else ''
                    body.append((norm(v), 'T', ci, ncol))
    return front_table, body


# ===================== 自证闸门 =====================

def render_baseline(md_path):
    """用引擎渲一份基线 docx（写作课页眉），再跑 style_front_page。"""
    fd, tmp = tempfile.mkstemp(suffix='.docx', prefix='backfill_base_')
    os.close(fd)
    E.convert(md_path, tmp,
              header_left='老约翰·同步习作', header_right='写清楚·写生动·有章法')
    try:
        F.restyle(__import__('pathlib').Path(md_path), __import__('pathlib').Path(tmp))
    except SystemExit as ex:
        print('[自证] style_front_page 跳过：%s' % ex)
    return tmp


def selfcheck(md_path, verbose=True):
    """断言 extract(基线 docx) ≡ shadow(md)。返回 (ok, 失配列表)。"""
    orig, raw, front_rows, units = shadow_units(md_path)
    tmp = render_baseline(md_path)
    try:
        _front, body = flatten_docx(extract_docx(tmp))
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass

    exp = [norm(u.expect) for u in units]
    got = [norm(t) for t, k, c, nc in body]
    bad = []
    sm = difflib.SequenceMatcher(None, exp, got, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        bad.append((tag, [(units[k].lineno, exp[k]) for k in range(i1, i2)],
                    got[j1:j2]))
    ok = not bad
    if verbose:
        head = os.path.basename(md_path)
        if ok:
            print('[自证] OK  %s  正文 %d 块，提纲表 %d 行' % (head, len(exp), len(front_rows)))
        else:
            print('[自证] MISMATCH  %s  影子 %d 块 vs 基线 %d 块，失配 %d 处'
                  % (head, len(exp), len(got), len(bad)))
            for tag, a, b in bad[:8]:
                print('   [%s]' % tag)
                for ln, t in a[:3]:
                    print('     影子 md:%-4d | %s' % (ln, t[:96]))
                for t in b[:3]:
                    print('     基线      | %s' % t[:96])
    return ok, bad


# ===================== 回贴 =====================

def rebuild_line(orig_line, u, new_text):
    """用 docx 新文本重建 md 行，保留 md 前缀标记。"""
    body = new_text
    if u.docx_pre and body.startswith(u.docx_pre):
        body = body[len(u.docx_pre):]
    body = body.replace('\n', '<br>') if u.kind == 'T' else body
    if u.kind == 'T':
        return body
    if u.md_pre == '**':
        return '**' + body + '**'
    return u.md_pre + body


def backfill(md_path, docx_path, out_path=None, dry_run=False, skip_selfcheck=False):
    name = os.path.basename(md_path)
    if not skip_selfcheck:
        ok, _ = selfcheck(md_path)
        if not ok:
            print('[中止] 影子自证未通过，拒绝回贴：%s' % name)
            return 2

    orig, raw, front_rows, units = shadow_units(md_path)
    front_tbl, body = flatten_docx(extract_docx(docx_path))

    exp = [norm(u.expect) for u in units]
    got = [norm(t) for t, k, c, nc in body]

    lines = list(orig)
    stat = {'same': 0, 'edit': 0, 'bold_hold': 0, 'del': 0, 'ins': 0, 'front': 0}
    edits = []          # (lineno, old, new)
    holds = []          # 含 ** 的行，不自动改
    inserts = []        # (after_lineno, text)
    deletes = []        # (lineno, text)

    sm = difflib.SequenceMatcher(None, exp, got, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            stat['same'] += i2 - i1
            continue
        if tag == 'replace':
            a, b = list(range(i1, i2)), list(range(j1, j2))
            if len(a) == len(b):
                pairs = list(zip(a, b))
            else:
                pairs = _greedy_pair(exp, got, a, b)
                for k in a:
                    if k not in [p[0] for p in pairs]:
                        deletes.append((units[k].lineno, exp[k]))
                        stat['del'] += 1
                for k in b:
                    if k not in [p[1] for p in pairs]:
                        anchor_ln = units[a[-1]].lineno if a else None
                        inserts.append((anchor_ln, got[k]))
                        stat['ins'] += 1
            for ia, ib in pairs:
                u = units[ia]
                if norm(u.expect) == norm(body[ib][0]):
                    stat['same'] += 1
                    continue
                if u.has_bold:
                    holds.append((u.lineno, exp[ia], got[ib]))
                    stat['bold_hold'] += 1
                    continue
                new_line = rebuild_line(lines[u.lineno - 1], u, body[ib][0])
                edits.append((u.lineno, u.col, new_line, exp[ia], got[ib]))
                stat['edit'] += 1
        elif tag == 'delete':
            for k in range(i1, i2):
                deletes.append((units[k].lineno, exp[k]))
                stat['del'] += 1
        elif tag == 'insert':
            anchor_ln = units[i1 - 1].lineno if i1 > 0 else None
            for k in range(j1, j2):
                inserts.append((anchor_ln, got[k]))
                stat['ins'] += 1

    # 表格：同一 md 行的多个 cell 要合并成一行后再写回
    tbl_edits = {}
    plain_edits = []
    for lineno, col, new_line, old_t, new_t in edits:
        if col is None:
            plain_edits.append((lineno, new_line, old_t, new_t))
        else:
            tbl_edits.setdefault(lineno, {})[col] = new_line

    for lineno, new_line, _o, _n in plain_edits:
        lines[lineno - 1] = new_line
    for lineno, colmap in tbl_edits.items():
        cells = E._split_table_row(lines[lineno - 1])
        for ci, v in colmap.items():
            if ci < len(cells):
                cells[ci] = v
        lines[lineno - 1] = '| ' + ' | '.join(cells) + ' |'

    # 首页提纲表
    front_report = []
    if front_tbl:
        fmap = {}
        for row in front_tbl:
            if len(row) >= 2:
                fmap[norm(row[0])] = norm(row[1])
        for label, value, ln in front_rows:
            k = norm(label)
            if k not in fmap:
                continue
            if _front_norm(value) == _front_norm(fmap[k]):
                continue
            if '**' in value:
                holds.append((ln, value, fmap[k]))
                stat['bold_hold'] += 1
                continue
            cells = E._split_table_row(lines[ln - 1])
            if len(cells) >= 2:
                cells[1] = fmap[k].replace('\n', '<br>')
                lines[ln - 1] = '| ' + ' | '.join(cells) + ' |'
                front_report.append((ln, label, value, fmap[k]))
                stat['front'] += 1

    # 结构变动（新增块 / 消失块）一律只报告、不自动改写。
    # 理由：docx 侧的一条「消失 + 新增」往往是同一块位置移动（页标最常见），
    # 自动插入而不删旧会造成重复；且插入点只能靠邻块推断，不可靠。
    # 这类属计划里的「乙档·必须人工判」，交由人逐条处置。
    moved = []
    for ai, (anchor_ln, text) in enumerate(inserts):
        for di, (dln, dtext) in enumerate(deletes):
            if norm(text) == norm(dtext):
                moved.append((dln, anchor_ln, text))
                break

    print('\n=== %s ===' % name)
    print('  同 %d · 改 %d · 首页 %d · 含**待核 %d · 新增 %d · 消失 %d'
          % (stat['same'], stat['edit'], stat['front'], stat['bold_hold'],
             stat['ins'], stat['del']))
    for ln, o, nw in holds:
        print('  [待核·含**] md:%d' % ln)
        print('      旧 | %s' % o[:110])
        print('      新 | %s' % nw[:110])
    for ln, t in deletes:
        tag = '移动源' if any(x[0] == ln for x in moved) else '消失'
        print('  [%s·待人工] md:%d | %s' % (tag, ln, t[:110]))
    for anchor_ln, t in inserts:
        tag = '移动' if any(norm(t) == norm(x[2]) for x in moved) else '新增'
        print('  [%s·待人工] 落在 md:%s 后 | %s' % (tag, anchor_ln, t[:110]))
    for ln, label, o, nw in front_report:
        print('  [首页] md:%d 「%s」' % (ln, label))
        print('      旧 | %s' % o[:110])
        print('      新 | %s' % nw[:110])

    if dry_run:
        print('  (--dry-run，未写盘)')
        return 1 if (stat['edit'] or stat['front']) else 0

    target = out_path or md_path
    eol = detect_eol(md_path)
    with open(target, 'w', encoding='utf-8', newline='') as f:
        f.write(eol.join(lines) + eol)
    print('  已写入 %s' % target)
    return 0


def _front_norm(v):
    """首页值列归一：_render_value 做过 `　│　` 重拼、剥 **、partition 后 strip。"""
    v = norm(v)
    parts = [p.strip() for p in re.split(r'[│|]', v) if p.strip()]
    return F.SEP.join(parts) if len(parts) > 1 else v


def _greedy_pair(exp, got, a, b):
    """replace 块内长度不等时按相似度贪心配对，ratio ≥ 0.55 才算同一段被改写。"""
    pairs, used = [], set()
    for ia in a:
        best, bi = 0.0, None
        for ib in b:
            if ib in used:
                continue
            r = difflib.SequenceMatcher(None, exp[ia], got[ib]).ratio()
            if r > best:
                best, bi = r, ib
        if bi is not None and best >= 0.55:
            pairs.append((ia, bi))
            used.add(bi)
    return pairs


def verify(md_path, docx_path):
    """收敛判据：重渲后的 docx 与外部 docx 在文本层是否已一致。"""
    tmp = render_baseline(md_path)
    try:
        _f1, b1 = flatten_docx(extract_docx(tmp))
        _f2, b2 = flatten_docx(extract_docx(docx_path))
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    a = [norm(t) for t, k, c, nc in b1]
    b = [norm(t) for t, k, c, nc in b2]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    diff = [(tag, a[i1:i2], b[j1:j2])
            for tag, i1, i2, j1, j2 in sm.get_opcodes() if tag != 'equal']
    name = os.path.basename(md_path)
    if not diff:
        print('[verify] OK  %s  重渲 docx 与外部件文本层一致（%d 块）' % (name, len(a)))
        return 0
    print('[verify] %s  仍有 %d 处差异（相似 %.4f）' % (name, len(diff), sm.ratio()))
    for tag, x, y in diff[:12]:
        print('  [%s]' % tag)
        for t in x[:2]:
            print('    本仓 | %s' % t[:110])
        for t in y[:2]:
            print('    外部 | %s' % t[:110])
    return 1


def main():
    ap = argparse.ArgumentParser(description='外部改稿 docx → 仓内 md 回贴器')
    sub = ap.add_subparsers(dest='cmd')

    p1 = sub.add_parser('selfcheck', help='只跑影子自证（兼作 docx 是否过期探测）')
    p1.add_argument('md')

    p2 = sub.add_parser('backfill', help='把外部 docx 的文本回贴进 md')
    p2.add_argument('md')
    p2.add_argument('docx')
    p2.add_argument('-o', '--out', default=None)
    p2.add_argument('--dry-run', action='store_true')
    p2.add_argument('--skip-selfcheck', action='store_true')

    p3 = sub.add_parser('verify', help='收敛判据：重渲 docx 与外部件比对')
    p3.add_argument('md')
    p3.add_argument('docx')

    args = ap.parse_args()
    if args.cmd == 'selfcheck':
        ok, _ = selfcheck(args.md)
        return 0 if ok else 2
    if args.cmd == 'backfill':
        return backfill(args.md, args.docx, args.out, args.dry_run, args.skip_selfcheck)
    if args.cmd == 'verify':
        return verify(args.md, args.docx)
    ap.print_help()
    return 3


if __name__ == '__main__':
    sys.exit(main())
