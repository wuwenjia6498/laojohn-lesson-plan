# -*- coding: utf-8 -*-
"""essay_audit.py — 写作课详案「示范文机检 E」：只报数、不判决、不改文件。

用法：
    PYTHONUTF8=1 python .claude/skills/laojohn-writing-lesson/assets/essay_audit.py <详案.md>

报什么（判据单一源＝references/model-essay.md，本脚本不复制判据）：
  ① 示范文篇幅：总字数、段数、各段字数、最长段（对 §三 A 表区间；师话里「共几段／哪段最长／一句带过」等可数断言据此核）
  ② 引文逐字审计：示范文引块之外、引号内 ≥6 字的句子，若与示范文高度相似却不逐字相同 → 报「疑似改写」；
     完全找不到相似片段的只计数（多半引的是别的材料，如③两段对照）。截断可接受、改写须打回。
  ③ 旁批表逐行比对：表头含「示范文／原文／句子」的表，其引句列每格须是示范文的子串；格内「……／、／；」与并列引语按片段顺序比对，内层引号剥掉。核 0 格打 [WARN]。
  ④ 笔法锚点复用：§四之三 两段风格示例的题材词与整句不得出现在示范文里（锚点句运行时从 model-essay.md 切出，题材词硬编码 ≥3 字）。
  ⑤ 交代段粗筛：逐段句数与首句，供人核 §六 第 7 问（来历／交代／外形段是否自犯本课反例的病）；只报数、不立数值线。
  示范文块：`> 【教师示范文】` 引块可能不止一个（§三 B 单点示范段 + A 整篇并存）；① 取最长的一块为整篇，②③④ 对全部块的并集比对。
  ⑥ 师话可数断言行：把含「几段／最长／最短／一句带过／两三句／几处」的 师： 行列出来，配 ① 的实数人工核。

设计约束：与 tone_gate 同款定位（[INFO] 通道），永不 exit 1；不解析 pools／rubric；不 import 任何 skill 私有模块。
"""
import re, sys, pathlib

ANCHOR_TOPICS = ['系鞋带', '光着袜子', '拎在手里', '缠的胶布', '车把上', '后座那块木板', '按了一下车铃', '把车挪正']
GRADE_RANGE = {'一': 'L1 50–150', '二': 'L2 50–150', '三': 'L3 300 左右', '四': 'L4 400 左右', '五': 'L5 450–500', '六': 'L6 500–600+'}
CLAIM_PAT = re.compile(r'几段|最长|最短|一句带过|两三句|几句|几处|多少字|第.段')
FRAG_SPLIT = re.compile(r'……|…|、|；|;')
INNER_QUOTES = re.compile(r'[“”‘’"\'「」]')

def strip_ws(s):
    return re.sub(r'[\s　]', '', s)

def load_anchor_sents():
    """运行时从 model-essay.md §四之三 两个 `>` 引块切句（≥6 字），锚点句不再硬编码；读不到就返回空。"""
    p = pathlib.Path(__file__).resolve().parent.parent / 'references' / 'model-essay.md'
    try:
        text = p.read_text(encoding='utf-8')
    except OSError:
        return []
    m = re.search(r'## 四之三.*?(?=\n## )', text, re.S)
    if not m:
        return []
    sents = []
    for q in re.findall(r'^> (.+)$', m.group(0), re.M):
        for s in re.split(r'[。！？，,]', q):
            s = strip_ws(s)
            if len(s) >= 6:
                sents.append(s)
    return sents

def frags_in_order(cell, hay):
    """格内容按「……／…／、／；」切片、剥内引号，各片段须按顺序逐字见于 hay（截断可、改写不可）。"""
    cell = re.sub(r'[”’]\s*[“‘]', '、', cell)   # 两段引语并列（“…”“…”）视作两个片段
    frags = [strip_ws(f) for f in FRAG_SPLIT.split(INNER_QUOTES.sub('', cell)) if strip_ws(f)]
    pos = 0
    for f in frags:
        k = hay.find(f, pos)
        if k < 0:
            return False
        pos = k + len(f)
    return True

def collect_block(lines, start):
    """从 start（`> 【教师示范文】` 行）起收一整块引文，返回 (end, 段列表)。"""
    i = start + 1; ess_lines = []
    while i < len(lines):
        l = lines[i]
        if l.lstrip().startswith('>'):
            ess_lines.append(l.lstrip()[1:].strip()); i += 1; continue
        # 空行或〖PPT 页标〗行之后若仍是 `>` 行（且不是另一个 `> 【…】` 引块的开头），视为同一篇示范文的延续
        if (l.strip() == '' or l.strip().startswith('〖PPT')):
            j = i + 1
            while j < len(lines) and (lines[j].strip() == '' or lines[j].strip().startswith('〖PPT')):
                j += 1
            if j < len(lines) and lines[j].lstrip().startswith('>') and not lines[j].lstrip().startswith('> 【'):
                i = j; continue
        break
    return i, [p for p in ess_lines if p]

