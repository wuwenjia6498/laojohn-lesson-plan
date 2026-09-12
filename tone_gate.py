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
本脚本只改「谁来执行」；改判据须同步本脚本。凡能从规则文件运行时解析的**结构化清单**
（writing「禁止逐字复用」/池6 发令词/池7 替换池/红线第六条禁用词、picture terminology 硬替换表）
一律解析、不在此双写。**判断标准＝解析目标是不是一个结构化清单**（bullet 列表、替换池、带
固定标记的枚举行）：是就解析；散文句里嵌的词**不解析**——规则文件改一个字，词表就悄悄变空
且不报错，比双写更危险，那类保持硬编码 ＋ 注释注明双写位置（如 PRAISE_WORDS）。
解析一律带回落常量，规则文件缺节/改版时降级而不崩。

writing 档另有一条**全文扫**的体例项：正文机制词「占位」（讲评括注须直接写动作指令）。

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
SKILLS_PARKED = os.path.join(ROOT, '.claude', 'skills-parked')


def _skill_path(name, *parts):
    """定位 skill 内文件：先找 .claude/skills/<name>，再找 .claude/skills-parked/<name>。
    2026-09-10 曾把读书会/看图写话线 skill 停用归档到 skills-parked，次日撤回（见 CLAUDE.md §3）；
    第二处查找保留无害。两处都没有就返回 skills 下的路径，交由调用方的 except OSError 走既有回落。"""
    for base in (SKILLS, SKILLS_PARKED):
        cand = os.path.join(base, name, *parts)
        if os.path.exists(cand):
            return cand
    return os.path.join(SKILLS, name, *parts)

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

    def items(self):
        """给外部脚本（polish_writing 等）取已收集的结果：[(kind, title, lines)]，
        kind ∈ {'FAIL','INFO'}；FAIL 的 lines 是 [(行号, 行)]，INFO 的 lines 是 [str]。"""
        out = [('FAIL', rule, hits) for rule, hits in self.fails]
        out += [('INFO', title, det) for title, det in self.infos]
        return out

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
    path = _skill_path('laojohn-picture-writing', 'references', 'terminology.md')
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
    # 师话短句占比：本档**只报数、不画线**（理由与实测数据见 SHORT_RATIO_HINT_PICTURE 处注释）
    n_short, n_all, ratio, _ = scan_short_sentence_ratio(lines)
    if n_all:
        rep.info(f'师话短句占比 {ratio:.1%}（{n_short}/{n_all} 句 ≤{SHORT_SENT_MAX} 字）'
                 f'——**本档不画筛查线**：实测改过与未改的四篇完全不可分（低年级短应答受 §13.6'
                 f'「不补」清单保护、数量压过病征）。此数**只供同一篇改动前后自比**，'
                 f'不判合规、不跨篇比优劣；判据是 prose-style-benchmark.md §二的成对判据', [])


# ---------- writing 档 ----------

WRT_BLACKLIST = ['宛如', '犹如', '交织', '无形中', '诉说着']
# 池6/池7/红线第六条禁用词均运行时解析规则文件（见 load_pool6/7_words、load_redline_ban_words）；
# 下列常量仅作**解析失败时的回落值**，不是判据源，别在此增删词——增删词一律改规则文件。
POOL6_FALLBACK = ['先别急', '谁愿意', '谁先来', '还没写完也没关系']
POOL7_FALLBACK = {'A': ['立起来', '站在眼前', '活生生'],
                  'B': ['干巴巴', '流水账'], 'C': ['怦怦直跳']}
# 回落值须与规则文件同步——「浮现在眼前」已于 2026-07-31 收窄为「重新浮现」，
#   不同步会在解析降级时误伤用户手定措辞（2026-09-01 审计修正）。
REDLINE_BAN_FALLBACK = ['真真切切', '重新浮现', '闪闪发光', '愿你们', '往后的日子里',
                        '被吸引着想', '留在了纸上', '有了眉目', '真切地感受到']
# 池7 形态变体：只对**确有形态变化的词族**逐族施加，不做通用模糊匹配（那会误伤）。
# (族内成员词, 正则, 显示名)；成员词会被从逐词计数里吸收，由族统一计一次，避免重复报数。
POOL7_FAMILIES = [
    (('立起来', '立不起'), r'立[得不]?起(?:来)?', '立起来/立不起'),  # 立起了一个人/立得起/立不起来
]
POOL7_PER_ITEM_CAP = 2   # pools 池7 硬规则：单篇同一说法至多两次
# PRAISE_WORDS 有意保留硬编码：pools 池6 硬规则里它嵌在散文句「空夸词(说得好/太妙了/太棒了)
# 单篇最多出现一次」中，不是结构化清单，抠词解析脆弱（改一字即静默变空）。
# ⚠ 双写位置＝variation-pools.md 池6「### 硬规则」第 2 条「④ 反馈语不进轮换」（那条括注已回指本处），改那里须同步这里。
PRAISE_WORDS = ['说得好', '太妙了', '太棒了']
PRAISE_CAP = 1
MECH_WORDS = ['A 档', 'A档', '降压', '兜底', '锚点', '指纹', '台账', '零件', '定起点']
# 「定起点」＝2026-08-30 新增:L5–L6 起步半环改判后的内部方法名(见 workflow-engine
# 环节⑥-起步改判块)。它同「降压」一样只供 skill 内部使用——详案环节名写平实话
# (「看着构思表,定下从哪儿起笔」),师话里出现「定起点」三个字即漏。
# 池8 技法口令：口令因课而异、无法预置词表，改动态检测全篇 ≥N 次的中文短语。
# 阈值 6 是四篇存量实测定的（≥4 每篇报 10–14 条、噪声六成；≥6 每篇 2–4 条）。
# ⚠ 它**不是**池8 配额（配额＝同一短语 ≤4 次，见 pools 池8），4~5 次的漏网归人工判。
JARGON_MIN_COUNT = 6
JARGON_NGRAM = (4, 12)


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
    path = _skill_path('laojohn-writing-lesson', 'references', 'variation-pools.md')
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


def _pools_text():
    path = _skill_path('laojohn-writing-lesson', 'references', 'variation-pools.md')
    try:
        return open(path, encoding='utf-8').read()
    except OSError:
        return ''


def _section(text, title_re):
    """取 `## X` 一节全文（止于下一个同级 ##）。"""
    m = re.search(title_re + r'.*?(?=\n## (?!#)|\Z)', text, re.S)
    return m.group(0) if m else ''


