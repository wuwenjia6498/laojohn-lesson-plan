# -*- coding: utf-8 -*-
"""
generate_images —— 看图写话「自动生图闭环」驱动。

读详案 .md 文末生图工单 → 对每个锚图/例库图（跳过格式图）：
  ① 调 AiHubMix（OpenAI 兼容）文生图，存 <详案stem>/图位/<编号>.png
  ② 调多模态视觉模型，对照「必须可见元素清单」逐项验收
  ③ 锚图缺项 → 强调缺项改写提示词重生（≤max_retries）；仍缺则标「需人工」
     例库图宽松（只验能否撑句式/时间线索），缺项告警不强制重生
最后写 <详案stem>/图位/_验收报告.md，并打印汇总。

用法（需先设密钥）：
  export AIHUBMIX_API_KEY=sk-xxx        # 或写进 scripts/imggen.config.json
  PYTHONUTF8=1 python generate_images.py <详案.md> [--max-retries N] [--only 锚-01,例-03]

设计纪律（见 CLAUDE.md 受约束例外口）：规格是事实源、生成图必须服从规格；本步把门禁4
「真图 vs 必须可见清单」的终检自动化，但不取消人工最终抽查（视觉模型对隐性约束如季节判定弱）。
"""
import os
import sys
import json
import base64
import argparse

import imgspec_parser as ip

# ---- 配置 ----
# AiHubMix 的图像后端按模型分两条路（文档实测）：
#   · Gemini Nano Banana 系（gemini-*-image-preview）：走原生 google-genai 客户端，
#     base_url=gemini_base_url，用 aspect_ratio + image_size，无 images.generate。
#   · FLUX.1-Kontext-pro 等：走 OpenAI 兼容 images.generate（/v1/images/generations）。
# 验收始终走 /v1 chat.completions（base_url）。
DEFAULTS = {
    'base_url': 'https://aihubmix.com/v1',             # 验收 + flux 生图
    'gemini_base_url': 'https://aihubmix.com/gemini',  # gemini 生图（原生 genai）
    'image_model': 'gemini-3-pro-image-preview',       # 默认走 gemini 通道
    'vision_model': 'gpt-4o',                          # 多模态验收，/v1 兼容
    'aspect_ratio': '4:3',                             # gemini/flux 横版
    'image_size': '2K',                                # gemini 专用：1K/2K/4K
    'size': '1536x1024',                               # 仅 openai-images 通道(flux 忽略)
    'max_retries': 2,                                  # 锚图缺项最多重生次数
    'width_cm': 12.0,                                  # 回插用，generate 阶段仅透传记录
}
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'imggen.config.json')


def _ensure_pkg(pip_name, import_name):
    import importlib
    import subprocess
    try:
        importlib.import_module(import_name)
        return
    except ImportError:
        pass
    for args in (
        [sys.executable, '-m', 'pip', 'install', '-q', pip_name],
        [sys.executable, '-m', 'pip', 'install', '-q', '--user', pip_name],
    ):
        try:
            subprocess.check_call(args)
            importlib.import_module(import_name)
            return
        except Exception:
            continue
    print(f'[错误] 无法自动安装 {pip_name}，请手动 `pip install {pip_name}` 后重试。')
    sys.exit(1)


def is_gemini(model):
    return 'gemini' in (model or '').lower()


def load_config():
    cfg = dict(DEFAULTS)
    if os.path.exists(_CONFIG_FILE):
        try:
            with open(_CONFIG_FILE, encoding='utf-8') as f:
                cfg.update({k: v for k, v in json.load(f).items() if v is not None})
        except Exception as e:
            print(f'[警告] 读取 {os.path.basename(_CONFIG_FILE)} 失败，用默认值：{e}')
    # 密钥：环境变量优先，其次 config 文件
    key = os.environ.get('AIHUBMIX_API_KEY') or cfg.get('api_key')
    if not key:
        print('[错误] 未找到 AIHUBMIX_API_KEY（环境变量或 imggen.config.json 的 api_key）。')
        print('       设置后重试：export AIHUBMIX_API_KEY=sk-xxx')
        sys.exit(1)
    cfg['api_key'] = key
    return cfg


