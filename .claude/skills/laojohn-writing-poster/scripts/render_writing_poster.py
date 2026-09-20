# -*- coding: utf-8 -*-
r"""render_writing_poster.py —— 单元海报 data.json → 自包含 HTML + JPG 长图（两段式第 3 步）

    PYTHONUTF8=1 python render_writing_poster.py <data.json> [--out-base <路径基名>]
        [--illustration <jpg>] [--logo <png>] [--qr <png>] [--campus <json>] [--template <html>]
        [--font-mode subset|full]

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


def render(data_path, out_base=None, illustration=None, logo=None, qr=None, campus=None,
           template=None, font_mode=None):
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

    tokens = {
        "/*__LOGO__*/": _jr.data_uri(str(logo_p)) if logo_p.exists() else "",
        "/*__QR__*/": _jr.data_uri(str(qr_p)) if qr_p.exists() else "",
        "/*__ILLU__*/": _jr.data_uri(str(illu)) if illu else "",
        "/*__FONT_BRUSH__*/": font_data_uri(title, font_mode or "subset"),
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
    a = ap.parse_args()
    render(a.data, a.out_base, a.illustration, a.logo, a.qr, a.campus, a.template, a.font_mode)
    return 0


if __name__ == "__main__":
    sys.exit(main())
