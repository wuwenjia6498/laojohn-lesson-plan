# -*- coding: utf-8 -*-
r"""宣传短视频线的公共层：路径、素材解析、共享件薄壳。

**三件共享真源一律 importlib 薄壳载入，禁复制**（CLAUDE.md §3）：
    ttsclient.py / ffmpeg_path.py / build_timeline.wrap
        → .claude\skills\laojohn-lesson-video\scripts\
改真源须回归备课视频线（五上四 `render_video.py --sample 6`）。

素材引用写法（脚本 json 里 visual.src）：
    repo:<相对项目根的路径>        本仓文件，如 repo:写作课海报输出/…/…-插画.jpg
    assets:<相对素材库根的路径>    外部素材库，如 assets:专注书写/专注书写 (19).jpg
    card:<卡片名>                  由 render_promo 按 visual.card 现渲的图文卡

素材库根**不写死盘符**（项目与素材库都在移动硬盘，CLAUDE.md §1）：
    环境变量 PROMO_ASSETS_ROOT  →  scripts\promo.config.json 的同名键（gitignored）
库里文件名是 Windows 去重式 `分类 (n).jpg`，重扫一次编号就会变——所以每张图在
脚本里钉 md5，渲染前核对，对不上就报错，绝不静默换图。
"""
import hashlib
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)


def project_root():
    p = HERE
    while True:
        if os.path.exists(os.path.join(p, "CLAUDE.md")) and \
                os.path.isdir(os.path.join(p, ".claude")):
            return p
        up = os.path.dirname(p)
        if up == p:
            raise SystemExit("找不到项目根（向上没有 CLAUDE.md）")
        p = up


ROOT = project_root()
LV = os.path.join(ROOT, ".claude", "skills", "laojohn-lesson-video", "scripts")
OUT_BASE = os.path.join(ROOT, "宣传短视频输出")
PRESENTER_BASE = os.path.join(ROOT, "品牌资产", "宣传片讲解员")


def _load(name, path):
    if LV not in sys.path:          # 真源之间互相 import（ttsclient → ffmpeg_path）
        sys.path.insert(0, LV)
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def ttsclient():
    return _load("ttsclient", os.path.join(LV, "ttsclient.py"))


def ffmpeg_path():
    return _load("ffmpeg_path", os.path.join(LV, "ffmpeg_path.py"))


def wrap_fn():
    return _load("build_timeline", os.path.join(LV, "build_timeline.py")).wrap


def _config():
    fn = os.path.join(HERE, "promo.config.json")
    if os.path.exists(fn):
        with open(fn, encoding="utf-8") as f:
            return json.load(f)
    return {}


def assets_root():
    r = os.environ.get("PROMO_ASSETS_ROOT") or _config().get("PROMO_ASSETS_ROOT")
    if not r:
        raise SystemExit("未设素材库根：环境变量 PROMO_ASSETS_ROOT，"
                         "或在 scripts\\promo.config.json 写 {\"PROMO_ASSETS_ROOT\": \"…\\_assets\"}")
    if not os.path.isdir(r):
        raise SystemExit("素材库根不存在：%s（移动硬盘换了盘符？）" % r)
    return r


def resolve(src):
    """repo:/assets: → 绝对路径；card: 返回 None（由渲染器现渲）。"""
    kind, _, rel = src.partition(":")
    if kind == "repo":
        return os.path.join(ROOT, rel)
    if kind == "assets":
        return os.path.join(assets_root(), rel)
    if kind == "card":
        return None
    raise SystemExit("素材写法不认识：%s（只认 repo:/assets:/card:）" % src)


def md5_of(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def out_dir(line, unit):
    return os.path.join(OUT_BASE, line, unit)


def script_path(line, unit):
    return os.path.join(out_dir(line, unit), unit + "-宣传片脚本.json")


def load_script(line, unit):
    p = script_path(line, unit)
    if not os.path.exists(p):
        raise SystemExit("没有脚本：%s" % p)
    with open(p, encoding="utf-8") as f:
        return json.load(f), p


def save_json(obj, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def script_digest(sc):
    """闸门 A 记账用：只算内容（去掉 meta.audit 自身，以及只动后期观感的 meta.grade）。"""
    body = dict(sc)
    meta = dict(body.get("meta") or {})
    meta.pop("audit", None)
    meta.pop("grade", None)
    body["meta"] = meta
    s = json.dumps(body, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(s.encode("utf-8")).hexdigest()


def all_lines(sc):
    for seg in sc["segments"]:
        for i, ln in enumerate(seg.get("lines") or []):
            yield seg, i, ln


def load_presenter(name):
    """讲解员档案：品牌资产/宣传片讲解员/<名>/档案.json（人像/场景/音色参考同目录）。
    未经用户定妆（confirmed_by 为空）就拒绝进生成——花钱的环节只吃人看过的档案。"""
    d = os.path.join(PRESENTER_BASE, name)
    p = os.path.join(d, "档案.json")
    if not os.path.exists(p):
        raise SystemExit("没有讲解员档案：%s（先跑 build_presenter.py）" % p)
    with open(p, encoding="utf-8") as f:
        prof = json.load(f)
    prof["_dir"] = d
    for k in ("portrait", "scene") + (("voice",) if prof.get("voice") else ()):
        fn = os.path.join(d, prof[k])
        if not os.path.exists(fn):
            raise SystemExit("讲解员档案缺文件：%s" % fn)
        if prof.get("md5", {}).get(k) and md5_of(fn) != prof["md5"][k]:
            raise SystemExit("讲解员素材被改过（md5 对不上）：%s" % fn)
    return prof
