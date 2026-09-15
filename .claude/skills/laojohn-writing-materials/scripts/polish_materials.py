# -*- coding: utf-8 -*-
"""
polish_materials —— 同步习作配套三侧 `_data.json` 文案「确定性润色」门（交付前机检 D · 2026-09-15 立）。

    PYTHONUTF8=1 python .claude/skills/laojohn-writing-materials/scripts/polish_materials.py <xx-学生用_data.json> [--dry-run] [--tier B] [--rules 1,2] [--plan <详案.md>] [--render]
    PYTHONUTF8=1 python .claude/skills/laojohn-writing-materials/scripts/polish_materials.py --all [--dry-run]     # 写作配套输出/ 下全部 42 份
    PYTHONUTF8=1 python .claude/skills/laojohn-writing-materials/scripts/polish_materials.py --check-exemplars [样本卡.md]   # 样本卡防漂移：每段须逐字等于源 json 某字段

做什么：对三侧 json 里**派生文案**字段跑 `laojohn-writing-lesson/assets/polish_rules.py` 的机械替换
（你们→大家、念→读、引出式破折号→冒号、这儿→这里、挑→选、跟→和、别→不要、教师侧 老师→教师……），
**逐字取自详案的字段一律不碰**（示范文、旁批引句、构思表行名、时间轴分钟数、对照示意句等，见 SIDES 表）。
改完自动验收：json 可解析、保护字段逐字相等、方向指标（口语词／破折号）不反向；任一不过整份回滚。

为什么是它（不是再往 SKILL 里加一条「对照 style-criteria 自查」）：详案线 2026-09-11 换靶实测——已定案的
词句替换交 agent 逐处裁量，一篇 18 处「你们」只动 3 处；做成脚本才落地。配套侧 0901 起只有「通读对照表自查」
一条，无机检，2026-09-15 抽《故事新编》三侧：口语词与引出式破折号成片、内部黑话（零打断／领步／定起点）
进了教师页。规则表与详案线**同一张**（单一源＝polish_rules.py，本文件不另存副本，新增词条去那边加）。

三侧的层与规则取舍（与详案线 layer 的对应）：
  学生侧 → 'shihua'（对学生说话；「老师」是学生对教师的称呼，不改）
  教师侧 → 'shihua' + 'hint'（教研旁注，第三人称：老师→教师 也跑）；不跑规则 2（旁注里的「你们」多是引号内学生话，已掩蔽）
  家长侧 → 'shihua'；不跑规则 2（「你们」指亲子二人，改「大家」错）、不跑规则 9（家长口中的「老师」不改「教师」）
  规则 21（句首「当然，」删）对 json 字符串起首不生效（依赖「师：」前缀），全侧不跑。

术语掩蔽：自动定位同课次详案 `写作课详案输出/<课次>-写作课详案.md`，取其指纹块「本篇术语表」串整段掩蔽
（技法名如「挑一件只有它才遇得上的事」里的「挑」不改）；找不到详案则掩蔽集为空，报告里注明。

产物：备份 `<课次目录>/_polish/<文件名>.bak`；报告 `<课次目录>/_润色报告-<文件 stem>.md`（含残余候选清单：
口语词逐词位置、剩余 `——`、内部黑话命中）——**残余清单是给人看的，判断类（生造术语／导演腔／升华式收尾）机器不判**。
两类产物已 gitignore，不进仓。

样本卡防漂移（--check-exemplars · 2026-09-15 立）：`references/prose-exemplars-materials.md` 的每一段都必须逐字等于
卡头点名课次三侧 json 的某个派生文案字段（样本＝现行 json 的快照，json 改一处样本同步）。0915 首版就抄了 0901 旧版、
2 段过期（「范文」未随 d40204d 改「示范文」、draftnote 低段句未随 55aceba 删），此后靠这条机检。

红线：
  - 只改 json 源；PDF/HTML 由各 render_*.py 重渲（`--render` 可顺手跑，页数／溢出告警照旧由 _shared 报）。
  - 保护字段（SIDES[*]['protect']）与弯引号段、书名号段、术语串一字不动。
  - json 落盘用 `indent=2, ensure_ascii=False`，保持原行尾与末尾换行；缩进原为 1 的旧件会统一成 2（一次性）。
"""
import argparse
import difflib
import glob
import io
import json
import os
import re
import subprocess
import sys
from collections import OrderedDict