def make_client(cfg):
    """OpenAI 兼容客户端：用于验收（始终）+ flux 生图。"""
    _ensure_pkg('openai', 'openai')
    from openai import OpenAI
    return OpenAI(api_key=cfg['api_key'], base_url=cfg['base_url'])


# ---- 生图：按模型分流（gemini 原生 genai / flux 等 images.generate）----
_GENAI = {}


def _genai_client(cfg):
    if 'c' not in _GENAI:
        _ensure_pkg('google-genai', 'google.genai')
        from google import genai
        _GENAI['c'] = genai.Client(
            api_key=cfg['api_key'],
            http_options={'base_url': cfg['gemini_base_url']},
        )
    return _GENAI['c']


def _coerce_bytes(data):
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        return base64.b64decode(data)
    return None


def _gemini_image_bytes(resp):
    """从 genai 响应里取第一张图字节，兼容多种 SDK 形态。"""
    cands = getattr(resp, 'candidates', None) or []
    parts = []
    if cands:
        content = getattr(cands[0], 'content', None)
        parts = getattr(content, 'parts', None) or []
    if not parts:
        parts = getattr(resp, 'parts', None) or []
    for part in parts:
        inline = getattr(part, 'inline_data', None)
        if inline is not None:
            b = _coerce_bytes(getattr(inline, 'data', None))
            if b:
                return b
        as_img = getattr(part, 'as_image', None)   # 部分版本返回 PIL Image
        if callable(as_img):
            try:
                img = as_img()
                if img is not None:
                    import io
                    buf = io.BytesIO()
                    img.save(buf, format='PNG')
                    return buf.getvalue()
            except Exception:
                pass
    raise RuntimeError('Gemini 响应里未找到图像数据（检查模型 id / 额度 / 安全拦截）')


_STYLE_REF_INSTR = (
    '\n\n【画风参考】随附的参考图是本课的锚图。请**严格沿用参考图的绘画风格**——'
    '线条粗细与颜色、上色方式与笔触质感、色彩饱和度与明暗、人物造型比例与脸部画法、背景留白处理，都要与参考图看起来出自同一位插画师、同一套绘本。'
    '**只改变画面内容**（人物、场景、动作按上面的描述画），不要改变画风。'
    '参考图应有的质感：水彩淡彩叠彩铅的手绘感、看得见纸纹与笔触、线条粗细有变化、'
    '低饱和柔和暖色、柔和的自然方向光与轻微环境光。'
    '**严禁回弹到默认卡通档**：不要塑料光泽、不要均匀矢量渐变、不要全图均质黑描边、'
    '不要糖果色或高饱和拉满、不要多重生硬高光。'
)  # 负面清单与 references/style-tokens.md 一致：模型在图生图时最容易漂回默认儿童插画档，这一路要再钉一次。


def _gen_gemini(cfg, prompt, out_png, style_ref=None):
    from google.genai import types
    client = _genai_client(cfg)
    # 画风靠参考图锁定：纯文字描述控不住画风（同一句"绘本插画风"在不同题材上会漂成
    # 水彩晕染或粗描边矢量卡通），故例库图一律带锚图作参考图生成。
    contents = prompt
    if style_ref and os.path.isfile(style_ref):
        with open(style_ref, 'rb') as f:
            ref_bytes = f.read()
        contents = [
            types.Part.from_bytes(data=ref_bytes, mime_type='image/png'),
            prompt + _STYLE_REF_INSTR,
        ]
    resp = client.models.generate_content(
        model=cfg['image_model'],
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=['TEXT', 'IMAGE'],
            image_config=types.ImageConfig(
                aspect_ratio=cfg.get('aspect_ratio', '4:3'),
                image_size=cfg.get('image_size', '2K'),
            ),
        ),
    )
    return _gemini_image_bytes(resp)