def main(path):
    text = pathlib.Path(path).read_text(encoding='utf-8')
    # 注释块只清空内容、不删行，行号与源文件一致
    body = re.sub(r'<!--.*?-->', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    lines = body.split('\n')
    starts = [i for i, l in enumerate(lines) if l.lstrip().startswith('>') and '【教师示范文】' in l]
    if not starts:
        stray = [i + 1 for i, l in enumerate(lines) if '【教师示范文】' in l]
        print(f'[WARN] 未找到 `> 【教师示范文】` 引块，示范文机检跳过——标注不在 `>` 引块里（lesson-structure 要求示范文用引块）'
              + (f'；非引块的 【教师示范文】 在行 {stray}' if stray else '；全文无此标注'))
        return
    blocks = []  # (start, end, paras)
    for s in starts:
        if blocks and s < blocks[-1][1]:
            continue
        e, ps = collect_block(lines, s)
        blocks.append((s, e, ps))
    # ① 以最长的一块为整篇；②③④ 对全部块的并集比对（§三 B 单点示范段与 A 整篇可并存）
    main_blk = max(blocks, key=lambda b: len(strip_ws(''.join(b[2]))))
    start, end, paras = main_blk
    essay = ''.join(paras)
    essay_ws = strip_ws(''.join(''.join(b[2]) for b in blocks))
    in_block = lambda n: any(b[0] <= n < b[1] for b in blocks)
    if len(blocks) > 1:
        print(f'[INFO] 示范文引块 {len(blocks)} 个（行 {"、".join(str(b[0] + 1) for b in blocks)}）；① 按最长块（行{start + 1}）报，②③④ 对全部块并集比对')
    m = re.search(r'([一二三四五六])[上下]-', pathlib.Path(path).name); grade = m.group(1) if m else '?'
    print(f'== 示范文机检 E · {pathlib.Path(path).name} ==')
    lens = [len(strip_ws(p)) for p in paras]
    print(f'[INFO] ① 篇幅：{len(essay_ws)} 字（去空白）／{len(paras)} 段；该级区间 {GRADE_RANGE.get(grade, "?")}（model-essay §三 A）')
    longest = max(range(len(paras)), key=lambda k: lens[k]) if paras else -1
    for k, p in enumerate(paras, 1):
        print(f'      第{k}段 {lens[k-1]:>4} 字{"  ← 最长" if k-1 == longest else ""}  ｜ {p[:22]}…')
    claims = [(n + 1, l) for n, l in enumerate(lines) if l.startswith('师：') and CLAIM_PAT.search(l)]
    print(f'[INFO] ⑥ 师话可数断言候选 {len(claims)} 行（配 ① 实数人工核，判据见记忆 model-essay-countable-claims）')
    for n, l in claims[:12]:
        print(f'      行{n}: {l[:70]}')
    quote_pat = re.compile(r'“([^”]{6,})”')
    rewritten, unmatched = [], 0
    for n, l in enumerate(lines):
        if in_block(n) or l.lstrip().startswith('>'):
            continue
        for q in quote_pat.findall(l):
            qs = strip_ws(q)
            if qs in essay_ws or frags_in_order(q, essay_ws):
                continue
            if len(qs) < 10:
                unmatched += 1; continue   # 短引句与示范文偶合 6 字即误报，不判改写
            best = 0
            for a in range(len(qs)):
                b = a + best + 1
                while b <= len(qs) and qs[a:b] in essay_ws:
                    best = b - a; b += 1
            if best >= 6 and best * 2 >= len(qs):
                rewritten.append((n + 1, q, best))
            else:
                unmatched += 1
    print(f'[INFO] ② 引文逐字审计：疑似改写 {len(rewritten)} 处（须打回，截断除外）；与示范文无关的引句 {unmatched} 处（多为③两段对照等别的材料，不计）')
    for n, q, best in rewritten:
        print(f'      行{n}: “{q[:40]}”（最长逐字命中 {best} 字）')
    tables, cur = [], []
    for n, l in enumerate(lines):
        if l.startswith('|'): cur.append((n + 1, l))
        else:
            if cur: tables.append(cur); cur = []
    if cur: tables.append(cur)
    checked = 0; misses = []
    for t in tables:
        head = t[0][1]
        if not re.search(r'示范文|原文|句子', head): continue
        cols = [c.strip() for c in head.strip('|').split('|')]
        col_idx = next((k for k, c in enumerate(cols) if re.search(r'示范文|原文|句子', c)), None)
        if col_idx is None: continue
        for n, l in t[2:]:
            cells = [c.strip() for c in l.strip('|').split('|')]
            if col_idx >= len(cells): continue
            cell = strip_ws(cells[col_idx]).strip('“”"')
            if len(cell) < 4: continue
            checked += 1
            # 「……」表示省略中段、「、；」表示并列片段：各片段须按顺序逐字见于示范文（截断可、改写不可）
            if not frags_in_order(cells[col_idx], essay_ws): misses.append((n, cells[col_idx][:40]))
    if checked == 0:
        print('[WARN] ③ 旁批表引句列比对：核 0 格——没找到表头含「示范文／原文／句子」的表；引句若走 `参考：` 行由 ② 覆盖，否则须人工核旁批表')
    else:
        print(f'[INFO] ③ 旁批表引句列比对：核 {checked} 格，不是示范文子串的 {len(misses)} 格（改写须打回）')
    for n, c in misses: print(f'      行{n}: {c}')
    anchor_sents = load_anchor_sents()
    hits = [w for w in ANCHOR_TOPICS + anchor_sents if strip_ws(w) in essay_ws]
    print(f'[INFO] ④ 笔法锚点题材／整句复用：{len(hits)} 处 {hits if hits else ""}（锚点句 {len(anchor_sents)} 条运行时取自 model-essay §四之三；对齐笔法不对齐内容）')
    print('[INFO] ⑤ 交代段粗筛（逐段句数与首句，供人核 model-essay §六 第 7 问；只报数、不立数值线）')
    for k, p in enumerate(paras, 1):
        sents = [s for s in re.split(r'[。！？]', p) if s.strip()]
        print(f'      第{k}段 {len(sents)} 句 ｜ 首句：{sents[0][:30] if sents else ""}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(0)
    main(sys.argv[1])
