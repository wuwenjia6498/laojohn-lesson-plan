"""中间稿合规校验脚本（laojohn-ppt-draft 契约）

P 编号已由工具自排（详案不再有换页点），本脚本只校验"页内连续不跳号、不重复"，
不再要求 P 编号与详案锚点一一对应。

用法：
  python _smoke_check.py                       # 默认扫 examples/ 下所有 .md
  python _smoke_check.py <file>                # 扫指定文件
  python _smoke_check.py <file> <start> <end>  # 额外断言 P 编号落在指定区间（可选）

退出码：0=PASS, 1=FAIL
"""
import sys, io, re, os, glob
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

VALID_PAGE_TYPES = {'封面','环节标题','引导问题','原文齐读','要点小结','填空表格'}
# 写作课 profile 专属新页型（仅当 is_writing 时并入校验）
WRITING_PAGE_TYPES = {'双栏对照','写作任务','情境任务','写法讲解','活动指令','示范文','实景观察'}
FORBID_KEYWORDS_IN_EYEBROW = ['导读课','阅读交流课','思辨应用课','写作指导课','当堂写作与评改课']

# v1.1 字段冲突矩阵（与 references/field-extraction.md 末尾矩阵保持一致）
FIELD_MATRIX = {
    '封面':     {'必填': ['标题'],                              '禁用': ['眉标','要点','表格','配图建议']},
    '环节标题': {'必填': ['眉标','标题'],                       '禁用': ['副标题','要点','表格']},
    '引导问题': {'必填': ['眉标','标题','要点'],                '禁用': ['副标题','表格']},
    '原文齐读': {'必填': ['眉标','标题','正文'],                '禁用': ['副标题','要点','表格','配图建议']},
    '要点小结': {'必填': ['眉标','标题','要点'],                '禁用': ['副标题','表格']},
    '填空表格': {'必填': ['眉标','标题','副标题','表格'],       '禁用': ['正文','要点','配图建议']},
}

# 写作课新页型字段矩阵（仅当 is_writing 时并入）。双栏对照字段灵活（块用左右栏、行用表格），
# 故只约束眉标/标题必填；写作任务计时/字数可选（详案缺字数不强求），不列必填。
# 讲解三页型：情境任务=整段陈述（必填正文）；写法讲解/活动指令=列点（必填要点）。
WRITING_FIELD_MATRIX = {
    '双栏对照': {'必填': ['眉标','标题'],          '禁用': []},
    '写作任务': {'必填': ['眉标','标题','要点'],   '禁用': ['表格']},
    '情境任务': {'必填': ['眉标','标题','正文'],   '禁用': ['表格','副标题']},
    '写法讲解': {'必填': ['眉标','标题','要点'],   '禁用': ['表格','副标题']},
    '活动指令': {'必填': ['眉标','标题','要点'],   '禁用': ['表格','副标题']},
    '示范文':   {'必填': ['眉标','标题','正文'],   '禁用': ['表格','要点','副标题']},
    # 实景观察（v8）：眉标/标题/场景 必填（场景为重复行、按 `场景：` 存在性校验）；不用正文/要点/副标题/表格。
    '实景观察': {'必填': ['眉标','标题','场景'],   '禁用': ['正文','要点','副标题','表格']},
}