def _openai_image_bytes(data0):
    b64 = getattr(data0, 'b64_json', None)
    if b64:
        return base64.b64decode(b64)
    url = getattr(data0, 'url', None)
    if url:
        import urllib.request
        with urllib.request.urlopen(url, timeout=120) as r:
            return r.read()
    raise RuntimeError('图像返回既无 b64_json 也无 url')


def _gen_openai_images(client, cfg, prompt, out_png):
    resp = client.images.generate(model=cfg['image_model'], prompt=prompt, n=1)
    return _openai_image_bytes(resp.data[0])


def generate_one(client, cfg, prompt, out_png, style_ref=None):
    """按 image_model 选后端生成并落盘。client 为 OpenAI 兼容客户端（gemini 通道不用它）。

    style_ref：画风参考图（本课锚图）。仅 gemini 通道支持；给了就走图生图锁画风。
    """
    if is_gemini(cfg['image_model']):
        img = _gen_gemini(cfg, prompt, out_png, style_ref)
    else:
        img = _gen_openai_images(client, cfg, prompt, out_png)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    with open(out_png, 'wb') as f:
        f.write(img)
    return out_png


# ---- 视觉验收 ----
_VERIFY_SYS = '你是严格的儿童绘本插画验收员。只依据图片本身回答，不臆测；输出严格 JSON，不要额外文字。'


def _verify_payload(png_path, items, extra_rule=''):
    with open(png_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    numbered = '\n'.join(f'{i+1}. {it}' for i, it in enumerate(items))
    instr = (
        '请逐项判断下面每个元素在图中是否清晰可见，并指出明显问题。\n'
        f'必须可见元素：\n{numbered}\n'
        + (f'额外硬性要求：{extra_rule}\n' if extra_rule else '')
        + '返回 JSON：{"items":[{"i":序号,"present":true/false,"note":"简述"}],'
          '"issues":["其它问题…"]}。present 仅在该元素清晰可辨时为 true。'
    )
    return b64, instr


def verify_image(client, cfg, png_path, items, extra_rule=''):
    """返回 dict：{present:[bool…], missing:[元素…], issues:[…], raw:str}。解析失败时保守判全缺。"""
    b64, instr = _verify_payload(png_path, items, extra_rule)
    try:
        resp = client.chat.completions.create(
            model=cfg['vision_model'],
            messages=[
                {'role': 'system', 'content': _VERIFY_SYS},
                {'role': 'user', 'content': [
                    {'type': 'text', 'text': instr},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/png;base64,{b64}'}},
                ]},
            ],
            temperature=0,
        )
        raw = resp.choices[0].message.content or ''
    except Exception as e:
        return {'present': [False] * len(items), 'missing': list(items),
                'issues': [f'验收调用失败：{e}'], 'raw': ''}
    data = _extract_json(raw)
    present = [False] * len(items)
    if data and isinstance(data.get('items'), list):
        for it in data['items']:
            try:
                idx = int(it.get('i', 0)) - 1
                if 0 <= idx < len(items):
                    present[idx] = bool(it.get('present'))
            except Exception:
                continue
    missing = [items[i] for i, p in enumerate(present) if not p]
    issues = data.get('issues', []) if data else []
    return {'present': present, 'missing': missing, 'issues': issues, 'raw': raw}


def _extract_json(text):
    text = text.strip()
    if text.startswith('```'):
        text = text.strip('`')
        text = text[text.find('{'):]
    a, b = text.find('{'), text.rfind('}')
    if a < 0 or b < 0:
        return None
    try:
        return json.loads(text[a:b + 1])
    except Exception:
        return None


# ---- 单图闭环 ----
def process_anchor(client, cfg, md_path, spec, log):
    items = spec.must_see
    extra = '画面只能有一个小孩；整体为低龄儿童绘本插画风、画面干净。'
    out = ip.image_path(md_path, spec.code)
    attempt, result = 0, None
    missing = list(items)
    while attempt <= cfg['max_retries']:
        prompt = spec.build_prompt(enforce_must_see=True)
        if attempt > 0 and missing:
            prompt += '\n特别注意：上一版缺失了以下元素，务必清晰画出：' + '；'.join(missing) + '。'
        log(f'  [{spec.code}] 生图第 {attempt+1} 次…')
        generate_one(client, cfg, prompt, out)
        result = verify_image(client, cfg, out, items, extra)
        missing = result['missing']
        if not missing:
            break
        log(f'    缺项：{missing}（将重生）' if attempt < cfg['max_retries'] else f'    仍缺：{missing}')
        attempt += 1
    passed = not result['missing']
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': attempt + 1,
            'items': items, 'present': result['present'], 'missing': result['missing'],
            'issues': result['issues'], 'png': out, 'manual': not passed}