def load_pool7_words():
    """解析 pools 池7 替换池 A/B/C 三类的**原词行**（`原词 · 原词 →轮换：` 那一行，
    `·` 与 `/` 分隔）。旧硬编码只有 6 词、漏了池内的 立不起/写活了/空话/空喊/心里咯噔/心软，
    实测漏检「空话 ×4」；解析后与 pools 同步为 12 词。解析不到回落。"""
    sec = _section(_pools_text(), r'## 池 7[:：]')
    out = {}
    for m in re.finditer(r'^\*\*([ABC])[.．][^\n]*\*\*\s*\n([^\n]+?)\s*→\s*轮换', sec, re.M):
        words = [w.strip() for w in re.split(r'[·・/／]', m.group(2)) if w.strip()]
        if words:
            out[m.group(1)] = words
    return out or {k: list(v) for k, v in POOL7_FALLBACK.items()}


def load_pool6_words():
    """解析 pools 池6 发令词变体池 ①②③ 的「原高频」词。
    **④ 有意不取**——pools 池6 硬规则明写「④ 反馈语不进轮换、进具体化红线」，
    由 PRAISE_WORDS 单管；两边都取会把 说得好/太妙了 重复报两遍。
    ③ 的原高频是整句（21 字），按标点切首片段——整句当计数词表抓不到任何变体。"""
    sec = _section(_pools_text(), r'## 池 6[:：]')
    out = []
    for m in re.finditer(r'^\*\*[①②③][^\n]*?[（(]原高频[:：]([^\n]*?)[)）]\*\*', sec, re.M):
        for w in re.findall(r'「(.+?)」', m.group(1)):
            frag = re.split(r'[，,。；;、]', w)[0].strip()
            if frag:
                out.append(frag)
    return out or list(POOL6_FALLBACK)


def load_redline_ban_words():
    """解析 lesson-structure §三「语言风格红线」第六条①的禁用词枚举行（顿号分隔、句号收尾）。
    ⚠ 体例锚＝`**禁用词(出现即改)**：…。`，改红线第六条的写法须同步本正则。"""
    path = _skill_path('laojohn-writing-lesson', 'references', 'lesson-structure.md')
    try:
        text = open(path, encoding='utf-8').read()
    except OSError:
        return list(REDLINE_BAN_FALLBACK)
    m = re.search(r'\*\*禁用词[（(][^）)]*[)）]\*\*[:：]([^。\n]+)', text)
    if not m:
        return list(REDLINE_BAN_FALLBACK)
    words = [w.strip() for w in re.split(r'[、,，/／]', m.group(1)) if w.strip()]
    return words or list(REDLINE_BAN_FALLBACK)


JARGON_SKELETON = re.compile(r'学生(?:互动分享|自由分享|动笔写作|动笔写)|（教师总结）|（本课总结）')

# 师话短句占比（电报体密度筛查 · 2026-08-04 立）。红线第 7 条「禁电报体压缩」是判断项、
# 不入机检，全线唯一的「加法」规则因此没有任何执行力——2026-08-04 用户逐句改稿四篇后指出
# AI 痕迹依然偏重，根因之一即此。本项**只报数、永不 fail**：短句占比高也可能是这一课确实
# 指令密集（当堂写作课时的分步问写），判合规仍归人工按 prose-style-benchmark.md 五类改法看。
# ⚠ 阈值 13% 是 2026-08-04 对全部 11 篇写作课详案实测定的，不是拍脑袋：
#   用户改过／已按基准调过的 5 篇 7.0–12.2%（推荐一个好地方 7.0、小小动物园 9.7、
#   写观察日记 10.0、猜猜他是谁 10.6、我和＿＿过一天 12.2）；
#   未经人工修订的存量 5 篇 13.7–19.2%（续写故事 13.7、这儿真美 15.9、我来编童话 16.1、
#   身边那些有特点的人 17.2、漫画的启示 19.2）。两组不重叠，分界恰好落在「有没有被人工改过」。
# ⚠ 曾试过的两条路都被实测否掉，别再走：① 方言/缩略词黑名单——「头一句/头一回」在基准篇
#   自己命中 9 次（「同一个人说，头一回人家没动」是用户保留的自然口语）；② 「末了/法子/
#   没得比」词表——残留全在教具说明、示范表格、指纹块等豁免区，正文零命中。这类病征依赖
#   语境，做不成词表，只有密度指标能分开两组。
SHORT_SENT_MAX = 7        # 句长 ≤ 该值计为短句（<8 字）
SHORT_RATIO_HINT = 0.13   # writing 档：超过即提示复看（不 fail）
# ⚠ picture 档**不画线**（2026-08-04 实测结论，别再去补一个阈值）：
#   四篇实测 <8 字占比——一上第3次（已按 prose-style-benchmark 整改）17.4%、一上第1次 18.0%、
#   二上第1次 18.1%、二上第2次 16.8%。**改过的那篇正落在三篇未改稿中间，两组完全不可分**；
#   均句长（17.4/17.0/18.8/19.5）与 <5 字占比（7.0/5.6/5.3/4.0，改过的反而最高）同样不可分。
#   根因：低年级师话的短句大半是「好」「对」「不着急」这类被 lesson-structure §13.6「不补」
#   清单明文保护的短应答，数量压过病征本身的增减；写作线能画线是因为那条线以讲解为主、
#   短应答占比低。故 picture 档只报数供同篇改动前后自比，**不得当合规门、不得跨篇比优劣**。
SHORT_RATIO_HINT_PICTURE = None


def scan_short_sentence_ratio(lines):
    """返回 (短句数, 总句数, 占比, [超短样例])；只统计 `师：` 行——`参考：` 是学生话轮，
    粗糙短口语是设计要求（红线第 7 条反向约束④），扫它会把设计当病征。
    行内 〔…〕[…]（…） 三类括注先剥掉：那是给老师读/做的提示，不是讲出口的话。"""
    sents = []
    for ln in lines:
        s = ln.strip()
        if not s.startswith('师：'):
            continue
        s = re.sub(r'^师：', '', s)
        s = re.sub(r'〔[^〕]*〕|\[[^\]]*\]|（[^）]*）', '', s)
        for part in re.split(r'[。！？；]', s):
            part = part.strip()
            if part:
                sents.append(part)
    if not sents:
        return 0, 0, 0.0, []
    short = [x for x in sents if len(x) <= SHORT_SENT_MAX]
    return len(short), len(sents), len(short) / len(sents), short


