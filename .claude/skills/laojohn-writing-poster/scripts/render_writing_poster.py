# -*- coding: utf-8 -*-
r"""render_writing_poster.py —— 单元海报 data.json → 自包含 HTML + JPG 长图（两段式第 3 步）

    PYTHONUTF8=1 python render_writing_poster.py <data.json> [--out-base <路径基名>]
        [--illustration <jpg>] [--logo <png>] [--qr <png>] [--campus <json>] [--template <html>]
        [--font-mode subset|full] [--no-creamify]

默认：out_base ＝ json 同目录 <课次>-习作海报；插画 ＝ 同目录 <课次>-插画.jpg（缺则留空区并 stderr 提示）；
logo/qr/校区信息 ＝ 项目根 品牌资产\（单一源，skill 内不存副本）。**所有覆盖参数默认 None**（CLAUDE.md §3 红线）。

渲染骨架来自 laojohn-book-card\scripts\_jpg_render.py（读书会书目卡/海报同一真源，importlib 薄壳、零复制），
口径与 course-poster 相同：1242px 宽、quality 92、device_scale_factor 2 ⇒ JPG 2484px 宽、高随内容。

毛笔标题字：assets\fonts\MaShanZheng-Regular.woff2（OFL；以 woff2 入库是为过 5MB 大文件闸门，读取需 fontTools+brotli）。
默认 subset ＝ 只切标题那几个字、解回 TTF 字节 base64 注入（几十 KB），html 自包含且小；--font-mode full ⇒ 整字库解成 TTF 内嵌（约 7.8 MB）。
两者都缺时警告并回退楷体（pip install fonttools brotli）。
渲染前机检（_common.check_text）：残留占位 / ASCII 直引号 / emoji / 「待补充」 ⇒ 拒绝渲染、逐条报位置。
"""
import argparse
import base64
import importlib.util
import io
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent / "assets"
DEFAULT_TEMPLATE = ASSETS / "template.html"
FONT_FILE = ASSETS / "fonts" / "MaShanZheng-Regular.woff2"   # 以 woff2 入库（<5MB 过大文件闸门），注入时解回 TTF 字节

_REAL = HERE.parents[1] / "laojohn-book-card" / "scripts" / "_jpg_render.py"
_spec = importlib.util.spec_from_file_location("_jpg_render_real", _REAL)
_jr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_jr)

WIDTH, QUALITY, VIEWPORT_H, SETTLE_MS = 1242, 92, 1000, 400


def font_data_uri(text, mode):
    """标题字体 → data URI。subset 只切 text 里的字（+ 常用标点），失败回退整字库。"""
    if not FONT_FILE.exists():
        print("  [警告] 毛笔字体缺失：%s，标题将回退楷体" % FONT_FILE, file=sys.stderr)
        return ""
    data = None
    if mode != "full":
        try:
            from fontTools import subset
            from fontTools.ttLib import TTFont
            chars = set(text) | set("，。：！？、·（）《》字")
            font = TTFont(str(FONT_FILE))
            opts = subset.Options()
            opts.name_IDs = ["*"]
            opts.notdef_outline = True
            sub = subset.Subsetter(opts)
            sub.populate(text="".join(chars))
            sub.subset(font)
            missing = [ch for ch in text if ord(ch) not in font.getBestCmap()]
            if missing:
                print("  [警告] 毛笔体缺字：%s（会回退楷体，建议改 title 避开）" % "".join(missing), file=sys.stderr)
            font.flavor = None                      # 解回 TTF：模板按 format("truetype") 加载
            buf = io.BytesIO()
            font.save(buf)
            data = buf.getvalue()
        except ImportError:
            print("  [提示] 未装 fontTools，改整字库内嵌", file=sys.stderr)
        except Exception as e:  # 子集化出错不阻断，退回整字库
            print("  [提示] 子集化失败（%s），整字库内嵌" % e, file=sys.stderr)
    if data is None:
        try:
            from fontTools.ttLib import TTFont
            font = TTFont(str(FONT_FILE))
            font.flavor = None
            buf = io.BytesIO()
            font.save(buf)
            data = buf.getvalue()
        except Exception as e:
            print("  [警告] 读不了 woff2 字体（%s），标题回退楷体；pip install fonttools brotli" % e, file=sys.stderr)
            return ""
    return "data:font/ttf;base64," + base64.b64encode(data).decode("ascii")


def load_campus(root, override):
    p = Path(override) if override else root / "品牌资产" / "校区信息.json"
    if not p.exists():
        print("  [提示] 校区信息缺失（%s），底部联系块整体隐藏" % p, file=sys.stderr)
        return {}
    d = C.load_json(p)
    return {k: v for k, v in d.items() if not str(k).startswith("_")}