def process_library(client, cfg, md_path, spec, log, style_ref=None):
    # 例库图轻量：验「能否支撑该句式 / 时间线索」，缺则告警不强制重生
    items = []
    if spec.support_pattern:
        items.append(f'画面能支撑句式「{spec.support_pattern}」所述场景')
    if spec.one_line:
        items.append(f'画面与「{spec.one_line}」一致')
    if spec.time_clue:
        items.append(f'含可推断时间的线索：{spec.time_clue}')
    if spec.accept:
        items.append(f'满足验收条款：{spec.accept}')
    if not items:
        items = ['画面内容与生图提示词一致']
    out = ip.image_path(md_path, spec.code)
    ref = style_ref if (style_ref and style_ref != out) else None
    log(f'  [{spec.code}] 生图{"（沿用锚图画风）" if ref else ""}…')
    generate_one(client, cfg, spec.build_prompt(), out, style_ref=ref)
    result = verify_image(client, cfg, out, items)
    passed = not result['missing']
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': 1,
            'items': items, 'present': result['present'], 'missing': result['missing'],
            'issues': result['issues'], 'png': out, 'manual': False}  # 例库图不拦交付


def verify_only(client, cfg, md_path, spec, log):
    """只验收已存在的图，绝不重生（--verify-only）。

    用于「规格收紧后回验」：改了必须可见元素清单，但图不该重画——重画会丢掉
    已人工核准的画面。缺图则记为需人工，不触发生成。
    """
    out = ip.image_path(md_path, spec.code)
    if not os.path.isfile(out):
        return {'code': spec.code, 'role': spec.role, 'passed': False, 'attempts': 0,
                'items': spec.must_see or ['（未生成）'], 'present': [], 'missing': spec.must_see or [],
                'issues': ['图不存在，未生成——本次为只验收模式，不代生图'],
                'png': out, 'manual': True}
    if spec.is_anchor:
        items = spec.must_see
        extra = '画面只能有一个小孩；整体为低龄儿童绘本插画风、画面干净。'
    else:
        items = []
        if spec.support_pattern:
            items.append(f'画面能支撑句式「{spec.support_pattern}」所述场景')
        if spec.one_line:
            items.append(f'画面与「{spec.one_line}」一致')
        if spec.time_clue:
            items.append(f'含可推断时间的线索：{spec.time_clue}')
        if spec.accept:
            items.append(f'满足验收条款：{spec.accept}')
        if not items:
            items = ['画面内容与生图提示词一致']
        extra = ''
    log(f'  [{spec.code}] 只验收（不重生）…')
    result = verify_image(client, cfg, out, items, extra)
    passed = not result['missing']
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': 0,
            'items': items, 'present': result['present'], 'missing': result['missing'],
            'issues': result['issues'], 'png': out, 'manual': spec.is_anchor and not passed}


