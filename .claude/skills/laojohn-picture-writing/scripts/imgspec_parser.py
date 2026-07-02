# -*- coding: utf-8 -*-
"""
imgspec_parser —— 解析「看图写话详案」文末「生图工单」里的 imgspec 规格块，
并扫描正文里的 `【图位:编号】` 占位标记。纯标准库、无网络、无第三方依赖。

被 generate_images.py / insert_images_docx.py 复用；也可单独跑做解析自测：
    PYTHONUTF8=1 python imgspec_parser.py <详案.md>
"""
import re
import sys
import os

# 已知字段名（去掉括号补充说明、去掉空格后比对）。出现在这一集合里的「X：」才算新字段，
# 否则视为上一字段的续行——这样生图提示词多行文本、□ 清单行、允许项列表都能正确归属。
KNOWN_FIELDS = {
    '编号', '角色', '环节', '承担训练点',
    '生图提示词', '必须可见元素清单', '允许但不强制', '风格/比例',
    '支持句式', '一句话画面', '验收', '时间线索', '引用资产', '说明',
}

# 角色枚举
ROLE_ANCHOR = '锚图'
ROLE_LIBRARY = '例库图'
ROLE_FORMAT = '格式图'

_FENCE_RE = re.compile(r'```imgspec\s*\n(.*?)```', re.S)
_FIELD_RE = re.compile(r'^[ \t]*([^\s:：][^:：]*?)[：:][ \t]*(.*)$')
_PLACEHOLDER_RE = re.compile(r'【图位[：:]\s*([锚例格]-\d+)')
_CODE_RE = re.compile(r'^\s*([锚例格]-\d+)\s*$')


def _norm_label(label):
    """把『风格 / 比例』『生图提示词（可直接复制喂工具）』归一成 KNOWN_FIELDS 里的键。"""
    label = re.sub(r'（.*?）', '', label)      # 去全角括号补充
    label = re.sub(r'\(.*?\)', '', label)       # 去半角括号补充
    label = label.replace(' ', '').replace('\t', '')
    return label.strip()


class ImgSpec:
    """一个图位规格。字段缺失则为 '' 或 []。"""
    def __init__(self):
        self.fields = {}        # 归一字段名 -> 文本值
        self.must_see = []      # 必须可见元素清单（□ 去前缀后的纯文本列表）
        self.raw = ''           # 原始块文本

    # —— 便捷属性 ——
    @property
    def code(self):
        return self.fields.get('编号', '').strip()

    @property
    def role(self):
        return self.fields.get('角色', '').strip()

    @property
    def prompt(self):
        return self.fields.get('生图提示词', '').strip()

    @property
    def style(self):
        return self.fields.get('风格/比例', '').strip()

    @property
    def time_clue(self):
        return self.fields.get('时间线索', '').strip()

    @property
    def one_line(self):
        return self.fields.get('一句话画面', '').strip()

    @property
    def support_pattern(self):
        return self.fields.get('支持句式', '').strip()

    @property
    def is_anchor(self):
        return self.role == ROLE_ANCHOR

    @property
    def is_library(self):
        return self.role == ROLE_LIBRARY

    @property
    def is_format(self):
        return self.role == ROLE_FORMAT

    def build_prompt(self, enforce_must_see=False):
        """组装喂生图工具的最终提示词：提示词 + 风格/比例（+ 锚图可选把必须可见清单逐条拼入）。"""
        parts = []
        if self.prompt:
            parts.append(self.prompt)
        if self.style:
            parts.append('风格与比例：' + self.style)
        if enforce_must_see and self.must_see:
            parts.append('画面必须同时清晰包含以下全部元素：' + '；'.join(self.must_see) + '。')
        return '\n'.join(parts).strip()

    def __repr__(self):
        return f'<ImgSpec {self.code} {self.role} must_see={len(self.must_see)}>'


