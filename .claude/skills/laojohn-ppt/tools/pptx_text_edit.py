# -*- coding: utf-8 -*-
"""pptx_text_edit.py - 对**外部已存在的 .pptx** 做文本级改稿的底层件。

适用面（2026-09-16 立 · 五上二《“漫画”老师》按改页清单改桌面终稿时写）：
外部平台生成的课件要按详案改几十处文字，人工在 PowerPoint 里逐页改易漏易错。
本件只改文字与形状几何，**不新建页、不换版式、不碰嵌入的图**，因此不与
CLAUDE.md §3「写作课 pptx 由外部生成、本仓只做动画后处理」冲突——它服务的正是
「把详案的改动带回外部件」这一步，产物仍是外部件，不入本仓。
⚠ 官方 pptx skill 的禁令同样不覆盖这里：那条禁的是「用它新建本仓产物」。

用法：import 本件，按页取 shape，用 sub_text/set_rich 改字，del_shape 删块，
**收尾必须调 prune_timing(prs) + normalize_paragraphs(prs) 再 save**。

━━━ 三个静默坑（python-pptx 全都读得出，PowerPoint 一律拒绝打开，
     且报错只说 "PowerPoint could not open the file"，不提是哪一条）━━━

1. **复制形状必须换 shape id**。对 shape._element 直接 deepcopy 会连 cNvPr 的
   id 一起复制，同一页出现两个相同 id。用 clone_shape()，别自己 deepcopy。

2. **删形状后时间轴会留空容器**。摘掉引用该形状的 clickEffect 之后，
   <p:childTnLst>/<p:bldLst> 可能变成空元素，schema 要求非空。用 prune_timing()
   自底向上裁到稳定。del_shape() 本身只负责摘效果节点，不负责裁空壳。

3. **<a:endParaRPr> 必须是 <a:p> 的最后一个子元素**，<a:pPr> 必须是第一个。
   往段落里 append run 会把它们的相对位置弄反。用 normalize_paragraphs() 收尾。

排查顺序也按 1→2→3：先查全页 shape id 是否唯一，再查 timing 空容器，
最后查段落子元素顺序。三项都干净还打不开，才去怀疑 COM 环境（见 shot_assets.py
头注释的三个 COM 坑，本机 WPS 抢注 .pptx 关联，WPS 开着时 COM 导出会失败）。

另注：set_rich 的 {b}…{/b} 标记**必须在同一行内闭合**，跨换行会静默吃掉四个字符
（已加 ValueError 拦截）；unwrap 用来消除手工换行造成的孤字行，但原文里的缩进
空格会留在句中，写文本时就别加缩进。
"""
import copy
from pptx.util import Pt

P_NS = '{http://schemas.openxmlformats.org/presentationml/2006/main}'
A_NS = '{http://schemas.openxmlformats.org/drawingml/2006/main}'


def _first_run(para):
    for r in para.runs:
        return r
    return None


def set_text(shape, text, size=None):
    """text 用 \n 分段（对应原形状的多段落结构）。保留原首段首 run 的格式。"""
    tf = shape.text_frame
    paras = tf.paragraphs
    proto = None
    for p in paras:
        r = _first_run(p)
        if r is not None:
            proto = copy.deepcopy(r._r)
            break
    if proto is None:
        raise ValueError('形状无可用 run 作格式母本')

    lines = text.split('\n')
    # 保留第一个段落的 pPr，其余段落删掉后按需重建
    first = paras[0]._p
    parent = first.getparent()
    for p in list(paras[1:]):
        parent.remove(p._p)
    # 清空首段的 run，塞入第一行
    for child in list(first):
        if child.tag in (A_NS + 'r', A_NS + 'br', A_NS + 'fld'):
            first.remove(child)
    r = copy.deepcopy(proto)
    r.find(A_NS + 't').text = lines[0]
    first.append(r)
    prev = first
    for ln in lines[1:]:
        np = copy.deepcopy(first)
        for child in list(np):
            if child.tag in (A_NS + 'r', A_NS + 'br', A_NS + 'fld'):
                np.remove(child)
        r = copy.deepcopy(proto)
        r.find(A_NS + 't').text = ln
        np.append(r)
        prev.addnext(np)
        prev = np
    if size is not None:
        for p in shape.text_frame.paragraphs:
            for run in p.runs:
                run.font.size = Pt(size)
    return shape


