# -*- coding: utf-8 -*-
"""
generate_images —— 看图写话「自动生图闭环」驱动。

读详案 .md 文末生图工单 → 对每个主图/练笔图/备选图（跳过格式图与留白格「状态: 留白」）：
  ① 调 AiHubMix（OpenAI 兼容）文生图，存 <详案stem>/图位/<编号>.png
  ② 调多模态视觉模型，对照「必须可见元素清单」逐项验收
  ③ 主图与练笔图（严格档）缺项 → 强调缺项改写提示词重生（≤max_retries）；仍缺则标「需人工」
     备选图宽松（只验能否撑句式/时间线索），缺项告警不强制重生
生成顺序固定 主图 → 练笔图 → 备选图：主图定调，练笔图与备选图都带主图作参考图（图生图）。
练笔图与主图是「同族异时」（同角色同场景·下一时刻），角色一致性尤其依赖这张参考图。
最后写 <详案stem>/图位/_验收报告.md，并打印汇总。

用法（需先设密钥）：
  export AIHUBMIX_API_KEY=sk-xxx        # 或写进 scripts/imggen.config.json
  PYTHONUTF8=1 python generate_images.py <详案.md> [--max-retries N] [--only 主-01,练-01]

设计纪律（见 CLAUDE.md 受约束例外口）：规格是事实源、生成图必须服从规格；本步把门禁4
「真图 vs 必须可见清单」的终检自动化，但不取消人工最终抽查（视觉模型对隐性约束如季节判定弱）。
"""
import os
import re
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
    'max_retries': 2,                                  # 主图缺项最多重生次数
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
    '\n\n【画风参考】随附的参考图是本课的主图。请**严格沿用参考图的绘画风格**——'
    '线条粗细与颜色、上色方式与笔触质感、色彩饱和度与明暗、人物造型比例与脸部画法、背景留白处理，都要与参考图看起来出自同一位插画师、同一套绘本。'
    '**只改变画面内容**（人物、场景、动作按上面的描述画），不要改变画风。'
    '参考图应有的质感：水彩淡彩叠彩铅的手绘感、看得见纸纹与笔触、线条粗细有变化、'
    '低饱和柔和暖色、柔和的自然方向光与轻微环境光。'
    '**严禁回弹到默认卡通档**：不要塑料光泽、不要均匀矢量渐变、不要全图均质黑描边、'
    '不要糖果色或高饱和拉满、不要多重生硬高光。'
)  # 负面清单与 references/style-tokens.md 一致：模型在图生图时最容易漂回默认儿童插画档，这一路要再钉一次。


# —— 定妆图角色参照指令（B 级 · 2026-07-30 新增，与 _STYLE_REF_INSTR 语境不同勿混用）——
# _STYLE_REF_INSTR＝跟随「本课主图」（练笔图/备选图用，连比例一起带）；
# 这一条＝跟随「角色定妆图」（assets/角色册/妆-0N）：锁画风 + 锁角色身份，**比例明确不跟随参考图**。
# （曾有第三条 _ANCHOR_REF_INSTR＝A 级全期锚图链，只锁画风明拒角色：0728 停用、0730 摘除。
#  措辞正文仍在定妆图手工出图使用，落在 assets/角色册/角色设定.md §八·0「只锁画风措辞」。）
# 措辞主干为 0729 小试二已验版本（带妆-01，见 docs/handoff/小试结论_头身比收口-0729.md）。
#
# ⚠ 指令里**故意不提身体比例**（2026-07-30 拍板删除，勿加回）。曾有一句「身体比例不要跟随参考
#   图，按画面描述为准」，0730 用户 A/B 实测（PS 缩头版参考图，加/不加各 2 张）证实**加与不加
#   输出完全一致**——那句是死措辞。删它不是为了省字，是因为留着会让人以为比例能靠措辞调，从而
#   往措辞上想办法（＝厚涂改造十余轮的失败模式，见 references/style-tokens.md 已终止节）。
#
# **比例的唯一控制点是定妆图本身**：参考图会把画风、角色身份、身体比例一起带过来，这不是需要
#   拦的副作用、而是唯一有效的调节手段——要改场景图比例就去改定妆图（现行做法：PS 缩头后
#   同名覆盖母版），不要回来改这段指令。也不加正向句「请跟随参考图比例」：参考图本来就在带，
#   多一句是多一个未验变量，且有让模型连定妆图的直立站姿一起照抄的风险（场景图要各种动作）。
_CHAR_REF_PREFIX = '\n\n【角色参照】'   # process_strict 日志 tag 判据（格式化后的串没法 is 比较）
_CHAR_REF_INSTR_TMPL = (
    _CHAR_REF_PREFIX +
    '随附的参考图是「{name}」的角色定妆图。请沿用参考图的画风，'
    '与这个角色的身份特征——脸型、发型、主色、{anchor}。'
    '**严禁回弹到默认卡通档**：不要塑料光泽、不要均匀矢量渐变、不要全图均质黑描边、'
    '不要糖果色或高饱和拉满、不要多重生硬高光。'
)


# —— B 级参考图链：角色定妆图（2026-07-30 接线）——
# 角色册格式由 assets/角色册/角色设定.md 定义（谁定义格式谁给解析器——此处仅按其稳定模式抽取：
# `## N、<角色名>（…）` 标题 + 紧随裸代码块里的【辨识锚】段）。角色册与根目录 -0728.md 的
# 双副本问题（交接说明挂账 5.2）不在此解，脚本读 assets 落盘件。
_CHAR_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         'assets', '角色册')
_CHAR_SHEET = os.path.join(_CHAR_DIR, '角色设定.md')
_CHAR_FEED_DIR = os.path.join(_CHAR_DIR, '_喂图副本')   # 可再生产物，已 gitignore
_CHAR_FEED_LONG = 1500
_CHAR_REG = {}