def _parse_block(block_text):
    spec = ImgSpec()
    spec.raw = block_text
    cur = None                      # 当前字段名（归一后）
    collecting_list = False         # 是否在收集 □ 清单
    for line in block_text.splitlines():
        if not line.strip():
            continue
        m = _FIELD_RE.match(line)
        is_new_field = False
        if m:
            norm = _norm_label(m.group(1))
            if norm in KNOWN_FIELDS:
                is_new_field = True
        if is_new_field:
            cur = norm
            val = m.group(2).strip()
            spec.fields[cur] = val
            collecting_list = (cur == '必须可见元素清单')
            # 同名字段若行尾即有值（如『允许但不强制: …』）直接存；清单字段值通常为空、随后是 □ 行
            continue
        # 续行：归属当前字段
        stripped = line.strip()
        if collecting_list and stripped.startswith('□'):
            item = stripped.lstrip('□').strip()
            if item:
                spec.must_see.append(item)
            continue
        if cur:
            # 多行文本字段（生图提示词等）拼接
            prev = spec.fields.get(cur, '')
            spec.fields[cur] = (prev + ('\n' if prev else '') + stripped).strip()
    return spec


def parse_worktickets(md_text):
    """返回详案文末生图工单里全部 ImgSpec（按出现顺序）。"""
    specs = []
    for block in _FENCE_RE.findall(md_text):
        spec = _parse_block(block)
        if spec.code:
            specs.append(spec)
    return specs


def scan_placeholders(md_text):
    """返回正文里 `【图位:编号】` 占位的 [(编号, 行号从1起), ...]，按出现顺序。"""
    out = []
    for i, line in enumerate(md_text.splitlines(), 1):
        for code in _PLACEHOLDER_RE.findall(line):
            out.append((code, i))
    return out


def load(md_path):
    """读详案 .md，返回 (specs, placeholders, md_text)。"""
    with open(md_path, encoding='utf-8') as f:
        text = f.read()
    return parse_worktickets(text), scan_placeholders(text), text


def image_dir(md_path):
    """生成图的统一落点：<详案目录>/<详案stem>/图位/ ；两脚本共用此口径。"""
    d = os.path.dirname(os.path.abspath(md_path))
    stem = os.path.splitext(os.path.basename(md_path))[0]
    return os.path.join(d, stem, '图位')


def image_path(md_path, code):
    """某编号图位的 png 路径。"""
    return os.path.join(image_dir(md_path), code + '.png')


def _selfcheck(md_path):
    specs, placeholders, _ = load(md_path)
    print(f'== 解析 {os.path.basename(md_path)} ==')
    print(f'工单规格块：{len(specs)} 个')
    anchors = [s for s in specs if s.is_anchor]
    libs = [s for s in specs if s.is_library]
    fmts = [s for s in specs if s.is_format]
    print(f'  锚图 {len(anchors)}：{[s.code for s in anchors]}')
    print(f'  例库图 {len(libs)}：{[s.code for s in libs]}')
    print(f'  格式图 {len(fmts)}：{[s.code for s in fmts]}')
    for s in anchors:
        print(f'  · {s.code} 必须可见清单 {len(s.must_see)} 项：')
        for it in s.must_see:
            print(f'      - {it}')
    used = [c for c, _ in placeholders]
    print(f'正文【图位:】占位：{len(placeholders)} 处，去重 {sorted(set(used))}')
    spec_codes = {s.code for s in specs}
    used_codes = set(used)
    missing_spec = used_codes - spec_codes        # 正文引用了、工单却没有
    unused_spec = spec_codes - used_codes          # 工单有、正文没用（格式图正常会缺）
    print(f'正文引用但工单缺规格：{sorted(missing_spec) or "无"}')
    print(f'工单有但正文未引用：{sorted(unused_spec) or "无"}')
    return specs, placeholders


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('用法: python imgspec_parser.py <详案.md>')
        sys.exit(1)
    _selfcheck(sys.argv[1])
