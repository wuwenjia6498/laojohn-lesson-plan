# -*- coding: utf-8 -*-
"""
polish_rules —— 写作课详案「确定性润色」规则表与引擎（polish_writing.py 的数据层）。

    from polish_rules import RULES, apply_rules
    new_line, hits = apply_rules(line, layer, RULES, term_strings, tier='A')

为什么有这张表（2026-09-11 立）：git 里 7 轮、12 篇、1789 行人工润色统计，改动几乎全是词句层——
`——`→`：`169 处/10 篇、`你们`→`大家`121/10、`念`→`读`104/11、`儿`→`里`66/8、`挑`→`选`36、
`跟`→`和`25、`得`→`要`23、`别`→`不要`22、提示层`老师`→`教师`21。这些改法 style-criteria 里早写着，
但冷审 agent 逐处裁量、一篇 18 处「你们」只动 3 处；机器做这一层，人只接残余。

三条红线：
  1. **本表只收已定案、可机械判定的替换**；需要语境判断的（生造词、中心宾语残缺、导演腔）不进来。
     新增规则须同步 style-criteria §二（那边是判据源，这边是执行位）。
  2. **保护区由 tone_gate.writing_protected_lines 决定，本文件不管行级取舍**；行内的弯引号段、
     书名号段、占位横线 ＿、指纹块「本篇术语表」里的串，由本文件的掩蔽机制挡住：
     quote_exempt=True 的规则不进引号（学生话、示范句原样引用），书名号/占位/术语串对所有规则一律掩蔽。
  3. **每条规则的 exclude 是它的陷阱清单**——新加规则先想「这个字还有什么别的用法」，
     宁可漏改不可误改（漏的人工还能补，误改会静默进 docx）。

layer：'shihua'＝`师：`/`（教师总结）` 行；'hint'＝`[…]`/`〔应答·…〕` 提示行；'both'＝两层都跑。
tier：'A' 默认开；'B' 须 `--tier B` 显式开（多义字，误改风险高）。

⚠ 本文件里的弯引号、私用区填充字符一律写成 \\u 转义——Write 工具与部分编辑器会把弯引号
  改成 ASCII 直引号，写成转义就不受影响（见 memory write-tool-normalizes-curly-quotes）。
"""
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

LQ, RQ = '“', '”'          # 弯双引号
LSQ, RSQ = '‘', '’'        # 弯单引号
MASK_A, MASK_B = '', ''  # 相邻保护段交替用两个填充字符，还原时才分得开
UL = '＿'                        # 全角占位横线 ＿


@dataclass
class Rule:
    id: int
    name: str
    pattern: Optional[str]                 # 正则；None 时用 func
    repl: str = ''                         # 替换串（可用 \\1）
    layer: str = 'both'                    # shihua | hint | both
    exclude: List[str] = field(default_factory=list)   # 命中若与这些正则重叠即跳过（±6 字窗口）
    sentence_exclude: Optional[str] = None # 命中所在句已含此串则跳过
    quote_exempt: bool = True              # True＝不进弯引号段
    tier: str = 'A'
    func: Optional[Callable[[str], Tuple[str, List[Tuple[str, str]]]]] = None
    note: str = ''


# ---------- 规则 1：引出式破折号 ----------

def _dash_rule(text):
    """引出式 `——` 改冒号/句号；成对（插入语）保留。判法复用 tone_gate.scan_lead_in_dash：
    按 `。！？` 切句，一句内恰好一个 `——` 视为引出式。后接行尾 / 右引号 / `〗` / 右括号 → `。`
    （悬念收束）；否则 → `：`；若破折号前已是 `，`/`：`/句末标点，只删破折号。
    ⚠ 引号内的破折号已被掩蔽（示范句自身的破折号不动）；`[…]：…——` 提示层引导句同改冒号。"""
    hits, out = [], []
    for sent in re.split(r'(?<=[。！？])', text):
        if sent.count('——') != 1:
            out.append(sent)
            continue
        i = sent.index('——')
        before, after = sent[:i], sent[i + 2:]
        tail = after.strip()
        if not tail or tail[0] in (RQ + RSQ + '〗）]〕'):
            rep = '。'
        elif before and before[-1] in '，：。！？':
            rep = ''
        elif tail.startswith(('就像', '就是', '比如', '例如', '像', '也就是', '也是', '这', '那')):
            rep = '，'          # 破折号后接补充说明而非引出下文，冒号会生硬
        else:
            rep = '：'
        out.append(before + rep + after)
        hits.append(('——', rep or '(删)'))
    return ''.join(out), hits


