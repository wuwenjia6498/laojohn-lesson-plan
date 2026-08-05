# -*- coding: utf-8 -*-
r"""
dewatermark_autocrop —— 原书插图素材清洗（去豆包水印 + 裁白边）。

一次性素材清洗工具，不属于任何 SKILL 流水线；放在 `读书会原书插图\_tools\` 是因为它对
**无 git 历史、无上游副本**的资产做不可逆变换，脚本本身就是"做过什么"的唯一记录
（该目录下 .py 不被 gitignore，图片才被挡）。

处理对象分两批，**策略不同、不可混用**：
  · 红描批（本书＝插-01…插-11）：原书真图经豆包 AI 处理过，右下角带水印，且四周大片纯白。
    → 去水印 + 裁白边。
  · 彩色批（插-12…插-32）：真实书页扫描，无水印，页边是阴影渐变而非白。
    → **整批只备份、不处理**。实测裁切在 19/21 张上空转，动了的 5 张切掉的是印刷页真实页边距。

两条硬约束：
  1. **去水印必须先于裁白边**。插-05/插-10 的画面全在上半部，水印是下半部唯一墨迹；
     先裁的话包围盒被水印拖到底，保留近 900px 纯白，裁切失效约 40%。故 --autocrop
     会断言 --dewatermark 已对该文件置位，否则拒绝运行。
  2. **处理从 `_原始\` 读、写回顶层规范路径**。不用侧车目录：回插件
     `insert_images_docx.py` 的 `resolve_images_dir` 缺省就是顶层路径，谁忘了传
     `--images-dir` 就会静默拿带水印的原图重建 docx 且不报错。

用法（按序，任一步失败即中止）：
  PYTHONUTF8=1 python dewatermark_autocrop.py <书目录> --backup
  PYTHONUTF8=1 python dewatermark_autocrop.py <书目录> --detect
  PYTHONUTF8=1 python dewatermark_autocrop.py <书目录> --clean     ← 日常走这个
  PYTHONUTF8=1 python dewatermark_autocrop.py <书目录> --verify
  PYTHONUTF8=1 python dewatermark_autocrop.py <书目录> --audit-docx <配图.docx>

--clean 把去水印与裁白边在内存里连做、**只存一次 JPEG**。分步的 --dewatermark /
--autocrop 保留作调试，但连着跑会多出一代 JPEG 重编码（实测每代让 sat 临界像素掉
0.4~1.2%），对不可再生的扫描件是白扔画质，日常不要用。
"""
import os
import sys
import json
import shutil
import hashlib
import zipfile
import argparse
import datetime

import numpy as np
from PIL import Image

BACKUP_DIR = '_原始'
STATE_FILE = '_清洗记录.json'
SHEET_FILE = '_图单.md'
IMG_EXTS = ('.jpg', '.jpeg', '.png')

# ---- 判据常量（实测值，改动前先重跑 --detect 对照 plan 里的实测表）----------
WM_SAT_MAX = 12      # 水印无彩色；红线抗锯齿边落在 13–24，故意两边都不认
WM_LUM_MAX = 246     # 实测水印亮度区间 203–246
WM_LUM_RELAX = 252   # 涂白时框内放宽，清掉字形边缘灰晕
ART_SAT_MIN = 25     # 彩色（红线）判据
ROI_X_FRAC = 0.70    # 水印 ROI：右 30% × 底 8%
ROI_Y_FRAC = 0.92
ROW_MIN = 12         # 行列剖面阈值：字形行约 55px/行，抗锯齿只 1–5px/行
COL_MIN = 6
DENSITY_RANGE = (0.10, 0.30)   # sanity 门
HEIGHT_RANGE = (50, 100)
CROP_T = 245         # 裁切墨迹阈值；实测 248–220 是平坦高原，252 不可用
CROP_PAD_FRAC = 0.03
JPEG_QUALITY = 95


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load_rgb(path):
    with Image.open(path) as im:
        return np.array(im.convert('RGB'))


def save_jpg(arr, path):
    Image.fromarray(arr).save(path, quality=JPEG_QUALITY, subsampling=0)