def scan_jargon(lines):
    """池8 技法口令的动态检测：统计正文中出现 ≥JARGON_MIN_COUNT 次的中文短语，返回 [(短语, 次数)]。
    口令因课而异、无法预置词表，故只报密度、不判合规——命中里必然混着课题名、材料指代、
    教学内容词等噪声，由人工剔除后再对 pools 池8 配额。
    排除：表格行/示范文引块/标题/`[…]` 舞台提示/`〔…〕` 话轮位标签/《…》/H1 课题名/固定话术骨架。"""
    title = ''
    for ln in lines:
        m = re.match(r'#\s*《(.+?)》', ln.strip())
        if m:
            title = m.group(1)
            break
    body = []
    for ln in lines:
        s = ln.strip()
        if not s or s.startswith(('|', '>', '#', '[', '〔')):
            continue
        s = re.sub(r'〔[^〕]*〕|\[[^\]]*\]|《[^》]*》', '', s)
        s = re.sub(r'^(?:师|参考)：', '', s)
        s = JARGON_SKELETON.sub('', s)
        if title:
            s = s.replace(title, '')
        body.append(s)
    lo, hi = JARGON_NGRAM
    cnt = {}
    for s in body:
        for seg in re.findall(r'[一-鿿]+', s):
            for n in range(lo, hi + 1):
                for i in range(len(seg) - n + 1):
                    g = seg[i:i + n]
                    cnt[g] = cnt.get(g, 0) + 1
    hits = {g: c for g, c in cnt.items() if c >= JARGON_MIN_COUNT}
    # 重叠归并：短语若是另一条更长命中的子串、且长者次数 ≥ 短者六成，只留长的（去 n-gram 碎片）
    out = [(g, c) for g, c in sorted(hits.items(), key=lambda x: (-len(x[0]), -x[1]))
           if not any(g != h and g in h and hits[h] >= c * 0.6 for h in hits)]
    return sorted(out, key=lambda x: -x[1])


def _pool7_line(cls, word, count, extra=''):
    """池7 的 INFO 行须把**判定结论**写出来、不只报数——上一次漏放就是因为只报数，
    读的人扫一眼就过去了（checklist E 组池7条据此要求超标项逐条处置或写明为何保留）。
    仍是 INFO、仍不 fail：配额型软规则永不升红灯（见本文件 docstring 的裁决序）。"""
    tail = f'（{extra}）' if extra else ''
    if count > POOL7_PER_ITEM_CAP:
        return (f'池7-{cls}「{word}」×{count}{tail} ⚠ 超单篇上限 {POOL7_PER_ITEM_CAP}，须改'
                f'（出路见 pools 池7 替换池；贴切>生造，优先改成具体说法而非换同义词）')
    if count == POOL7_PER_ITEM_CAP:
        return f'池7-{cls}「{word}」×{count}{tail}（上限 {POOL7_PER_ITEM_CAP}，达线）'
    return f'池7-{cls}「{word}」×{count}{tail}（上限 {POOL7_PER_ITEM_CAP}）'


# ---------- 红线第六条④⑥⑦ 与第九条：句式层候选清单（2026-08-31 立） ----------
# 立条缘由：红线 6②-⑦ 原写明「判断项、不入机检，归 checklist E 组人工判」，而 E 组措辞条
# 又于 2026-08-04 后移到冷审 Pass B，冷审按篇手动跑、覆盖不到三分之一。2026-08-31 实证取样
# 四份详案通读 92 条病灶，57% 属「规则已写但没执行」——《漫画的启示》第 1 课时格言体对举
# 实测 6 处（配额 1）、三份稿结课位全部命中 6⑥。规则判据清晰、形态固定，缺的只是「谁在什么
# 时候扫」。
#
# ⚠ 本组除预演式总结外一律 [INFO]，**只捞候选、不判决**（同 batch_ngram_scan 的定位）：
# 6⑦ 自带「教学演示位不计配额」例外，其判据是「把这句删掉，学生少学到一个可照做的东西吗」
# ——机器判不了，硬做成 FAIL 会误伤红线第 8 条要求的写法对比句（2026-08-24 冷审实测：一篇
# 5 处命中里 3 处是第 8 条的产物）。有了带行号的候选清单，人工逐条判是几秒钟的事；没有清单
# 才要通读全篇，这正是它一年没被扫过的原因。
#
# 适用范围分两档（2026-09-01 订正，此前注释与实现不符）：6④⑥⑦ 与第九条严格照红线
# 「只限师话层」——只扫 `师：` 与 `（教师总结）` 行；引出式破折号候选**另扫 `[…]`/`〔…〕`
# 提示行**（依据＝style-criteria §二.7 提示层引导句破折号同改冒号）。
# 示范文/表格/`参考：` 学生话轮一律不扫（红线明写「不得反向误伤」）。

# 不含「（本课总结）」：writing 骨架只有（教师总结），（本课总结）在 picture 档是
#   标记漂移 FAIL（check_picture），两档定性须一致（2026-09-01 审计修正）。
SHIHUA_PREFIX = ('师：', '（教师总结）')

# 6⑦ 格言体对举判断句（配额：每课时 <=1，文末附录讲评环节单独算 <=1）
MAXIM_PATTERNS = [
    (r'不是[^。！？\n]{2,28}[，,—]+\s*(?:其实说的|而)?是[^。！？\n]{2,28}', '不是A，(而)是B'),
    (r'不看[^。！？\n]{2,28}[，,—]+\s*看[^。！？\n]{2,28}', '不看X，看Y'),
    (r'不在[^。！？\n]{2,28}[，,—]+\s*(?:而)?在[^。！？\n]{2,28}', '不在A，(而)在B'),
    (r'只是[^。！？\n]{1,20}[，,][^。！？\n]{0,22}才是[^。！？\n]{1,20}', 'A只是引子，B才是主体'),
    (r'(?<!来)(?<!越)越(?!来越)[^。！？\n]{1,16}[，,]?[^。！？\n]{0,8}就?越(?!来)', '越…越…'),
]

# 第九条 预演式总结：把还没发生的课堂结果写成既成事实（2026-08-31 立）
# ⚠ 判据是**评价性完成体**，不是「都」字本身（2026-08-31 全线 17 篇实测校准）：
#   命中——「大部分同学…都想到了」「刚才这几位…都念得让人看见了」「你们观察到的都写出来了」
#   不命中——「等一会儿每个人都要在组里念」（将来时，分派任务）、「现在每个人都有事做」
#           （分派）、「每个人都给日记本写下了第一篇」（纯动作完成，本课必做任务，不是
#           对学生表现的预先评价）
# 早前版本按「每…都＋动词」宽匹配，17 篇里误报 4 条、全是将来时与任务分派，故收窄。
PREEMPTIVE_PATTERNS = [
    r'大部分同学[^。！？\n]{0,14}都',
    r'刚才这[几两]位[^。！？\n]{0,18}都',
    r'(?:每个人|每位同学|每个同学|你们|同学们|全班|大家)[^。！？\n]{0,10}都'
    r'(?:想到|做到|找到|用上|答对|说对|写出|说出|讲出|至少)',
    r'(?:每个人|每位同学|每个同学|你们|同学们|全班|大家)[^。！？\n]{0,10}都'
    r'(?:念|讲|写|说|读)得[^。！？\n]{0,10}了',
]


