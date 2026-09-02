#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""外部 pptx 入库前的媒体压缩器（写作课线「外部 PPT 后处理链」第 1.5 步）。

为什么必做——体积账（2026-09-02 立）：
外部平台重做的 pptx 每份 13~22MB，**89% 是 ppt/media/ 里的 PNG**；一轮 7 份就是
125.5MB。而 `写作课件PPT输出/` 是入库的（CLAUDE.md §8）、git 只进不出，每轮外部
重做都会再叠一次。08-20 定"PPT 入库"时 pptx 都是本仓 build_ppt.py 烘焙的、每份约
1MB，那条决策的前提对外部件已不成立。

病因不是分辨率——实测这些图全部 ≤1.4MP、长边不超 2000px，投屏够用；是 **AI 插画
用无损 PNG 承载**。zip 层也压不动（PNG 本身已是压缩格式，compress_size≈file_size）。
量化到 256 色后实测降到 17%，且透明通道保住。

只动 ppt/media/*.png 的字节，不碰任何 XML／rels／SVG，**幻灯片结构、形状 ID、动画
时间树一律原样**——所以压缩前后 python-pptx 读出的页数与形状数必须完全相等，
这也是验收判据。

⚠ 三个坑：
1. `Image.quantize(method=MEDIANCUT)` **不支持 RGBA，直接抛 ValueError**。带透明的
   图必须走 FASTOCTREE（本批 25 张里 11 张带透明）。
2. zip 条目必须**保持原顺序与原 compress_type**。PNG 原件多为 ZIP_STORED（存过一次
   压不动），照抄回去，别一律 DEFLATED。
3. 压完与外部原件不再字节一致，`external-pptx-duplicate-drop-0825` 那条判重的
   **media md5 项会失效**——故默认写 sidecar `<pptx>-origin.json` 存原件指纹，
   判重改与它比。别关 sidecar。

用法：
    python shrink_pptx_media.py <pptx...> [--colors 256] [--dry-run]
                                [--min-gain 0.15] [--no-sidecar]
退出码：0 成功（或 dry-run 完成）/ 1 有文件处理失败 / 3 参数错
"""
import os
import io
import sys
import json
import zipfile
import hashlib
import argparse
import datetime

try:
    from PIL import Image
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")

MEDIA_PREFIX = "ppt/media/"


def _md5(b):
    return hashlib.md5(b).hexdigest()


def quantize_png(raw, colors):
    """PNG 量化。带透明走 FASTOCTREE（MEDIANCUT 不支持 RGBA），否则 MEDIANCUT（质量更好）。"""
    im = Image.open(io.BytesIO(raw))
    has_alpha = (im.mode in ("RGBA", "LA")
                 or (im.mode == "P" and "transparency" in im.info))
    if has_alpha:
        q = im.convert("RGBA").quantize(colors=colors, method=Image.FASTOCTREE)
    else:
        q = im.convert("RGB").quantize(colors=colors, method=Image.MEDIANCUT)
    buf = io.BytesIO()
    q.save(buf, "PNG", optimize=True)
    return buf.getvalue(), has_alpha


def shrink(path, colors=256, min_gain=0.15, dry_run=False, sidecar=True):
    src_size = os.path.getsize(path)
    with open(path, "rb") as f:
        origin_bytes = f.read()

    zin = zipfile.ZipFile(io.BytesIO(origin_bytes))
    infos = zin.infolist()

    origin_media = {}
    stat = {"n_png": 0, "n_shrunk": 0, "before": 0, "after": 0, "alpha": 0}
    out_buf = io.BytesIO()
    zout = zipfile.ZipFile(out_buf, "w")

    for i in infos:
        data = zin.read(i.filename)
        if i.filename.startswith(MEDIA_PREFIX):
            origin_media[i.filename] = _md5(data)
        if (i.filename.startswith(MEDIA_PREFIX)
                and i.filename.lower().endswith(".png")):
            stat["n_png"] += 1
            stat["before"] += len(data)
            try:
                new, has_alpha = quantize_png(data, colors)
                if has_alpha:
                    stat["alpha"] += 1
                # 只在确有收益时替换，避免反向增大
                if len(new) < len(data) * (1 - min_gain):
                    data = new
                    stat["n_shrunk"] += 1
            except Exception as ex:      # 单张失败不拖垮整份
                print("      ! %s 量化失败，保留原图：%s" % (i.filename, ex))
            stat["after"] += len(data)
        # 保持原条目顺序、原压缩类型与属性
        zi = zipfile.ZipInfo(i.filename, date_time=i.date_time)
        zi.compress_type = i.compress_type
        zi.external_attr = i.external_attr
        zi.internal_attr = i.internal_attr
        zi.create_system = i.create_system
        zout.writestr(zi, data)

    zout.close()
    new_bytes = out_buf.getvalue()
    name = os.path.basename(path)

    print("  %-46s %6.1f MB → %6.1f MB  (%.0f%%)  PNG %d 张压 %d 张，带透明 %d"
          % (name[:44], src_size / 1048576, len(new_bytes) / 1048576,
             100.0 * len(new_bytes) / src_size if src_size else 0,
             stat["n_png"], stat["n_shrunk"], stat["alpha"]))

    if dry_run:
        return src_size, len(new_bytes), False

    if len(new_bytes) >= src_size:
        print("      (无收益，保持原文件不动)")
        return src_size, src_size, False

    if sidecar:
        side = os.path.splitext(path)[0] + "-origin.json"
        payload = {
            "note": ("外部原件指纹。本仓 pptx 已做媒体压缩、与外部件不再字节一致，"
                     "判重（三项比对的 media md5 项）请与本文件比，不要与仓内 pptx 比。"),
            "shrunk_at": datetime.date.today().isoformat(),
            "origin_bytes": src_size,
            "origin_md5": _md5(origin_bytes),
            "shrunk_bytes": len(new_bytes),
            "colors": colors,
            "origin_media_md5": origin_media,
        }
        with open(side, "w", encoding="utf-8", newline="") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    with open(path, "wb") as f:
        f.write(new_bytes)
    return src_size, len(new_bytes), True


def main():
    ap = argparse.ArgumentParser(description="pptx 媒体压缩（入库前必跑）")
    ap.add_argument("pptx", nargs="+")
    ap.add_argument("--colors", type=int, default=256)
    ap.add_argument("--min-gain", type=float, default=0.15,
                    help="单张至少省这么多比例才替换（默认 0.15）")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-sidecar", action="store_true",
                    help="不写原件指纹（不推荐，会丢判重能力）")
    args = ap.parse_args()

    tb = ta = 0
    bad = 0
    for p in args.pptx:
        if not os.path.isfile(p):
            print("  ! 找不到：%s" % p)
            bad += 1
            continue
        try:
            b, a, _ = shrink(p, args.colors, args.min_gain,
                             args.dry_run, not args.no_sidecar)
            tb += b
            ta += a
        except Exception as ex:
            print("  ! %s 处理失败：%s" % (os.path.basename(p), ex))
            bad += 1

    if tb:
        print("\n合计 %.1f MB → %.1f MB，省下 %.1f MB（降到 %.0f%%）%s"
              % (tb / 1048576, ta / 1048576, (tb - ta) / 1048576,
                 100.0 * ta / tb, "  [dry-run，未写盘]" if args.dry_run else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
