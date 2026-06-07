"""中间稿合规校验脚本（laojohn-ppt-draft v1.1 契约）

用法：
  python _smoke_check.py                       # 默认扫 examples/ 下所有 .md
  python _smoke_check.py <file>                # 扫指定文件
  python _smoke_check.py <file> <start> <end>  # 同时校验 P 编号区间

退出码：0=PASS, 1=FAIL
"""
import sys, io, re, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VALID_PAGE_TYPES = {'封面','环节标题','引导问题','原文齐读','要点小结','填空表格'}
FORBID_KEYWORDS_IN_EYEBROW = ['导读课','阅读交流课','思辨应用课']

# v1.1 字段冲突矩阵（与 references/field-extraction.md 末尾矩阵保持一致）
FIELD_MATRIX = {
    '封面':     {'必填': ['标题'],                              '禁用': ['眉标','要点','表格','配图建议']},
    '环节标题': {'必填': ['眉标','标题'],                       '禁用': ['副标题','要点','表格']},
    '引导问题': {'必填': ['眉标','标题','要点'],                '禁用': ['副标题','表格']},
    '原文齐读': {'必填': ['眉标','标题','正文'],                '禁用': ['副标题','要点','表格','配图建议']},
    '要点小结': {'必填': ['眉标','标题','要点'],                '禁用': ['副标题','表格']},
    '填空表格': {'必填': ['眉标','标题','副标题','表格'],       '禁用': ['正文','要点','配图建议']},
}


def check_file(target: str, expect_range=None) -> tuple[list[str], list[str], list[tuple]]:
    text = open(target, encoding='utf-8').read()
    errs, warns, report = [], [], []

    # 元信息
    head = text[:300]
    for k in ['书名：','课时：','作者：','年级：']:
        if k not in head:
            errs.append(f'[meta] 缺 {k}')

    # 页编号
    ids = [int(m.group(1)) for m in re.finditer(r'^## P(\d+) \|', text, re.MULTILINE)]
    if expect_range and ids != list(range(expect_range[0], expect_range[1]+1)):
        errs.append(f'[P] 期望 {expect_range}, 实际 {ids}')

    # 页型
    for m in re.finditer(r'^## P(\d+) \| 页型:(\S+)', text, re.MULTILINE):
        if m.group(2) not in VALID_PAGE_TYPES:
            errs.append(f'[P{m.group(1)}] 非法页型: {m.group(2)}')

    # 眉标禁课型
    for m in re.finditer(r'眉标：(.+)', text):
        for word in FORBID_KEYWORDS_IN_EYEBROW:
            if word in m.group(1):
                errs.append(f'[眉标] 含课型: {m.group(1).strip()}')

    # 逐页检查
    pages = re.split(r'\n## P', text)
    for p in pages[1:]:
        h = re.search(r'^(\d+) \| 页型:(\S+)', p)
        if not h: continue
        pid, pt = h.group(1), h.group(2)
        eb = re.search(r'眉标：(.+)', p)
        ti = re.search(r'标题：(.+)', p)
        sub = re.search(r'副标题：(.+)', p)
        if eb and ti:
            report.append((pid, pt, eb.group(1).strip(), ti.group(1).strip()))

        # v1.1 去重核心校验（环节标题、封面例外）
        if pt not in ('环节标题', '封面') and eb and ti:
            ebt = eb.group(1).strip()
            if ebt in ti.group(1):
                errs.append(f'[P{pid} {pt}] 眉标 in 标题: "{ebt}" 包含于 "{ti.group(1).strip()}"')
            if pt == '填空表格' and sub and ebt in sub.group(1):
                errs.append(f'[P{pid} {pt}] 眉标 in 副标题: "{ebt}" 包含于 "{sub.group(1).strip()}"')

        # 字段冲突矩阵
        rules = FIELD_MATRIX.get(pt, {})
        for must in rules.get('必填', []):
            if f'{must}：' not in p:
                errs.append(f'[P{pid} {pt}] 缺必填字段: {must}')
        for ban in rules.get('禁用', []):
            if f'{ban}：' in p:
                errs.append(f'[P{pid} {pt}] 出现禁用字段: {ban}')

        # 要点用 - 列表
        kp = re.search(r'要点：\s*\n?([\s\S]+?)(?=\n[^-\s]|\Z)', p)
        if kp and '/' in kp.group(1).split('\n')[0] and '- ' not in kp.group(1):
            errs.append(f'[P{pid}] 要点用 / 分隔(旧格式)')

    return errs, warns, report


def main():
    args = sys.argv[1:]
    if not args:
        targets = sorted(glob.glob(os.path.join(os.path.dirname(__file__), 'examples', '*.md')))
    elif len(args) == 1:
        targets = [args[0]]
    else:
        targets = [args[0]]
        expect_range = (int(args[1]), int(args[2]))
        run_one(targets[0], expect_range)
        return

    all_pass = True
    for t in targets:
        errs, warns, report = check_file(t)
        print(f'=== {os.path.basename(t)} ===')
        for pid, pt, eb, ti in report:
            print(f'  P{pid:<4}{pt:<8}{eb:<14}{ti}')
        if errs:
            all_pass = False
            print('  FAIL:')
            for e in errs: print(f'    {e}')
        else:
            print('  PASS')
        if warns:
            print('  WARN:')
            for w in warns: print(f'    {w}')
        print()
    sys.exit(0 if all_pass else 1)


def run_one(target, expect_range):
    errs, warns, report = check_file(target, expect_range)
    print(f'=== 校验报告: {target} ===')
    for pid, pt, eb, ti in report:
        print(f'P{pid:<4}{pt:<8}{eb:<14}{ti}')
    print()
    if errs:
        print('FAIL:')
        for e in errs: print(f'  {e}')
        sys.exit(1)
    else:
        print('PASS')
    if warns:
        print('WARN:')
        for w in warns: print(f'  {w}')


if __name__ == '__main__':
    main()
