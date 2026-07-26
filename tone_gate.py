# -*- coding: utf-8 -*-
"""
tone_gate —— 详案「AI 腔／语言肌理」机检门（两线共用，仓根与 check_quotes.py 同级）。

把 checklist 里可 grep 的语言类机检项收进一条命令，人工清单只留判断项：
    PYTHONUTF8=1 python tone_gate.py <详案.md> --profile picture|writing

输出分两级：
  [FAIL] 命中即不合规（对应 checklist 机检条款，判据一字不改自各规则文件），exit code 1；
  [INFO] 筛查线索（破折号计数、参考行长度、池6/池7 词频等），只报数不判、永不 fail——
         这些是「按判断执行」的配额型软规则，裁决序＝教学链条完整性＞拟真度＞密度指标，
         冷审只标不判、争议归用户（见两线 review-rubric 对应条）。

判据唯一源仍是各 skill 的 checklist / lesson-structure / SKILL / variation-pools / terminology——
本脚本只改「谁来执行」；改判据须同步本脚本。凡能从规则文件运行时解析的清单
（writing「禁止逐字复用」、picture terminology 硬替换表）一律解析、不在此双写。

预处理：剔除 <!-- --> 注释块（生图工单/真实性自检/指纹块）与 ``` 代码围栏后才检正文；
picture/writing 的 `*` 在 `## 教案提纲表` 节内豁免（首页版式化脚本的解析锚）。
"""
import argparse
import io
import os
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.abspath(__file__))
SKILLS = os.path.join(ROOT, '.claude', 'skills')

FOUR_DIM_TAGS = ['【语言运用】', '【思维能力】', '【审美创造】', '【文化自信】']


# ---------- 预处理 ----------

def load_body(md_path):
    """返回 (lines, in_outline)：注释块/代码围栏行替换为空串（保行号）；
    in_outline[i]=True 表示该行在 `## 教案提纲表` 节内（* 豁免区）。"""
    with open(md_path, encoding='utf-8') as f:
        raw = f.read().splitlines()
    lines, in_comment, in_fence = [], False, False
    for ln in raw:
        s = ln.strip()
        if not in_comment and not in_fence and s.startswith('<!--') and '-->' not in s[4:]:
            in_comment = True
            lines.append('')
            continue
        if in_comment:
            if '-->' in s:
                in_comment = False
            lines.append('')
            continue
        if s.startswith('```'):
            in_fence = not in_fence
            lines.append('')
            continue
        if in_fence:
            lines.append('')
            continue
        # 单行注释 <!-- ... -->
        ln = re.sub(r'<!--.*?-->', '', ln)
        lines.append(ln)
    in_outline, flag = [], False
    for ln in lines:
        s = ln.strip()
        if s.startswith('## '):
            flag = s.startswith('## 教案提纲表')
        in_outline.append(flag)
    return lines, in_outline


def has_cjk(s):
    return re.search(r'[一-鿿]', s) is not None


# ---------- 报告 ----------

class Report:
    def __init__(self):
        self.fails = []   # (规则名, [(行号, 摘录), ...])
        self.infos = []   # (说明, 明细行列表)

    def fail(self, rule, hits):
        if hits:
            self.fails.append((rule, hits))

    def info(self, title, detail_lines):
        self.infos.append((title, detail_lines))

    def dump(self):
        for rule, hits in self.fails:
            print(f'[FAIL] {rule}（{len(hits)} 处）')
            for no, ln in hits[:8]:
                print(f'    行{no}: {ln.strip()[:80]}')
            if len(hits) > 8:
                print(f'    … 还有 {len(hits) - 8} 处')
        for title, det in self.infos:
            print(f'[INFO] {title}')
            for d in det[:10]:
                print(f'    {d}')
            if len(det) > 10:
                print(f'    … 还有 {len(det) - 10} 条')
        if not self.fails:
            print('== tone_gate：机检全绿 ==')
        else:
            print(f'== tone_gate：{len(self.fails)} 项 FAIL ==')
        return 1 if self.fails else 0


def grep(lines, pattern, exempt=None):
    """返回 [(行号, 行)]；pattern 为已编译正则；exempt(i, line) 为 True 跳过。"""
    out = []
    for i, ln in enumerate(lines):
        if not ln:
            continue
        if exempt and exempt(i, ln):
            continue
        if pattern.search(ln):
            out.append((i + 1, ln))
    return out


# ---------- 通用检查（两档共用） ----------

