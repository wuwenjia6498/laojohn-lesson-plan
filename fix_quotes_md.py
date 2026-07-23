# -*- coding: utf-8 -*-
"""
fix_quotes_md.py
把课案 MD 文件里的 ASCII 直引号（U+0022 / U+0027）批量转换为中文弯引号。
逐行处理，逐字符转换，与 md_to_laojohn_docx.py 里的 smart_quotes 逻辑完全对齐。
"""
import sys
import os
import re

FILES = [
    r'e:\laojohn-lesson-plan\读书会详案输出\洞-课案详案.md',
    r'e:\laojohn-lesson-plan\读书会详案输出\俗世奇人-课案详案.md',
    r'e:\laojohn-lesson-plan\读书会详案输出\手斧男孩-课案详案.md',
]


def smart_quotes_line(text: str) -> str:
    """逐字符把 ASCII 直引号转为中文弯引号（逐行独立处理，引号对在行内闭合）。"""
    result = []
    d_open = True
    s_open = True
    for k, ch in enumerate(text):
        if ch == '\x22':   # ASCII 双引号 U+0022
            result.append('\u201c' if d_open else '\u201d')
            d_open = not d_open
        elif ch == '\x27':  # ASCII 单引号 U+0027
            prev_alpha = k > 0 and text[k - 1].isascii() and text[k - 1].isalpha()
            next_alpha = (k + 1 < len(text)
                          and text[k + 1].isascii() and text[k + 1].isalpha())
            if prev_alpha and next_alpha:   # 英文撇号（don't），保持原样
                result.append(ch)
            else:
                result.append('\u2018' if s_open else '\u2019')
                s_open = not s_open
        else:
            result.append(ch)
    return ''.join(result)


def fix_file(path: str) -> None:
    if not os.path.exists(path):
        print(f'[跳过] 文件不存在: {path}')
        return
    text = open(path, encoding='utf-8').read()
    before_dq = text.count('\x22')
    before_sq = text.count('\x27')
    if before_dq == 0 and before_sq == 0:
        print(f'[已正常] {os.path.basename(path)}（无 ASCII 直引号，跳过）')
        return
    fixed_lines = [smart_quotes_line(line) for line in text.splitlines(keepends=True)]
    fixed_text = ''.join(fixed_lines)
    after_dq = fixed_text.count('\x22')
    after_sq = fixed_text.count('\x27')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fixed_text)
    print(f'[已修复] {os.path.basename(path)}')
    print(f'         ASCII双引号: {before_dq} → {after_dq}')
    print(f'         ASCII单引号: {before_sq} → {after_sq}')
    print(f'         中文弯双引号: {fixed_text.count(chr(0x201c))}/{fixed_text.count(chr(0x201d))} (左/右)')


if __name__ == '__main__':
    targets = sys.argv[1:] if len(sys.argv) > 1 else FILES
    for f in targets:
        fix_file(f)
    print('\n全部处理完毕。')
