# -*- coding: utf-8 -*-
import os

files = [
    r'e:\laojohn-lesson-plan\读书会详案输出\洞-课案详案.md',
    r'e:\laojohn-lesson-plan\读书会详案输出\俗世奇人-课案详案.md',
    r'e:\laojohn-lesson-plan\读书会详案输出\手斧男孩-课案详案.md',
    r'e:\laojohn-lesson-plan\写作课详案输出\三下-身边那些有特点的人-写作课详案.md',
]

for f in files:
    if not os.path.exists(f):
        print(f'NOT FOUND: {f}')
        continue
    text = open(f, encoding='utf-8').read()
    ascii_dq  = text.count('\x22')   # U+0022 ASCII直双引号
    ascii_sq  = text.count('\x27')   # U+0027 ASCII直单引号
    curly_l   = text.count('\u201c') # 中文左双 "
    curly_r   = text.count('\u201d') # 中文右双 "
    sq_l      = text.count('\u2018') # 中文左单 '
    sq_r      = text.count('\u2019') # 中文右单 '
    name = os.path.basename(f)
    print(f'=== {name} ===')
    print(f'  ASCII直双引号(U+0022): {ascii_dq}')
    print(f'  ASCII直单引号(U+0027): {ascii_sq}')
    print(f'  中文左双引号 \u201c (U+201C): {curly_l}')
    print(f'  中文右双引号 \u201d (U+201D): {curly_r}')
    print(f'  中文左单引号 \u2018 (U+2018): {sq_l}')
    print(f'  中文右单引号 \u2019 (U+2019): {sq_r}')
    if ascii_dq > 0:
        lines = text.splitlines()
        shown = 0
        print(f'  -- 含ASCII直双引号的行（前5处）--')
        for i, line in enumerate(lines):
            if '\x22' in line:
                print(f'  [行{i+1}] {line[:100]}')
                shown += 1
                if shown >= 5:
                    remaining = sum(1 for ln in lines[i+1:] if '\x22' in ln)
                    print(f'  ... 还有 {remaining} 行')
                    break
    if ascii_sq > 0:
        print(f'  -- 含ASCII直单引号(U+0027)的行（前5处）--')
        lines = text.splitlines()
        shown = 0
        for i, line in enumerate(lines):
            if '\x27' in line:
                print(f'  [行{i+1}] {line[:100]}')
                shown += 1
                if shown >= 5:
                    remaining = sum(1 for ln in lines[i+1:] if '\x27' in ln)
                    print(f'  ... 还有 {remaining} 行')
                    break
    print()