def check_common(lines, in_outline, rep, profile):
    # ASCII 直引号（正文，注释/围栏已剔）
    rep.fail('ASCII 直引号 " / \'（须弯引号）', grep(lines, re.compile(r'["\']')))
    if profile == 'writing':
        # 星号仅 writing 线全文禁（picture 线正文允许成对 ** 加粗，见 CLAUDE.md §4 两线政策差异）。
        # 豁免：教案提纲表节（版式化脚本解析锚）＋ `> **可压缩预案**：…` 式引块批注
        # （title-naming §3.5 规定体例；存量另有同款「> **节奏提示**：」，按引块批注家族统一豁免）。
        rep.fail('星号 *（提纲表节与引块批注 > **…**： 外禁用）',
                 grep(lines, re.compile(r'\*'),
                      exempt=lambda i, ln: in_outline[i]
                      or re.match(r'>\s*\*\*[^*]+\*\*：', ln.strip())))
    # ASCII 下划线：路径/文件名等纯 ASCII 记号内豁免；提纲表节豁免（统编官方题目《游____》《____即景》）
    def _us_exempt(i, ln):
        if in_outline[i]:
            return True
        t = ln
        for tok in re.findall(r'[A-Za-z0-9_\\/.\-]+', t):
            if '_' in tok and ('.' in tok or '/' in tok or '\\' in tok or tok.isupper()):
                t = t.replace(tok, '')
        return '_' not in t
    rep.fail('ASCII 下划线 _（填空须全角＿）', grep(lines, re.compile(r'_'), exempt=_us_exempt))
    # HTML 样式标签（放行 <br>）
    rep.fail('HTML 样式标签（引擎不解析，原样印进 docx）',
             grep(lines, re.compile(r'<(?!br\b)[A-Za-z][^>]*>')))
    # 黑板/白板/板书
    rep.fail('黑板/板书/白板（教室无黑板白板）', grep(lines, re.compile(r'黑板|板书|白板')))
    # 四维素养标签
    rep.fail('四维素养标签（目标节已废）',
             grep(lines, re.compile('|'.join(map(re.escape, FOUR_DIM_TAGS)))))
    # 换页点与下游提示标签
    rep.fail('【PPT换页 / [可视化建议（全项目已废弃）',
             grep(lines, re.compile(r'【PPT换页|\[可视化建议')))


# ---------- picture 档 ----------

PIC_BAN_WORDS = ['侦探', '段子', '胖句子', '加料', '变身', '魔法卡片', '小秘密', '墙面张贴', '模块']
PIC_FORBIDDEN_REF = ['四个都用上了', '都用上了——']  # 另有「是看得见的；」单独查 参考： 行

def load_terminology_words():
    """解析 picture terminology.md 硬替换表第一列（单一源，不在脚本双写）。"""
    path = os.path.join(SKILLS, 'laojohn-picture-writing', 'references', 'terminology.md')
    words = []
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return words
    sec = re.search(r'## 硬替换表.*?(?=\n## |\Z)', text, re.S)
    if not sec:
        return words
    for m in re.finditer(r'^\|\s*([^|]+?)\s*\|', sec.group(0), re.M):
        w = m.group(1).strip()
        if w in ('原词', '---', '') or w.startswith('-'):
            continue
        for part in re.split(r'[／/]', w):
            part = part.strip()
            if part:
                words.append(part)
    return words