def sub_text(shape, old, new, must=True):
    """段落内子串替换。段内若跨 run，则把整段并成一个 run（取首 run 格式）。"""
    hit = 0
    for para in shape.text_frame.paragraphs:
        full = ''.join(r.text for r in para.runs)
        if old not in full:
            continue
        hit += full.count(old)
        newfull = full.replace(old, new)
        runs = para.runs
        if len(runs) == 1:
            runs[0].text = newfull
        else:
            runs[0].text = newfull
            for r in runs[1:]:
                r._r.getparent().remove(r._r)
    if must and hit == 0:
        raise ValueError('未命中: %r' % old)
    return hit


def set_size(shape, size):
    for p in shape.text_frame.paragraphs:
        for r in p.runs:
            r.font.size = Pt(size)


def del_shape(slide, shape):
    """删形状；同时摘掉 timing 里引用它的 clickEffect（p:par 祖先）。"""
    sid = str(shape.shape_id)
    el = slide._element
    timing = el.find(P_NS + 'timing')
    if timing is not None:
        for spTgt in timing.iter(P_NS + 'spTgt'):
            if spTgt.get('spid') != sid:
                continue
            node = spTgt
            top = None
            while node is not None:
                if node.tag == P_NS + 'par':
                    ctn = node.find(P_NS + 'cTn')
                    if ctn is not None and ctn.get('nodeType') in ('clickEffect', 'afterEffect', 'withEffect'):
                        top = node
                        break
                node = node.getparent()
            if top is not None and top.getparent() is not None:
                top.getparent().remove(top)
        # 清掉 bldLst 里对该 spid 的构建项
        for bld in list(timing.iter(P_NS + 'bldP')) + list(timing.iter(P_NS + 'bldGraphic')):
            if bld.get('spid') == sid:
                bld.getparent().remove(bld)
    shape._element.getparent().remove(shape._element)


def set_rich(shape, text, size=None):
    """整段重写，支持 {b}…{/b} 标加粗。
    普通文字取原形状里第一个非粗 run 作格式母本，加粗文字取第一个粗 run 作母本
    （这样原有的强调色一并保留）；缺哪一种就拿另一种复制后改 bold。
    """
    import re
    tf = shape.text_frame
    plain = bold = None
    for p in tf.paragraphs:
        for r in p.runs:
            if r.font.bold and bold is None:
                bold = copy.deepcopy(r._r)
            if not r.font.bold and plain is None:
                plain = copy.deepcopy(r._r)
    if plain is None and bold is None:
        raise ValueError('形状无 run')
    if plain is None:
        plain = copy.deepcopy(bold)
        rPr = plain.find(A_NS + 'rPr')
        if rPr is not None:
            rPr.set('b', '0')
    if bold is None:
        bold = copy.deepcopy(plain)
        rPr = bold.find(A_NS + 'rPr')
        if rPr is not None:
            rPr.set('b', '1')

    paras = tf.paragraphs
    first = paras[0]._p
    parent = first.getparent()
    for p in list(paras[1:]):
        parent.remove(p._p)

    def fill(pel, line):
        for child in list(pel):
            if child.tag in (A_NS + 'r', A_NS + 'br', A_NS + 'fld'):
                pel.remove(child)
        for chunk in re.split(r'(\{b\}.*?\{/b\})', line):
            if not chunk:
                continue
            if chunk.startswith('{b}'):
                r = copy.deepcopy(bold); txt = chunk[3:-4]
            else:
                r = copy.deepcopy(plain); txt = chunk
            if not txt:
                continue
            r.find(A_NS + 't').text = txt
            pel.append(r)

    lines = text.split('\n')
    for ln in lines:
        if ln.count('{b}') != ln.count('{/b}'):
            raise ValueError('标记跨行未配对，须在同一行内闭合: %r' % ln)
    fill(first, lines[0])
    prev = first
    for ln in lines[1:]:
        np = copy.deepcopy(first)
        fill(np, ln)
        prev.addnext(np)
        prev = np
    if size is not None:
        set_size(shape, size)
    return shape