def check_file(target: str, expect_range=None) -> tuple[list[str], list[str], list[tuple]]:
    text = open(target, encoding='utf-8').read()
    errs, warns, report = [], [], []

    # 元信息（写作课模式无书作者：以 `文体：写作` 开关，要求 文体、豁免 作者）
    head = text[:300]
    is_writing = '文体：写作' in head or '文体:写作' in head
    required_meta = ['书名：','课时：','年级：'] + (['文体：'] if is_writing else ['作者：'])
    # profile-aware：写作课并入新页型与其字段矩阵
    valid_types = VALID_PAGE_TYPES | (WRITING_PAGE_TYPES if is_writing else set())
    field_matrix = {**FIELD_MATRIX, **(WRITING_FIELD_MATRIX if is_writing else {})}
    for k in required_meta:
        if k not in head:
            errs.append(f'[meta] 缺 {k}')
    # 读书会新样式（声明了主题色）：封面与原文齐读也配图，配图建议须带 形=/画面=，出处禁页码
    m_theme = re.search(r'^主题色[:：]\s*(\S+)', head, re.MULTILINE)
    is_v9 = bool(m_theme) and not is_writing
    if is_v9:
        field_matrix = {k: dict(v) for k, v in field_matrix.items()}
        for pt_ in ('封面', '原文齐读'):
            field_matrix[pt_]['禁用'] = [f for f in field_matrix[pt_]['禁用'] if f != '配图建议']

    # 页编号
    ids = [int(m.group(1)) for m in re.finditer(r'^## P(\d+) \|', text, re.MULTILINE)]
    # 常驻校验：P 编号连续不跳号、不重复（工具自排，每节课从 P01 起；本脚本按单文件校验，天然适配）
    dups = {x for x in ids if ids.count(x) > 1}
    if dups:
        errs.append(f'[P] 编号重复: {sorted(dups)}')
    for a, b in zip(ids, ids[1:]):
        if b != a + 1:
            errs.append(f'[P] 编号不连续: P{a} 之后是 P{b}（应为 P{a+1}）')
    # 可选：额外断言 P 落在指定区间
    if expect_range and ids != list(range(expect_range[0], expect_range[1]+1)):
        errs.append(f'[P] 期望区间 {expect_range}, 实际 {ids}')

    # 页型
    for m in re.finditer(r'^## P(\d+) \| 页型:(\S+)', text, re.MULTILINE):
        if m.group(2) not in valid_types:
            errs.append(f'[P{m.group(1)}] 非法页型: {m.group(2)}')

    # 眉标禁课型
    for m in re.finditer(r'眉标：(.+)', text):
        for word in FORBID_KEYWORDS_IN_EYEBROW:
            if word in m.group(1):
                errs.append(f'[眉标] 含课型: {m.group(1).strip()}')

    # v1.2 环节标题相关校验：序号一致性 + 相邻禁连
    section_pages = []  # [(pid_int, title)]
    pid_to_type = []    # [(pid_int, page_type)] 按出现顺序
    for m in re.finditer(r'^## P(\d+) \| 页型:(\S+)', text, re.MULTILINE):
        pid_to_type.append((int(m.group(1)), m.group(2)))
    pages_split = re.split(r'\n## P', text)
    for p in pages_split[1:]:
        h = re.search(r'^(\d+) \| 页型:环节标题', p)
        if not h: continue
        ti = re.search(r'标题：(.+)', p)
        section_pages.append((int(h.group(1)), ti.group(1).strip() if ti else ''))

    # C1：单环节课时不应带"一、"前缀；多环节课时序号 1→N 不跳号
    SECTION_NUMERALS = ['一、','二、','三、','四、','五、','六、']
    if len(section_pages) == 1:
        _, title = section_pages[0]
        if any(title.startswith(n) for n in SECTION_NUMERALS):
            errs.append(f'[环节序号] 单环节课时标题不应带"一、"前缀: "{title}"')
    elif len(section_pages) >= 2:
        for i, (pid, title) in enumerate(section_pages):
            expected = SECTION_NUMERALS[i]
            if not title.startswith(expected):
                errs.append(f'[环节序号] P{pid} 第 {i+1} 个环节应以"{expected}"开头，实际: "{title}"')
        if len(section_pages) > 4:
            warns.append(f'[环节序号] 单课时环节数={len(section_pages)} 超过推荐上限 4')

    # C2：禁止两个相邻的环节标题页
    for i in range(len(pid_to_type) - 1):
        if pid_to_type[i][1] == '环节标题' and pid_to_type[i+1][1] == '环节标题':
            errs.append(f'[环节连续] P{pid_to_type[i][0]} 与 P{pid_to_type[i+1][0]} 均为环节标题，禁止相邻')

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

        # 四图网格变体：引导问题页带 ≥2 条配图建议时，要点改由各格题面承载、不再必填
        img_sug_count = len(re.findall(r'^配图建议[:：]', p, re.MULTILINE))
        is_image_grid = (pt == '引导问题' and img_sug_count >= 2)

        # 字段冲突矩阵
        rules = field_matrix.get(pt, {})
        for must in rules.get('必填', []):
            if is_image_grid and must == '要点':
                continue  # 网格页豁免要点必填
            if must == '要点' and '要点样式：对比' in p:
                continue  # 对比版式内容写在 左/右正文
            if f'{must}：' not in p:
                errs.append(f'[P{pid} {pt}] 缺必填字段: {must}')
        for ban in rules.get('禁用', []):
            if f'{ban}：' in p:
                errs.append(f'[P{pid} {pt}] 出现禁用字段: {ban}')

        if is_v9:
            for sug in re.findall(r'^配图建议[:：]\s*(.+)$', p, re.MULTILINE):
                if sug.strip() in ('无', '无配图', '—'):
                    body_m = re.search(r'正文：([\s\S]*?)(?=\n配图建议|\n要点|\Z)', p)
                    long_quote = pt == '原文齐读' and body_m and len(body_m.group(1)) > 150
                    if pt in ('封面', '引导问题', '原文齐读') and not long_quote:
                        warns.append(f'[P{pid} {pt}] 新样式此页应配图，却写了「无」')
                    continue
                if re.search(r'插\s*[=＝]\s*(封面|插-\d+)', sug):
                    pass    # 原书插图／书封：不生图，形=、画面= 可省
                elif not re.search(r'形\s*[=＝]\s*(抠图|场景)', sug):
                    errs.append(f'[P{pid} {pt}] 配图建议缺 形=抠图|场景')
                if not re.search(r'插\s*[=＝]', sug) and not re.search(r'画面\s*[=＝]', sug):
                    errs.append(f'[P{pid} {pt}] 配图建议缺 画面=（生图描述）')
                if re.search(r'书内\s*P|P\d+', sug.split('画面')[0]):
                    errs.append(f'[P{pid} {pt}] 配图建议写了页码（档案无页码，改写章节）')
            if pt in ('引导问题', '要点小结') and '要点样式：时间轴' not in p and not re.search(r'^配图建议[:：]', p, re.MULTILINE):
                warns.append(f'[P{pid} {pt}] 新样式此页应配图，缺配图建议')
            if pt == '原文齐读' and re.search(r'节选自.*P\d+', p):
                errs.append(f'[P{pid} {pt}] 出处写了页码（档案无页码，只写章节）')

        # 要点用 - 列表
        kp = re.search(r'要点：\s*\n?([\s\S]+?)(?=\n[^-\s]|\Z)', p)
        if kp and '/' in kp.group(1).split('\n')[0] and '- ' not in kp.group(1):
            errs.append(f'[P{pid}] 要点用 / 分隔(旧格式)')

        # 填空表格答案标记 {{}} 配对校验（避免漏写半个括号导致渲染错位）
        if pt == '填空表格' and (p.count('{{') or p.count('}}')):
            n_open, n_close = p.count('{{'), p.count('}}')
            if n_open != n_close:
                errs.append(f'[P{pid} {pt}] 答案标记花括号不配对：左 {n_open} / 右 {n_close}')

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