def check_picture(lines, in_outline, rep):
    check_common(lines, in_outline, rep, 'picture')
    rep.fail('禁词（SKILL 语言风格条）',
             grep(lines, re.compile('|'.join(map(re.escape, PIC_BAN_WORDS)))))
    # 期N 对外旧口径（正文；注释区已剔，那里允许内部编号）
    rep.fail('「期N」对外旧口径（对外一律 学期＋课次＋方法名）',
             grep(lines, re.compile(r'期[0-9０-９]')))
    rep.fail('年级档括注/标注（〔L1〕〔L2〕/L1 档/L2 档）',
             grep(lines, re.compile(r'〔L[12]〕|L[12]\s*档')))
    # terminology 硬替换表原词
    words = load_terminology_words()
    if words:
        rep.fail('机构自造简写（terminology 硬替换表）',
                 grep(lines, re.compile('|'.join(map(re.escape, words)))))
    # 禁止再现句式（限 参考： 行）
    ref_lines = [(i, ln) for i, ln in enumerate(lines) if ln.strip().startswith('参考：')]
    hits = [(i + 1, ln) for i, ln in ref_lines
            if any(p in ln for p in PIC_FORBIDDEN_REF) or '是看得见的；' in ln]
    rep.fail('禁止再现句式（§14：一句报全四问/一句说完两看两想）', hits)
    # 应答配对
    n_open = sum(ln.count('〔应答·') for ln in lines)
    n_close = sum(ln.count('〔应答完〕') for ln in lines)
    if n_open != n_close:
        rep.fail(f'〔应答·〕/〔应答完〕不配对（{n_open}/{n_close}）', [(0, '（计数不等）')])
    # 标记漂移
    rep.fail('标记漂移（引导句式（/师：（教师总结）/（本课总结））',
             grep(lines, re.compile(r'引导句式（|师：（教师总结）|（本课总结）')))
    # （注：）每课时 ≤3
    seg_no, counts = 0, {}
    for ln in lines:
        if ln.startswith('## 第') and '课时' in ln:
            seg_no += 1
        counts[seg_no] = counts.get(seg_no, 0) + ln.count('（注：')
    over = [(0, f'第{k}课时 {v} 条') for k, v in counts.items() if k > 0 and v > 3]
    rep.fail('（注：…）超量（>3/课时）', over)
    # 修订留痕与生成侧自检不入正文（lesson-structure §12）
    rep.fail('修订留痕/生成侧自检词（原配/拆出/规格核查，§12 不入正文）',
             grep(lines, re.compile(r'原配|拆出|规格核查')))
    # INFO：破折号计数 + 参考行超长
    dash = sum(ln.count('——') for ln in lines)
    rep.info(f'「——」正文共 {dash} 处（筛查线索：抛词——解释式约一半改句号，逐处按 §13.3 判断，'
             f'真转折/留白/枚举合法；冷审只标不判）', [])
    long_refs = [f'行{i + 1}（{len(ln.strip()) - 3}字）: {ln.strip()[:60]}'
                 for i, ln in ref_lines if len(ln.strip()) - 3 > 40 and '／' not in ln and '；' not in ln]
    if long_refs:
        rep.info('参考：单行 >40 字且无并列分隔（提示查追问链；事实罗列/多人集合豁免，人工判）', long_refs)


# ---------- writing 档 ----------

WRT_BLACKLIST = ['宛如', '犹如', '交织', '无形中', '诉说着']
POOL6_WORDS = ['先别急', '谁愿意', '谁先来', '还没写完也没关系']
POOL7_WORDS = ['立起来', '站在眼前', '活生生', '干巴巴', '流水账', '怦怦直跳']
PRAISE_WORDS = ['说得好', '太妙了', '太棒了']
MECH_WORDS = ['A 档', 'A档', '降压', '兜底', '锚点', '指纹', '台账', '零件']


def _norm(s):
    """比对归一：去空白/星号/引号类，半角标点转同类，供「禁止逐字复用」近似命中。"""
    s = re.sub(r'[\s*＊]', '', s)
    s = re.sub(r'[「」『』“”‘’"\']', '', s)
    table = str.maketrans('，。！？；：、,.!?;:', '　　　　　　　　　　　　　')
    s = s.translate(table)
    return s.replace('　', '')


def load_forbidden_phrases():
    """解析 variation-pools.md「禁止逐字复用」清单（含预防性收录，止于导演腔小节——
    导演腔与词级黑名单有专项检查）。取每条 bullet 的 「…」/`…` 串：
    含 ／ 或 / 的括号段视作备择、删除；其余括号只剥壳保内容。按标点切片后，
    取 单片段 ≥8 字 ＋ 相邻片段拼接 ≥8 字 作核心短语（近似命中口径）——
    6~7 字单片段（「遇到不会写的字」「听得见的东西」等）过泛，实测误报，弃用。
    「学生互动分享…」条属跨篇形态要求（单篇一次不违规），整条跳过、归人工 G 组。"""
    path = os.path.join(SKILLS, 'laojohn-writing-lesson', 'references', 'variation-pools.md')
    needles = {}
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return needles
    m = re.search(r'## 已知「禁止逐字复用」.*?(?=### 教师「导演腔」|## (?!#)|\Z)', text, re.S)
    if not m:
        return needles
    for bullet in re.findall(r'^- (.+)$', m.group(0), re.M):
        quoted = re.findall(r'「(.+?)」', bullet) + re.findall(r'`(.+?)`', bullet)
        if not quoted:
            continue
        src = quoted[0]
        if _norm(src).startswith(('学生互动分享', '学生自由分享')):
            continue
        # 备择括号段（含斜杠）删除；普通括号剥壳保内容
        body = re.sub(r'[（(][^（）()]*[／/][^（）()]*[)）]', '', src)
        body = re.sub(r'[（()）]', '', body)
        frags = [f for f in re.split(r'[，,、。；;：:／/…—＿_]+|\.\.\.', body) if _norm(f)]
        cands = [_norm(f) for f in frags]
        joined = [cands[i] + cands[i + 1] for i in range(len(cands) - 1)]
        for frag_n in cands + joined:
            if len(frag_n) >= 8:
                needles[frag_n] = src[:30]
    return needles


