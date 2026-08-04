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
REDLINE_BAN_FALLBACK = ['真真切切', '浮现在眼前', '闪闪发光', '愿你们', '往后的日子里',
                        '被吸引着想', '留在了纸上', '有了眉目', '真切地感受到']
# 池7 形态变体：只对**确有形态变化的词族**逐族施加，不做通用模糊匹配（那会误伤）。
# (族内成员词, 正则, 显示名)；成员词会被从逐词计数里吸收，由族统一计一次，避免重复报数。
POOL7_FAMILIES = [
    (('立起来', '立不起'), r'立[得不]?起(?:来)?', '立起来/立不起'),  # 立起了一个人/立得起/立不起来
]
POOL7_PER_ITEM_CAP = 2   # pools 池7 硬规则：单篇同一说法至多两次
# PRAISE_WORDS 有意保留硬编码：pools 池6 硬规则里它嵌在散文句「空夸词(说得好/太妙了/太棒了)
# 单篇最多出现一次」中，不是结构化清单，抠词解析脆弱（改一字即静默变空）。
# ⚠ 双写位置＝variation-pools.md 池6「### 硬规则」第 2 条，改那里须同步这里。
PRAISE_WORDS = ['说得好', '太妙了', '太棒了']
PRAISE_CAP = 1
MECH_WORDS = ['A 档', 'A档', '降压', '兜底', '锚点', '指纹', '台账', '零件']
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


def _pools_text():
    path = os.path.join(SKILLS, 'laojohn-writing-lesson', 'references', 'variation-pools.md')
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
    path = os.path.join(SKILLS, 'laojohn-writing-lesson', 'references', 'lesson-structure.md')
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
    # 讲评括注禁机制词「占位」（lesson-structure §三「填空横线写法」，2026-07-31 用户拍板；
    # 同步定义在 checklist B 组附讲评条、workflow-engine 讲评模块）：横线旁的括注**直接写
    # 动作指令**（`＿＿＿（念该生最传神的一两句）`），「占位」是生成侧机制词、印进 docx 对
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
        if '不必念给学生' not in s:
            no_note.append((i + 1, s))
        j = i - 1
        while j >= 0 and not lines[j].strip():
            j -= 1
        prev = lines[j].strip() if j >= 0 else ''
        if prev.startswith('师：') and re.search(r'[：:—]$', prev):
            dangling.append((i + 1, f'{s[:26]} ←上文师话止于「{prev[-18:]}」'))
    rep.fail('悬空师话：〔…教师掌握〕上方师话以 ：/—— 收尾（⑥.1；预告了就须在师话里讲完）', dangling)
    rep.fail('〔…教师掌握〕标题缺括注「不必念给学生」（⑥.4）', no_note)
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
    for w in load_pool6_words():
        c = sum(ln.count(w) for ln in lines)
        if c:
            det.append(f'池6 发令词「{w}」×{c}（跨篇同款须查台账，本脚本只报数）')
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
        c = sum(ln.count(w) for ln in lines)
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