RULES: List[Rule] = [
    Rule(1, '引出式破折号改冒号/句号', None, func=_dash_rule, layer='both', quote_exempt=True,
         note='成对插入语保留；引号内不动；后接行尾或右引号→句号，否则→冒号'),
    Rule(2, '你们→大家', r'你们', '大家', layer='shihua', quote_exempt=True,
         exclude=[r'你们(?:两个|俩|几个|组|这一组|小组|谁|中间|之间|之中|语文书|课本|班|当中|里|学校|这个单元|这一单元|这个学期|年级|老师|自己)'],
         sentence_exclude='大家',
         note='特指小群体（你们两个/你们组）、所属关系（你们学校/你们这个单元/你们语文书）、关系义（你们之间＝你和它之间，配套侧 0915 实测误改）不改；同句已有「大家」不改，防「大家…大家」'),
    Rule(3, '念→读', r'念', '读', layer='both', quote_exempt=True,
         exclude=[r'念头|纪念|念书|想念|念念|念叨|悬念|概念|观念|信念|留念|思念|挂念|默念|念想|惦念|怀念'],
         note='只改「朗读」义；名词义（念头/概念）与「念念不忘」不动。〔…教师掌握（不必念给学生）〕行在保护区'),
    Rule(4, '这儿/那儿/哪儿→这里/那里/哪里', r'([这那哪])儿', r'\1里', layer='both', quote_exempt=True,
         note='《这儿真美》靠书名号掩蔽；一会儿/劲儿等不在模式内（待会儿见规则 16）'),
    Rule(5, '挑→选', r'挑(?=[一二两三几出最那这好])', '选', layer='both', quote_exempt=True,
         exclude=[r'挑战|挑剔|挑起|挑动|挑担|挑刺|挑衅|挑明|挑食|专挑'],
         note='术语表串（如技法名「挑一件只有它才遇得上的事」）已整段掩蔽；「专挑」留给人工'),
    Rule(6, '跟→和', r'跟', '和', layer='both', quote_exempt=True,
         exclude=[r'跟着|跟上|跟不上|跟得上|跟读|跟前|跟进|跟随|跟头|跟脚|跟我|跟不住|跟得住|紧跟|鞋跟|脚跟|高跟|后跟|跟部',
                  r'跟[去来到没不了过住紧牢]'],
         note='只改介词「和」义；动词义（跟着/跟上/跟读/跟去/跟没跟上）不动——「跟去看」「跟没跟上」是 0915 配套侧实测误改'),
    Rule(7, '别→不要', r'别', '不要', layer='shihua', quote_exempt=True,
         exclude=[r'(?<=[区差特个类级性告各派分辨识久离惜送临阔永辞诀话作拜])别', r'别(?=[的人处出致名号称样扭针在有字])'],
         note='区别/别的/别人/告别/别在（笔别在头发上）不动；离别义前字整族排除（久别重逢/惜别/送别/阔别/诀别…）——2026-09-15 五上四实测「久别重逢」被改成「久不要重逢」；「别急」→「不要急」'),
    Rule(8, '得→要（必须义）', r'得(?=[先再把去写说想找留记补换改选站坐拿])', '要', layer='shihua',
         quote_exempt=True, tier='B',
         exclude=[r'(?<=[觉写看听读说记跑做念画讲想吃玩改变显认懂来出])得',
                  r'得到|得出|得分|得意|得了|得很|得多|得好|得住|不得|获得|值得|懂得|舍不得|来得及|记得|晓得|认得|使得|免得|省得|难得|非得'],
         note='Tier B。「得」三义（dei 必须 / de 补语 / de 获得），只改必须义；前字排除补语用法，默认关'),
    Rule(9, '提示层 老师→教师', r'老师', '教师', layer='hint', quote_exempt=True,
         exclude=[r'老师们|漫画老师|语文老师|[]老师|老师说的话'],
         note='只在 [ 与 〔应答 起首的提示行；师话里老师自称「老师」不动；带引号的“漫画”老师靠引号掩蔽'),
    Rule(10, '头一回→第一次', r'头一回', '第一次', layer='both', quote_exempt=True),
    Rule(11, 'N回→N次', r'([一两几这那每上下])回(?![来去到头答家忆顾应收想信声校合事])', r'\1次',
         layer='both', quote_exempt=True,
         note='回头/回答/回家/回想/回顾/回收/一回事 等由 lookahead 排除'),
    Rule(12, '用不着→不必', r'用不着', '不必', layer='both', quote_exempt=True),
    Rule(13, '咱们→我们', r'咱们', '我们', layer='both', quote_exempt=True),
    Rule(14, '要是→如果', r'(?<![只需一二三四也还都更总先再仍定须得必务])要是', '如果', layer='both', quote_exempt=True,
         note='「只要是」「需要是」「仍要是老师编的」「一要…二要是你自己想的」（要＋是）不动；「仍要是」是 0915 配套侧实测误改'),
    Rule(15, '头一篇/句/段/个→第一…', r'(?<![开抬从到起低回])头一(?=[篇句段个次条张])', '第一', layer='both', quote_exempt=True,
         note='「开头一句」「开头一次」「抬头一看」里的「头」是名词/动词残部，不是「头一＝第一」——0915 配套侧实测「开头一句→开第一句」误改 9 处'),
    Rule(16, '待会儿/等会儿→等一下', r'(?:待会儿|等会儿|待会|等会)', '等一下', layer='both', quote_exempt=True,
         note='不改成「接下来」（那需要看语境）'),
    Rule(17, '十有八九→往往', r'十有八九', '往往', layer='both', quote_exempt=True),
    Rule(18, '句末 就行→即可', r'就行(?:了)?(?=[。！])', '即可', layer='both', quote_exempt=True,
         note='只改句末；句中「就行了吗」不动'),
    Rule(19, '单字动词双音化', r'(?<!一)([想说看听试读数比])\1(?:看)?(?!一|自己)', r'\1一\1', layer='shihua',
         quote_exempt=True,
         exclude=[r'数数字|看看看'],
         note='想想→想一想、说说看→说一说、试试→试一试；名词「数数」少见于师话，命中后人工复看'),
    Rule(20, '吧？→吗？', r'([了对是懂会没]|明白|清楚)吧？', r'\1吗？', layer='shihua', quote_exempt=True,
         note='只在确认问（想到了吧？→想到了吗？）；「开始吧？」「好吧？」不动'),
    Rule(21, '句首 当然，删', r'(?:(?<=师：)|(?<=[。！？；]))当然，', '', layer='shihua', quote_exempt=True,
         note='「好，」不删（style-criteria §三.5 用户保留「好，请停笔。」）'),
    Rule(22, '这会儿/那会儿→现在/那时', r'这会儿', '现在', layer='both', quote_exempt=True,
         note='style-criteria §六①-a 地域词；「那会儿」语境多变，留人工'),
]


