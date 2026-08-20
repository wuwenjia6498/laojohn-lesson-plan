# -*- coding: utf-8 -*-
"""批量去豆包AI水印 · 第二批（四个目录）。

与第一批同管线；方位判定改为「已知参考模板形状匹配」：
  * 启动时从第一批(孤独的小螃蟹, 1728x2304 组, 右下角)重建参考模板 REF0
  * 每组: min堆栈证据图(腐蚀) 与 REF0 做 TM_CCOEFF_NORMED, 4方向取最优;
    匹配分达标才认定水印方位, 再按该方向建本组模板与alpha
  * n<4 小组/单张: 逐张同法匹配(优先同目录大组模板), 不达标=无水印只缩放
  * 输入只认原图: *.png + 无同名png且不带-800后缀的 *.jpg
  * 源是.jpg的输出加-800后缀; 原宽<=800不放大
"""
import cv2
import numpy as np
from pathlib import Path
from collections import defaultdict

REF_DIR = Path(r"C:\Users\69491\Desktop\孤独的小螃蟹插图\孤独的小螃蟹")
DIRS = [
    Path(r"C:\Users\69491\Desktop\克雷洛夫寓言插图\克雷洛夫寓言插图"),
    Path(r"C:\Users\69491\Desktop\大头儿子和小头爸爸插图\大头儿子和小头爸爸插图"),
    Path(r"C:\Users\69491\Desktop\稻草人插图\稻草人插图"),
    Path(r"C:\Users\69491\Desktop\小狗的小房子插图\小狗的小房子插图"),
]
PREVIEW = Path(__file__).parent / "previews_batch2"
PREVIEW.mkdir(exist_ok=True)

ROI_H, ROI_W = 110, 340
TARGET_W = 800
JPG_QUALITY = 92
ITERS = 4
MIN_GROUP = 4
MATCH_TH = 0.45        # 形状匹配分数下限（组与单张同用）
K3 = np.ones((3, 3), np.uint8)

rng = np.random.default_rng(20260805)

def imread(p):
    return cv2.imdecode(np.fromfile(str(p), dtype=np.uint8), cv2.IMREAD_COLOR)

def imwrite(p, img, params=None):
    ok, buf = cv2.imencode(Path(p).suffix, img, params or [])
    assert ok, p
    buf.tofile(str(p))

def source_files(d: Path):
    pngs = sorted(d.glob("*.png"))
    png_stems = {p.stem for p in pngs}
    jpgs = [p for p in sorted(d.glob("*.jpg")) if p.stem not in png_stems and not p.stem.endswith("-800")]
    return pngs + jpgs

def out_name(src: Path) -> Path:
    if src.suffix.lower() in (".jpg", ".jpeg"):
        return src.with_name(src.stem + "-800.jpg")
    return src.with_suffix(".jpg")

def rot(img, k):
    return np.ascontiguousarray(np.rot90(img, k)) if k % 4 else img

def unrot(img, k):
    return np.ascontiguousarray(np.rot90(img, -k)) if k % 4 else img

def evidence(gray_list, T_dil):
    evid = []
    for g in gray_list:
        B = cv2.inpaint(g, T_dil, 5, cv2.INPAINT_TELEA).astype(np.float32)
        e = (g.astype(np.float32) - B) / np.maximum(255.0 - B, 12.0)
        evid.append(e)
    return np.median(np.stack(evid), axis=0)

def emin_map(gray_roi_min):
    se = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
    bg = cv2.morphologyEx(gray_roi_min.astype(np.uint8), cv2.MORPH_OPEN, se)
    bg = cv2.medianBlur(bg, 15).astype(np.float32)
    return (gray_roi_min.astype(np.float32) - bg) / np.maximum(255.0 - bg, 12.0)