def _lesson_sections(lines):
    """按 `## 第N课时` 与 `## 附：` 切段，返回 [(段名, 起行idx, 止行idx)]。
    提纲表与文首不计入（那里没有师话）。"""
    marks = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('## 第') and '课时' in s:
            marks.append((i, s.lstrip('# ').strip()))
        elif s.startswith('## 附'):
            marks.append((i, s.lstrip('# ').strip()))
    out = []
    for k, (i, name) in enumerate(marks):
        end = marks[k + 1][0] if k + 1 < len(marks) else len(lines)
        out.append((name, i, end))
    return out


def _is_shihua(ln):
    return ln.strip().startswith(SHIHUA_PREFIX)


# 可改层四种起首：师话、教师总结、舞台提示 `[…]`、应答标签 `〔应答·…〕`。其余一律保护。
EDITABLE_PREFIX = SHIHUA_PREFIX + ('[', '〔应答')
_PROTECT_PREFIX = ('#', '|', '>', '〖', '参考：', '【教师示范文】',
                   '本课完。', '全课完。', '本环节完。')


def writing_protected_lines(lines, in_outline):
    """写作线「保护区」：返回 0 基行号集合，自动润色 / 方向指标计数**一律不碰**这些行。
    （2026-09-11 立 · polish_writing 与 report_direction 共用同一口径，勿各写一份。）

    立此函数的依据＝2026-09-01 网页端润色回贴的实证：148 段改动里越界 47 段——
    `参考：` 行 13（学生话轮书面化）、表格 15、页标 11、附录体例 3、示范文风格 4。
    前三类纯机械可挡，就是这里挡的。判据与 style-criteria §三保留边界、
    batch_ngram_scan.load_lines 的剥除口径对齐（那边是横审计数面，这边是改写面）。

    进保护区的行：
      - load_body 已置空的行（<!-- --> 注释块 / 指纹块 / 代码围栏）与空行、纯分隔线；
      - `## 教案提纲表` 节内（in_outline 为 True；体例归 lesson-structure §四）；
      - 行首 `#` 标题、`|` 表格、`>` 引块（示范文）、`〖` 页标、`参考：` 学生话轮、
        `【教师示范文】`、`本课完。/全课完。/本环节完。`；
      - 行首 `〔` 且不是 `〔应答`（〔教师示范·〕/〔图意〕/〔材料〕/〔三档标准·教师掌握〕/
        〔修改符号说明·教师掌握〕 都是老师「读」的信息或机检认的固定串）；
      - 含全角占位横线 `＿＿＿` 的行（讲评占位槽须保持书面规范）；
      - **兜底**：凡不以 EDITABLE_PREFIX（师：/（教师总结）/[/〔应答）起首的行也进保护区——
        未知体例宁可不改。
    """
    prot = set()
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s or in_outline[i]:
            prot.add(i)
            continue
        if set(s) <= set('-–—=·*'):
            prot.add(i)
            continue
        if s.startswith(_PROTECT_PREFIX):
            prot.add(i)
            continue
        if s.startswith('〔') and not s.startswith('〔应答'):
            prot.add(i)
            continue
        if '＿＿＿' in s:
            prot.add(i)
            continue
        if not s.startswith(EDITABLE_PREFIX):
            prot.add(i)
    return prot


def scan_lead_in_dash(lines):
    """引出式破折号候选（2026-08-31 立 · style-criteria §二.2「AI 痕迹头号形态」）。

    判据（该文件给的原判法）：**把破折号后半截删掉，句子仍完整＝插入语，保留；
    删掉就断头＝引出式，改冒号/句号**。机器用「一句内破折号成对＝插入语、单个＝引出式」
    近似它——成对是插入语的可靠标志（「这几句——A、B——只有它才有」）。

    ⚠ 立此条的直接原因＝**整体改写对这一类不稳定**（当时那道工序叫 Pass C，已撤）：同一份 prompt、同一配方，
    2026-08-31 首验《漫画的启示》把它从 36 处压到 5 处，次日《我的心爱之物》却一处没动
    （36→36），漏的正是 style-criteria 逐字点名的「第一段——“…”」形态。
    「只给目标、不给禁令清单」换来的语感，代价就是**可判定形态会看运气**。
    故按既定分工收口：**改写工序管语感，可判定的形态归机检兜底**（同预演式总结那条）。
    """
    hits = []
    for i, ln in enumerate(lines, 1):
        s = ln.strip()
        if '——' not in s or not s.startswith(SHIHUA_PREFIX + ('[', '〔')):
            continue
        for sent in re.split(r'(?<=[。！？])', s):
            if sent.count('——') == 1:
                hits.append(f'行{i}: {sent.strip()[:72]}')
    return hits