# ---------- 引擎 ----------

def _spans(text, quote_exempt, term_strings):
    """返回须掩蔽的 [(start, end)]：术语串（先）、书名号段、占位横线连写、按需弯引号段。"""
    spans = []
    cands = set()
    for t in term_strings:
        if len(t) < 2:
            continue
        cands.add(t)
        # 技法名在正文里常以变体出现（「挑一件只有它才遇得上的事，把这一件写详细」），
        # 连同 >=4 字的前缀一起掩蔽，宁可多掩不误改术语
        for k in range(4, len(t)):
            cands.add(t[:k])
    for t in sorted(cands, key=len, reverse=True):
        for m in re.finditer(re.escape(t), text):
            spans.append(m.span())
    for rx in (r'《[^》]*》', UL + '+'):
        for m in re.finditer(rx, text):
            spans.append(m.span())
    if quote_exempt:
        for rx in (LQ + '[^' + RQ + ']*' + RQ, LSQ + '[^' + RSQ + ']*' + RSQ):
            for m in re.finditer(rx, text):
                spans.append(m.span())
    spans.sort()
    merged = []
    for s, e in spans:
        if merged and s < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(e, merged[-1][1]))
        else:
            merged.append((s, e))
    return merged


def _mask(text, spans):
    out, pos, fill, keep = [], 0, MASK_A, []
    for s, e in spans:
        out.append(text[pos:s])
        out.append(fill * (e - s))
        keep.append(text[s:e])
        fill = MASK_B if fill == MASK_A else MASK_A
        pos = e
    out.append(text[pos:])
    return ''.join(out), keep


_SEG = re.compile('[]+|[]+|[^]+')


def _unmask(masked, keep):
    out, k = [], 0
    for m in _SEG.finditer(masked):
        seg = m.group(0)
        if seg[0] in (MASK_A, MASK_B):
            out.append(keep[k])
            k += 1
        else:
            out.append(seg)
    assert k == len(keep), '掩蔽段数与还原段数不一致'
    return ''.join(out)


def _sentence_of(text, pos):
    a = max(text.rfind(ch, 0, pos) for ch in '。！？；')
    ends = [x for x in (text.find(ch, pos) for ch in '。！？；') if x >= 0]
    b = min(ends) if ends else len(text)
    return text[a + 1:b]


def _apply_one(rule, text):
    if rule.func is not None:
        return rule.func(text)
    hits = []
    ex = [re.compile(p) for p in rule.exclude]

    def cb(m):
        s, e = m.span()
        win_s = max(0, s - 6)
        win = text[win_s:e + 6]
        for rx in ex:
            for mm in rx.finditer(win):
                ms, me = mm.start() + win_s, mm.end() + win_s
                if ms < e and me > s:
                    return m.group(0)
        if rule.sentence_exclude and rule.sentence_exclude in _sentence_of(text, s):
            return m.group(0)
        new = m.expand(rule.repl)
        hits.append((m.group(0), new))
        return new
    return re.sub(rule.pattern, cb, text), hits


def apply_rules(line, layer, rules, term_strings=(), tier='A', only_ids=None):
    """对一行可改文本跑规则表。返回 (new_line, hits)，hits=[(rule_id, rule_name, old, new)]。
    layer 属于 {'shihua','hint'}；tier='B' 时 A、B 两档都跑；only_ids 限定规则 id 集合。"""
    hits = []
    text = line
    for rule in rules:
        if only_ids and rule.id not in only_ids:
            continue
        if rule.tier == 'B' and tier != 'B':
            continue
        if rule.layer != 'both' and rule.layer != layer:
            continue
        masked, keep = _mask(text, _spans(text, rule.quote_exempt, term_strings))
        new_masked, h = _apply_one(rule, masked)
        if not h:
            continue
        text = _unmask(new_masked, keep)
        hits.extend((rule.id, rule.name, o, n) for o, n in h)
    return text, hits