def _load_char_registry():
    """角色名 → {'png': 定妆图母版路径, 'anchor': 辨识锚文本}。解析失败只降级不中断。"""
    if _CHAR_REG:
        return _CHAR_REG
    import glob
    for p in sorted(glob.glob(os.path.join(_CHAR_DIR, '妆-*_*.png'))):
        m = re.match(r'妆-\d+_(.+)\.png$', os.path.basename(p))
        if m:
            _CHAR_REG[m.group(1)] = {'png': p, 'anchor': ''}
    try:
        with open(_CHAR_SHEET, encoding='utf-8') as f:
            text = f.read()
        for name, info in _CHAR_REG.items():
            hm = re.search(r'^##\s*[^\n]*、' + re.escape(name) + r'（[^\n]*$', text, re.M)
            if not hm:
                continue
            block = re.search(r'```\n(.*?)```', text[hm.end():], re.S)
            if not block:
                continue
            am = re.search(r'【辨识锚】(.*?)(?=\n\s*【|\Z)', block.group(1), re.S)
            if am:
                info['anchor'] = ' '.join(am.group(1).split()).rstrip('。')
    except Exception as e:
        print(f'[告警] 解析角色册失败（定妆参考将降级为不带参考图）：{e}')
    return _CHAR_REG


def _feed_copy(master):
    """定妆图喂图副本：长边缩至 1500 + 转 RGB（交接说明 §3.3 无损衍生规格，不含内容修改）。

    母版一个字节不动；副本缺失或母版 mtime 更新时懒生成。母版单张 6~7MB、base64 后约 9MB，
    每张场景图都要带参考图，不缩会白烧带宽。"""
    _ensure_pkg('pillow', 'PIL')
    from PIL import Image
    stem = os.path.splitext(os.path.basename(master))[0]
    out = os.path.join(_CHAR_FEED_DIR, f'{stem}_1500.png')
    try:
        if (not os.path.isfile(out)) or os.path.getmtime(out) < os.path.getmtime(master):
            os.makedirs(_CHAR_FEED_DIR, exist_ok=True)
            im = Image.open(master)
            r = _CHAR_FEED_LONG / max(im.size)
            if r < 1:
                im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
            im.convert('RGB').save(out)
        return out
    except Exception as e:
        print(f'[告警] 喂图副本生成失败（本图降级为不带参考图）：{e}')
        return None


def char_ref(spec):
    """B 级：主图规格 `定妆参考: <角色名>` → (喂图副本路径, 已填辨识锚的指令)；不可用 → (None, None)。

    任何一环失败（角色名不在角色册/辨识锚解析不到/副本生成失败）都打告警并降级为不带参考图，
    不中断跑批——但绝不静默：A 级曾因空串静默停用、日志无异常被误判在工作（排查结论 0729 §一）。"""
    name = (spec.char_ref or '').strip()
    if not name or name == '无':
        return None, None
    reg = _load_char_registry()
    if name not in reg:
        print(f'  [告警] [{spec.code}] 定妆参考「{name}」在 assets/角色册/ 找不到定妆图，'
              '本图降级为不带参考图。')
        return None, None
    info = reg[name]
    if not info['anchor']:
        print(f'  [告警] [{spec.code}] 角色「{name}」的【辨识锚】未能从角色设定.md 解析，'
              '本图降级为不带参考图。')
        return None, None
    feed = _feed_copy(info['png'])
    if not feed:
        return None, None
    return feed, _CHAR_REF_INSTR_TMPL.format(name=name, anchor=info['anchor'])