# stdout 的 utf-8 包装由 tone_gate 导入时统一做（两处包装会把底层 buffer 关掉，同 polish_writing）

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
LESSON_ASSETS = os.path.join(ROOT, '.claude', 'skills', 'laojohn-writing-lesson', 'assets')
for p in (ROOT, LESSON_ASSETS):
    if p not in sys.path:
        sys.path.insert(0, p)

import tone_gate  # noqa: E402  仓根；提供 _count_colloquial / COLLOQUIAL_WORDS / MECH_WORDS
from polish_rules import RULES, apply_rules  # noqa: E402  单一源，禁复制

OUT_ROOT = os.path.join(ROOT, '写作配套输出')
PLAN_ROOT = os.path.join(ROOT, '写作课详案输出')
RENDERERS = {'学生': 'render_student.py', '教师': 'render_teacher.py', '家长': 'render_parent.py'}

# 路径写法：以 '.' 分段，'[]' 表示列表的每一项，'*' 表示字典的每个键
SIDES = {
    '学生': {
        'edit': [
            ('worksheet.lead', 'shihua'), ('worksheet.skills', 'shihua'),
            ('worksheet.page2_lead', 'shihua'), ('worksheet.draftnote', 'shihua'),
            ('worksheet.outline_hint', 'shihua'),
            ('worksheet.plan_rows[].note', 'shihua'), ('worksheet.outline_rows[].note', 'shihua'),
            ('essay.lead', 'shihua'), ('essay.notes[].a', 'shihua'),
            ('essay.method', 'shihua'), ('essay.footer', 'shihua'),
        ],
        'protect': ['meta', 'essay.title', 'essay.paragraphs', 'essay.notes[].q',
                    'worksheet.plan_cols', 'worksheet.plan_rows[].label', 'worksheet.plan_rows[].prefill',
                    'worksheet.plan_rows[].cells', 'worksheet.outline_rows[].label', 'worksheet.outline_rows[].cells',
                    'worksheet.marks'],
        'skip_rules': {21},
        'hint_rules': set(),
    },
    '教师': {
        'edit': [
            ('overview.goal', 'shihua'), ('overview.warns[]', 'shihua'),
            ('overview.lessons[].steps[].name', 'shihua'), ('overview.lessons[].after', 'shihua'),
            ('overview.materials[]', 'shihua'),
            ('delivery.envs[].heading', 'shihua'), ('delivery.envs[].rows[].text', 'shihua'),
            ('delivery.nono[]', 'shihua'),
        ],
        'protect': ['meta', 'overview.essay', 'overview.lessons[].title', 'overview.lessons[].steps[].min',
                    'delivery.envs[].rows[].type'],
        'skip_rules': {2, 21},
        'hint_rules': {9},          # 第二遍以 'hint' 层只跑这些（老师→教师）
    },
    '家长': {
        'edit': [
            ('onepager.oneline', 'shihua'), ('onepager.para', 'shihua'),
            ('onepager.compare.bad.note', 'shihua'), ('onepager.compare.good.note', 'shihua'),
            ('onepager.task.steps[]', 'shihua'), ('onepager.task.tip', 'shihua'),
            ('onepager.dont[]', 'shihua'),
        ],
        'protect': ['meta', 'onepager.compare.bad.quote', 'onepager.compare.good.quote', 'onepager.task.title'],
        'skip_rules': {2, 9, 21},
        'hint_rules': set(),
    },
}

# 配套侧「内部黑话」候选：tone_gate.MECH_WORDS（详案师话禁词）＋ 配套页实测惯犯。只报不改，判断归人。
JARGON_EXTRA = ['零打断', '领步', '分档收束', '重开选材', '起步', '半环', '话轮', '装置', '载体',
                '闸门', '同构', '拟真', '差异轴', '零件层', '避让']
# 「判据」不列：0901 用户认可的《推荐一个好地方》教师页定稿保留了「这一对比就是全课的判据」。


# ---------- 路径遍历 ----------