# ---- 插画自动取色：光晕与牛皮纸卡跟着本课插画走（主底奶油不动，插画融合才不破） ----
# 取色只影响装饰层；json 顶层 "theme_hue"（0–360 数字）可覆盖自动结果。
def _hsl(h, s, l, a=None):
    import colorsys
    r, g, b = colorsys.hls_to_rgb((h % 360) / 360.0, l, s)
    r, g, b = int(round(r * 255)), int(round(g * 255)), int(round(b * 255))
    return "rgba(%d,%d,%d,%s)" % (r, g, b, a) if a is not None else "#%02X%02X%02X" % (r, g, b)


def illu_hues(path, nbin=36):
    """返回 (主色相, 强调色相或 None)。奶油/木色/土黄纸底带排除在外，否则四张都取成同一个橙。"""
    import colorsys
    from PIL import Image
    im = Image.open(path).convert("RGB")
    im.thumbnail((160, 160))
    bins = [0.0] * nbin
    for r, g, b in im.getdata():
        h, s, v = colorsys.rgb_to_hsv(r / 255., g / 255., b / 255.)
        if v < .22 or s < .42:
            continue
        if 0.055 <= h <= 0.17 and s < .62 and v > .72:   # 纸底与木色，不算主色
            continue
        bins[int(h * nbin) % nbin] += s * v
    total = sum(bins)
    if total <= 0:
        return None, None
    main = max(range(nbin), key=lambda i: bins[i])
    far = [i for i in range(nbin)
           if min((i - main) % nbin, (main - i) % nbin) * (360.0 / nbin) >= 45
           and bins[i] / total >= .05]
    acc = max(far, key=lambda i: bins[i]) if far else None
    deg = lambda i: (i + .5) * (360.0 / nbin)
    return deg(main), (deg(acc) if acc is not None else None)



# ---- 插画白纸边 → 奶油底（2026-09-22 立）----
# 生图提示词早写死了背景 #FFF6E3，模型仍常把四周画成纯白纸边；模板的双层 mask 只负责渐隐，
# 白边渐隐到奶油底上就是一条横贯画面的发白带（实测海报插画上缘 (255,255,253) vs 底色 (255,248,232)）。
# 故在转 data URI 前于内存里把「白点」重映射到奶油：只吃高光、中间调不动，主体与淡彩几乎不变。
# 原图不覆盖，随时可回退；满幅到边的图（外环不近白）自动跳过。
CREAM_RGB = (255, 246, 227)