def check_writing_style_candidates(lines, rep):
    sections = _lesson_sections(lines)
    if not sections:
        sections = [('全篇', 0, len(lines))]

    # --- 6⑦ 格言体对举：按课时计数，超配额给结论 ---
    compiled = [(re.compile(p), label) for p, label in MAXIM_PATTERNS]
    detail, over = [], []
    for name, a, b in sections:
        hits = []
        for i in range(a, b):
            ln = lines[i]
            if not ln or not _is_shihua(ln):
                continue
            for rx, label in compiled:
                m = rx.search(ln)
                if m:
                    hits.append((i + 1, label, m.group(0)[:46]))
                    break
        if not hits:
            continue
        flag = ' ⚠ 超配额' if len(hits) > 1 else ''
        detail.append(f'【{name}】{len(hits)} 处（配额 1）{flag}')
        for no, label, frag in hits:
            detail.append(f'    行{no} [{label}] {frag}')
        if len(hits) > 1:
            over.append(name)
    if detail:
        head = '格言体对举判断句候选（红线6⑦ · 每课时 ≤1、文末附录单独算 ≤1）'
        if over:
            head += f'——⚠ {"／".join(over)} 超配额，须逐条判后处置'
        rep.info(head + '。**本清单只捞候选不判决**：红线6⑦「教学演示位不计配额」例外'
                 '（对举两端均为可照抄的具体写法样例／承载红线第8条三步对比的），'
                 '按「把这句删掉，学生少学到一个可照做的东西吗」逐条判——少→不计配额，'
                 '不少、只是少了一句漂亮话→照计', detail)

    # --- 6④ 三个及以上对仗分句作收束 ---
    # 红线6④管的是「作**收束**」，故只扫收束位：（教师总结）行 + 每个 ### 环节的末条师话。
    # 早前版本全量扫师话，噪声压过病征（技法三步口令「读画面、提寓意、联生活」这类并列举例
    # 会大量命中，而它们正当）。
    closing = set()
    seg_start = None
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('### ') or s.startswith('## '):
            if seg_start is not None:
                last = max((j for j in range(seg_start, i) if lines[j] and _is_shihua(lines[j])),
                           default=None)
                if last is not None:
                    closing.add(last)
            seg_start = i
    if seg_start is not None:
        last = max((j for j in range(seg_start, len(lines)) if lines[j] and _is_shihua(lines[j])),
                   default=None)
        if last is not None:
            closing.add(last)
    for i, ln in enumerate(lines):
        if ln and ln.strip().startswith(('（教师总结）', '（本课总结）')):
            closing.add(i)

    par = []
    for i in sorted(closing):
        ln = lines[i]
        if not ln or not _is_shihua(ln):
            continue
        body = ln.strip()
        for pre in SHIHUA_PREFIX:
            if body.startswith(pre):
                body = body[len(pre):]
                break
        for sent in re.split(r'[。！？]', body):
            parts = [p for p in re.split(r'[，,、；;]', sent) if p.strip()]
            if len(parts) < 3:
                continue
            lens = [len(p.strip()) for p in parts]
            if min(lens) < 3 or max(lens) > 14:
                continue
            if max(lens) - min(lens) <= 2:
                par.append(f'行{i + 1}: {sent.strip()[:56]}（{len(parts)} 分句，'
                           f'字数 {"/".join(map(str, lens))}）')
    if par:
        rep.info('三分句以上字数齐平的对仗句候选（红线6④「不得用三个及以上对仗分句作收束」）'
                 '——含并列举例的正当用法，逐条判：是收束性的金句才算，'
                 '单纯罗列要素/材料的不算', par)

    # --- 6⑥ 结课位抒情段：位置固定，直接摘出来交人判 ---
    tail = []
    for name, a, b in sections:
        last = None
        for i in range(a, b):
            if lines[i] and _is_shihua(lines[i]):
                last = i
        if last is not None:
            tail.append(f'【{name}】行{last + 1}: {lines[last].strip()[:120]}')
    if tail:
        rep.info('结课位师话（红线6⑥「结课祈愿·抒情段」——存量体检 6 篇中 5 篇命中，'
                 '是全线最普遍的抒情形态）。判据：**把这段删掉，课的完整性有没有损失**。'
                 '⚠ 本条实操从宽（style-criteria §三.2：2026-08-31 用户润色实测保留了'
                 '禁用表原例句）——**只标注、不激进删，删不删由用户逐处拍板**；'
                 '生成新稿时仍不主动写这类收束', tail)

    # --- 引出式破折号候选（style-criteria §二.2） ---
    dash_hits = scan_lead_in_dash(lines)
    if dash_hits:
        rep.info('引出式破折号候选（style-criteria §二.2「AI 痕迹头号形态」；'
                 '本清单只取「一句内单个破折号」，成对的插入语已排除）。'
                 '判据：**把破折号后半截删掉，句子还完整吗**——完整＝插入语，保留；'
                 '断头＝引出式，改冒号或直接成句（「第一段——“…”」→「第一段：“…”」）。'
                 '⚠ 改写类工序对这一类**不稳定**（2026-08-31 实测：同一配方两篇，'
                 '一篇 36→5、一篇 36→36），**整体改写跑完必须照本清单再核一遍**', dash_hits)

    # --- 第九条 预演式总结（FAIL：几无正当用法） ---
    pre_re = re.compile('|'.join(PREEMPTIVE_PATTERNS))
    hits = [(i + 1, ln) for i, ln in enumerate(lines)
            if ln and _is_shihua(ln) and pre_re.search(ln)]
    rep.fail('预演式总结：把还没发生的课堂结果写成既成事实（红线第九条；'
             '真老师不可能在稿子上预先宣布全班答对了。改成条件式或指向具体某一位）', hits)




# ---------- 术语一致性（2026-08-31 立 · 治 08-30 诊断的头号病症） ----------
# 2026-08-30 全线 17 篇通读：③ 教学用语 108 处 > ① 生僻口语 103 处，而 ③ 里又以「术语混用」
# 为主症——《缩写故事》同一组技法在「动作／方法／小方法／小技巧／小窍门／小原则／项」间换了
# 八个名字，《我的心爱之物》「妙招」10 次「写法」10 次「方法」2 次「一招」2 次指同一件事，
# 「示范文」与「范文」并存全线 9 篇命中。它比文风更硬——**老师照着上课会当场卡住，学生也
# 对不上号**。
#
# ⚠ 只有「范文」一条做 FAIL，其余一律 [INFO] 候选：是不是「同一件事的第 N 个名字」是语义
# 判断，机器分不出来。2026-08-31 实测《缩写故事》「方法×6／写法×7」并存，但其中「方法」指
# 摘删缩改四个动作、「写法」指学生的两种写法，两者本就不是一回事——按词频硬判会误伤。
# 真正的源头解法是生成侧的**术语登记**（指纹块「本篇术语表」字段，写之前先定名、全篇服从），
# 本清单只负责验证登记有没有被遵守。

# ⚠ 词表与阈值均按 2026-08-31 全线 17 篇实测校准，收紧过一轮：
#   「习作」（单元习作是专名）、「稿子」（多指学生手里那张纸）有正当分工，全篇必然并存，
#   收进来等于每篇都报、报告没人看；表格单位的「行」在中文里过泛（「写两行字」），
#   故要求次少的那种也达 MIN 次才算并存。**报告太长没人看，是「没牙齿的规则」的另一种死法。**
# 元组＝(组名, 词表, 并存种数门槛 min_kinds, 单词最低出现次数 min_count)。
# min_count=2（2026-09-01 立）：出现 1 次的词不算并存成员——实测「技法统称」组曾 16/17 篇
# 恒亮，多因「本事×1」「路子×1」类单次噪声；偶现一次是行文自然波动，不是术语混用。
TERM_GROUPS = [
    ('技法统称', ['写法', '方法', '法子', '本事', '妙招', '窍门', '路子', '招数',
                  '要领', '诀窍', '小技巧', '小原则'], 2, 2),
    ('文体称谓', ['作文', '文章', '文稿', '片段'], 3, 2),
]
TABLE_UNIT_MIN = 3
TABLE_UNIT_PATTERNS = [
    ('栏', r'[这那每]\s*一?\s*栏|[一二三四五六七八九十两\d]\s*栏'),
    ('格', r'[这那每]\s*一?\s*格|[一二三四五六七八九十两\d]\s*格'),
    ('行', r'[这那每]\s*一?\s*行(?![为走人业列])|[一二三四五六七八九十两\d]\s*行(?![为走人业列])'),
]