def unwrap(shape):
    """把形状里的多个段落并成一段，交给 PowerPoint 自动折行（消除孤字行）。
    段落交界处若两边都不是标点就不补字符，原样相接。"""
    tf = shape.text_frame
    paras = tf.paragraphs
    if len(paras) < 2:
        return shape
    first = paras[0]._p
    for p in paras[1:]:
        for child in list(p._p):
            if child.tag in (A_NS + 'r', A_NS + 'br', A_NS + 'fld'):
                first.append(child)
        p._p.getparent().remove(p._p)
    return shape


def set_fill(shape, rgb):
    from pptx.dml.color import RGBColor
    shape.fill.solid()
    shape.fill.fore_color.rgb = RGBColor.from_string(rgb)
    shape.line.fill.background()


def normalize_paragraphs(prs):
    """收尾校正：a:endParaRPr 必须是 a:p 的最后一个子元素，a:pPr 必须是第一个。
    编辑过程中往段落里 append run 会把它们的相对位置弄反，python-pptx 读得出、
    PowerPoint 会直接拒绝打开文件。"""
    fixed = 0
    for sl in prs.slides:
        for p_el in sl._element.iter(A_NS + 'p'):
            kids = list(p_el)
            end = [c for c in kids if c.tag == A_NS + 'endParaRPr']
            ppr = [c for c in kids if c.tag == A_NS + 'pPr']
            changed = False
            for e in end:
                if kids[-1] is not e:
                    p_el.remove(e); p_el.append(e); changed = True
            for e in ppr:
                if list(p_el)[0] is not e:
                    p_el.remove(e); p_el.insert(0, e); changed = True
            if changed:
                fixed += 1
    return fixed


def clone_shape(slide, proto, name=None):
    """在同一页复制一个形状并分配唯一 shape id。
    ⚠ 直接 deepcopy 会让 cNvPr 的 id 与母本重复，python-pptx 读得出、
    PowerPoint 一律拒绝打开（报 could not open the file，不提 id）。"""
    def walk(shs):
        for s in shs:
            yield s
            if s.shape_type == 6:
                for x in walk(s.shapes):
                    yield x
    nxt = max(s.shape_id for s in walk(slide.shapes)) + 1
    el = copy.deepcopy(proto._element)
    proto._element.addnext(el)
    for cNvPr in el.iter('{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr'):
        cNvPr.set('id', str(nxt))
        if name:
            cNvPr.set('name', name)
        nxt += 1
    for s in slide.shapes:
        if s._element is el:
            return s
    raise RuntimeError('克隆后未能在页面上找回该形状')


def prune_timing(prs):
    """收尾校正：删过形状后时间轴会留下空的 <p:childTnLst>/<p:bldLst> 等容器，
    以及只剩壳、没有任何子时间节点的 par。python-pptx 读得出、PowerPoint 拒绝打开。
    自底向上反复裁剪到稳定为止。"""
    removed = 0
    for sl in prs.slides:
        t = sl._element.find(P_NS + 'timing')
        if t is None:
            continue
        while True:
            changed = False
            for tag in ('bldLst', 'childTnLst', 'subTnLst'):
                for e in list(t.iter(P_NS + tag)):
                    if len(e) == 0:
                        e.getparent().remove(e)
                        changed = True; removed += 1
            for tag in ('par', 'seq'):
                for e in list(t.iter(P_NS + tag)):
                    ctn = e.find(P_NS + 'cTn')
                    if ctn is None:
                        continue
                    if ctn.get('nodeType') in ('tmRoot', 'mainSeq'):
                        continue
                    if ctn.find(P_NS + 'childTnLst') is None and len(ctn) == 0:
                        parent = e.getparent()
                        if parent is not None:
                            parent.remove(e)
                            changed = True; removed += 1
            if not changed:
                break
        tn = t.find(P_NS + 'tnLst')
        if tn is not None and len(tn) == 0:
            t.getparent().remove(t)
            removed += 1
    return removed