def creamify_illu(path, enabled=None):
    """插画四周若是白纸边就把白点染成奶油，返回 data URI。enabled=False 关掉，None=自动判定。"""
    if enabled is False:
        return _jr.data_uri(str(path))
    import numpy as np
    from PIL import Image
    im = Image.open(str(path)).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    bw, bh = max(1, int(w * .05)), max(1, int(h * .05))
    ring = np.concatenate([a[:bh].reshape(-1, 3), a[-bh:].reshape(-1, 3),
                           a[:, :bw].reshape(-1, 3), a[:, -bw:].reshape(-1, 3)])
    lo, hi = ring.min(axis=1), ring.max(axis=1)
    near_white = ((lo > 244) & (hi - lo < 12)).mean()   # 近白且低饱和的占比
    if near_white < .25:                                # 没有白纸边：再看是不是偏黄的纸底
        return _match_paper(a, path)
    # 权重按 min 通道在 235→255 之间平滑升到 1：235 以下完全不动，纯白处完全落到奶油
    t = np.clip((a.min(axis=2) - 235.0) / 20.0, 0, 1)
    t = (t * t * (3 - 2 * t))[..., None]                # smoothstep
    cream = np.array(CREAM_RGB, dtype=np.float32) / 255.0
    out = a * (1 - t) + (a * cream) * t
    buf = io.BytesIO()
    Image.fromarray(np.clip(out, 0, 255).astype("uint8")).save(buf, "JPEG", quality=95)
    print("  [插画] 检出白纸边（外环近白 %.0f%%），已把白点染成奶油 #FFF6E3" % (near_white * 100))
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _match_paper(a, path):
    """纸底偏黄时整体挪到奶油色，返回 data URI；不是纸底就原样返回。
    gpt-image 出的图纸底常是 (251,233,190) 这类米黄，比页面奶油深一档，插画四周就显出一块偏暖的方形（2026-09-23
    六上一、三上五实测）。取上方两角当纸色（下缘常是草地），须同时满足：两角颜色均匀、够亮、暖色（R≥G≥B）、
    离奶油不远（≤45，挡住淡蓝天空这类满幅背景）且确有色差（>6）。只挪「接近纸色」的像素：
    与纸色相差 20 以内整段挪到奶油，70 以外不动，中间线性过渡——人物、暖光、草地都不受影响。"""
    import numpy as np
    from PIL import Image
    h, w = a.shape[:2]
    k = max(1, int(min(h, w) * .06))
    corners = np.concatenate([a[:k, :k].reshape(-1, 3), a[:k, -k:].reshape(-1, 3)])
    paper = np.median(corners, axis=0)
    cream = np.array(CREAM_RGB, dtype=np.float32)
    gap = float(np.linalg.norm(paper - cream))
    r, g, b = paper
    uniform = float(np.median(np.linalg.norm(corners - paper, axis=1))) < 8
    if not (uniform and paper.min() > 180 and r >= g >= b and 6 < gap <= 45):
        return _jr.data_uri(str(path))
    wgt = np.clip(1 - (np.linalg.norm(a - paper, axis=2) - 20) / 50, 0, 1)[..., None]
    out = a + wgt * (cream - paper)
    buf = io.BytesIO()
    Image.fromarray(np.clip(out, 0, 255).astype("uint8")).save(buf, "JPEG", quality=95)
    print("  [插画] 纸底 %s 偏离奶油 %.0f，已挪到 #FFF6E3（只动接近纸色的像素）"
          % (paper.round().astype(int).tolist(), gap))
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def keyout_bg_illu(path):
    """纯色块平涂图（illustration.feather:false）专用：把插画底色抠成透明，返回 PNG data URI。
    关掉羽化后插画是个硬矩形，底色与页面光晕差一点就显出方框（2026-09-23 三上一实测）；
    平涂图底色均匀，按外环中位色做色差抠图最干净。与底色相差 12 以内全透明、36 以外不动，中间平滑过渡。"""
    import numpy as np
    from PIL import Image
    im = Image.open(str(path)).convert("RGB")
    a = np.asarray(im).astype(np.float32)
    h, w = a.shape[:2]
    bw, bh = max(1, int(w * .03)), max(1, int(h * .03))
    ring = np.concatenate([a[:bh].reshape(-1, 3), a[:, :bw].reshape(-1, 3), a[:, -bw:].reshape(-1, 3)])
    bg = np.median(ring, axis=0)
    dist = np.linalg.norm(a - bg, axis=2)
    alpha = np.clip((dist - 12.0) / 24.0, 0, 1)
    rgba = np.dstack([a, alpha * 255]).astype("uint8")
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG", optimize=True)
    print("  [插画] feather:false → 已按底色 %s 抠成透明" % bg.round().astype(int).tolist())
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def logo_uri(path, target_w=640):
    """logo 源图只有 292px 宽，2 倍渲染下直接放大发虚：先 Lanczos 上采样再轻锐化，救回一点小字边缘。
    换上 ≥600px 的 品牌资产\logo.png 后本函数自动不介入（够宽就原样返回）。"""
    from PIL import Image, ImageFilter
    im = Image.open(str(path))
    if im.width >= target_w:
        return _jr.data_uri(str(path))
    im = im.convert("RGB").resize(
        (target_w, round(im.height * target_w / im.width)), Image.LANCZOS)
    im = im.filter(ImageFilter.UnsharpMask(radius=1.6, percent=105, threshold=2))
    buf = io.BytesIO(); im.save(buf, "PNG", optimize=True)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def theme_css(illu, data):
    """生成覆盖 :root 的主题变量：插画取色 + 插画浓度；两者互不依赖，缺一个不影响另一个。"""
    out = []
    # 插画浓度：铅笔淡彩这类偏浅的图调 1.2–1.4；只是滤镜，原图不动，随时回退
    punch = (data.get("illustration") or {}).get("punch")
    try:
        punch = float(punch)
    except (TypeError, ValueError):
        punch = None
    if punch and abs(punch - 1) > 1e-6:
        d = punch - 1
        out.append("--illu-filter:saturate(%.3f) contrast(%.3f) brightness(%.3f);"
                   % (1 + d * 1.30, 1 + d * 0.55, 1 - d * 0.10))

    # 头部整体下移（json 顶层 head_offset，单位 px）：插画自身上缘留白多、头部与画面之间显空时用
    off = data.get("head_offset")
    try:
        off = float(off)
    except (TypeError, ValueError):
        off = None
    if off:
        out.append("--head-offset:%gpx;" % off)

    hue = data.get("theme_hue")
    acc = None
    if hue is None and illu:
        try:
            hue, acc = illu_hues(str(illu))
        except Exception:
            hue = None
    if hue is None:
        return (":root{%s}" % "".join(out)) if out else ""
    ah = acc if acc is not None else hue
    # 牛皮纸只允许向主色偏一点，偏多了就不像纸（原色 #EBD3A8 / #E0BF8C ≈ 38°）
    kh = 38 + max(-8, min(8, ((hue - 38 + 180) % 360) - 180))
    # 三条要点条一律同色（2026-09-22 用户定，三档递进与两档都已并掉）；
    # 第三条只靠左缘橙条与橙调栏目名区分，不靠底色
    out.append("--glow-a:%s;--glow-b:%s;--tone-a:%s;"
               # 光晕两次调整，现取两端中点：原 (.78,.80,.50)/(.70,.88,.42) 上半页压出一片黄、标题发闷，
               # 2026-09-22 砍到 (.68,.89,.26)/(.60,.93,.22) 又太淡、上半页空得没有层次（用户反馈），
               # 同日回到中点。主底奶油（#FFF6E3）不动，插画融合口径不受影响。
               % (_hsl(hue, .73, .865, ".38"), _hsl(ah, .65, .905, ".32"),
                  _hsl(kh, .52, .83)))
    return ":root{%s}" % "".join(out)