def sat_lum(a):
    """返回 (饱和度, 亮度)，输入 uint8 HxWx3。"""
    a = a.astype(np.int16)
    return a.max(axis=2) - a.min(axis=2), a.sum(axis=2) / 3.0


def list_images(d):
    out = []
    for fn in sorted(os.listdir(d)):
        stem, ext = os.path.splitext(fn)
        if ext.lower() in IMG_EXTS and not stem.startswith('_'):
            out.append(stem)
    return out


def state_path(book_dir):
    return os.path.join(book_dir, STATE_FILE)


def load_state(book_dir):
    p = state_path(book_dir)
    if os.path.isfile(p):
        with open(p, encoding='utf-8') as f:
            return json.load(f)
    return {'book': os.path.basename(book_dir.rstrip('\\/')),
            'targets': [], 'detected': {}, 'dewatermarked': [], 'autocropped': {}}


def save_state(book_dir, st):
    st['updated'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(state_path(book_dir), 'w', encoding='utf-8') as f:
        json.dump(st, f, ensure_ascii=False, indent=2)


def find_file(d, stem):
    for ext in IMG_EXTS:
        p = os.path.join(d, stem + ext)
        if os.path.isfile(p):
            return p
    return None


# ---------------------------------------------------------------- 水印检测
def detect_wm(arr):
    """行列剖面法定位水印。返回 (box, density, (w,h)) 或 None。

    朴素包围盒会被红线抗锯齿边污染（如 (243,236,236) sat=7 lum=238 也满足水印判据），
    在插-11 上把上边界从 y=2113 顶到 2088。故先按行/列填充数过滤再取包围盒。
    """
    H, W = arr.shape[:2]
    x0, y0 = int(ROI_X_FRAC * W), int(ROI_Y_FRAC * H)
    roi = arr[y0:, x0:]
    sat, lum = sat_lum(roi)
    is_wm = (sat <= WM_SAT_MAX) & (lum <= WM_LUM_MAX)

    rows = np.where(is_wm.sum(axis=1) >= ROW_MIN)[0]
    cols = np.where(is_wm.sum(axis=0) >= COL_MIN)[0]
    if rows.size == 0 or cols.size == 0:
        return None
    y1, y2 = int(rows.min()), int(rows.max())
    x1, x2 = int(cols.min()), int(cols.max())
    density = float(is_wm[y1:y2 + 1, x1:x2 + 1].mean())
    w, h = x2 - x1 + 1, y2 - y1 + 1
    return (x0 + x1, y0 + y1, x0 + x2, y0 + y2), density, (w, h)


def sanity_ok(density, size):
    lo, hi = DENSITY_RANGE
    hlo, hhi = HEIGHT_RANGE
    return lo <= density <= hi and hlo <= size[1] <= hhi


# ---------------------------------------------------------------- 去水印
ART_DILATE = 15      # 「画面附近」的膨胀核，护住红线不被误涂
ART_DILATE_IT = 2


def remove_wm(arr, box, pad=3):
    """框内去水印：**只清白底上的水印，压在画面上的一律不动**。

    返回 (清除px, 残留px)；残留 > 0 表示该图有不可去除的水印痕。

    走到这个策略是因为前两种都实测失败了（别再回头试）：
      · 纯涂白（sat<=12 全涂）——水印压在红线上时把红线一起涂白，目视是红色线条中间
        挖出「豆包AI生成」的白色负形，比不处理更刺眼。
      · cv2.inpaint(TELEA)——掩码覆盖整个字形区，TELEA 无法重建细密线条纹理，
        把插-11 的桌饰糊成一片粉色色块，更差。
      · 收紧 sat 阈值到 2/4/6/8 也无效：五档实测字形负形一样清晰——**水印覆盖处的
        红线信息在豆包处理时就已烧掉、不可恢复**，能选的只是「留什么样的痕」。

    故：把 sat>25 的画面掩码膨胀出「画面附近」，该范围内不动笔。白底恢复干净，
    压在画面上的水印保留为淡痕——画面结构完整，是三者里最好的。
    """
    H, W = arr.shape[:2]
    x1, y1, x2, y2 = box
    x1, y1 = max(0, x1 - pad), max(0, y1 - pad)
    x2, y2 = min(W - 1, x2 + pad), min(H - 1, y2 + pad)
    sub = arr[y1:y2 + 1, x1:x2 + 1]
    sat, lum = sat_lum(sub)
    is_wm = (sat <= WM_SAT_MAX) & (lum <= WM_LUM_RELAX)

    art = (sat > ART_SAT_MIN).astype(np.uint8)
    if art.any():
        import cv2
        near = cv2.dilate(art, np.ones((ART_DILATE, ART_DILATE), np.uint8),
                          iterations=ART_DILATE_IT).astype(bool)
    else:
        near = np.zeros(sat.shape, dtype=bool)

    mask = is_wm & (~near)
    sub[mask] = 255
    return int(mask.sum()), int((is_wm & near).sum())


# ---------------------------------------------------------------- 裁白边
def content_bbox(arr, T=CROP_T):
    """内容包围盒（四边都算，留白不总在上方：插-05/10 在下、横向插-02 在左）。"""
    sat, lum = sat_lum(arr)
    ink = (lum <= T) | (sat > ART_SAT_MIN)
    H, W = ink.shape
    rows = np.where(ink.sum(axis=1) >= max(3, W // 300))[0]
    cols = np.where(ink.sum(axis=0) >= max(3, H // 300))[0]
    if rows.size == 0 or cols.size == 0:
        return None
    return int(cols.min()), int(rows.min()), int(cols.max()), int(rows.max())


def pad_clamp(box, W, H):
    """按裁后短边 3% 加留白，**必须 clamp**：插-01/05/10/11 加边后会超出原图。"""
    x1, y1, x2, y2 = box
    pad = int(round(CROP_PAD_FRAC * min(x2 - x1 + 1, y2 - y1 + 1)))
    return (max(0, x1 - pad), max(0, y1 - pad),
            min(W - 1, x2 + pad), min(H - 1, y2 + pad))


# ================================================================ 子命令
def cmd_backup(book_dir, targets):
    bak = os.path.join(book_dir, BACKUP_DIR)
    if os.path.isdir(bak) and os.listdir(bak):
        print(f'[中止] {BACKUP_DIR}\\ 已存在且非空——幂等护栏。')
        print('       重复裁切会叠加、inpaint 不幂等。要重做请先人工确认并清空该目录。')
        return 1
    os.makedirs(bak, exist_ok=True)

    stems = list_images(book_dir)
    if not stems:
        print('[中止] 目录里没有图片。')
        return 1
    print(f'备份全部 {len(stems)} 张（不只处理目标的 {len(targets)} 张）→ {BACKUP_DIR}\\')
    bad = []
    for stem in stems:
        src = find_file(book_dir, stem)
        dst = os.path.join(bak, os.path.basename(src))
        shutil.copy2(src, dst)
        if sha256(src) != sha256(dst):
            bad.append(stem)
    if bad:
        print(f'[中止] SHA-256 校验失败：{bad}')
        return 1
    print(f'  {len(stems)} 张全部逐对 SHA-256 校验通过。')

    st = load_state(book_dir)
    st['targets'] = targets
    st['all_images'] = stems
    st['backup_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st['sha_original'] = {s: sha256(find_file(bak, s)) for s in stems}
    save_state(book_dir, st)
    print(f'  记录写入 {STATE_FILE}')
    print(f'\n⚠ {BACKUP_DIR}\\ 同样被 gitignore 挡着，**不是防磁盘损坏的真备份**。')
    print('  建议现在把它拷到外部存储，否则清洗前状态只存在于这块硬盘。')
    return 0


def cmd_detect(book_dir, targets, dry_run=True):
    bak = os.path.join(book_dir, BACKUP_DIR)
    src_dir = bak if os.path.isdir(bak) else book_dir
    st = load_state(book_dir)
    print(f'从 {os.path.basename(src_dir)} 检测水印（仅 {len(targets)} 张红描批）\n')
    print(f'{"文件":<8} {"尺寸":<12} {"水印框(x1,y1,x2,y2)":<26} {"w×h":<10} {"密度":<6} 门')
    ok = True
    for stem in targets:
        p = find_file(src_dir, stem)
        if not p:
            print(f'{stem:<8} [缺失]')
            ok = False
            continue
        arr = load_rgb(p)
        H, W = arr.shape[:2]
        r = detect_wm(arr)
        if not r:
            print(f'{stem:<8} {W}×{H:<7} 未检出')
            ok = False
            continue
        box, density, size = r
        gate = '通过' if sanity_ok(density, size) else '**未过**'
        if not sanity_ok(density, size):
            ok = False
        print(f'{stem:<8} {W}×{H:<7} {str(box):<26} {size[0]}×{size[1]:<6} '
              f'{density:.3f}  {gate}')
        st.setdefault('detected', {})[stem] = {
            'size': [W, H], 'box': list(box), 'density': round(density, 4),
            'wm_size': list(size)}
    if not dry_run:
        save_state(book_dir, st)
    print(f'\n{"全部通过 sanity 门" if ok else "⚠ 有未检出或未过门的，先查阈值再继续"}')
    return 0 if ok else 1


def cmd_dewatermark(book_dir, targets):
    bak = os.path.join(book_dir, BACKUP_DIR)
    if not os.path.isdir(bak):
        print(f'[中止] 没有 {BACKUP_DIR}\\，先跑 --backup。处理一律从备份读、写回顶层。')
        return 1
    st = load_state(book_dir)
    done = []
    print('去水印（选择性涂白，从 _原始\\ 读 → 写顶层）\n')
    for stem in targets:
        src = find_file(bak, stem)
        if not src:
            print(f'  {stem}: [缺失于备份]')
            return 1
        arr = load_rgb(src)
        r = detect_wm(arr)
        if not r:
            print(f'  {stem}: 未检出水印，跳过')
            return 1
        box, density, size = r
        if not sanity_ok(density, size):
            print(f'  {stem}: sanity 门未过（density={density:.3f} h={size[1]}），中止')
            return 1
        n, resid = remove_wm(arr, box)
        dst = os.path.join(book_dir, os.path.basename(src))
        save_jpg(arr, dst)
        done.append(stem)
        print(f'  {stem}: 清除 {n} px，残留 {resid} px  box={box}')
    st['dewatermarked'] = done
    st['dewatermark_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_state(book_dir, st)
    print(f'\n{len(done)} 张完成。彩色批未触碰。')
    return 0


def cmd_autocrop(book_dir, targets):
    st = load_state(book_dir)
    missing = [s for s in targets if s not in st.get('dewatermarked', [])]
    if missing:
        print('[中止] 以下文件尚未去水印，拒绝裁切：', missing)
        print('       顺序硬约束：水印在右下、远离画面主体，先裁会把水印算进包围盒，')
        print('       插-05/插-10 会保留近 900px 纯白，裁切失效约 40%。先跑 --dewatermark。')
        return 1

    print('裁白边（T=245、留白 3% 短边、clamp 到原图边界；仅红描批）\n')
    print(f'{"文件":<8} {"原尺寸":<12} {"内容包围盒":<26} {"裁后":<12} 变化')
    rec = {}
    for stem in targets:
        p = find_file(book_dir, stem)
        arr = load_rgb(p)
        H, W = arr.shape[:2]
        bb = content_bbox(arr)
        if not bb:
            print(f'{stem:<8} 未找到内容，跳过')
            return 1
        x1, y1, x2, y2 = pad_clamp(bb, W, H)
        out = arr[y1:y2 + 1, x1:x2 + 1]
        nh, nw = out.shape[:2]
        save_jpg(out, p)
        rec[stem] = {'from': [W, H], 'bbox': list(bb), 'to': [nw, nh]}
        print(f'{stem:<8} {W}×{H:<7} {str(bb):<26} {nw}×{nh:<7} '
              f'{nw * nh / (W * H):.2f}×面积')
    st['autocropped'] = rec
    st['autocrop_at'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    save_state(book_dir, st)
    print('\n注意：部分图裁后**页面占位反而变小**（纵向翻横向＝从限高改限宽），')
    print('      但画面内容显著放大。验收看内容占比，不是看图变大。')
    return 0


def rebuild_mid(bak_path, box):
    """重建「已去水印、未裁切」的中间态（确定性重算，供验收逐像素对比用）。"""
    arr = load_rgb(bak_path)
    remove_wm(arr, tuple(box))
    return arr


def cmd_clean(book_dir, targets):
    """一次成型：去水印 + 裁白边在内存里连做，**只存一次 JPEG**。

    分步跑 --dewatermark 再 --autocrop 会让图片经历三代 JPEG（原始/去水印/裁切），
    对不可再生的扫描件是白扔一代画质。分步子命令保留作调试用，日常走本命令。
    顺序（先涂白后裁切）在函数内天然成立——见模块头注释的顺序硬约束。
    """
    bak = os.path.join(book_dir, BACKUP_DIR)
    if not os.path.isdir(bak):
        print(f'[中止] 没有 {BACKUP_DIR}\\，先跑 --backup。')
        return 1
    st = load_state(book_dir)
    print('一次成型清洗（去水印 + 裁白边，单次编码）\n')
    print(f'{"文件":<8} {"原尺寸":<12} {"清除px":>8}{"残留px":>8}  {"内容包围盒":<26} {"裁后":<12}')
    det, dew, rec = {}, [], {}
    for stem in targets:
        src = find_file(bak, stem)
        if not src:
            print(f'{stem:<8} [缺失于备份]')
            return 1
        arr = load_rgb(src)
        H, W = arr.shape[:2]

        r = detect_wm(arr)
        if not r or not sanity_ok(r[1], r[2]):
            print(f'{stem:<8} 水印检测未过 sanity 门，中止')
            return 1
        box, density, size = r
        n, resid = remove_wm(arr, box)     # ① 先去水印（只清白底，护住画面）
        det[stem] = {'size': [W, H], 'box': list(box),
                     'density': round(density, 4), 'wm_size': list(size)}
        dew.append(stem)

        bb = content_bbox(arr)            # ② 再裁白边（此时水印已不在包围盒里）
        if not bb:
            print(f'{stem:<8} 未找到内容，中止')
            return 1
        x1, y1, x2, y2 = pad_clamp(bb, W, H)
        out = arr[y1:y2 + 1, x1:x2 + 1]
        nh, nw = out.shape[:2]
        save_jpg(out, os.path.join(book_dir, os.path.basename(src)))   # 只存这一次
        rec[stem] = {'from': [W, H], 'bbox': list(bb), 'to': [nw, nh]}
        det[stem]['wm_cleared'] = n
        det[stem]['wm_residual'] = resid
        print(f'{stem:<8} {W}×{H:<7} {n:>8}{resid:>8}  {str(bb):<26} {nw}×{nh:<7}'
              + ('  ← 有残留痕' if resid else ''))

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    st['detected'], st['dewatermarked'], st['autocropped'] = det, dew, rec
    st['cleaned_at'] = now
    st['pipeline'] = 'clean(单次编码：去水印+裁切一次成型)'
    save_state(book_dir, st)
    print(f'\n{len(dew)} 张完成，单次编码。彩色批未触碰。')
    return 0


def cmd_verify(book_dir, targets):
    bak = os.path.join(book_dir, BACKUP_DIR)
    st = load_state(book_dir)
    allimg = st.get('all_images') or list_images(book_dir)
    color = [s for s in allimg if s not in targets]
    fails = []

    print('=== ① 水印是否清净（检出且过 sanity 门才算残留）===')
    for stem in targets:
        arr = load_rgb(find_file(book_dir, stem))
        r = detect_wm(arr)
        known = st.get('detected', {}).get(stem, {}).get('wm_residual', 0)
        if r and sanity_ok(r[1], r[2]) and known:
            # 已登记的不可恢复残留：水印压在画面上，原始像素在豆包处理时已被烧掉
            print(f'  {stem}: 已知残留痕 {known}px（压在画面上，信息不可恢复）'
                  f' density={r[1]:.3f}')
        elif r and sanity_ok(r[1], r[2]):
            print(f'  {stem}: **仍检出水印** {r[0]} density={r[1]:.3f}')
            fails.append(f'①{stem}')
        elif r:
            # 裁掉空白后画面线条会落进底右 ROI，密度远低于文字（水印 0.14–0.23）
            print(f'  {stem}: 清净（ROI 内有画面线条 density={r[1]:.3f}，非文字）')
        else:
            print(f'  {stem}: 清净')

    print('\n=== ② 编码保真度（同一裁切区域内，处理前后彩色像素比，阈值 0.985）===')
    print('    分母＝去水印中间态按同一框裁出的未编码 array；单次 q95 重编码本身就掉')
    print('    0.4–1.2%。内容有没有被切掉，看下面的 ③，不看本项。')
    for stem in targets:
        rec = st['autocropped'][stem]
        box = st['detected'][stem]['box']
        mid = rebuild_mid(find_file(bak, stem), box)
        H, W = mid.shape[:2]
        cx1, cy1, cx2, cy2 = pad_clamp(tuple(rec['bbox']), W, H)
        s_mid, _ = sat_lum(mid[cy1:cy2 + 1, cx1:cx2 + 1])
        s_new, _ = sat_lum(load_rgb(find_file(book_dir, stem)))
        n_mid, n_new = int((s_mid > ART_SAT_MIN).sum()), int((s_new > ART_SAT_MIN).sum())
        ratio = n_new / n_mid if n_mid else 0
        flag = '  ←重点' if stem in ('插-06', '插-11') else ''
        # 阈值 0.985：分母是未编码的内存 array，单次 JPEG(q95) 重编码本身就会让
        # sat 临界像素掉 0.4–1.2%（已实测：插-03 单次即 0.9880）。本项测的是**编码
        # 保真度**，内容完整性由 ③「裁切框外无画面」判定——那项才是硬判据。
        bad = ratio < 0.985
        print(f'  {stem}: {ratio:.4f} ({n_new}/{n_mid}){flag}{"  **不足**" if bad else ""}')
        if bad:
            fails.append(f'②{stem}')

    print('\n=== ③ 裁切框外没有画面（红线判据 sat>25，不受纸张噪声影响）===')
    for stem in targets:
        rec = st['autocropped'][stem]
        box = st['detected'][stem]['box']
        mid = rebuild_mid(find_file(bak, stem), box)
        H, W = mid.shape[:2]
        cx1, cy1, cx2, cy2 = pad_clamp(tuple(rec['bbox']), W, H)
        s_mid, _ = sat_lum(mid)
        art = s_mid > ART_SAT_MIN
        outside = art.copy()
        outside[cy1:cy2 + 1, cx1:cx2 + 1] = False
        lost, total = int(outside.sum()), int(art.sum())
        frac = lost / total if total else 0
        bad = frac > 0.001
        print(f'  {stem}: 框外画面像素 {lost}/{total} = {frac * 100:.4f}%'
              f'{"  **切到内容**" if bad else ""}')
        if bad:
            fails.append(f'③{stem}')

    print('\n=== ④ 长宽比无一超 3:1 ===')
    for stem in targets:
        arr = load_rgb(find_file(book_dir, stem))
        H, W = arr.shape[:2]
        ar = max(W / H, H / W)
        bad = ar > 3
        print(f'  {stem}: {W}×{H} 比 {ar:.2f}{"  **超限**" if bad else ""}')
        if bad:
            fails.append(f'④{stem}')

    print(f'\n=== ⑤ 彩色批 {len(color)} 张 SHA-256 与 _原始\\ 完全一致（不可妥协）===')
    diff = []
    for stem in color:
        p_new, p_old = find_file(book_dir, stem), find_file(bak, stem)
        if not p_new or not p_old or sha256(p_new) != sha256(p_old):
            diff.append(stem)
    if diff:
        print(f'  **不一致**：{diff}')
        fails.append('⑤')
    else:
        print('  全部一致——危险路径从未跑到扫描件上。')

    print('\n=== ⑥ 每张能被 Pillow 与 docx 读取器读出 ===')
    from docx.image.image import Image as DocxImage
    for stem in allimg:
        p = find_file(book_dir, stem)
        try:
            with Image.open(p) as im:
                im.convert('RGB')
            di = DocxImage.from_file(p)
            assert di.px_width > 0 and di.px_height > 0
        except Exception as e:
            print(f'  {stem}: **失败** {e}')
            fails.append(f'⑥{stem}')
    print('  全部可读' if not any(f.startswith('⑥') for f in fails) else '  有失败')

    print('\n' + '=' * 60)
    if fails:
        print(f'✗ 未通过：{fails}')
        return 1
    print('✓ 六项断言全部通过。仍需人工目视：')
    print('  · 插-06/插-11 放 100%：压过水印的红线连续、无灰晕无白缺口')
    print('  · 插-05/插-10：下方空白确已消失（裁切顺序的哨兵）')
    print('  · 插-02：左侧空白已去（唯一横向图、唯一 300px 水印）')
    print('  · 插-03/07/09/11：新裁边附近淡红细线完好')
    print('  · 11 张右下角：无残留灰框或光晕')
    return 0


def cmd_audit_docx(docx_path, book_dir):
    """比对 docx 内嵌图与「清洗版/原始版」的 SHA-256。出现 ORIGINAL 即硬失败。"""
    bak = os.path.join(book_dir, BACKUP_DIR)
    clean = {sha256(find_file(book_dir, s)): s for s in list_images(book_dir)}
    orig = {}
    if os.path.isdir(bak):
        orig = {sha256(find_file(bak, s)): s for s in list_images(bak)}

    print(f'审计 {os.path.basename(docx_path)}\n')
    verdicts = []
    with zipfile.ZipFile(docx_path) as z:
        media = [n for n in z.namelist() if n.startswith('word/media/')]
        for name in sorted(media):
            data = z.read(name)
            h = hashlib.sha256(data).hexdigest()
            if h in clean:
                v, who = 'CLEANED', clean[h]
            elif h in orig:
                v, who = 'ORIGINAL', orig[h]
            else:
                v, who = 'UNKNOWN', '(非本目录图，可能是封面/logo)'
            verdicts.append(v)
            print(f'  {os.path.basename(name):<16} -> {v:<9} {who}')

    n_orig = verdicts.count('ORIGINAL')
    print(f'\n共 {len(verdicts)} 项：CLEANED {verdicts.count("CLEANED")} / '
          f'ORIGINAL {n_orig} / UNKNOWN {verdicts.count("UNKNOWN")}')
    if n_orig:
        print('✗ 硬失败：docx 里仍嵌着未清洗的原图，重跑回插。')
        return 1
    print('✓ 无 ORIGINAL。（UNKNOWN 多为封面页书封与 logo，属正常）')
    return 0


def main():
    ap = argparse.ArgumentParser(description='原书插图素材清洗（去水印 + 裁白边）')
    ap.add_argument('book_dir', nargs='?', default='', help='书目录，如 读书会原书插图\\神笔马良')
    ap.add_argument('--targets', default='插-01..插-11',
                    help='需处理的红描批编号区间或逗号清单（默认 插-01..插-11）')
    for flag in ('backup', 'detect', 'clean', 'dewatermark', 'autocrop', 'verify'):
        ap.add_argument(f'--{flag}', action='store_true')
    ap.add_argument('--dry-run', action='store_true', help='仅 --detect：不写记录文件')
    ap.add_argument('--audit-docx', default='')
    args = ap.parse_args()

    book_dir = args.book_dir
    if not book_dir:
        ap.error('需要给出书目录（位置参数），如 "读书会原书插图\\神笔马良"')

    if args.audit_docx:
        return cmd_audit_docx(args.audit_docx, book_dir)

    if not os.path.isdir(book_dir):
        print(f'[中止] 目录不存在：{book_dir}')
        return 1

    spec = args.targets
    if '..' in spec:
        a, b = spec.split('..')
        pre = a.rsplit('-', 1)[0]
        lo, hi = int(a.rsplit('-', 1)[1]), int(b.rsplit('-', 1)[1])
        targets = [f'{pre}-{i:02d}' for i in range(lo, hi + 1)]
    else:
        targets = [s.strip() for s in spec.split(',') if s.strip()]

    if args.backup:
        return cmd_backup(book_dir, targets)
    if args.detect:
        return cmd_detect(book_dir, targets, dry_run=args.dry_run)
    if args.clean:
        return cmd_clean(book_dir, targets)
    if args.dewatermark:
        return cmd_dewatermark(book_dir, targets)
    if args.autocrop:
        return cmd_autocrop(book_dir, targets)
    if args.verify:
        return cmd_verify(book_dir, targets)
    ap.error('需要指定一个动作：--backup/--detect/--dewatermark/--autocrop/--verify/--audit-docx')


if __name__ == '__main__':
    sys.exit(main())