def check_terminology_consistency(lines, rep):
    # 「范文」→ 全线统一用「示范文」（2026-08-30 全线改 15 处）。注释块/指纹块已由
    # load_body 清空，故元描述里的「一整篇范文」不会误报。
    rx = re.compile(r'(?<!示)范文')
    rep.fail('术语不统一：独立的「范文」（全线统一用「示范文」，'
             '体例单一源＝title-naming §四之二）',
             grep(lines, rx))

    det = []
    for name, words, min_kinds, min_count in TERM_GROUPS:
        found = []
        for w in words:
            hits = [(i + 1, ln) for i, ln in enumerate(lines) if ln and w in ln]
            c = sum(ln.count(w) for _, ln in hits)
            if c >= min_count:
                found.append((w, c, hits[0][0]))
        if len(found) >= min_kinds:
            cells = '／'.join(f'「{w}」×{c}(首现行{no})' for w, c, no in
                             sorted(found, key=lambda x: -x[1]))
            det.append(f'{name}：{len(found)} 种并存 —— {cells}')
    units = [(u, len(re.findall(pat, '\n'.join(lines)))) for u, pat in TABLE_UNIT_PATTERNS]
    units = [(u, c) for u, c in units if c >= TABLE_UNIT_MIN]
    if len(units) >= 2:
        det.append('表格单位：' + '／'.join(f'「{u}」×{c}' for u, c in units)
                   + ' —— 同一张表的单位须前后一致（栏／格／行三选一）')
    if det:
        rep.info('术语一致性候选（2026-08-30 诊断头号病症：同一件事换名字，'
                 '老师照着上课会卡住、学生对不上号）。⚠ **只捞候选不判决**——'
                 '并存本身不等于混用（「方法」指四个动作、「写法」指学生的两种写法，'
                 '本就不是一回事）。逐条问一句：**这几个词指的是不是同一件事？**'
                 '是 → 挑一个、全篇统一，并回填指纹块「本篇术语表」字段', det)