def _gen_gemini(cfg, prompt, out_png, style_ref=None, ref_instr=None):
    from google.genai import types
    client = _genai_client(cfg)
    # 画风靠参考图锁定：纯文字描述控不住画风（同一句"绘本插画风"在不同题材上会漂成
    # 水彩晕染或粗描边矢量卡通），故备选图一律带主图作参考图生成。
    contents = prompt
    if style_ref and os.path.isfile(style_ref):
        with open(style_ref, 'rb') as f:
            ref_bytes = f.read()
        contents = [
            types.Part.from_bytes(data=ref_bytes, mime_type='image/png'),
            prompt + (ref_instr or _STYLE_REF_INSTR),
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


# ---- 后处理：裁掉生成图四边的空白带（2026-07-27 画风改造定案：白边走工程解）----
# 生成模型对「满幅出血」类措辞不完全服从（备-03 母图两轮实测均残留白带），故落盘后统一裁边；
# 令牌不再为白边加码，后续调令牌也不要再往里加满幅出血相关措辞（见 references/style-tokens.md）。
_TRIM_LUMA = 240        # 行/列判空白带：灰度均值下限
_TRIM_STD = 8           # 行/列判空白带：灰度标准差上限（均匀白带方差低；浅色画面内容方差高）
_TRIM_MAX_RATIO = 0.15  # 四边裁量合计超过任一边的 15% 判异常：不裁、告警（防整幅浅色图被误吃）


def trim_border(png_path):
    """裁掉图像四边的白色/纸底空白带，再以中心为基准裁回 4:3；原地覆写，只裁不缩放（绝不拉伸）。

    每次 generate_one 落盘后自动调用。从上/下/左/右四边分别向内逐行（列）扫描：
    灰度均值 > _TRIM_LUMA 且标准差 < _TRIM_STD 判为空白带，遇到第一行（列）不满足即停。
    """
    _ensure_pkg('pillow', 'PIL')
    from PIL import Image, ImageStat

    img = Image.open(png_path)
    w, h = img.size
    gray = img.convert('L')

    def blank(box):
        st = ImageStat.Stat(gray.crop(box))
        return st.mean[0] > _TRIM_LUMA and st.stddev[0] < _TRIM_STD

    top = 0
    while top < h and blank((0, top, w, top + 1)):
        top += 1
    bottom = h
    while bottom > top and blank((0, bottom - 1, w, bottom)):
        bottom -= 1
    left = 0
    while left < w and blank((left, 0, left + 1, h)):
        left += 1
    right = w
    while right > left and blank((right - 1, 0, right, h)):
        right -= 1

    cut_x, cut_y = left + (w - right), top + (h - bottom)
    if cut_x > w * _TRIM_MAX_RATIO or cut_y > h * _TRIM_MAX_RATIO:
        print(f'    [trim_border] 异常：判白量过大（横 {cut_x}px / 竖 {cut_y}px，'
              f'上限任一边 {int(_TRIM_MAX_RATIO * 100)}%），疑整幅浅色图被误判，不裁：'
              f'{os.path.basename(png_path)}')
        return png_path
    if cut_x == 0 and cut_y == 0:
        return png_path            # 无白边：不动原图（也不做 4:3 重裁）

    tw, th = right - left, bottom - top
    if tw * 3 > th * 4:            # 裁后偏宽 → 以中心收左右回 4:3
        nw = th * 4 // 3
        x0 = left + (tw - nw) // 2
        box = (x0, top, x0 + nw, bottom)
    else:                          # 裁后偏高（或恰 4:3）→ 以中心收上下
        nh = tw * 3 // 4
        y0 = top + (th - nh) // 2
        box = (left, y0, right, y0 + nh)
    img.crop(box).save(png_path)
    print(f'    [trim_border] 已裁白边：上{top} 下{h - bottom} 左{left} 右{w - right}px，'
          f'裁后 {box[2] - box[0]}x{box[3] - box[1]}（4:3）')
    return png_path


# 生图接口偶发服务端断连（实发 `Server disconnected without sending a response.`，
# 一次断连就废掉整轮闭环）。指数退避重试，纯标准库、不引依赖。
_RETRY_WAITS = (2, 6, 18)


def _with_retry(fn, what, log=print):
    import time
    last = None
    for i in range(len(_RETRY_WAITS) + 1):
        try:
            return fn()
        except Exception as e:
            last = e
            if i == len(_RETRY_WAITS):
                break
            log(f'    [网络重试 {i+1}/{len(_RETRY_WAITS)}] {what}：{e} → {_RETRY_WAITS[i]}s 后重试')
            time.sleep(_RETRY_WAITS[i])
    raise last


def generate_one(client, cfg, prompt, out_png, style_ref=None, ref_instr=None):
    """按 image_model 选后端生成并落盘。client 为 OpenAI 兼容客户端（gemini 通道不用它）。

    style_ref：参考图。仅 gemini 通道支持；给了就走图生图。
    ref_instr：随参考图附的指令。缺省 _STYLE_REF_INSTR（换内容·锁画风）；
               定向编辑要传 _EDIT_REF_INSTR（锁一切·只改一处），两者方向相反，勿混用。
    """
    name = os.path.basename(out_png)
    if is_gemini(cfg['image_model']):
        img = _with_retry(lambda: _gen_gemini(cfg, prompt, out_png, style_ref, ref_instr), name)
    else:
        img = _with_retry(lambda: _gen_openai_images(client, cfg, prompt, out_png), name)
    os.makedirs(os.path.dirname(out_png), exist_ok=True)
    with open(out_png, 'wb') as f:
        f.write(img)
    trim_border(out_png)
    return out_png


# —— 定向编辑指令（`--edit`）：与 _STYLE_REF_INSTR 方向相反，勿混用 ——
# _STYLE_REF_INSTR 是「换内容·锁画风」（出练笔图/备选图用）；这一条是「锁一切·只改一处」，
# 用于一张已人工核准的图只有某个局部不达标时（如手指指向落空、族裔画错），
# 从零重生会顺带丢掉上一版画对却难描述的东西（光影氛围、角色脸型），故走定向编辑。
_EDIT_REF_INSTR = (
    '\n\n【定向编辑·最小改动】随附的图是这个图位的现行真图。请**以它为基准做最小改动**：'
    '只按上面那一条要求改动指定之处，**其余一切原样保留**——所有人物的脸型、五官、表情、发型、衣着、'
    '身体朝向与姿态，所有物件的位置与形态，背景、构图、镜头、光线方向、投影、色调，以及画风与笔触质感，'
    '**都必须与参考图完全一致**。不要重新构图、不要移动或增删任何东西、不要改变画风、不要改变画面比例。'
    '除指定改动处之外，输出应当看起来就是同一张图。'
)


def _backup_png(out, suffix):
    """把现版复制进 图位/_历史/<编号><suffix>.png（重名自动 -2/-3…），返回备份路径。

    「不删除任何已有图片资产」是本线纪律：定点编辑就地覆写，改砸了要能拿回上一版。"""
    hist_dir = os.path.join(os.path.dirname(out), '_历史')
    os.makedirs(hist_dir, exist_ok=True)
    stem = os.path.splitext(os.path.basename(out))[0]
    backup = os.path.join(hist_dir, f'{stem}{suffix}.png')
    n = 2
    while os.path.exists(backup):
        backup = os.path.join(hist_dir, f'{stem}{suffix[:-1]}-{n}）.png')
        n += 1
    with open(out, 'rb') as f_in, open(backup, 'wb') as f_out:
        f_out.write(f_in.read())
    return backup




def process_edit(client, cfg, md_path, spec, edit_req, log):
    """定向编辑一张已存在的真图：只改 edit_req 描述的那一处，其余锁死。

    改完按该图位现行规格逐项复验（严格档才有 must_see）；编辑前的版本备份到
    图位/_历史/<编号>（编辑前）.png，符合「不删除任何已有图片资产」。"""
    out = ip.image_path(md_path, spec.code)
    if not os.path.isfile(out):
        raise RuntimeError(f'{spec.code} 还没有真图，定向编辑无从下手（先正常生图）')
    backup = _backup_png(out, '（编辑前）')
    log(f'  [{spec.code}] 现版已备份 → {os.path.basename(backup)}')
    log(f'  [{spec.code}] 定向编辑（锁一切·只改一处）…')
    generate_one(client, cfg, edit_req, out, style_ref=backup, ref_instr=_EDIT_REF_INSTR)
    items = spec.must_see if spec.is_strict else []
    if not items:
        return {'code': spec.code, 'role': spec.role, 'passed': True, 'attempts': 0, 'edits': 1,
                'items': ['（非严格档，未逐项复验）'], 'present': [True],
                'missing': [], 'extras': [], 'issues': [], 'png': out, 'manual': True}
    result = verify_image(client, cfg, out, items, strict_extra(spec),
                          whitelist=spec.prompt, deep=True)
    passed = not result['missing'] and not result['extras']   # missing 不含数量项（只报不拦）
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': 0, 'edits': 1,
            'items': items, 'present': result['present'], 'missing': result['missing'],
            'extras': result['extras'], 'counts': result['counts'], 'count_detail': result['count_detail'],
            'count_bad': result['count_bad'], 'count_uncertain': result['count_uncertain'],
            'poses': result['poses'], 'issues': result['issues'],
            'png': out, 'manual': True}   # 编辑后一律人工再看


# 严格档验收的附加要求。**不含人数约束**——人数属该课规格自己的事（写在「必须可见元素清单」
# 里，如「唯一人物主角」或「一共只有两个孩子」）。曾在这里硬编码「画面只能有一个小孩」，
# 与「两个角色有互动/对视（语言有对象）」这类方法点要求直接打架。要按图收紧就写规格的
# 「验收附加:」字段，本常量只作缺省。
_DEFAULT_EXTRA = '整体为低龄儿童手绘绘本插画风、画面干净、主角与要素清晰可辨。'