def _walk(obj, path_parts, prefix=''):
    """按路径描述产出 (container, key, full_path)；'[]' 展开列表，'*' 展开字典。"""
    if not path_parts:
        return
    head, rest = path_parts[0], path_parts[1:]
    key = head[:-2] if head.endswith('[]') else head
    if key == '*':
        items = list(obj.items()) if isinstance(obj, dict) else []
    else:
        if not isinstance(obj, dict) or key not in obj:
            return
        items = [(key, obj[key])]
    for k, v in items:
        fp = f'{prefix}.{k}' if prefix else k
        if head.endswith('[]'):
            if not isinstance(v, list):
                continue
            for i, item in enumerate(v):
                ifp = f'{fp}[{i}]'
                if rest:
                    yield from _walk(item, rest, ifp)
                else:
                    yield v, i, ifp
        else:
            if rest:
                yield from _walk(v, rest, fp)
            else:
                yield obj, k, fp


def iter_leaves(obj, path):
    yield from _walk(obj, path.split('.'))


def snapshot(obj, paths):
    """保护字段的 (full_path → json 串) 快照，用于验收逐字比对。"""
    snap = OrderedDict()
    for p in paths:
        for cont, k, fp in iter_leaves(obj, p):
            snap[fp] = json.dumps(cont[k], ensure_ascii=False, sort_keys=True)
    return snap


# ---------- 术语串 ----------

def plan_path_for(json_path):
    lesson = os.path.basename(os.path.dirname(os.path.abspath(json_path)))
    cand = os.path.join(PLAN_ROOT, lesson + '-写作课详案.md')
    return cand if os.path.exists(cand) else None


_HEADING = re.compile(r'^###\s*(?:[一二三四五六七八九十]+、)?\s*(.+?)\s*(?:（[^）]*）)?\s*$')


def term_strings_from_plan(plan_md):
    """两类串整段掩蔽：① 指纹块「本篇术语表」（复用 polish_writing.term_strings）；② 详案 `###` 环节标题正文
    （去序号、去尾括号）——教师侧时间轴 `steps[].name`／`envs[].heading` 是环节标题压短，标题在详案里属保护区、
    polish_writing 不改它，这边若改了「挑一件事情」→「选一件事情」，时间轴与详案标题就对不上（0915 实测）。"""
    terms = set()
    try:
        import polish_writing  # noqa: E402
        with open(plan_md, encoding='utf-8') as f:
            lines = f.read().splitlines()
        terms |= set(polish_writing.term_strings(lines))
        for ln in lines:
            m = _HEADING.match(ln)
            if m:
                core = m.group(1)
                terms.add(core)
                for seg in re.split(r'[：:，、]', core):     # 「学写法：挑一件事情，写清楚」拆出「挑一件事情」
                    if len(seg) >= 3:
                        terms.add(seg)
    except Exception as e:  # pragma: no cover
        print('  [术语串] 读取失败，掩蔽集为空：%s' % e)
    return terms


# ---------- 侧别与文件 ----------

def side_of(json_path):
    m = re.search(r'-(学生|教师|家长)用_data\.json$', os.path.basename(json_path))
    if not m:
        sys.exit('文件名须以 -学生用/-教师用/-家长用_data.json 结尾：%s' % json_path)
    return m.group(1)


def read_json(path):
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8-sig')
    eol = '\r\n' if raw.count(b'\r\n') else '\n'
    return json.loads(text, object_pairs_hook=OrderedDict), eol, text.endswith(('\n', '\r\n')), raw


def dump_json(obj, eol, trailing):
    s = json.dumps(obj, ensure_ascii=False, indent=2)
    if eol != '\n':
        s = s.replace('\n', eol)
    return s + (eol if trailing else '')


# ---------- 润色 ----------

def polish(obj, side_cfg, terms, tier, only_ids):
    hits = []   # (full_path, rule_id, rule_name, old, new)
    skip = side_cfg['skip_rules']
    for path, layer in side_cfg['edit']:
        for cont, k, fp in iter_leaves(obj, path):
            val = cont[k]
            if not isinstance(val, str) or not val:
                continue
            ids = only_ids if only_ids else {r.id for r in RULES} - skip
            new, h = apply_rules(val, layer, RULES, term_strings=terms, tier=tier, only_ids=ids)
            if side_cfg['hint_rules'] and (not only_ids or only_ids & side_cfg['hint_rules']):
                hid = side_cfg['hint_rules'] if not only_ids else only_ids & side_cfg['hint_rules']
                new, h2 = apply_rules(new, 'hint', RULES, term_strings=terms, tier=tier, only_ids=hid)
                h = h + h2
            if new != val:
                cont[k] = new
                hits.extend((fp, rid, name, o, n) for rid, name, o, n in h)
    return hits


