# -*- coding: utf-8 -*-
"""
polish_writing —— 写作课详案「确定性润色」流水线（交付前兜底层 · 2026-09-11 立）。

    PYTHONUTF8=1 python .claude/skills/laojohn-writing-lesson/assets/polish_writing.py <详案.md> [--stage det] [--dry-run] [--tier B] [--rules 1,2,3]

做什么：对可改层（`师：`/`（教师总结）`/`[…]`/`〔应答·…〕` 行）跑 polish_rules.RULES 的机械替换
（你们→大家、念→读、引出式破折号→冒号……），其余一律不碰；改完自动验收，验不过整篇回滚。

为什么是「机械层」而不是子 agent：冷审 Pass B 对同一批词一篇只动几处（台账第 18–21 点），
外部润色每篇要改 100 多行、七成落在这十几条替换上。已定案的改法交机器，人只接残余。

流程（--stage det）：
  1. 读文件、探测行尾（CRLF/LF 原样保持，否则 git diff 整篇标改动）；
  2. tone_gate.load_body + writing_protected_lines 划出保护区（注释/围栏/提纲表/标题/表格/引块/页标/
     参考行/示范文/固定括注/占位槽行/未知体例）；
  3. 从指纹块「本篇术语表：」行取术语串（技法名等），整段掩蔽不改；
  4. 可改行按起首分层跑规则；改动行若含 ASCII 直引号，过 fix_quotes_md.smart_quotes_line；
  5. --dry-run：只打 unified diff 与各规则命中数，不落盘；
     否则：备份到 <md 所在目录>/_polish/<篇名>/<篇名>.md.bak → 写盘 → verify：
       a. tone_gate --profile writing：**新增** FAIL 项（改前没有、改后有）即回滚 exit 2；
       b. tone_gate.report_direction(改后, 备份)：口语词/破折号反向、或保护区改动行数非 0 即回滚 exit 2；
       c. 行数不变、保护行逐行相等、指纹块逐字相等，否则回滚 exit 2；
     → 写 <md 所在目录>/_润色报告-<篇名>.md（各规则命中数与摘录、方向指标三行、tone_gate 结论）。

红线：
  - 只跑在 .md 源上，docx 由引擎重渲（md_to_laojohn_docx.py --header-left/--header-right + style_front_page.py）。
  - 术语表串、引号内学生话/示范句、参考行、示范文一字不动（保护区与掩蔽两道）。
  - 「好，」不删、参考行不书面化、短指令不加长（style-criteria §三）。
  - --stage split / apply（子 agent 逐段层）本轮只留接口占位，未实现。

产物不进 git：`_polish/` 与 `_润色报告-*.md` 已加 .gitignore；`batch_ngram_scan._lesson_mds()` 也按 `_` 前缀排除。
"""
import argparse
import difflib
import io
import os
import re
import subprocess
import sys
from collections import Counter, OrderedDict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)
# stdout 的 utf-8 包装由 tone_gate 导入时统一做（两处包装会把底层 buffer 关掉）

import tone_gate  # noqa: E402
from polish_rules import RULES, apply_rules  # noqa: E402
try:
    from fix_quotes_md import smart_quotes_line  # noqa: E402
except Exception:  # pragma: no cover
    smart_quotes_line = None

TONE_GATE = os.path.join(ROOT, 'tone_gate.py')


def detect_eol(path):
    """复制自 docx_backfill.detect_eol：写回必须原样保持行尾。"""
    with open(path, 'rb') as f:
        data = f.read()
    return '\r\n' if data.count(b'\r\n') else '\n'


def read_lines(path):
    with open(path, 'rb') as f:
        raw = f.read()
    text = raw.decode('utf-8')
    return text.splitlines(), detect_eol(path), text.endswith(('\n', '\r\n'))


def write_lines(path, lines, eol, trailing):
    data = eol.join(lines) + (eol if trailing else '')
    with open(path, 'wb') as f:
        f.write(data.encode('utf-8'))