def write_report(md_path, records, cfg):
    path = os.path.join(ip.image_dir(md_path), '_验收报告.md')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dims = (f'{cfg.get("aspect_ratio","")} {cfg.get("image_size","")}'.strip()
            if is_gemini(cfg['image_model']) else cfg.get('size', ''))
    lines = ['# 生图验收报告', '',
             f'- 源详案：`{os.path.basename(md_path)}`',
             f'- 生图模型：`{cfg["image_model"]}` · 验收模型：`{cfg["vision_model"]}` · 尺寸：{dims}',
             '']
    need_manual = [r for r in records if r['manual']]
    lines.append(f'**汇总：{len(records)} 图，{sum(r["passed"] for r in records)} 过，'
                 f'{len(need_manual)} 需人工复核。**')
    if need_manual:
        lines.append('需人工：' + '、'.join(r['code'] for r in need_manual))
    lines.append('')
    for r in records:
        flag = '✅ 过' if r['passed'] else ('⚠ 需人工' if r['manual'] else '⚠ 有告警')
        lines.append(f'## {r["code"]}（{r["role"]}） — {flag} · 生图 {r["attempts"]} 次')
        for it, p in zip(r['items'], r['present']):
            lines.append(f'- [{"x" if p else " "}] {it}')
        if r['issues']:
            lines.append(f'- 其它问题：{"；".join(str(x) for x in r["issues"])}')
        lines.append('')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('md_path')
    ap.add_argument('--max-retries', type=int, default=None)
    ap.add_argument('--only', default='', help='只生指定编号，逗号分隔，如 锚-01,例-03')
    ap.add_argument('--verify-only', action='store_true',
                    help='只按现行规格验收已有的图、绝不重生（规格收紧后回验用；缺图记为需人工，不代生）')
    args = ap.parse_args()

    cfg = load_config()
    if args.max_retries is not None:
        cfg['max_retries'] = args.max_retries

    specs, _, _ = ip.load(args.md_path)
    targets = [s for s in specs if s.is_anchor or s.is_library]
    if args.only:
        want = {x.strip() for x in args.only.split(',') if x.strip()}
        targets = [s for s in targets if s.code in want]
    if not targets:
        print('没有可生成的锚图/例库图（格式图跳过）。')
        return

    # 本课锚图＝全课画风基准；例库图带它做图生图，保证五张图一套画风
    anchor_png = None
    for s in specs:
        if s.is_anchor:
            cand = ip.image_path(args.md_path, s.code)
            if os.path.isfile(cand):
                anchor_png = cand
            break

    client = make_client(cfg)
    log = print
    if args.verify_only:
        print(f'共 {len(targets)} 图待验收（只验收模式：按现行规格核对已有的图，不重生、不覆盖）…')
    else:
        print(f'共 {len(targets)} 图待生成（锚图严格验收+重生，例库图轻量）…')
    records = []
    for s in targets:
        try:
            if args.verify_only:
                records.append(verify_only(client, cfg, args.md_path, s, log))
            elif s.is_anchor:
                records.append(process_anchor(client, cfg, args.md_path, s, log))
            else:
                records.append(process_library(client, cfg, args.md_path, s, log, style_ref=anchor_png))
        except Exception as e:
            print(f'  [{s.code}] 生成失败：{e}')
            records.append({'code': s.code, 'role': s.role, 'passed': False, 'attempts': 0,
                            'items': s.must_see or [], 'present': [], 'missing': s.must_see or [],
                            'issues': [f'异常：{e}'], 'png': ip.image_path(args.md_path, s.code),
                            'manual': True})
    report = write_report(args.md_path, records, cfg)
    passed = sum(r['passed'] for r in records)
    manual = sum(r['manual'] for r in records)
    print(f'\n完成：{passed}/{len(records)} 过，{manual} 需人工。图位目录：{ip.image_dir(args.md_path)}')
    print(f'验收报告：{report}')


if __name__ == '__main__':
    main()