def editable_text(obj, side_cfg):
    parts = []
    for path, _ in side_cfg['edit']:
        for cont, k, fp in iter_leaves(obj, path):
            if isinstance(cont[k], str):
                parts.append(cont[k])
    return '\n'.join(parts)


def _strip_quotes(text):
    return re.sub('“[^”]*”|‘[^’]*’|《[^》]*》', '', text)


def residual_report(obj, side_cfg):
    """残余候选：口语词逐词计数（剥引号/书名号段）、剩余 ——、内部黑话。只报不判。"""
    text = _strip_quotes(editable_text(obj, side_cfg))
    rows = []
    for w in tone_gate.COLLOQUIAL_WORDS:
        c = text.count(w)
        ex = tone_gate._COLLOQUIAL_EXCLUDE.get(w)
        if ex is not None:
            c -= len(ex.findall(text))
        if c > 0:
            rows.append(('口语词', w, c))
    n_dash = text.count('——')
    if n_dash:
        rows.append(('破折号', '——', n_dash))
    for w in tone_gate.MECH_WORDS + JARGON_EXTRA:
        c = text.count(w)
        if c:
            rows.append(('内部黑话', w, c))
    return rows


def direction(before_text, after_text):
    rows, warn = [], False
    for label, fn in (('口语词合计', tone_gate._count_colloquial), ('破折号 ——', lambda t: t.count('——'))):
        b, a = fn(_strip_quotes(before_text)), fn(_strip_quotes(after_text))
        if a > b:
            warn = True
            v = f'⚠ 反向 +{a - b}'
        elif a < b:
            v = f'✓ 下降 {b - a}（{100 * (b - a) / b:.0f}%）'
        else:
            v = '持平'
        rows.append(f'{label}：改前 {b} → 改后 {a}　{v}')
    return rows, warn


def write_report(path, stem, hits, dir_rows, protect_ok, residual, verdict, terms_note, eol):
    by_rule = OrderedDict()
    for fp, rid, name, o, n in hits:
        by_rule.setdefault((rid, name), []).append((fp, o, n))
    out = ['# 润色报告 · ' + stem, '',
           '> 由 polish_materials.py 生成（配套侧确定性层）。只改派生文案字段；示范文、旁批引句、'
           '构思表行名、时间轴分钟数、对照示意句等逐字取自详案的字段一律未动。' + terms_note, '',
           '## 一、结论', '',
           '- 验收：' + verdict,
           '- 规则命中合计：%d 处 / %d 条规则，改动字段 %d 个' % (len(hits), len(by_rule), len({h[0] for h in hits})),
           '- 保护字段逐字比对：' + ('✓ 全部一致' if protect_ok else '⚠ 有变动'), '',
           '## 二、方向指标（vs 改前备份）', '']
    out += ['- ' + r for r in dir_rows]
    out += ['', '## 三、各规则命中（每条至多列 3 处摘录）', '', '| 规则 | 命中 | 摘录（字段：改前→改后） |', '|---|---|---|']
    for (rid, name), items in by_rule.items():
        ex = '；'.join('%s：%s→%s' % (fp, o, n) for fp, o, n in items[:3])
        out.append('| %d %s | %d | %s |' % (rid, name, len(items), ex))
    out += ['', '## 四、残余候选（机器只报数，判断归人：生造术语／导演腔／升华式收尾脚本不判）', '']
    if residual:
        out += ['| 类 | 串 | 次 |', '|---|---|---|']
        out += ['| %s | %s | %d |' % r for r in residual]
    else:
        out.append('- 无')
    text = (eol.join(out) + eol).replace('"', '“').replace("'", '‘')
    with open(path, 'wb') as f:
        f.write(text.encode('utf-8'))