def check_writing(lines, in_outline, rep):
    check_common(lines, in_outline, rep, 'writing')
    check_writing_style_candidates(lines, rep)
    check_terminology_consistency(lines, rep)
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
    rep.fail('内部机制名漏进师话/参考（A 档/降压/定起点/兜底/锚点/指纹/台账/零件）', hits)
    # 讲评括注禁机制词「占位」（lesson-structure §三「填空横线写法」，2026-07-31 用户拍板；
    # 同步定义在 checklist B 组附讲评条、workflow-engine 讲评模块）：横线旁的括注**直接写
    # 动作指令**（`＿＿＿（读该生最传神的一两句）`），「占位」是生成侧机制词、印进 docx 对
    # 上课老师是噪声，故正文检索应为零。上面那条 MECH_WORDS 只扫 师：/参考： 行，而「占位」
    # 也出现在选稿列表与 blockquote 提示里，故本条**全文扫**。误伤已核：指纹/生图工单等
    # <!-- --> 块已由 load_body 清空；`【图位:编号】` 与示范文数据占位的规范写法
    # 「（此处数据以…为准）」都不含「占位」二字。2026-08-01 补：此前三道关（机检无规则、
    # checklist 埋在超长复合条中段、rubric 无判据）全漏，四篇存量带前缀交付。
    rep.fail('正文出现机制词「占位」（讲评括注应直接写动作指令，见 §三「填空横线写法」）',
             grep(lines, re.compile('占位')))
    # 师话书面抒情禁用词（lesson-structure §三 红线第六条①）——**只扫 `师：` 行**：不扫 `参考：`，
    # 更不像 WRT_BLACKLIST 那样全文 grep——示范文里写「浮现」「留在纸上」可能正是正当的描写示范，
    # 全文扫会直接误伤环节④的示范文（红线第六条明写「适用范围只限师话层，不得反向误伤」）。
    ban_re = re.compile('|'.join(map(re.escape, load_redline_ban_words())))
    rep.fail('师话书面抒情禁用词（红线第六条①；只扫 师： 行，示范文/表格/提示段不扫）',
             [(i + 1, f'{ln.strip()[:44]}… ←命中「{"／".join(dict.fromkeys(ban_re.findall(ln)))}」')
              for i, ln in enumerate(lines)
              if ln.strip().startswith('师：') and ban_re.search(ln)])
    # 教师掌握块的口语转述义务（§三「参考：标签纪律」⑥.1 悬空师话 / ⑥.4 括注缺失）——
    # 这是体例/结构检查、不是配额，故进 FAIL 级。
    dangling, no_note = [], []
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not re.search(r'〔[^〕]*教师掌握[^〕]*〕', s):
            continue
        if not re.search(r'不必[念读]给学生', s):   # 0831 方向 念→读 后两写法并认
            no_note.append((i + 1, s))
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        prev = lines[j].strip() if j >= 0 else ''
        if prev.startswith('师：') and re.search(r'[：:—]$', prev):
            dangling.append((i + 1, f'{s[:26]} ←上文师话止于「{prev[-18:]}」'))
    rep.fail('悬空师话：〔…教师掌握〕上方师话以 ：/—— 收尾（⑥.1；预告了就须在师话里讲完）', dangling)
    rep.fail('〔…教师掌握〕标题缺括注「不必念给学生／不必读给学生」（⑥.4）', no_note)
    # 行首全角（ 的行级提示（（教师总结）豁免）
    rep.fail('行首全角（ 的行级提示（应改半角方括号 […] 体例）',
             grep(lines, re.compile(r'^（(?!教师总结）)'),
                  exempt=lambda i, ln: ln.strip().startswith('（教师总结）')))
    # 半角标点（中文语境；数字范围 – 箭头 → 斜杠 / 已非半角组；纯 ASCII 记号行豁免）
    # 另豁免 `【图位:编号｜图注】` 占位内部的半角冒号：那是 insert_images_docx 的跨技能
    # 契约写法（读书会/看图写话/写作课三线同款），不是中文行文里的标点。只剥占位本身——
    # 同一行占位之外若还有半角标点，照报不误。
    def _punct_exempt(i, ln):
        if not has_cjk(ln):
            return True
        return not re.search(r'[,:?!;()]', re.sub(r'【图位[：:][^】]*】', '', ln))
    rep.fail('中文语境半角标点 ,:?!;()',
             grep(lines, re.compile(r'[,:?!;()]'), exempt=_punct_exempt))
    # 禁止逐字复用清单（运行时解析 variation-pools）
    needles = load_forbidden_phrases()
    if not needles:
        print('[WARN] 「禁止逐字复用」清单解析为 0 条——variation-pools.md 的节标题「## 已知「禁止逐字复用」」或止于「### 教师「导演腔」」的锚可能被改，本项机检等于没跑')
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
    # 短串硬命中（2026-09-01 立）：pools 里为进机检而显式单列、却低于 load_forbidden_phrases
    # >=8 字门槛的串——门槛会把它们静默丢弃（正是 docstring 警告的那类静默失效）。
    # 逐字口径、只扫师话层；词表极小、逐条有出处，增删同步 pools 对应 bullet。
    SHORT_FORBIDDEN_EXACT = {'确实不糙': 'pools 单列条·四篇复发族第四形态'}
    sf_hits = [(i + 1, ln.strip()[:50] + ' <-命中[' + w + ']') 
               for i, ln in enumerate(lines)
               if ln and ln.strip().startswith(SHIHUA_PREFIX)
               for w in SHORT_FORBIDDEN_EXACT if w in ln]
    rep.fail('「禁止逐字复用」短串硬命中（<8 字显式单列条，逐字口径）', sf_hits)
    # INFO：破折号 + 池6/池7/空夸词计数
    dash = sum(ln.count('——') for ln in lines)
    rep.info(f'「——」正文共 {dash} 处（筛查线索，逐处按 pools「破折号套式」判断；冷审只标不判）', [])
    det = []
    # 池6 与空夸词只扫师话层（2026-09-01 收窄）：此前全文 count，「先别急」落在示范文
    #   正文与旁批表被计入，measurement-ledger 数据点 10/11/12 三次记录同一误报——
    #   「有牙齿但咬错地方」。口径同红线 6① 机检（lesson-structure §三红线第 6 条①）。
    shihua = [ln for ln in lines if ln and ln.strip().startswith(SHIHUA_PREFIX)]
    for w in load_pool6_words():
        c = sum(ln.count(w) for ln in shihua)
        if c:
            det.append(f'池6 发令词「{w}」×{c}（只计师话层；跨篇同款须查台账，本脚本只报数）')
    pool7 = load_pool7_words()
    fam_members = {w for members, _, _ in POOL7_FAMILIES for w in members}
    for cls in ('A', 'B', 'C'):
        for w in pool7.get(cls, []):
            if w in fam_members:
                continue        # 同族词由下面的族正则统一计一次，避免「立起来」「立不起」重复报
            c = sum(ln.count(w) for ln in lines)
            if c:
                det.append(_pool7_line(cls, w, c))
    for members, pat, label in POOL7_FAMILIES:
        cls = next((k for k, v in pool7.items() if set(members) & set(v)), 'A')
        rx = re.compile(pat)
        c = sum(len(rx.findall(ln)) for ln in lines)
        if c:
            forms = sorted({m.group(0) for ln in lines for m in rx.finditer(ln)})
            det.append(_pool7_line(cls, label, c, extra='实际形态：' + '／'.join(forms)))
    for w in PRAISE_WORDS:
        c = sum(ln.count(w) for ln in shihua)
        if c > PRAISE_CAP:
            det.append(f'空夸词「{w}」×{c} ⚠ 超单篇上限 {PRAISE_CAP}，须改'
                       f'（其余改成「复述+点一句」，落到学生的具体句子上）')
    if det:
        rep.info('池6/池7/空夸词计数（池7 已带超标结论；⚠ 项须逐条处置或写明为何保留，不得只看不动）',
                 det)
    # 师话短句占比（电报体密度筛查，见常量处的实测校准与两条已否掉的路子）
    n_short, n_all, ratio, samples = scan_short_sentence_ratio(lines)
    if n_all:
        verdict = ('⚠ 高于筛查线，按 prose-style-benchmark.md §二五类改法逐处复看'
                   if ratio > SHORT_RATIO_HINT else '在基准区间内')
        rep.info(f'师话短句占比 {ratio:.1%}（{n_short}/{n_all} 句 ≤{SHORT_SENT_MAX} 字）'
                 f'——筛查线 {SHORT_RATIO_HINT:.0%}，{verdict}。'
                 f'只报数不判：指令密集的课时天然偏高，判据仍是「读出声像不像真老师顺嘴讲」',
                 [f'最短的几句：' + '／'.join(sorted(set(samples), key=len)[:8])] if samples else [])
    # 池8 技法口令密度（动态检测，无预置词表）
    jargon = scan_jargon(lines)
    if jargon:
        cells = [f'「{g}」×{c}' for g, c in jargon]
        rows = ['  '.join(cells[i:i + 5]) for i in range(0, len(cells), 5)]
        rep.info(f'技法口令高密度项（脚本只报全篇 ≥{JARGON_MIN_COUNT} 次；规则配额为同一短语 ≤4 次'
                 f'——4~5 次的漏网须人工判，机检全绿 ≠ 本条合规。'
                 f'下列含课题名/材料指代等噪声，先剔除再对 pools 池8 配额）', rows)


# ---------- main ----------

# ---------- 方向指标（2026-09-01 立 · --baseline） ----------
# 立此条的直接原因：2026-08-31 那道 Pass C（整篇师话重写，只给一句话目标）在《我的心爱之物》
# 上**把方向跑反了**——口语词 82→105，甚至把原稿的「现在」改成了「这会儿」——而当时的验收
# （护栏零侵入 ＋ 机检全绿）**全部通过**。教训：**护栏对、机检绿，不等于方向对**。
#
# ⚠ 这批词做不成禁令表（`prose-style-benchmark.md` 2026-08-04 已实测否掉：「头一回」在基准篇
# 自己命中 9 次，是用户保留的自然口语）。但作为**同一篇改前改后的相对增减**是成立的：
# 它不判定单个词该不该留，只回答「这一轮整体朝哪个方向走」。同一批词，当禁令表无效、
# 当方向指标有效——同仓内既有判据「这类病征依赖语境，只有密度指标能分开两组」。
#
# 实测校准（2026-09-01 复测 · 当时 21 词表＋剥注释/引块/参考行的计数面；
#   ⚠ 2026-09-11 词表补 4 词、计数面改为保护区口径，复测数据见本块末尾「0911 复测」；
#   词表或计数面再变动时须重测本块，过期快照曾在 0901 审计被点名）：
#   《猜猜他是谁》网页端润色     22 → 6   ✓ 下降 73%
#   《漫画的启示》Pass C         32 → 22  ✓ 下降 31%
#   《我的心爱之物》网页端回贴   30 → 5   ✓ 下降 83%
#   《我的心爱之物》Pass C 作废版 30 → 45  ⚠ 反向 ← 本参数就是为抓住这种情况而立
#   （事故原始口径为 82→105：16 词表·全文计数，见 memory 与 detail-review 留痕）