def check_writing(lines, in_outline, rep):
    check_common(lines, in_outline, rep, 'writing')
    rep.fail('词级黑名单（宛如/犹如/交织/无形中/诉说着）',
             grep(lines, re.compile('|'.join(WRT_BLACKLIST))))
    rep.fail('词级黑名单（「不仅…更…」递进套式）',
             grep(lines, re.compile(r'不仅[^。！？\n]{0,30}更')))
    # 导演腔（按出现次数计，同行多次也算多次）
    kj_re = re.compile(r'一下子?就[^\n]{0,6}看见')
    hits_kj = grep(lines, kj_re)
    n_kj = sum(len(kj_re.findall(ln)) for ln in lines)
    if n_kj > 1:
        rep.fail(f'导演腔：「一下(子)就“看见”」全篇 >1 次（共 {n_kj} 次）', hits_kj)
    rep.fail('导演腔：「平时不太/不常/不爱举手」模板句',
             grep(lines, re.compile(r'平时不[太常爱]\S{0,4}举手')))
    rep.fail('导演腔：「今天不是完成一篇作文,是要…」对举句',
             grep(lines, re.compile(r'不是[^\n。]{0,10}完成一篇作文')))
    rep.fail('机构拟人（老约翰说/老约翰老师）',
             grep(lines, re.compile(r'老约翰说|老约翰老师|我是老约翰')))
    # 内部机制名（只扫师话/参考话轮）
    mech = re.compile('|'.join(map(re.escape, MECH_WORDS)))
    hits = [(i + 1, ln) for i, ln in enumerate(lines)
            if ln.strip().startswith(('师：', '参考：')) and mech.search(ln)]
    rep.fail('内部机制名漏进师话/参考（A 档/降压/兜底/锚点/指纹/台账/零件）', hits)
    # 行首全角（ 的行级提示（（教师总结）豁免）
    rep.fail('行首全角（ 的行级提示（应改半角方括号 […] 体例）',
             grep(lines, re.compile(r'^（(?!教师总结）)'),
                  exempt=lambda i, ln: ln.strip().startswith('（教师总结）')))
    # 半角标点（中文语境；数字范围 – 箭头 → 斜杠 / 已非半角组；纯 ASCII 记号行豁免）
    def _punct_exempt(i, ln):
        return not has_cjk(ln)
    rep.fail('中文语境半角标点 ,:?!;()',
             grep(lines, re.compile(r'[,:?!;()]'), exempt=_punct_exempt))
    # 禁止逐字复用清单（运行时解析 variation-pools）
    needles = load_forbidden_phrases()
    hits = []
    for i, ln in enumerate(lines):
        if not ln:
            continue
        n = _norm(ln)
        for frag, src in needles.items():
            if frag in n:
                hits.append((i + 1, f'{ln.strip()[:50]} ←命中「{src}…」'))
                break
    rep.fail('「禁止逐字复用」清单命中（variation-pools，近似口径＝核心短语同款）', hits)
    # INFO：破折号 + 池6/池7/空夸词计数
    dash = sum(ln.count('——') for ln in lines)
    rep.info(f'「——」正文共 {dash} 处（筛查线索，逐处按 pools「破折号套式」判断；冷审只标不判）', [])
    det = []
    for w in POOL6_WORDS:
        c = sum(ln.count(w) for ln in lines)
        if c:
            det.append(f'池6 发令词「{w}」×{c}（跨篇同款须查台账，本脚本只报数）')
    for w in POOL7_WORDS:
        c = sum(ln.count(w) for ln in lines)
        if c:
            det.append(f'池7 讲评/心理词「{w}」×{c}（单篇同一说法至多两次，人工判）')
    for w in PRAISE_WORDS:
        c = sum(ln.count(w) for ln in lines)
        if c > 1:
            det.append(f'空夸词「{w}」×{c}（单篇至多一次，超出须落到具体句子）')
    if det:
        rep.info('池6/池7/空夸词计数', det)


# ---------- main ----------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md_path')
    ap.add_argument('--profile', required=True, choices=['picture', 'writing'])
    args = ap.parse_args()
    lines, in_outline = load_body(args.md_path)
    rep = Report()
    print(f'== tone_gate · {args.profile} 档 · {os.path.basename(args.md_path)} ==')
    if args.profile == 'picture':
        check_picture(lines, in_outline, rep)
    else:
        check_writing(lines, in_outline, rep)
        print('（注：本门是**新稿交付门**。存量已交付稿的「禁止逐字复用/导演腔/行首提示体例」'
              '历史命中不回溯——SKILL 批次横审：存量不强制回改、用户点名才回改重导。）')
    sys.exit(rep.dump())


if __name__ == '__main__':
    main()