def run_render(json_path):
    side = side_of(json_path)
    script = os.path.join(HERE, RENDERERS[side])
    out_dir = os.path.dirname(os.path.abspath(json_path))
    r = subprocess.run([sys.executable, script, json_path, out_dir], capture_output=True,
                       env=dict(os.environ, PYTHONUTF8='1'), cwd=ROOT)
    out = r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace')
    warns = [ln for ln in out.splitlines() if '!!' in ln or 'Traceback' in ln]
    return r.returncode, warns, out


# ---------- 样本卡防漂移 ----------

CARD_DEFAULT = os.path.join(HERE, '..', 'references', 'prose-exemplars-materials.md')


def card_segments(card_text):
    """正文（首个 --- 之后）逐行切段：跳过标题/括注/空行；去掉行首〔…〕标签；按全角「／」再切。"""
    body = card_text.split('\n---\n', 1)[1] if '\n---\n' in card_text else card_text
    segs = []
    for ln in body.splitlines():
        t = ln.strip()
        if not t or t.startswith(('#', '（', '>')):
            continue
        t = re.sub(r'^〔[^〕]*〕', '', t)
        segs += [x.strip() for x in t.split('／') if x.strip()]
    return segs


def check_exemplars(card_path):
    card_path = os.path.abspath(card_path)
    text = io.open(card_path, encoding='utf-8').read()
    m = re.search(r'《([^》]+)》', text)
    if not m:
        print('[check-exemplars] 卡头未点名课次（须有《<年级册>-第N单元-<题目>》）'); return 1
    course = m.group(1)
    files = sorted(glob.glob(os.path.join(OUT_ROOT, course, '*_data.json')))
    if not files:
        print('[check-exemplars] 找不到课次目录或 json：%s' % os.path.join(OUT_ROOT, course)); return 1
    values = {}
    for f in files:
        side = side_of(f)
        obj, _, _, _ = read_json(f)
        for path, _layer in SIDES[side]['edit']:
            for cont, k, fp in iter_leaves(obj, path):
                if isinstance(cont[k], str):
                    values.setdefault(cont[k], '%s侧 %s' % (side, fp))
    segs = card_segments(text)
    drift = []
    for x in segs:
        if x in values:
            continue
        near = [(v, w) for v, w in values.items() if v[:10] == x[:10]]
        drift.append((x, near[0] if near else None))
    print('== check-exemplars · %s ==' % os.path.basename(card_path))
    print('  课次 %s；样本段 %d；源字段 %d' % (course, len(segs), len(values)))
    if not drift:
        print('  ✓ 零漂移：每段都逐字等于源 json 某字段'); return 0
    for x, near in drift:
        print('  ⚠ 漂移 样本段：%s' % x[:60])
        if near:
            print('           现行 %s：%s' % (near[1], near[0][:60]))
        else:
            print('           现行：找不到同起首字段（该段可能被删或改了开头）')
    print('  共 %d 段漂移——样本＝现行 json 快照，改 json 须同步样本卡（或反之）' % len(drift))
    return 1


# ---------- 单份处理 ----------