# 「劲儿」「本事」已移出（2026-09-01 审计）：二者是 style-criteria §三.1 明载的示范文
#   保留项（「风风火火的劲儿」「画画的本事」），留在表里会成为永不下降的地板、
#   或反过来诱导去改保留边界。计数面收窄见 report_direction 预处理。
COLLOQUIAL_WORDS = ['这会儿', '哪儿', '那儿', '咱们', '干什么', '一回', '几回', '念',
                    '块钱', '挺', '里头', '有的是', '说说看', '点子上', '搁',
                    # ↓ 2026-09-01 从 framework §7.8 机械自检清单收编
                    '宝贝', '玩意儿', '待会儿', '等会儿', '脑子里', '蹦出',
                    # ↓ 2026-09-11 补：七轮人工润色统计里的四个最大宗（你们→大家 121 处/10 篇、
                    #   挑→选 36、别→不要 22、跟→和 25）此前不在表内，方向指标「双降」与
                    #   「你们 18 处仍在」曾并存——指标测不到它们，就等于没测。
                    '你们', '挑', '别', '跟']

# 多义字的计数排除（只管方向指标的计数，不是改写规则；改写规则的排除表见 polish_rules.py）
_COLLOQUIAL_EXCLUDE = {
    '别': re.compile(r'别(?=[的人处出致名号称样扭针])|(?<=[区差特个类级性告各派])别'),
    '跟': re.compile(r'跟(?=[着上前读进随头脚])'),
    '挑': re.compile(r'挑(?=[战剔起动担刺衅明食])|(?<=专)挑'),
}


def _count_colloquial(text):
    n = 0
    for w in COLLOQUIAL_WORDS:
        c = text.count(w)
        ex = _COLLOQUIAL_EXCLUDE.get(w)
        if ex is not None:
            c -= len(ex.findall(text))
        n += max(c, 0)
    return n


def report_direction(md_path, baseline_path, do_print=True):
    """把「改前 vs 改后」的方向指标打出来，并返回 (rows, warn)。只报数不 fail——判据仍是人读，
    但方向反了必须显眼，否则会像 2026-08-31 那次一样被「机检全绿」盖过去。

    计数面（2026-09-11 起）＝ writing_protected_lines 之外的行（师话/教师总结/舞台提示/应答标签），
    与 polish_writing 的改写面同一口径：此前只剥注释、`> ` 引块、`参考：` 行，**表格与页标不剥**，
    自动润色若误改了表格里的口语词，方向指标会把越界当成绩。
    第三指标「保护区改动行数」逐行比对 base/cur 的保护行，须为 0——它答的是「有没有碰禁区」，
    与前两项答的「朝哪个方向走」互补；两份文件行数不等时按较短者比、差额计入。
    """
    def _load(path):
        lines, in_outline = load_body(path)
        prot = writing_protected_lines(lines, in_outline)
        raw = io.open(path, encoding='utf-8').read().splitlines()
        return lines, prot, raw
    cur_lines, cur_prot, cur_raw = _load(md_path)
    base_lines, base_prot, base_raw = _load(baseline_path)
    cur = chr(10).join(ln for i, ln in enumerate(cur_lines) if i not in cur_prot)
    base = chr(10).join(ln for i, ln in enumerate(base_lines) if i not in base_prot)
    rows, warn = [], False
    for label, fn in (
        ('口语词合计', _count_colloquial),
        ('破折号 ——', lambda t: t.count('——')),
    ):
        b, a = fn(base), fn(cur)
        if a > b:
            warn = True
            verdict = f'⚠ 反向 +{a - b}'
        elif a < b:
            verdict = f'✓ 下降 {b - a}（{100 * (b - a) / b:.0f}%）' if b else '✓'
        else:
            verdict = '持平'
        rows.append(f'{label}：改前 {b} → 改后 {a}　{verdict}')
    # 第三指标：保护区改动行数——把两稿的保护行各取成序列做 SequenceMatcher 对齐，
    # 只数对不上的保护行（改写/删除/新增），可改层插入或删除行不会连累它
    #（2026-09-11 改：此前按行号硬对齐，可改层多插三行就把后面全部保护行报成改动）。
    import difflib as _difflib
    base_idx = sorted(base_prot)
    base_p = [base_raw[i] for i in base_idx if i < len(base_raw)]
    cur_p = [cur_raw[i] for i in sorted(cur_prot) if i < len(cur_raw)]
    sm = _difflib.SequenceMatcher(None, base_p, cur_p, autojunk=False)
    changed, extra = [], 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == 'equal':
            continue
        changed.extend(base_idx[k] + 1 for k in range(i1, i2) if k < len(base_idx))
        extra += max(0, (j2 - j1) - (i2 - i1))
    total = len(changed) + extra
    if total:
        warn = True
        note = f'⚠ 非 0（改前行 {", ".join(map(str, changed[:8]))}' + ('…' if len(changed) > 8 else '') +                (f'；新增保护行 {extra}' if extra else '') + '）'
    else:
        note = '✓ 0'
    rows.append(f'保护区改动行数：{total}　{note}')
    if do_print:
        head = '方向指标（vs %s）' % os.path.basename(baseline_path)
        if warn:
            head += ' ⚠ **有指标不降反升或碰了保护区——这一轮的改写方向可能反了，逐处复看再交付**'
        print('[INFO] ' + head)
        for r in rows:
            print('    ' + r)
    return rows, warn


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md_path')
    ap.add_argument('--profile', required=True, choices=['picture', 'writing'])
    ap.add_argument('--baseline', help='改前稿 .md：给出后追加方向指标（口语词/破折号的前后增减）。改写类工序跑完必看——护栏对、机检绿，不等于方向对。')
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
    code = rep.dump()
    if args.baseline:
        print()
        report_direction(args.md_path, args.baseline)
    sys.exit(code)


if __name__ == '__main__':
    main()