# 「不许多画」条（2026-07-27 补验收漏洞）：原验收只查 must_see「缺没缺」、不查画面「多没多」，
# 模型自作主张添的道具会静默通过（备-03 v4 凭空多出一个高饱和红毛线球）。备选图无所谓，
# 主图/练笔图上多画一朵小黄花就会让「当堂数一共几朵」直接失效，故严格档一律追加此条。
# **不并进 _DEFAULT_EXTRA**：现存详案的严格档规格全部写了「验收附加:」，会整条顶掉缺省值，
# 并进去等于永不生效——必须在严格档路径上无条件拼（见 strict_extra）。
_NO_EXTRA_PROPS = (
    '画面中不得出现生图提示词与必须可见元素清单之外的显眼道具、人物或动物；'
    '若有，逐一列入 extras 并判为不通过。'
)


def strict_extra(spec):
    """严格档验收要求＝该图「验收附加:」（缺省 _DEFAULT_EXTRA）＋ 无条件的「不许多画」条。"""
    return (spec.extra_rule or _DEFAULT_EXTRA) + _NO_EXTRA_PROPS


# ---- 视觉验收 ----
_VERIFY_SYS = '你是严格的儿童绘本插画验收员。只依据图片本身回答，不臆测；输出严格 JSON，不要额外文字。'