def process(json_path, args):
    json_path = os.path.abspath(json_path)
    side = side_of(json_path)
    cfg = SIDES[side]
    stem = os.path.splitext(os.path.basename(json_path))[0]
    outdir = os.path.dirname(json_path)
    only_ids = {int(x) for x in args.rules.split(',')} if args.rules else None

    obj, eol, trailing, orig_bytes = read_json(json_path)
    plan = args.plan or plan_path_for(json_path)
    terms = term_strings_from_plan(plan) if plan else set()
    terms_note = ('术语掩蔽串 %d 个（取自 %s）。' % (len(terms), os.path.basename(plan))) if plan else '未找到同课次详案，术语掩蔽集为空。'

    before_text = editable_text(obj, cfg)
    snap_before = snapshot(obj, cfg['protect'])
    hits = polish(obj, cfg, terms, args.tier, only_ids)
    after_text = editable_text(obj, cfg)

    by_rule = OrderedDict()
    for fp, rid, name, o, n in hits:
        by_rule.setdefault((rid, name), []).append((fp, o, n))
    print('== polish_materials · %s（%s侧）==' % (os.path.basename(json_path), side))
    print('  ' + terms_note)
    for (rid, name), items in by_rule.items():
        print('  规则%2d %s：%d 处' % (rid, name, len(items)))
    print('  合计 %d 处，改动字段 %d 个' % (len(hits), len({h[0] for h in hits})))
    residual = residual_report(obj, cfg)
    if residual:
        print('  残余候选：' + '、'.join('%s×%d' % (w, c) for _, w, c in residual))

    if args.dry_run:
        for d in difflib.unified_diff(before_text.splitlines(), after_text.splitlines(), 'before', 'after', lineterm='', n=0):
            if not d.startswith(('---', '+++', '@@')):
                print('  ' + d)
        return 0

    if not hits:
        print('  无改动，不落盘。')
        return 0

    # 验收 a：保护字段逐字相等；b：方向指标不反向；c：重新序列化可解析
    protect_ok = snapshot(obj, cfg['protect']) == snap_before
    dir_rows, warn = direction(before_text, after_text)
    new_text = dump_json(obj, eol, trailing)
    try:
        json.loads(new_text)
        parse_ok = True
    except Exception:
        parse_ok = False
    parts = []
    if not protect_ok:
        parts.append('保护字段被改动')
    if warn:
        parts.append('方向指标反向')
    if not parse_ok:
        parts.append('落盘 json 不可解析')
    verdict = '通过' if not parts else '不通过（' + '；'.join(parts) + '）'

    bakdir = os.path.join(outdir, '_polish')
    os.makedirs(bakdir, exist_ok=True)
    bak = os.path.join(bakdir, os.path.basename(json_path) + '.bak')
    with open(bak, 'wb') as f:
        f.write(orig_bytes)
    report = os.path.join(outdir, '_润色报告-' + stem + '.md')
    write_report(report, stem, hits, dir_rows, protect_ok, residual, verdict, terms_note, eol)
    for r in dir_rows:
        print('  ' + r)
    if verdict != '通过':
        print('  [未落盘] ' + verdict + '；报告：' + report)
        return 2
    with open(json_path, 'wb') as f:
        f.write(new_text.encode('utf-8'))
    print('  已备份 %s，已写盘；报告：%s' % (os.path.relpath(bak, ROOT), os.path.relpath(report, ROOT)))

    if args.render:
        code, warns, _ = run_render(json_path)
        if code != 0 or warns:
            print('  [渲染告警] ' + ('；'.join(warns) or ('exit %d' % code)) + '——先压派生文案，不动模板')
            return 3
        print('  渲染通过（页数／溢出／Type3 自检无告警）')
    return 0


def main():
    ap = argparse.ArgumentParser(description='同步习作配套三侧 data.json 确定性润色')
    ap.add_argument('json_path', nargs='?', help='某侧 _data.json；与 --all 二选一')
    ap.add_argument('--all', action='store_true', help='跑 写作配套输出/ 下全部 *_data.json')
    ap.add_argument('--dry-run', action='store_true', help='只打命中统计与 diff，不落盘')
    ap.add_argument('--tier', default='A', choices=['A', 'B'], help='B＝连多义字规则（得→要）一起跑')
    ap.add_argument('--rules', help='只跑这些规则 id，逗号分隔')
    ap.add_argument('--plan', help='指定详案 .md 取术语串（默认按课次目录名自动定位）')
    ap.add_argument('--render', action='store_true', help='落盘后顺手重渲该侧 PDF 并转报自检告警')
    ap.add_argument('--check-exemplars', nargs='?', const=CARD_DEFAULT, metavar='样本卡.md',
                    help='样本卡防漂移：每段须逐字等于卡头课次三侧 json 的某派生字段；漂移 exit 1')
    args = ap.parse_args()

    if args.check_exemplars:
        sys.exit(check_exemplars(args.check_exemplars))

    if args.all:
        files = sorted(glob.glob(os.path.join(OUT_ROOT, '*', '*_data.json')))
    elif args.json_path:
        files = [args.json_path]
    else:
        ap.error('给一个 _data.json 路径，或 --all')
    worst = 0
    for f in files:
        worst = max(worst, process(f, args))
        print()
    sys.exit(worst)


if __name__ == '__main__':
    main()