def render(data_path, out_base=None, illustration=None, logo=None, qr=None, campus=None,
           template=None, font_mode=None, creamify=None):
    data_path = Path(data_path)
    data = C.load_json(data_path)
    problems = C.check_text(data)
    if problems:
        print("机检不过，拒绝渲染（%d 处）：" % len(problems), file=sys.stderr)
        for path, why in problems:
            print("  ✗ %s：%s" % (path, why), file=sys.stderr)
        sys.exit(2)

    root = C.repo_root(data_path)
    cid = data.get("course", {}).get("id") or data_path.stem.replace("-习作海报", "")
    out_base = str(Path(out_base)) if out_base else str(data_path.parent / ("%s-习作海报" % cid))

    illu = Path(illustration) if illustration else data_path.parent / ("%s-插画.jpg" % cid)
    if not illu.exists():
        print("  [提示] 插画缺失（%s），已留空白区；先跑 gen_illustration.py 再重渲" % illu.name, file=sys.stderr)
        illu = None
    logo_p = Path(logo) if logo else root / "品牌资产" / "logo.png"
    qr_p = Path(qr) if qr else root / "品牌资产" / "qrcode.png"
    for p, name in ((logo_p, "logo"), (qr_p, "二维码")):
        if not p.exists():
            print("  [警告] %s 缺失：%s" % (name, p), file=sys.stderr)

    if "campus" not in data:
        data = dict(data)
        data["campus"] = load_campus(root, campus)
    title = data.get("title") or data.get("course", {}).get("topic", "")
    # 白边奶油化：CLI --no-creamify 优先，其次 json 的 illustration.creamify，缺省 None＝自动判定
    cream_on = creamify if creamify is not None else (data.get("illustration") or {}).get("creamify")

    tokens = {
        "/*__LOGO__*/": logo_uri(logo_p) if logo_p.exists() else "",
        "/*__QR__*/": _jr.data_uri(str(qr_p)) if qr_p.exists() else "",
        "/*__ILLU__*/": (keyout_bg_illu(illu) if (data.get("illustration") or {}).get("feather") is False
                         else creamify_illu(illu, cream_on)) if illu else "",
        "/*__FONT_BRUSH__*/": font_data_uri(title, font_mode or "subset"),
        "/*__THEME__*/": theme_css(illu, data),
    }
    tpl = str(Path(template) if template else DEFAULT_TEMPLATE)
    jpg, html = _jr.shoot(tpl, out_base, data, tokens,
                          width=WIDTH, quality=QUALITY, viewport_height=VIEWPORT_H, settle_ms=SETTLE_MS)
    try:
        from PIL import Image
        w, h = Image.open(jpg).size
        print("JPG %d×%d，%.2f MB → %s" % (w, h, os.path.getsize(jpg) / 1048576, jpg))
    except Exception:
        print("JPG → %s" % jpg)
    print("HTML → %s（%.1f MB）" % (html, os.path.getsize(html) / 1048576))
    return jpg, html


def main():
    ap = argparse.ArgumentParser(description="单元海报 json → html + jpg")
    ap.add_argument("data", help="<课次>-习作海报.json")
    ap.add_argument("--out-base", default=None)
    ap.add_argument("--illustration", default=None, help="插画路径（默认同目录 <课次>-插画.jpg）")
    ap.add_argument("--logo", default=None)
    ap.add_argument("--qr", default=None)
    ap.add_argument("--campus", default=None, help="校区信息 json（默认 品牌资产/校区信息.json）")
    ap.add_argument("--template", default=None)
    ap.add_argument("--font-mode", default=None, choices=["subset", "full"])
    ap.add_argument("--no-creamify", dest="creamify", action="store_const", const=False, default=None,
                    help="关掉插画白纸边自动染奶油（缺省自动判定；json 侧 illustration.creamify:false 同效）")
    a = ap.parse_args()
    render(a.data, a.out_base, a.illustration, a.logo, a.qr, a.campus, a.template, a.font_mode, a.creamify)
    return 0


if __name__ == "__main__":
    sys.exit(main())