def term_strings(raw_lines):
    """指纹块「本篇术语表： 技法统称=写法｜本课技法名=A／B｜文体称谓=习作（成稿称文章）｜表格单位=栏」→ 串集合。"""
    out = set()
    for ln in raw_lines:
        s = ln.strip()
        if not s.startswith('本篇术语表'):
            continue
        body = s.split('：', 1)[1] if '：' in s else s
        for item in re.split(r'[｜|]', body):
            if '=' in item:
                item = item.split('=', 1)[1]
            for part in re.split(r'[／/、，,；;（）()]', item):
                part = part.strip()
                if len(part) >= 2:
                    out.add(part)
    return sorted(out, key=len, reverse=True)


def fingerprint_block(lines):
    out, on = [], False
    for ln in lines:
        if 'VARIATION-FINGERPRINT' in ln:
            on = True
        if on:
            out.append(ln)
            if '-->' in ln:
                on = False
    return out


def layer_of(line):
    s = line.strip()
    if s.startswith(tone_gate.SHIHUA_PREFIX):
        return 'shihua'
    if s.startswith(('[', '〔应答')):
        return 'hint'
    return None


def polish(lines, prot, terms, tier, only_ids):
    new_lines = list(lines)
    hits = []   # (lineno1, rule_id, rule_name, old, new)
    for i, ln in enumerate(lines):
        if i in prot:
            continue
        layer = layer_of(ln)
        if layer is None:
            continue
        nl, h = apply_rules(ln, layer, RULES, term_strings=terms, tier=tier, only_ids=only_ids)
        if nl != ln:
            if smart_quotes_line and ('"' in nl or "'" in nl):
                nl = smart_quotes_line(nl)
            new_lines[i] = nl
            hits.extend((i + 1, rid, name, o, n) for rid, name, o, n in h)
    return new_lines, hits


def run_tone_gate(path):
    r = subprocess.run([sys.executable, TONE_GATE, path, '--profile', 'writing'],
                       capture_output=True, env=dict(os.environ, PYTHONUTF8='1'))
    out = r.stdout.decode('utf-8', 'replace')
    fails = re.findall(r'^\[FAIL\] (.+?)（(\d+) 处）', out, flags=re.M)
    return r.returncode, {name: int(n) for name, n in fails}, out


def summarize(hits):
    by_rule = OrderedDict()
    for lineno, rid, name, o, n in hits:
        by_rule.setdefault((rid, name), []).append((lineno, o, n))
    return by_rule


def write_report(path, stem, src_lines, hits, direction_rows, gate_before, gate_after, verdict, eol):
    by_rule = summarize(hits)
    changed_lines = sorted({h[0] for h in hits})
    out = []
    out.append('# 润色报告 · ' + stem)
    out.append('')
    out.append('> 由 polish_writing.py 生成（确定性层）。改动只落在师话/教师总结/舞台提示/应答标签行；'
               '参考行、示范文、表格、页标、提纲表、固定括注、术语表串一律未动。')
    out.append('')
    out.append('## 一、结论')
    out.append('')
    out.append('- 验收：' + verdict)
    out.append('- 改动行数：%d（总行 %d）' % (len(changed_lines), len(src_lines)))
    out.append('- 规则命中合计：%d 处 / %d 条规则' % (len(hits), len(by_rule)))
    out.append('')
    out.append('## 二、方向指标（vs 改前备份）')
    out.append('')
    for r in direction_rows:
        out.append('- ' + r)
    out.append('')
    out.append('## 三、tone_gate')
    out.append('')
    out.append('- 改前 FAIL：%s' % (('、'.join('%s×%d' % kv for kv in gate_before.items())) or '无'))
    out.append('- 改后 FAIL：%s' % (('、'.join('%s×%d' % kv for kv in gate_after.items())) or '无'))
    out.append('')
    out.append('## 四、各规则命中（每条至多列 3 处摘录）')
    out.append('')
    out.append('| 规则 | 命中 | 摘录（行：改前→改后） |')
    out.append('|---|---|---|')
    for (rid, name), items in by_rule.items():
        ex = '；'.join('行%d：%s→%s' % (ln, o, n) for ln, o, n in items[:3])
        out.append('| %d %s | %d | %s |' % (rid, name, len(items), ex))
    out.append('')
    out.append('## 五、改动行清单')
    out.append('')
    for ln in changed_lines:
        out.append('- 行%d：%s' % (ln, src_lines[ln - 1].strip()[:60]))
    text = eol.join(out) + eol
    text = text.replace('"', '“').replace("'", '‘')
    with open(path, 'wb') as f:
        f.write(text.encode('utf-8'))