def clean_T(T):
    T = cv2.morphologyEx(T, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    ncc, lab, stats, _ = cv2.connectedComponentsWithStats(T, connectivity=8)
    for i in range(1, ncc):
        if stats[i, cv2.CC_STAT_AREA] < 12:
            T[lab == i] = 0
    return T

def br_roi_gray(img):
    h, w = img.shape[:2]
    return cv2.cvtColor(img[h-ROI_H:h, w-ROI_W:w], cv2.COLOR_BGR2GRAY)

def build_group_template(grays_roi):
    gmin = np.stack(grays_roi).astype(np.float32).min(axis=0)
    T = (emin_map(gmin) > 0.28).astype(np.uint8) * 255
    return clean_T(T)

def ref_tpl(ref):
    """参考模板腐蚀后按bbox裁出，返回(tpl, tx0, ty0)。"""
    Te = cv2.erode(ref["T"], K3)
    ys, xs = np.where(Te > 0)
    ty0, ty1, tx0, tx1 = ys.min(), ys.max()+1, xs.min(), xs.max()+1
    return (Te[ty0:ty1, tx0:tx1] > 0).astype(np.float32), tx0, ty0

def match_evidence(e_binary, ref):
    """腐蚀证据图 vs 参考模板：返回(score, dx, dy)。"""
    tpl, tx0, ty0 = ref_tpl(ref)
    e = cv2.erode(e_binary.astype(np.uint8), K3).astype(np.float32)
    res = cv2.matchTemplate(e, tpl, cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(res)
    return float(mx), loc[0]-tx0, loc[1]-ty0

def detect_group_rotation(imgs, ref):
    """4方向对参考模板匹配组min堆栈证据，返回(k, score)。"""
    best = (0, -1.0)
    for k in range(4):
        grays = [br_roi_gray(rot(im, k)) for im in imgs]
        gmin = np.stack(grays).astype(np.float32).min(axis=0)
        e = (emin_map(gmin) > 0.28).astype(np.uint8)
        score, _, _ = match_evidence(e, ref)
        if score > best[1]:
            best = (k, score)
    return best

def group_alpha(imgs_rot, T):
    h, w = imgs_rot[0].shape[:2]
    rois = [im[h-ROI_H:h, w-ROI_W:w].astype(np.float32) for im in imgs_rot]
    T_dil = cv2.dilate(T, np.ones((7, 7), np.uint8), iterations=1)
    sel = T_dil > 0
    alpha = np.zeros((ROI_H, ROI_W), np.float32)
    for it in range(ITERS):
        a3 = np.minimum(alpha, 0.85)[..., None]
        rec_grays = [cv2.cvtColor(np.clip((r - a3*255.0)/np.maximum(1.0-a3, 0.15), 0, 255).astype(np.uint8), cv2.COLOR_BGR2GRAY) for r in rois]
        resid = np.clip(evidence(rec_grays, T_dil), -0.5, 1.0)
        alpha = np.clip(alpha + resid*(1.0-np.minimum(alpha, 0.9)), 0.0, 1.0)
        alpha[~sel] = 0.0
    core = ((alpha > 0.7).astype(np.uint8)) * 255
    core = cv2.dilate(core, K3, iterations=1)
    alpha = cv2.GaussianBlur(alpha, (3, 3), 0)
    return alpha, T_dil, core

def finish_box(img_u8, bx0, bx1, by0, by1, ring_px, flat_th, excl=None):
    H, W = img_u8.shape[:2]
    g = cv2.cvtColor(img_u8, cv2.COLOR_BGR2GRAY).astype(np.float32)
    imgf = img_u8.astype(np.float32)
    rows_above = list(range(max(0, by0 - ring_px), by0))
    rows_below = list(range(by1, min(H, by1 + ring_px)))
    if not rows_above:
        rows_above = rows_below
    if not rows_below:
        rows_below = rows_above
    assert rows_above and rows_below, "文字框上下环带均为空"
    ring = g[rows_above + rows_below, bx0:bx1]
    col_std = ring.std(axis=0)
    col_std = cv2.blur(col_std.reshape(1, -1), (1, 17)).ravel()
    col_flat = (col_std < flat_th).astype(np.float32)

    top_c = imgf[rows_above, bx0:bx1].mean(axis=0)
    bot_c = imgf[rows_below, bx0:bx1].mean(axis=0)
    top_c = cv2.blur(top_c.reshape(1, -1, 3), (1, 17)).reshape(-1, 3)
    bot_c = cv2.blur(bot_c.reshape(1, -1, 3), (1, 17)).reshape(-1, 3)
    bh = by1 - by0
    t = ((np.arange(bh) + 0.5) / bh)[:, None, None]
    fill = top_c[None, :, :] * (1 - t) + bot_c[None, :, :] * t
    ring_col = imgf[rows_above + rows_below, bx0:bx1]
    hp = ring_col - cv2.blur(ring_col, (5, 5))

    fill_g = fill.mean(axis=2)
    box_g = g[by0:by1, bx0:bx1]
    absd = np.abs(box_g - fill_g)
    if excl is not None:
        absd = np.where(excl[by0:by1, bx0:bx1], np.nan, absd)
    with np.errstate(all="ignore"):
        dev = np.nanpercentile(absd, 95, axis=0)
    dev = np.nan_to_num(dev, nan=0.0)
    dev = cv2.blur(dev.reshape(1, -1).astype(np.float32), (1, 9)).ravel()
    col_flat = col_flat * (dev < 25).astype(np.float32)
    min_run = max(10, (bx1 - bx0) // 8)
    flags = col_flat > 0.5
    run_ok = np.zeros_like(flags)
    i = 0
    N = len(flags)
    while i < N:
        if flags[i]:
            j = i
            while j < N and flags[j]:
                j += 1
            if j - i >= min_run:
                run_ok[i:j] = True
            i = j
        else:
            i += 1
    col_flat = run_ok.astype(np.float32)
    col_flat = cv2.blur(col_flat.reshape(1, -1), (1, 7)).ravel()

    hp_col = hp.std(axis=(0, 2))
    flat_idx = col_flat > 0.5
    sigma = float(np.median(hp_col[flat_idx])) if flat_idx.any() else 1.0
    n = rng.normal(0, max(sigma, 0.5) * 0.5, (fill.shape[0], fill.shape[1], 1))
    fill = fill + n

    out = imgf.copy()
    cf = col_flat[None, :, None]
    out[by0:by1, bx0:bx1] += (fill - imgf[by0:by1, bx0:bx1]) * cf
    return np.clip(out, 0, 255).astype(np.uint8)

def restore_image(img_rot, alpha, T, T_dil, core, k, src: Path, prefix: str,
                  skip_wm=False):
    h, w = img_rot.shape[:2]
    if skip_wm:
        out = img_rot
    else:
        a3 = np.minimum(alpha, 0.85)[..., None]
        roi = img_rot[h-ROI_H:h, w-ROI_W:w].astype(np.float32)
        rec = np.clip((roi - a3*255.0)/np.maximum(1.0-a3, 0.15), 0, 255).astype(np.uint8)
        if core.any():
            rec = cv2.inpaint(rec, core, 3, cv2.INPAINT_TELEA)
        k5 = np.ones((5, 5), np.uint8)
        edge_band = cv2.dilate(T, k5) & cv2.bitwise_not(cv2.erode(T, k5))
        eb3 = (edge_band > 0)[..., None]
        med = cv2.medianBlur(rec, 5)
        rec = np.where(eb3, med, rec)
        med = cv2.medianBlur(rec, 5)
        rec = np.where(eb3, med, rec)
        out = img_rot.copy()
        out[h-ROI_H:h, w-ROI_W:w] = rec

        ys, xs = np.where(T > 0)
        rbx0, rbx1 = max(0, xs.min()-4), min(ROI_W, xs.max()+5)
        rby0, rby1 = max(0, ys.min()-4), min(ROI_H, ys.max()+5)
        excl_full = np.zeros(out.shape[:2], bool)
        excl_full[h-ROI_H:h, w-ROI_W:w] = cv2.dilate(T_dil, np.ones((5, 5), np.uint8)) > 0
        out = finish_box(out,
                         w-ROI_W+rbx0, w-ROI_W+rbx1,
                         h-ROI_H+rby0, h-ROI_H+rby1,
                         ring_px=12, flat_th=6.5, excl=excl_full)

    W_orig = h if k % 2 else w
    scale = TARGET_W / W_orig if W_orig > TARGET_W else 1.0
    if scale != 1.0:
        resized = cv2.resize(out, (round(w*scale), round(h*scale)), interpolation=cv2.INTER_AREA)
    else:
        resized = out

    if not skip_wm:
        rh, rw = resized.shape[:2]
        bx0 = max(0, round((w-ROI_W+rbx0-2)*scale)); bx1 = min(rw, round((w-ROI_W+rbx1+2)*scale))
        by0 = max(0, round((h-ROI_H+rby0-2)*scale)); by1 = min(rh, round((h-ROI_H+rby1+2)*scale))
        excl_small = cv2.resize(excl_full.astype(np.uint8), (rw, rh), interpolation=cv2.INTER_NEAREST) > 0
        resized = finish_box(resized, bx0, bx1, by0, by1, ring_px=6, flat_th=5.0, excl=excl_small)
        crop = resized[max(0, rh-70):, max(0, rw-260):]
        imwrite(PREVIEW / f"corner_{prefix}_{src.stem}.png", crop)

    final = unrot(resized, k)
    imwrite(out_name(src), final, [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])

def match_singleton(img, ref):
    best = (None, -1.0, 0, 0)
    for k in range(4):
        r = rot(img, k)
        hh, ww = r.shape[:2]
        if hh < ROI_H or ww < ROI_W:
            continue
        e = (emin_map(br_roi_gray(r).astype(np.float32)) > 0.28).astype(np.uint8)
        score, dx, dy = match_evidence(e, ref)
        if score > best[1]:
            best = (k, score, dx, dy)
    k, score, dx, dy = best
    if k is None or score < MATCH_TH:
        return None, None, None, score
    M = np.float32([[1, 0, dx], [0, 1, dy]])
    T_shift = cv2.warpAffine(ref["T"], M, (ROI_W, ROI_H))
    A_shift = cv2.warpAffine(ref["alpha"], M, (ROI_W, ROI_H))
    return k, T_shift, A_shift, score

# ---------------- 参考模板（第一批 · 已知右下角） ----------------
ref_imgs = []
for p in sorted(REF_DIR.glob("*.png")):
    img = imread(p)
    if img.shape[:2] == (2304, 1728):
        ref_imgs.append(img)
print(f"reference: {len(ref_imgs)} imgs from 孤独的小螃蟹 1728x2304")
T0 = build_group_template([br_roi_gray(im) for im in ref_imgs])
A0, _, _ = group_alpha(ref_imgs, T0)
REF0 = {"T": T0, "alpha": A0}
print("reference template px:", int((T0 > 0).sum()))

# ---------------- 主流程 ----------------
for D in DIRS:
    prefix = D.parent.name.replace("插图", "")
    files = source_files(D)
    groups = defaultdict(list)
    for p in files:
        img = imread(p)
        groups[img.shape[:2]].append((p, img))
    print(f"=== {D.parent.name}: {len(files)} files, {len(groups)} groups")

    smalls = []
    folder_ref = {}
    for (h, w), items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        if len(items) < MIN_GROUP:
            smalls.extend(items)
            continue
        imgs = [im for _, im in items]
        k, score = detect_group_rotation(imgs, REF0)
        print(f"  group {w}x{h} n={len(items)} -> k={k} match={score:.2f}")
        if score < MATCH_TH:
            print("    -> 无水印，整组直接缩放")
            for p, im in items:
                restore_image(im, None, None, None, None, 0, p, prefix, skip_wm=True)
            continue
        imgs_rot = [rot(im, k) for im in imgs]
        T = build_group_template([br_roi_gray(im) for im in imgs_rot])
        alpha, T_dil, core = group_alpha(imgs_rot, T)
        if "T" not in folder_ref or score > folder_ref["score"]:
            folder_ref = {"T": T, "alpha": alpha, "score": score}
        for (p, _), im_rot in zip(items, imgs_rot):
            restore_image(im_rot, alpha, T, T_dil, core, k, p, prefix)

    for p, img in smalls:
        use_ref = folder_ref if "T" in folder_ref else REF0
        k, T_s, A_s, score = match_singleton(img, use_ref)
        if k is None:
            print(f"  {p.name}: match={score:.2f} -> 无水印，直接缩放")
            restore_image(img, None, None, None, None, 0, p, prefix, skip_wm=True)
        else:
            print(f"  {p.name}: match={score:.2f} k={k} -> 模板迁移修复")
            T_s = clean_T((T_s > 127).astype(np.uint8) * 255)
            T_dil = cv2.dilate(T_s, np.ones((7, 7), np.uint8), iterations=1)
            core = ((A_s > 0.7).astype(np.uint8)) * 255
            core = cv2.dilate(core, K3, iterations=1)
            restore_image(rot(img, k), A_s, T_s, T_dil, core, k, p, prefix)

print("all done")