# —— 计数轨（2026-07-27 补第三个洞）——
# missing 只查「缺没缺」、extras 只查「多没多新品类」：3 朵小黄花画成 4 朵，两轨都不落——
# 花在（不缺）、不是新品类（不多），静默通过。而主-01 第 2 课时要当堂数「一共有几朵」，
# 数错整个环节就废了。故第三轨：清单里写了明确数量的元素，实点实数、本地复核。
_CN_NUM = {'零': 0, '〇': 0, '一': 1, '两': 2, '二': 2, '三': 3, '四': 4,
           '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}
# 只认带限定词的数量（共/一共/只有/仅…），避免「一个背着书包的男孩」这类描述性数词被误判。
_WANT_RE = re.compile(
    r'(?:共|一共|总共|只有|仅|恰好)[^，。；、]{0,6}?'
    r'([0-9]+|[零〇一两二三四五六七八九十]+)\s*'
    r'[朵个只条棵人块张片颗双群辆把支名位]')


def _to_int(s):
    s = str(s).strip()
    if s.isdigit():
        return int(s)
    if len(s) == 1 and s in _CN_NUM:
        return _CN_NUM[s]
    if len(s) == 2 and s[0] == '十' and s[1] in _CN_NUM:      # 十一~十九
        return 10 + _CN_NUM[s[1]]
    if len(s) == 2 and s[1] == '十' and s[0] in _CN_NUM:      # 二十~九十
        return _CN_NUM[s[0]] * 10
    return None


# 注：曾试过「主验收里让模型报 counts、本地按物名关键词比对」，两处踩坑已弃：
#   ① 关键词匹配把 counts 的「小男孩:1」命中了黄花那条里的校准注释（注释提到男孩），误报要3实1；
#   ② 更致命的是模型估数本身就错（4 朵报成 3），本地再怎么比对也救不回。
# 现改为枚举专项（enum_count）：物名与总数都由那一次专项调用产出，不再做关键词匹配。


def _b64(png_path):
    with open(png_path, 'rb') as f:
        return base64.b64encode(f.read()).decode()


def _ask_json(client, cfg, b64, instr):
    """发一次多模态问询并解析 JSON；失败返回 None（调用方各自兜底）。"""
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
        return _extract_json(resp.choices[0].message.content or '')
    except Exception as e:
        print(f'    [专项验收调用失败] {e}')
        return None


def _verify_payload(png_path, items, extra_rule='', whitelist=''):
    """whitelist＝该图的生图提示词，作「画面本该有什么」的白名单参照（严格档才传）。

    只给必须可见清单不足以判「多画」——清单只列教学要素，场景里合规的树、窗台都不在其中，
    模型会把它们当多余物报上来。故把生图提示词一并交出去，并限定只报**显眼**的新增物。
    数量与姿态**不在这一问里判**——混在多项里问，VLM 一律给「满足」；各自走专项调用。"""
    b64 = _b64(png_path)
    numbered = '\n'.join(f'{i+1}. {it}' for i, it in enumerate(items))
    instr = (
        '请逐项判断下面每个元素在图中是否清晰可见，并指出明显问题。\n'
        f'必须可见元素：\n{numbered}\n'
        + (f'额外硬性要求：{extra_rule}\n' if extra_rule else '')
        + (('画面白名单（这张图本该画的内容，以下描述之内的一切都算允许）：\n'
            f'{whitelist}\n'
            '除白名单与必须可见元素之外，若还出现了**显眼的**道具、人物或动物'
            '（会被孩子当成故事要素、影响「数一数 / 找一找」的新增物），逐一填进 extras；'
            '背景里合乎场景的一般环境物（天空、地面、草木、墙面、家具轮廓）不算，不要填。\n')
           if whitelist else '')
        + '返回 JSON：{"items":[{"i":序号,"present":true/false,"note":"简述"}],'
          '"extras":["画面多出来的显眼物…"],"issues":["其它问题…"]}。'
          'present 仅在该元素清晰可辨时为 true；没有多余物时 extras 为空数组。'
    )
    return b64, instr


# —— 专项一：枚举计数（2026-07-27）——
# 混在主验收里问总数，gpt-4o 把 4 朵黄花报成 3 并判通过（主-01 实发）。VLM 数同类小物体本就弱，
# 主因解是**逼它逐个列举方位**而不是估数——枚举比估数准，且列举结果可供人工照着数。
# —— 计数两步走，顺序不可反（2026-07-27 第三版）——
# 这一轨的历史：不枚举时假阴性（真 4 报 3，泄漏了答案）→ 改枚举后假阳性（真 3 报 4）。
# 根因是**任务形式在制造幻觉**：指令要求「逐个列举方位」，模型就必须凑出 N 个方位，
# 于是硬凑出「最左/左起第二/第三/最左」四项，数字被列举任务反向绑架。
# 改法：先只问总数（不许描述位置，没有凑数压力），拿到数后再单独问定位，并**明说位置可以
# 重复或留空、不影响计数**。定位只为人工复核好找，不参与计数。
# {what} 由 _sanitize_count_item 脱敏后填入——**指令里绝不能出现期望数量**（见该函数注释）。
_COUNT_ONLY_INSTR = (
    '这张图里有几个（朵/只）：{what}\n'
    '**只回答一个数字，不要描述位置、不要列举、不要解释。**\n'
    '返回 JSON：{{"name":"物名（简短，如 小黄花）","total":数字}}'
)
_LOCATE_INSTR = (
    '这张图里有 {n} 个（朵/只）{name}。请指出这 {n} 个各在什么位置。\n'
    '**若某几个位置相近，可以用同一句描述；不必凑出 {n} 个不同的方位，允许重复、也允许留空**'
    '——位置描述只供人工复核时好找，**不影响也不改变上面那个数量**。\n'
    '返回 JSON：{{"enumeration":[{{"i":1,"where":"左下角偏左"}}]}}'
)

# —— 专项二：姿态核对（2026-07-27）——
# 缺项能查、多画能查、数量刚查上，姿态查不了：VLM 看到「有手、在身前」就判满足，
# 主-01 首发把「收在膝前（读作蹲着看）」判成了「双手向前伸出（刚扔出去）」。
# 解法是不许它答「满足」，先客观描述实际位置与朝向，再与要求逐字比对。
_POSE_KEYS = ('伸出', '伸直', '张开', '抬起', '抬至', '抬到', '前倾', '朝向', '朝着',
              '看着', '视线', '掌心', '指向', '蹲', '跑')
_POSE_INSTR = (
    '下面这条要求描述的是人物的姿态。\n'
    '要求原文：{item}\n'
    '请**先客观描述**画面中该部位的实际位置与朝向——双臂的走向与高度（相对肩线是高是低）、'
    '手掌朝向、指尖指向何处、头部转向、视线落点、身体重心与姿势；'
    '**不允许只回答「满足」或「不满足」**。\n'
    '**手部必须单独描述一条**：五指是并拢还是张开、有没有单根手指（尤其食指）单独伸出、'
    '整只手是平展还是握起、掌心朝向哪里。曾有一版画成食指指点的手势，而验收只报了'
    '「手在前方、满足」，漏判过去。\n'
    '**判定口径（严格照此，不要自行加码）**：\n'
    '· 只拿「要求原文」里**用文字直接写出来**的项去比对。\n'
    '· **不得从要求原文里推断未写明的细节**——例如原文只写「双手向前伸出」，'
    '就**不能**推断出「五指必须并拢」「手掌必须平」「掌心必须朝下」并据此判为不符；'
    '原文没写的，一律只描述、不判。\n'
    '· mismatch 里只能出现「原文写了 X、画面却是 Y」这种形式；'
    '凡带「要求暗示 / 应该 / 通常」这类推断措辞的，都不要写进 mismatch。'
    '描述完成后，再把你的描述与要求逐字比对，逐条指出对不上的地方。\n'
    '返回 JSON：{{"observed":"对该部位的客观描述","mismatch":["对不上的地方…"],"ok":true/false}}'
)


# —— 送检指令必须脱敏：不许把期望数量交给验收模型（2026-07-27 三组对照实验定案）——
# 枚举法首版把清单项**原文**塞进指令，而原文里明写着「全画面共 3 朵」——模型直接照着答 3，
# 连问三次都是 3（真图是 4 朵）。这不是分辨率问题，是**提示词泄漏答案**：给了标准答案的
# 计数题，模型不会再去数。
# 三组实测（同一张 主-01，各问 2 次，真值 4）：
#   ① 整图 + 原文（泄漏 3 朵）      → 3、3          ← 首版，静默漏判
#   ② 整图 + 脱敏                    → 4、4          ← **稳定正确，采用**
#   ③ 局部裁切 + 脱敏                → 45%框 5、5；40%框 4、4/4  ← 随框大小在 4↔5 跳，且会过数
# 故：**计数一律整图 + 脱敏**。局部裁切送检看着像加固，实测反而不稳（放大后相邻花瓣被
# 数成两朵），已撤销、勿再加回。
_PAREN_RE = re.compile(r'（[^（）]*）|\([^()]*\)')
_NUMQ_RE = re.compile(r'(?:共|一共|总共|只有|仅|恰好)?\s*'
                      r'(?:[0-9]+|[零〇一两二三四五六七八九十]+)\s*'
                      r'([朵个只条棵人块张片颗双群辆把支名位])')


def _sanitize_count_item(item):
    """把清单项脱敏成「数什么」——去括注（校准注释里也常复述数量）、去强调符、数量→若干。"""
    s = item
    for _ in range(3):                       # 括注可能嵌套一两层，扫几遍
        s2 = _PAREN_RE.sub('', s)
        if s2 == s:
            break
        s = s2
    s = s.replace('**', '').replace('__', '')
    s = _NUMQ_RE.sub(r'若干\1', s)
    return re.sub(r'\s+', ' ', s).strip()


def enum_count(client, cfg, png_path, item, want=None):
    """数一条含数量的清单项。返回 {'name','total','where':[…],'uncertain','tries':[n1,n2]} 或 None。

    两步走见 _COUNT_ONLY_INSTR 注释。第一步**独立跑两次**：两次数字一致才采信；不一致则
    uncertain=True、total=None——该条判为「需人工复核」，既不判过也不判失败，更不触发重生。"""
    b64 = _b64(png_path)
    what = _sanitize_count_item(item)
    tries, name = [], ''
    for _ in range(2):
        data = _ask_json(client, cfg, b64, _COUNT_ONLY_INSTR.format(what=what))
        if not data:
            return None
        n = _to_int(data.get('total'))
        if n is None:
            return None
        tries.append(n)
        name = name or str(data.get('name') or '').strip()
    name = name or '该元素'
    if tries[0] != tries[1]:
        return {'name': name, 'total': None, 'where': [], 'uncertain': True, 'tries': tries}
    n = tries[0]
    where = []
    if n:
        data = _ask_json(client, cfg, b64, _LOCATE_INSTR.format(n=n, name=name))
        where = [str(e.get('where', '')).strip() for e in ((data or {}).get('enumeration') or [])
                 if isinstance(e, dict)]
        where = [w for w in where if w]
    return {'name': name, 'total': n, 'where': where, 'uncertain': False, 'tries': tries}


def _fmt_observed(obs):
    """observed 模型有时给字符串、有时给分部位的对象（arm_position/gaze/…），统一成一行可读文本。"""
    if isinstance(obs, dict):
        return '；'.join(f'{k}＝{v}' for k, v in obs.items() if v)
    if isinstance(obs, list):
        return '；'.join(str(x) for x in obs if x)
    return str(obs or '').strip()


def check_pose(client, cfg, b64, item):
    """姿态专项。返回 {'observed','mismatch':[…],'ok'} 或 None。"""
    data = _ask_json(client, cfg, b64, _POSE_INSTR.format(item=item))
    if not data:
        return None
    mm = [str(x).strip() for x in (data.get('mismatch') or []) if str(x).strip()]
    ok = bool(data.get('ok')) and not mm      # 说了对不上却标 ok 的，以 mismatch 为准
    return {'observed': data.get('observed') or '', 'mismatch': mm, 'ok': ok}


def verify_image(client, cfg, png_path, items, extra_rule='', whitelist='', deep=False):
    """返回 dict：{present, missing, lack, extras, counts, count_detail, count_bad,
    poses, pose_bad, issues, raw}。四轨判定（deep=True＝严格档，才跑后两轨）：

    missing＝缺没缺／extras＝多没多新品类（须传 whitelist）／count_bad＝数量对不对（枚举专项）
    ／pose_bad＝姿态对不对（姿态专项）。数量与姿态不符的项一并计入 missing（判不通过），
    但**单列出来**：三者的修法完全不同（缺→补画、多→删、姿态→重建），混进「请补画」分支
    会让模型在已经多画的基础上继续加。lack＝纯缺项（已剔除数量与姿态项），供重试话术用。"""
    b64, instr = _verify_payload(png_path, items, extra_rule, whitelist)
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
        return {'present': [False] * len(items), 'missing': list(items), 'lack': list(items),
                'extras': [], 'counts': {}, 'count_detail': {}, 'count_bad': [],
                'count_uncertain': False, 'poses': [], 'pose_bad': [],
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
    issues = list(data.get('issues', []) if data else [])
    extras = [str(x).strip() for x in (data.get('extras') or [])] if data else []
    extras = [x for x in extras if x]

    counts, count_detail, count_bad, poses, pose_bad = {}, {}, [], [], []
    count_uncertain = False
    if deep:
        for item in items:
            m = _WANT_RE.search(item)
            if not m:
                continue
            want = _to_int(m.group(1))
            if want is None:
                continue
            got = enum_count(client, cfg, png_path, item, want)
            if not got:
                continue
            if got['uncertain']:
                counts[got['name']] = f'两次数不一致（{got["tries"][0]} / {got["tries"][1]}）'
                count_detail[got['name']] = {'want': want, 'where': [], 'item': item}
                issues.append(f'数量存疑（**需人工数一遍**）：{got["name"]} 两次分别数出 '
                              f'{got["tries"][0]} 与 {got["tries"][1]}，要求 {want}')
                count_uncertain = True
                continue
            counts[got['name']] = got['total']
            count_detail[got['name']] = {'want': want, 'where': got['where'], 'item': item}
            if got['total'] != want:
                count_bad.append((got['name'], want, got['total'], item))
                issues.append(f'数量存疑（**仅报告、不拦交付**，请人工数一遍）：'
                              f'{got["name"]} 要求 {want}，机器数出 {got["total"]}'
                              + (f'（{"、".join(got["where"])}）' if got['where'] else ''))
        for item in items:
            if not any(k in item for k in _POSE_KEYS):
                continue
            r = check_pose(client, cfg, b64, item)
            if not r:
                continue
            poses.append({'item': item, 'observed': r['observed'],
                          'mismatch': r['mismatch'], 'ok': r['ok']})
            if not r['ok']:
                pose_bad.append((item, _fmt_observed(r['observed']), r['mismatch']))
                issues.append('姿态不符：' + '；'.join(r['mismatch'] or ['与要求不一致']))
    # —— 计数轨只报不拦（2026-07-27 定，重要）——
    # 这一轨自身误判率未知（假阴性、假阳性各出过一次），**假阳性比假阴性贵得多**：
    # 假阴性只是漏放一张要人工看的图；假阳性会把合格图判成不合格然后重生，而重生是掷骰子——
    # 画风、姿态、构图全部重洗（23:27 那张合格图正是这样被推去 edit 弄坏的）。
    # 故 count_bad 只写报告与 issues、标 manual 提示人工数，**不并入 missing、不影响 passed、
    # 不进重试话术、不触发重生**。等积累若干张真图验证稳定后再由人拍板恢复拦截。
    # 姿态轨仍拦：它抓出过「手收在膝前」这种实错，且描述可逐字核对。
    bad_items = {p[0] for p in pose_bad}
    for it in bad_items:
        if it in items:
            present[items.index(it)] = False
    missing = [items[i] for i, p in enumerate(present) if not p]
    lack = [m for m in missing if m not in bad_items]
    return {'present': present, 'missing': missing, 'lack': lack, 'extras': extras,
            'counts': counts, 'count_detail': count_detail, 'count_bad': count_bad,
            'count_uncertain': count_uncertain, 'poses': poses, 'pose_bad': pose_bad,
            'issues': issues, 'raw': raw}


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
def process_strict(client, cfg, md_path, spec, log, style_ref=None, ref_instr=None):
    """严格档（主图 + 练笔图）：逐项验收 + 缺项重生。

    style_ref：练笔图带本课主图——「同族异时」要求同一个角色、同一场景的下一时刻，靠图生图
    锁角色与画风，纯文字描述锁不住。主图缺省不带参考图（它就是本课基准）；规格写了
    `定妆参考:` 时主图带定妆图，此时须一并传 ref_instr=_CHAR_REF_INSTR_TMPL 的填充结果。
    ref_instr：缺省 None＝走 generate_one 的 _STYLE_REF_INSTR（换内容·锁画风+锁角色）。"""
    items = spec.must_see
    extra = strict_extra(spec)
    out = ip.image_path(md_path, spec.code)
    ref = style_ref if (style_ref and style_ref != out) else None
    if not ref:
        tag = ''
    elif ref_instr and ref_instr.startswith(_CHAR_REF_PREFIX):
        tag = '（沿用定妆图角色与画风）'
    else:
        tag = '（沿用主图画风与角色）'

    regen, result = 0, None
    lack, extras, count_bad, pose_bad = list(items), [], [], []
    while True:
        prompt = spec.build_prompt(enforce_must_see=True)
        # 各分支互斥拼装：**数量与姿态的项绝不能进「请补画」分支**——那会让模型在已经
        # 多画的基础上继续加（4 朵变 5 朵），是会主动恶化的路径。
        if regen and lack:
            prompt += ('\n特别注意：上一版缺失了以下要素，请补画进近景教学层并清晰可辨：'
                       + '；'.join(lack) + '。'
                       '补画时不要改变画风、不要把画面摊平成逐一陈列，'
                       '其余部分仍按色域与氛围处理。')
        # 数量不进重试话术：这一轨只报不拦（见 verify_image），拿一个可能是假阳性的数字去
        # 改提示词，等于让模型把画对的数量改错——曾有一版真 3 朵被报成 4 朵。
        if regen and pose_bad:
            for item, observed, mm in pose_bad:
                prompt += (f'\n特别注意：上一版姿态不符——实际画成了：{observed}；'
                           f'对不上的地方：{"；".join(mm) or "与要求不一致"}。'
                           f'必须严格改为：{item}')
        log(f'  [{spec.code}] 生图第 {regen+1} 次{tag}…')
        generate_one(client, cfg, prompt, out, style_ref=ref, ref_instr=ref_instr)
        regen += 1

        result = verify_image(client, cfg, out, items, extra, whitelist=spec.prompt, deep=True)
        lack, extras = result['lack'], result['extras']
        count_bad, pose_bad = result['count_bad'], result['pose_bad']
        cnt = ('；'.join(f'{n} 要{w}机器数出{g}' for n, w, g, _ in count_bad)
               or ('两次数不一致' if result['count_uncertain'] else '无'))
        if cnt != '无':
            log(f'    数量存疑（仅报告不拦、不重生，请人工数）：{cnt}')
        if not (lack or extras or pose_bad):
            break
        log(f'    缺项：{lack or "无"}｜多画：{extras or "无"}'
            f'｜姿态：{"、".join(p[0][:14] + "…" for p in pose_bad) or "无"}')

        # —— 一律整图重生（2026-07-27 撤销「多画/超数走 --edit 定点删」）——
        # 曾按「能定点改就别重生」分流，实测 --edit 是整图重绘且不受控：对一张 3 朵花的合格图
        # 连发两次「只删除多余的那 1 朵」，结果花变成 4 朵，还带回白边、把天空压成阴天灰、
        # 画风漂离锚图档。**它会主动制造违规**，比它想省下的那次重生代价大得多。
        # 画面元素的修正一律回生成端（改工单/改重试话术再重生）；--edit 只留 CLI 手动通道。
        if regen > cfg['max_retries']:
            log(f'    已达重生上限（{cfg["max_retries"]} 次重试），停。')
            break

    # passed 不含 count_bad（计数轨只报不拦）；但数量存疑仍标 manual＝提醒人工数一遍
    passed = not (lack or extras or pose_bad)
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': regen,
            'items': items, 'present': result['present'],
            'missing': result['missing'], 'extras': extras, 'counts': result['counts'],
            'count_detail': result['count_detail'], 'count_bad': count_bad,
            'count_uncertain': result['count_uncertain'], 'poses': result['poses'],
            'issues': result['issues'], 'png': out,
            'manual': not passed or bool(count_bad) or result['count_uncertain']}


def process_alt(client, cfg, md_path, spec, log, style_ref=None):
    # 备选图轻量：验「能否支撑该句式 / 时间线索」，缺则告警不强制重生
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
    log(f'  [{spec.code}] 生图{"（沿用主图画风）" if ref else ""}…')
    generate_one(client, cfg, spec.build_prompt(), out, style_ref=ref)
    # 备选图不传 whitelist：轻量档不查「多画」（只用来撑句式/时间线索，多个道具无妨），
    # 保持与改造前完全一致的行为。
    result = verify_image(client, cfg, out, items)
    passed = not result['missing']
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': 1,
            'items': items, 'present': result['present'], 'missing': result['missing'],
            'extras': [], 'issues': result['issues'], 'png': out, 'manual': False}  # 备选图不拦交付