def main():
    ap = argparse.ArgumentParser(description='写作课详案确定性润色')
    ap.add_argument('md_path')
    ap.add_argument('--stage', default='det', choices=['det', 'split', 'apply', 'verify', 'all'])
    ap.add_argument('--dry-run', action='store_true', help='只打 diff 与命中统计，不落盘')
    ap.add_argument('--tier', default='A', choices=['A', 'B'], help='B＝连多义字规则（得→要）一起跑')
    ap.add_argument('--rules', help='只跑这些规则 id，逗号分隔')
    ap.add_argument('--no-verify', action='store_true', help='落盘后不跑验收（调试用）')
    args = ap.parse_args()

    if args.stage in ('split', 'apply', 'all'):
        print('[未实现] --stage %s：子 agent 逐段层本轮只留接口占位，请用 --stage det。' % args.stage)
        sys.exit(3)

    md = os.path.abspath(args.md_path)
    stem = os.path.splitext(os.path.basename(md))[0]
    outdir = os.path.dirname(md)
    only_ids = {int(x) for x in args.rules.split(',')} if args.rules else None

    src_lines, eol, trailing = read_lines(md)
    body, in_outline = tone_gate.load_body(md)
    prot = tone_gate.writing_protected_lines(body, in_outline)
    terms = term_strings(src_lines)
    new_lines, hits = polish(src_lines, prot, terms, args.tier, only_ids)

    by_rule = summarize(hits)
    print('== polish_writing · %s ==' % os.path.basename(md))
    print('可改行 %d / 总行 %d；术语表掩蔽串 %d 个' % (len(src_lines) - len(prot), len(src_lines), len(terms)))
    for (rid, name), items in by_rule.items():
        print('  规则%2d %s：%d 处' % (rid, name, len(items)))
    print('  合计 %d 处，改动 %d 行' % (len(hits), len({h[0] for h in hits})))

    if args.dry_run:
        diff = difflib.unified_diff(src_lines, new_lines, 'before', 'after', lineterm='', n=0)
        for d in diff:
            if d.startswith(('---', '+++', '@@')):
                continue
            print(d)
        return

    if not hits:
        print('无改动，不落盘。')
        return

    bakdir = os.path.join(outdir, '_polish', stem)
    os.makedirs(bakdir, exist_ok=True)
    bak = os.path.join(bakdir, stem + '.md.bak')
    with open(md, 'rb') as f:
        orig_bytes = f.read()
    with open(bak, 'wb') as f:
        f.write(orig_bytes)
    write_lines(md, new_lines, eol, trailing)
    print('已备份到 %s，已写盘。' % bak)

    if args.no_verify:
        return

    def rollback(reason):
        with open(md, 'wb') as f:
            f.write(orig_bytes)
        print('[回滚] ' + reason + '（已从备份还原）')
        sys.exit(2)

    # a. tone_gate 新增 FAIL
    code_b, fails_b, _ = run_tone_gate(bak)
    code_a, fails_a, out_a = run_tone_gate(md)
    new_fail = {k: v for k, v in fails_a.items() if v > fails_b.get(k, 0)}
    # b. 方向指标
    rows, warn = tone_gate.report_direction(md, bak, do_print=False)
    # c. 结构不变
    after_lines, _, _ = read_lines(md)
    struct_ok = (len(after_lines) == len(src_lines)
                 and all(after_lines[i] == src_lines[i] for i in prot)
                 and fingerprint_block(after_lines) == fingerprint_block(src_lines))

    verdict_parts = []
    if new_fail:
        verdict_parts.append('tone_gate 新增 FAIL：' + '、'.join('%s×%d' % kv for kv in new_fail.items()))
    if warn:
        verdict_parts.append('方向指标反向或碰保护区')
    if not struct_ok:
        verdict_parts.append('行数/保护行/指纹块发生变化')
    verdict = '通过' if not verdict_parts else '不通过（' + '；'.join(verdict_parts) + '）'

    report = os.path.join(outdir, '_润色报告-' + stem + '.md')
    write_report(report, stem, src_lines, hits, rows, fails_b, fails_a, verdict, eol)
    print('报告：%s' % report)
    for r in rows:
        print('  ' + r)
    if verdict != '通过':
        rollback(verdict)
    print('验收通过。')


if __name__ == '__main__':
    main()
