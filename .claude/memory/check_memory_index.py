# -*- coding: utf-8 -*-
"""记忆索引防回弹机检（2026-09-01 立）。

背景：MEMORY.md 有 24.4KB 读取上限，超限时尾部被静默截断（不报错，
0901 实际发生过——「已交付归档」区整区丢失）。两人双机都在追加行，
且加条目的多是 AI（任务收尾写记忆时），人无从知道时机——故本脚本
已挂 SessionStart hook（`.claude/settings.json`，随 git 双机生效）：
每次会话启动自动以 --quiet 跑一遍，全绿沉默、有 WARN/ERROR 才出声。
人工手跑（不带参数看全量报告）：

    PYTHONUTF8=1 python .claude/memory/check_memory_index.py

检查六项（MEMORY.md 有两个读取上限：24.4KB 字符 + 200 行，超任一都静默截尾）：
  1. 总字符数：>17,500 WARN（该归档了，参照维护规则⑤：归档区外移 +
     长条目瘦身，先做快照）；>24,000 ERROR（逼近读取上限，尾部将被
     静默截断，必须立即归档）。
  2. 总行数：>150 WARN（删空行/同主题相邻条目并行）；>190 ERROR。
  3. 超长行：>300 字符的行逐条列出（INFO，人工判断——多链接合并
     条可容忍，小作文式条目应把细节下沉主题文件；单条钩子仍以≤200为度）。
  3. 断链：](xxx.md) 指向的文件不存在 → ERROR。
  4. 孤儿文件：memory 目录下未被 MEMORY.md 或任何主题文件引用（含
     [[name]] 双链）的 .md → INFO（不算错，提示可能忘了挂索引）。
     memory-index-* 快照/归档件豁免。
  5. 弯引号配对：U+201C/201D、U+2018/2019 计数应成对 → INFO
     （防 Write 工具吞弯引号后混入 ASCII 直引号）。

exit code：有 ERROR 返回 1，否则 0。路径取脚本自身所在目录，
用户目录与仓内 .claude/memory/ 是目录联接、写哪边都是同一份。
"""
import re
import sys
from pathlib import Path

WARN_CHARS = 17500
ERROR_CHARS = 24000
WARN_LINES = 150
ERROR_LINES = 190
LINE_CAP = 300
EXEMPT_PREFIX = 'memory-index-'

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    quiet = '--quiet' in sys.argv[1:]
    mem_dir = Path(__file__).resolve().parent
    index = mem_dir / 'MEMORY.md'
    if not index.exists():
        print('ERROR: 找不到 MEMORY.md（脚本应位于记忆目录内）')
        return 1

    text = index.read_bytes().decode('utf-8').replace('\r\n', '\n')
    lines = text.split('\n')
    errors, warns, infos = [], [], []

    # 1. 总字符数
    n = len(text)
    if n > ERROR_CHARS:
        errors.append(f'总字符数 {n} > {ERROR_CHARS}：逼近 24.4KB 读取上限，尾部将被静默截断，立即归档（先快照）')
    elif n > WARN_CHARS:
        warns.append(f'总字符数 {n} > {WARN_CHARS}：该归档了（归档区外移/长条目瘦身，先快照）')
    else:
        infos.append(f'总字符数 {n}（安全区，上限 24.4KB）')

    # 2. 总行数（200 行读取上限）
    ln = len(lines)
    if ln > ERROR_LINES:
        errors.append(f'总行数 {ln} > {ERROR_LINES}：逼近 200 行读取上限，尾部将被静默截断，立即压行')
    elif ln > WARN_LINES:
        warns.append(f'总行数 {ln} > {WARN_LINES}：该压行了（删空行/同主题相邻条目并行）')
    else:
        infos.append(f'总行数 {ln}（安全区，上限 200 行）')

    # 3. 超长行
    long_lines = [(i, l) for i, l in enumerate(lines, 1) if len(l) > LINE_CAP]
    for i, l in long_lines:
        infos.append(f'超长行 L{i}（{len(l)} 字符）: {l[:40]}…')

    # 3. 断链（仅查指向本目录 .md 的相对链接）
    links = set(re.findall(r'\]\(([^)/\\]+\.md)\)', text))
    for f in sorted(links):
        if not (mem_dir / f).exists():
            errors.append(f'断链: {f}')

    # 4. 孤儿文件（收集全目录引用：markdown 链接 + [[name]] 双链）
    referenced = set(links)
    for md in mem_dir.glob('*.md'):
        if md.name == 'MEMORY.md':
            continue
        body = md.read_bytes().decode('utf-8', errors='replace')
        referenced.update(re.findall(r'\]\(([^)/\\]+\.md)\)', body))
        referenced.update(m + '.md' for m in re.findall(r'\[\[([^\]#|]+)\]\]', body))
    for md in sorted(mem_dir.glob('*.md')):
        if md.name == 'MEMORY.md' or md.name.startswith(EXEMPT_PREFIX):
            continue
        if md.name not in referenced:
            infos.append(f'孤儿文件（无任何引用，可能忘挂索引）: {md.name}')

    # 5. 弯引号配对
    pairs = [('“', '”', '双引号'), ('‘', '’', '单引号')]
    for lo, hi, name in pairs:
        a, b = text.count(lo), text.count(hi)
        if a != b:
            warns.append(f'弯{name}不配对: 左 {a} / 右 {b}（可能被 Write 工具吞成 ASCII 直引号）')
    if text.count('"') > 0:
        infos.append(f'含 ASCII 双引号 {text.count(chr(34))} 处（索引正文应用弯引号或「」）')

    if quiet and not errors and not warns:
        return 0
    groups = (('ERROR', errors), ('WARN', warns)) if quiet else (
        ('ERROR', errors), ('WARN', warns), ('INFO', infos))
    for tag, items in groups:
        for msg in items:
            print(f'[{tag}] {msg}')
    if quiet:
        print('记忆索引机检告警——请按 .claude/memory/check_memory_index.py docstring 处置(归档/压行,先快照)')
    else:
        print(f'—— 检查完成: {len(errors)} ERROR / {len(warns)} WARN / {len(infos)} INFO')
    return 1 if errors else 0

if __name__ == '__main__':
    sys.exit(main())
