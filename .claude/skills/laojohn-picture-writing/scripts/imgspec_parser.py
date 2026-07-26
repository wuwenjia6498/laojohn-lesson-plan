# -*- coding: utf-8 -*-
"""
imgspec_parser —— 解析「看图写话详案」文末「生图工单」里的 imgspec 规格块，
并扫描正文里的 `【图位:编号】` 占位标记。纯标准库、无网络、无第三方依赖。

图位口径（2026-07-26 三图位定案）：主-0N 主图 ／ 练-0N 练笔图 ／ 备-0N 备选图 ／ 格-0N 格式图；
旧前缀 锚-／例- 保留兼容位。自测输出含「三图位齐备」与「意外点项」两项机检。

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
    '同族关系',            # 练笔图必填：与主图的「同族异时」关系（同角色同场景·下一时刻）
    '验收附加',            # 可选：该图专属的验收附加要求（人数、画面干净度等），缺省见 generate_images
}

# 角色枚举（2026-07-26 晚：一课三图位定案，见 references/image-spec.md §一课三图位）。
# 编号前缀同步改名：主-0N（主图）／练-0N（练笔图）／备-0N（备选图）／格-0N（格式图）；
# 旧前缀 锚-0N／例-0N 与旧角色名「锚图／例库图」由下面的别名与正则兼容位继续认（旧稿不报错）。
ROLE_MAIN = '主图'
ROLE_PRACTICE = '练笔图'
ROLE_ALT = '备选图'
ROLE_FORMAT = '格式图'
_ROLE_ALIASES = {
    '锚图': ROLE_MAIN, '例库图': ROLE_ALT,
    '备用图': ROLE_ALT,          # 规则文用「备用图」，仓内口径统一为「备选图」
    '练习图': ROLE_PRACTICE, '练笔用图': ROLE_PRACTICE,
}

# —— 全局画风令牌（运行时事实源在这里；人读文档见 references/style-tokens.md，两处必须一字一致）——
# 收成全局两档的原因：风格若散在每张图的「生图提示词」里各写各的，只会漂到模型默认的
# 塑料感儿童插画档。主图定调、其余靠图生图跟随，所以真正要拉起来的是主图这一张。
# 主图档收在「可读」——学生要数要素、圈画面，可读性优先于美观（硬红线）。
# **练笔图与主图同走 clean 档**：学生当堂写作要对着它数细节、回溯任务提示，可读性同样是硬要求。
MAIN_STYLE_TOKEN = (
    '画风：柔和的水彩淡彩叠加彩色铅笔质感的手绘插画，看得见纸张纹理与自然笔触，'
    '不要矢量扁平风、不要塑料光泽、不要均匀渐变；线条轻盈、粗细有变化，'
    '不要每个物体都描一圈同样粗细的黑色轮廓；配色低饱和、以柔和的暖色系为主，'
    '只保留一处克制的强调色，不要糖果色、荧光色、不要整体高饱和拉满；'
    '光线是柔和的自然方向光，带轻微的环境光与柔和投影，画面有空气感、有主次虚实。'
    '同时保证可读：主角与每一个要素都清晰、边缘可辨，构图干净、留白充足，'
    '孩子要能一眼看清、数得出、圈得住，氛围一律服从可读。'
)
# 备选图档基调与主图同源（否则图生图跟随会打架），只在收尾放开氛围。
ALT_STYLE_TOKEN = (
    '画风：柔和的水彩淡彩叠加彩色铅笔质感的手绘插画，看得见纸张纹理与自然笔触，'
    '不要矢量扁平风、不要塑料光泽、不要均匀渐变；线条轻盈、粗细有变化，'
    '不要每个物体都描一圈同样粗细的黑色轮廓；配色低饱和、以柔和的暖色系为主，'
    '只保留一处克制的强调色，不要糖果色、荧光色、不要整体高饱和拉满；'
    '光线是柔和的自然方向光，带轻微的环境光与柔和投影，光影可以更丰富、'
    '氛围可以更浓一些，但仍要看起来与本课主图出自同一位插画师、同一套绘本。'
)

_FENCE_RE = re.compile(r'```imgspec\s*\n(.*?)```', re.S)
_FIELD_RE = re.compile(r'^[ \t]*([^\s:：][^:：]*?)[：:][ \t]*(.*)$')
# 编号前缀字符集：主/练/备/格 为现行口径，锚/例 为旧稿兼容位（勿删，存量详案未迁完）。
# 三处正则同一口径：本文件两条 + insert_images_docx.py 的 _PLACE_RE，改一处必须同步。
_PLACEHOLDER_RE = re.compile(r'【图位[：:]\s*([主练备格锚例]-\d+)')
_CODE_RE = re.compile(r'^\s*([主练备格锚例]-\d+)\s*$')
# 「意外点」项的识别前缀：清单项写成 `□ 意外点＝…` 才能被机检认出（判有没有写，不判画得对不对）。
_SURPRISE_RE = re.compile(r'^意外点\s*[＝=：:]')


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
        raw = self.fields.get('角色', '').strip()
        return _ROLE_ALIASES.get(raw, raw)

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
    def accept(self):
        """备选图「验收:」条款。曾长期只解析不使用（验收项只取支持句式/一句话画面），
        导致规格里收紧的条款从未被机器验过——例-02 的动作与地点失配正是这样漏过去的。"""
        return self.fields.get('验收', '').strip()

    @property
    def extra_rule(self):
        """该图专属的「验收附加:」要求。曾把「画面只能有一个小孩」硬编码在 generate_images 里，
        与「两个孩子有互动（语言有对象）」这类规格直接打架，故改为规格驱动、缺省不含人数约束。"""
        return self.fields.get('验收附加', '').strip()

    @property
    def kinship(self):
        """练笔图「同族关系:」——与主图的同族异时说明（同角色同场景·下一时刻）。"""
        return self.fields.get('同族关系', '').strip()

    @property
    def surprise(self):
        """清单里的「意外点＝…」项（四问类主图的一票否决项）；没写则为 ''。

        清单项常带 Markdown 强调（`□ **意外点＝…**`），故比对前先剥掉行首的 * 与空白——
        否则加粗写法会被判成「没写意外点」。"""
        for it in self.must_see:
            if _SURPRISE_RE.match(it.strip().lstrip('*').strip()):
                return it.strip()
        return ''

    @property
    def is_main(self):
        return self.role == ROLE_MAIN

    @property
    def is_practice(self):
        return self.role == ROLE_PRACTICE

    @property
    def is_alt(self):
        return self.role == ROLE_ALT

    @property
    def is_format(self):
        return self.role == ROLE_FORMAT

    @property
    def is_strict(self):
        """严格验收通道＝主图 + 练笔图。练笔图承担学生当堂写作，其清单要撑住任务提示与
        过关判定例句，宽规格不够，故与主图同档逐项核查。"""
        return self.is_main or self.is_practice

    def build_prompt(self, enforce_must_see=False):
        """组装喂生图工具的最终提示词：提示词 + 风格/比例（+ 严格档可选把必须可见清单逐条拼入）
        + 按角色自动追加全局画风令牌（主图/练笔图 clean 档 / 备选图 atmos 档）。

        画风令牌统一在这里注入，规格里不再逐图写风格形容词——见 references/style-tokens.md。
        `风格/比例` 字段保留原样拼接（它管的是比例/横版，与令牌不冲突）。"""
        parts = []
        if self.prompt:
            parts.append(self.prompt)
        if self.style:
            parts.append('风格与比例：' + self.style)
        if enforce_must_see and self.must_see:
            parts.append('画面必须同时清晰包含以下全部元素：' + '；'.join(self.must_see) + '。')
        if self.is_strict:
            parts.append(MAIN_STYLE_TOKEN)
        elif self.is_alt:
            parts.append(ALT_STYLE_TOKEN)
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
    mains = [s for s in specs if s.is_main]
    pracs = [s for s in specs if s.is_practice]
    alts = [s for s in specs if s.is_alt]
    fmts = [s for s in specs if s.is_format]
    print(f'  主图 {len(mains)}：{[s.code for s in mains]}')
    print(f'  练笔图 {len(pracs)}：{[s.code for s in pracs]}')
    print(f'  备选图 {len(alts)}：{[s.code for s in alts]}')
    print(f'  格式图 {len(fmts)}：{[s.code for s in fmts]}')
    for s in mains + pracs:
        print(f'  · {s.code}（{s.role}）必须可见清单 {len(s.must_see)} 项：')
        for it in s.must_see:
            print(f'      - {it}')
    # —— 三图位齐备（image-spec.md §一课三图位硬门）——
    lack = [name for name, got in (('主图', mains), ('练笔图', pracs), ('备选图', alts)) if not got]
    print(f'三图位齐备：{"齐" if not lack else "缺 " + "、".join(lack)}')
    for s in pracs:
        print(f'  练笔图 {s.code} 同族关系：{s.kinship or "**未写（须补：同角色同场景·下一时刻）**"}')
    # —— 意外点（四问类主图的一票否决项；机检只判「清单里有没有写」）——
    for s in mains:
        print(f'  主图 {s.code} 意外点项：{s.surprise or "无（四问类课必须有，其余课型不强制）"}')
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