def verify_only(client, cfg, md_path, spec, log):
    """只验收已存在的图，绝不重生（--verify-only）。

    用于「规格收紧后回验」：改了必须可见元素清单，但图不该重画——重画会丢掉
    已人工核准的画面。缺图则记为需人工，不触发生成。
    """
    out = ip.image_path(md_path, spec.code)
    if not os.path.isfile(out):
        return {'code': spec.code, 'role': spec.role, 'passed': False, 'attempts': 0,
                'items': spec.must_see or ['（未生成）'], 'present': [], 'missing': spec.must_see or [],
                'extras': [], 'issues': ['图不存在，未生成——本次为只验收模式，不代生图'],
                'png': out, 'manual': True}
    if spec.is_strict:
        items = spec.must_see
        extra = strict_extra(spec)
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
    result = verify_image(client, cfg, out, items, extra,
                          whitelist=spec.prompt if spec.is_strict else '',
                          deep=spec.is_strict)
    passed = not result['missing'] and not result['extras']
    return {'code': spec.code, 'role': spec.role, 'passed': passed, 'attempts': 0,
            'items': items, 'present': result['present'], 'missing': result['missing'],
            'extras': result['extras'], 'counts': result['counts'], 'count_detail': result['count_detail'],
            'count_bad': result['count_bad'], 'count_uncertain': result['count_uncertain'],
            'poses': result['poses'], 'issues': result['issues'], 'png': out,
            # 数量存疑不拦通过，但要标 manual——否则汇总会显示「0 需人工」，
            # 人不会知道还有一处要自己数（曾漏标一次）
            'manual': spec.is_strict and (not passed or bool(result['count_bad'])
                                          or result['count_uncertain'])}


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
        ed = f' · 定点编辑 {r["edits"]} 次' if r.get('edits') else ''
        lines.append(f'## {r["code"]}（{r["role"]}） — {flag} · 生图 {r["attempts"]} 次{ed}')
        for it, p in zip(r['items'], r['present']):
            lines.append(f'- [{"x" if p else " "}] {it}')
        for k, v in (r.get('counts') or {}).items():
            # 方位明细必须落报告：人工要照着它一处处点，才知道模型漏数在哪
            where = ((r.get('count_detail') or {}).get(k) or {}).get('where') or []
            lines.append(f'- 枚举计数：{k}={v}'
                         + (f'　→ 逐个方位：{"、".join(where)}' if where else ''))
        for p in r.get('poses') or []:
            mark = '✅' if p['ok'] else '⚠'
            lines.append(f'- {mark} 姿态核对（供人工复核）：{_fmt_observed(p["observed"])}'
                         + (f'　→ 对不上：{"；".join(p["mismatch"])}' if p['mismatch'] else ''))
        if r.get('count_bad') or r.get('count_uncertain'):
            lines.append('- ⚠ **数量存疑，请人工数一遍**（本轨只报不拦、不参与通过判定）：'
                         + ('；'.join(f'{n} 要求 {w}、机器数出 {g}'
                                     for n, w, g, _ in r.get('count_bad') or [])
                            or '同一张图两次数出的数字不一致'))
        if r.get('extras'):
            lines.append(f'- ⚠ 多画（规格外显眼物，须去掉）：{"；".join(str(x) for x in r["extras"])}')
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
    ap.add_argument('--only', default='', help='只生指定编号，逗号分隔，如 主-01,练-01')
    ap.add_argument('--edit', default='', metavar='要改的这一处',
                    help='定向编辑模式：以现行真图为基准只改这一处，其余锁死（须配 --only 指定单个编号）。'
                         '用于局部不达标但整图已人工核准的情况；编辑前版本自动备份到 图位/_历史/')
    ap.add_argument('--verify-only', action='store_true',
                    help='只按现行规格验收已有的图、绝不重生（规格收紧后回验用；缺图记为需人工，不代生）')
    args = ap.parse_args()

    cfg = load_config()
    if args.max_retries is not None:
        cfg['max_retries'] = args.max_retries

    specs, _, _ = ip.load(args.md_path)
    # 生成顺序固定 主图 → 练笔图 → 备选图：主图先落盘，后两类才能拿它做参考图
    order = {ip.ROLE_MAIN: 0, ip.ROLE_PRACTICE: 1, ip.ROLE_ALT: 2}
    targets = sorted([s for s in specs if s.is_strict or s.is_alt],
                     key=lambda s: order.get(s.role, 9))
    if args.only:
        want = {x.strip() for x in args.only.split(',') if x.strip()}
        targets = [s for s in targets if s.code in want]
    if not targets:
        print('没有可生成的主图/练笔图/备选图（格式图跳过）。')
        return

    # 三图位齐备是交付硬门（image-spec.md §一课三图位）：这里只告警、不拦生成，
    # 因为工单可能分批出图；交付前的把关在 checklist 与冷审。
    lack = [n for n, got in (('主图', [s for s in specs if s.is_main]),
                             ('练笔图', [s for s in specs if s.is_practice]),
                             ('备选图', [s for s in specs if s.is_alt])) if not got]
    if lack:
        print(f'[告警] 工单缺图位：{"、".join(lack)}——一课三图位是交付硬门，请确认是分批出图还是漏写规格。')

    # 本课主图＝全课画风基准；练笔图与备选图都带它做图生图，保证全课一套画风
    # （练笔图还要靠它锁住「同一个角色」）
    anchor_png = None
    for s in specs:
        if s.is_main:
            cand = ip.image_path(args.md_path, s.code)
            if os.path.isfile(cand):
                anchor_png = cand
            break

    client = make_client(cfg)
    log = print
    # —— 定向编辑：单图、不走批量分流 ——
    if args.edit:
        if len(targets) != 1:
            print('[错误] --edit 须配 --only 指定**单个**编号（当前命中 '
                  f'{len(targets)} 个：{[s.code for s in targets]}）。')
            sys.exit(1)
        spec = targets[0]
        rec = process_edit(client, cfg, args.md_path, spec, args.edit, log)
        flag = '过' if rec['passed'] else '仍缺项'
        print(f"\n定向编辑完成：{spec.code} 复验{flag}"
              + (f"，缺：{rec['missing']}" if rec['missing'] else ''))
        if rec['issues']:
            print('  其它问题：' + '；'.join(str(x) for x in rec['issues']))
        print('⚠ 编辑后**必须人工看图**确认「只改了那一处、其余没跑」，'
              '并按需重跑 --verify-only 更新完整验收报告。')
        return
    if args.verify_only:
        print(f'共 {len(targets)} 图待验收（只验收模式：按现行规格核对已有的图，不重生、不覆盖）…')
    else:
        print(f'共 {len(targets)} 图待生成（主图/练笔图严格验收+重生，备选图轻量）…')
    records = []
    for s in targets:
        if s.is_blank:
            # 缺图补全课的留白格（image-spec §组图）：不生图、不验收，由学生想象补出
            log(f'  [{s.code}] 留白格（状态: 留白）——跳过生图与验收。')
            records.append({'code': s.code, 'role': s.role, 'passed': True, 'attempts': 0,
                            'items': ['留白格：不生图（学生想象补出）'], 'present': [], 'missing': [],
                            'issues': [], 'png': '', 'manual': False})
            continue
        try:
            if args.verify_only:
                records.append(verify_only(client, cfg, args.md_path, s, log))
            elif s.is_main:
                # 组图（多个主图格）：主-02 起带主-01 作参考图，锁全组画风与角色。
                # 组内首格落 B 级：规格写了 `定妆参考: <角色名>` 就带其定妆图（喂图副本）
                # + _CHAR_REF_INSTR（锁画风锁角色、比例不跟图）；没写就不带参考图（与该字段
                # 出现前行为一致）。char_ref 任一环失败已返回 (None, None)，无需再退化。
                # ⚠ anchor_png 可能就是本格自己（重跑已存在的主图时预置的），那不算「组内首格」，
                # 必须走下面的 else——否则 process_strict 的 ref != out 保护会把它置空，
                # 参考图链对单主图课静默失效。
                if anchor_png and anchor_png != ip.image_path(args.md_path, s.code):
                    ref, instr = anchor_png, None
                else:
                    ref, instr = char_ref(s)
                    if ref:
                        log(f'  [{s.code}] 定妆参考已启用：{s.char_ref} ← {os.path.basename(ref)}')
                records.append(process_strict(client, cfg, args.md_path, s, log,
                                              style_ref=ref, ref_instr=instr))
                # 首格刚落盘：后续各格/练笔图/备选图的参考图就位（基准固定为第一格，不随后续格漂移）
                if anchor_png is None:
                    cand = ip.image_path(args.md_path, s.code)
                    if os.path.isfile(cand):
                        anchor_png = cand
            elif s.is_practice:
                records.append(process_strict(client, cfg, args.md_path, s, log, style_ref=anchor_png))
            else:
                records.append(process_alt(client, cfg, args.md_path, s, log, style_ref=anchor_png))
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
