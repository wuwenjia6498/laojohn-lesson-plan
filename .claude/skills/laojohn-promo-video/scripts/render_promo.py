# -*- coding: utf-8 -*-
r"""宣传片链末步：讲解员口播片段 + B-roll 穿插 + 字幕 → 9:16 成片。**确定性，不调任何模型。**

    PYTHONUTF8=1 python render_promo.py <线> <课次> [--sample N] [--bgm <音频>] [--bgm-level -24]

画面结构（1080×1920，30fps，全屏出血——2026-09-27 由「奶油外框+圆角窗」改）：
    底层    讲解员口播片段（H3 生成，自带声音），等比铺满裁中
    B-roll  盖画不盖声：照片整屏替换画面（缓推缓拉）、kw/line 卡叠在讲解员上方；声音始终是讲解员
    角标    年级胶囊 + AI 标识，全片常驻左上
    字幕    逐句，白字深底条，放下三分之一（避开平台底部 UI）
    片尾    整屏卡：毛笔书名 + 二维码 + 行动句（取 品牌资产\校区信息.json，空项隐藏）

时间轴纪律（零漂移）：
    1. 每段长度＝片段实测开口前 HEAD 秒到收口后 TAIL 秒，按帧取整；首尾空白掐掉，节奏紧。
    2. 视频逐段编码后 concat 复制；**音频另走 PCM**：每段按 帧数×1600 样本精确截齐再拼，
       最后一次性编 AAC——AAC 逐段拼接会每段带进约 20ms padding，六七段累积就口型对不上。
    3. 句子时间：ASR 分段数与台词句数相等就用 ASR 时间；否则在开口～收口间按字数比例分。
"""
import argparse
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import wave

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _shared as S  # noqa: E402
import h3_prompt  # noqa: E402

FPS = 30
AR = 48000
SPF = AR // FPS                  # 1600 样本/帧
HEAD, TAIL = 0.12, 0.30          # 开口前留、收口后留（秒）
END_HOLD = 3.2                   # 片尾卡时长
SUB_Y = 1380                     # 字幕条顶：胸前留给手势，底部 ~380px 是平台 UI
CARD_Y = {"kw": 960, "line": 920}          # 讲解员胸前：脸在 y≈350~750，字幕条在 1230
THEME = {"bg": "#FBF5EA", "ink": "#2B2724", "accent": "#E07B24"}
FONT_SANS = r"C:\Windows\Fonts\NotoSansSC-VF.ttf"      # OFL，可商用
FONT_BRUSH = os.path.join(S.ROOT, ".claude", "skills", "laojohn-writing-poster",
                          "assets", "fonts", "MaShanZheng-Regular.woff2")  # OFL
MOTIONS = ("in", "out", "up", "down", "left", "right", "none")
CREAM = (255, 246, 229)          # 课件配图版的底带色（FFF6E5），插图、分屏面板都铺它
SPLIT_TOP, SPLIT_H = 270, 960    # 分屏：讲解员原画面从 y=270 起取 960 高（避开角标、含脸与手），放上半屏
SPLIT_SUB_DY = 250               # 分屏时字幕从 1380 挪到 1630，让出下半屏课件
PAN_H = 730                      # 横摇：裁出的那条放大到的高度（P09 三步框时第二步正好一屏宽）


def furl(p):
    return pathlib.Path(p).resolve().as_uri()


def ff():
    return S.ffmpeg_path().ffmpeg()


def run(args, cwd=None):
    r = subprocess.run([ff(), "-hide_banner", "-loglevel", "error", "-y"] + args,
                       cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg 失败：\n%s" % (r.stderr or "")[-1500:])


def spoken_len(t):
    return max(1, len(re.sub(r"[，。？！、：；“”‘’,.?!:;\s{}/b]", "", t)))


# ---------------------------------------------------------------- 时间轴
def plan(sc, out, segs):
    sb = json.load(open(os.path.join(out, "storyboard.json"), encoding="utf-8"))
    fresh = {r["id"]: r for r in h3_prompt.storyboard(sc, S.load_presenter(sc["meta"]["presenter"]), out)["segments"]}
    fresh_json = os.path.join(out, "storyboard.json")
    S.save_json(dict(json.load(open(fresh_json, encoding="utf-8")), approved=sb.get("approved")), fresh_json)
    plans = []
    for seg in segs:
        row = fresh[seg["id"]]
        mp4 = os.path.join(out, row["clip"])
        mj = mp4[:-4] + ".json"
        if not (os.path.exists(mp4) and os.path.exists(mj)):
            raise SystemExit("%s 还没生成口播片段（或台词改过、哈希变了）——先跑 gen_clips.py" % seg["id"])
        info = json.load(open(mj, encoding="utf-8"))
        if info.get("verdict") == "misread":
            raise SystemExit("%s 片段 ASR 判念错（相似度 %s），不许进成片" % (seg["id"], info.get("sim")))
        if info.get("verdict") == "unknown":
            print("  ？ %s 转写未核，成片后须人耳听一遍" % seg["id"])
        ss, se, dur = info["speech_start"], info["speech_end"], info["duration"]
        t0 = max(0.0, ss - HEAD)
        t1 = min(dur, se + TAIL)
        n = int(round((t1 - t0) * FPS))
        L = n / float(FPS)
        lines = seg["lines"]
        asr = info.get("asr_segments") or []
        if len(asr) == len(lines):
            starts = [max(0.0, a["start"] - t0) for a in asr]
            starts[0] = 0.0
        else:
            span0, span1 = ss - t0, se - t0
            w = [spoken_len(x) for x in lines]
            acc, starts = 0, []
            for x in w:
                starts.append(0.0 if not starts else span0 + (span1 - span0) * acc / float(sum(w)))
                acc += x
        cues = [{"start": starts[j], "end": starts[j + 1] if j + 1 < len(lines) else L, "text": lines[j]}
                for j in range(len(lines))]
        brolls = []
        for b in seg.get("broll") or []:
            st = cues[b["at"]]["start"] + b.get("offset", 0.25 if b["at"] else 0.6)
            en = min(st + b["dur"], L - (0 if b.get("layout") == "split" else 0.15))   # 分屏里人一直在，可贴到段尾
            brolls.append(dict(b, start=round(st, 3), end=round(en, 3)))
        brolls.sort(key=lambda b: b["start"])
        for a_, b_ in zip(brolls, brolls[1:]):      # 前一条让给后一条，不叠画
            a_["end"] = min(a_["end"], b_["start"])
        brolls = [b for b in brolls if b["end"] - b["start"] >= 0.8]
        fixes = antiflash(brolls, L)
        plans.append({"seg": seg, "clip": mp4, "t0": t0, "frames": n, "L": L, "cues": cues,
                      "brolls": brolls, "info": info, "fixes": fixes})
    return plans


MIN_SHOW = 1.0      # 讲解员全屏不足这么久就是「闪一下」（2026-09-28 用户点名），自动吸附掉


def antiflash(brolls, L):
    """把段内讲解员全屏空档里短于 MIN_SHOW 的吸附掉：段首→穿插提前到 0；两条之间→前一条接上；段尾→延到段尾。
    所有换画面的穿插都算（full / pan / split——分屏切回全屏讲解员不足 1 秒同样像闪）；字卡只叠一层，不算。返回调整说明。"""
    cov = [b for b in brolls if not b["src"].startswith("card:")]
    fixes = []
    if not cov:
        return fixes
    if 0 < cov[0]["start"] < MIN_SHOW:
        fixes.append("段首 %.2fs→0" % cov[0]["start"])
        cov[0]["start"] = 0.0
    for a, b in zip(cov, cov[1:]):
        gap = b["start"] - a["end"]
        if 0 < gap < MIN_SHOW:
            fixes.append("两条之间 %.2fs 接上" % gap)
            a["end"] = b["start"]
    if 0 < L - cov[-1]["end"] < MIN_SHOW:
        fixes.append("段尾 %.2fs 延到段尾" % (L - cov[-1]["end"]))
        cov[-1]["end"] = round(L, 3)
    return fixes


# ---------------------------------------------------------------- 画面层
class Layers(object):
    def __init__(self, sc, out):
        from playwright.sync_api import sync_playwright
        self.sc = sc
        self.dir = os.path.join(out, "_build", "layers")
        os.makedirs(self.dir, exist_ok=True)
        self._pw = sync_playwright().start()
        self._b = self._pw.chromium.launch()
        self.page = self._b.new_page(viewport={"width": 1080, "height": 1920})
        self.page.goto(furl(os.path.join(S.SKILL, "templates", "layer.html")))
        meta = sc["meta"]
        self.base = {"theme": dict(THEME, **(meta.get("theme") or {})),
                     "capsule": meta.get("capsule", ""), "ai_label": meta.get("ai_label") or "",
                     "logo": furl(os.path.join(S.ROOT, "品牌资产", "logo.png")),
                     "fonts": {"sans": furl(FONT_SANS),
                               "brush": furl(FONT_BRUSH) if os.path.exists(FONT_BRUSH) else ""}}
        self.wrap = S.wrap_fn()
        self.face_target = (face_target_of(S.load_presenter(meta["presenter"]))
                            if (meta.get("grade") or {}).get("auto") else None)

    def shot(self, name, spec):
        self.page.evaluate("s => render(s)", dict(self.base, **spec))
        fn = os.path.join(self.dir, name + ".png")
        self.page.locator("#stage").screenshot(path=fn, omit_background=True)
        return fn

    def sub(self, name, text):
        # 脚本 sub_breaks 给了手动断行（含换行符）就原样用，不再自动折——自动折会把「单元」这类词拆开
        body = text if "\n" in text else self.wrap(text, sub_max=14, line_max=15)
        return self.shot(name, {"layer": "sub2", "sub_y": SUB_Y, "text": body})

    def close(self):
        self._b.close()
        self._pw.stop()


def end_spec(sc):
    meta = sc["meta"]
    info = {}
    p = os.path.join(S.ROOT, "品牌资产", "校区信息.json")
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            info = json.load(f)
    e = dict(meta.get("end") or {})
    e.setdefault("title", meta.get("title", ""))
    if e.get("style") == "closing":         # 呼应首页：标题＋副题＋海报插画＋商标，不放二维码与行动句
        img = S.resolve(e["illus"])
        if S.md5_of(img) != e.get("md5"):
            raise SystemExit("片尾插画 md5 对不上：%s（先跑 check_script.py --pin）" % e["illus"])
        e["illus"] = furl(img)
        return {"layer": "end", "end": e}
    e.setdefault("cta", info.get("cta") or "扫码预约体验课")
    e.setdefault("note", info.get("note") or "")
    parts = [x for x in (info.get("address"), info.get("phone")) if x]
    e.setdefault("address", "　".join(parts))
    e["qrcode"] = furl(os.path.join(S.ROOT, "品牌资产", "qrcode.png"))
    return {"layer": "end", "end": e}


# ---------------------------------------------------------------- 分段渲染
def zoom(m, n):
    table = {
        "in": ("1+0.08*on/%d" % n, "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),
        "out": ("1.08-0.08*on/%d" % n, "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"),
        "up": ("1.08", "(iw-iw/zoom)/2", "(ih-ih/zoom)*(1-on/%d)" % n),
        "down": ("1.08", "(iw-iw/zoom)/2", "(ih-ih/zoom)*on/%d" % n),
        "left": ("1.08", "(iw-iw/zoom)*(1-on/%d)" % n, "(ih-ih/zoom)/2"),
        "right": ("1.08", "(iw-iw/zoom)*on/%d" % n, "(ih-ih/zoom)/2"),
        "none": ("1", "0", "0"),
    }
    z, x, y = table[m]
    return "zoompan=z='%s':x='%s':y='%s':d=%d:s=1080x1920:fps=%d" % (z, x, y, n, FPS)


def render_seg(L_, p, idx, bdir):
    seg, n, L = p["seg"], p["frames"], p["L"]
    name = "%02d_%s" % (idx, seg["id"])
    inputs = ["-i", p["clip"], "-loop", "1", "-framerate", str(FPS), "-t", "%.4f" % L,
              "-i", L_.shot("badge", {"layer": "badge"})]
    g = L_.sc["meta"].get("grade") or {}
    if g.get("auto"):
        # 按段对齐定妆照肤色：H3 每段曝光不一，固定提亮值调不准（实测 s1 L*57、s3 L*62，定妆照 69）
        p["grade"] = auto_grade(p["clip"], p["t0"], L, L_.face_target, g.get("strength", 0.85))
        gr = p["grade"]
        eq = (",eq=gamma_r=%.3f:gamma_g=%.3f:gamma_b=%.3f:saturation=%.3f"
              % (gr["gamma_r"], gr["gamma_g"], gr["gamma_b"], g.get("saturation", 1)))
    else:                                     # 旧写法：固定提亮值，如 {"gamma": 1.1}
        eq = (",eq=gamma=%.3f:brightness=%.3f:saturation=%.3f" % (g.get("gamma", 1), g.get("brightness", 0),
                                                                 g.get("saturation", 1))) if g else ""
    fc = ["[0:v]trim=start=%.4f:duration=%.4f,setpts=PTS-STARTPTS,fps=%d,"
          "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1%s[v0]"
          % (p["t0"], L, FPS, eq)]
    splits = [b for b in p["brolls"] if b.get("layout") == "split"]
    if splits:                                  # 分屏要复用讲解员画面：先把底层分出几路
        fc.append("[v0]split=%d[v0m]%s" % (len(splits) + 1, "".join("[pv%d]" % i for i in range(len(splits)))))
        last = "[v0m]"
    else:
        last = "[v0]"
    k, si = 2, 0
    for j, b in enumerate(p["brolls"]):
        src = b["src"]
        tag = "[b%d]" % j
        lay = b.get("layout", "full")
        if lay in ("split", "pan"):
            img = S.resolve(src)
            if S.md5_of(img) != b.get("md5"):
                raise SystemExit("%s 穿插素材 md5 对不上：%s（先跑 check_script.py）" % (seg["id"], src))
            if lay == "split":
                # 上半屏讲解员（口型不断）＋下半屏课件：面板 png 铺底，讲解员裁上段盖在上面
                panel = split_panel(img, b.get("crop"), os.path.join(bdir, "clips", "%s_split%d.png" % (name, j)))
                top = b.get("top_y", SPLIT_TOP)
                inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.4f" % L, "-i", panel]
                fc.append("[pv%d]crop=1080:%d:0:%d[pt%d]" % (si, SPLIT_H, top, si))
                fc.append("[%d:v][pt%d]overlay=0:0,format=yuv420p[ps%d]" % (k, si, si))
                fc.append("%s[ps%d]overlay=0:0:enable='between(t,%.3f,%.3f)'%s"
                          % (last, si, b["start"], b["end"], tag))
                si += 1
            else:
                # 横版页放大后横摇：先裁出一条，按高度放大，镜头从 pan[0] 缓动到 pan[1]
                strip, bw = pan_strip(img, b.get("crop"), b.get("pan_h", PAN_H),
                                      os.path.join(bdir, "clips", "%s_pan%d.png" % (name, j)))
                c0, c1 = b.get("pan", [0.0, 1.0])
                x0 = max(0, min(bw - 1080, c0 * bw - 540))
                x1 = max(0, min(bw - 1080, c1 * bw - 540))
                d = max(0.1, b["end"] - b["start"])
                # 起点停 30%、移动 50%、终点停 20%：镜头落在「最关键」那一框上让人读
                u = "clip((t-%.3f)/%.3f,0,1)" % (b["start"] + 0.3 * d, 0.5 * d)
                ease = "(3*pow(%s,2)-2*pow(%s,3))" % (u, u)
                inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.4f" % L, "-i", strip]
                fc.append("[%d:v]crop=1080:1920:x='%.1f+(%.1f)*%s':y=0,setsar=1,format=yuv420p[pp%d]"
                          % (k, x0, x1 - x0, ease, j))
                fc.append("%s[pp%d]overlay=0:0:enable='between(t,%.3f,%.3f)'%s"
                          % (last, j, b["start"], b["end"], tag))
        elif src.startswith("card:"):
            kind = src[5:]
            png = L_.shot("%s_%s%d" % (name, kind, j), {"layer": kind, "card": b["card"], "card_y": CARD_Y[kind]})
            inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.4f" % L, "-i", png]
            fc.append("%s[%d:v]overlay=0:0:enable='between(t,%.3f,%.3f)'%s" % (last, k, b["start"], b["end"], tag))
        else:
            img = S.resolve(src)
            if S.md5_of(img) != b.get("md5"):
                raise SystemExit("%s 穿插素材 md5 对不上：%s（先跑 check_script.py）" % (seg["id"], src))
            m = b.get("motion", "in")
            if m not in MOTIONS:
                raise SystemExit("%s motion 只认 %s" % (seg["id"], "/".join(MOTIONS)))
            if b.get("fit") == "contain":            # 横版素材（课件首页等）：完整放中间，底铺模糊
                img = contain_frame(img, os.path.join(bdir, "clips", "%s_contain%d.png" % (name, j)), b.get("crop"))
            elif b.get("fit") == "cutout":           # 课件透明底插图：铺课件同款米色底
                img = cutout_frame(img, os.path.join(bdir, "clips", "%s_cutout%d.png" % (name, j)), b.get("crop"))
            bn = int(round((b["end"] - b["start"]) * FPS)) + 1
            fx, fy = b.get("focus", [0.5, 0.5])
            inputs += ["-i", img]
            fc.append("[%d:v]scale=3240:5760:force_original_aspect_ratio=increase,"
                      "crop=3240:5760:(iw-3240)*%.3f:(ih-5760)*%.3f,setsar=1,%s,format=yuv420p,"
                      "setpts=PTS-STARTPTS+%.4f/TB[p%d]" % (k, fx, fy, zoom(m, bn), b["start"], j))
            fc.append("%s[p%d]overlay=0:0:eof_action=pass:enable='between(t,%.3f,%.3f)'%s"
                      % (last, j, b["start"], b["end"], tag))
        last, k = tag, k + 1
    fc.append("%s[1:v]overlay=0:0[vb]" % last)
    last = "[vb]"
    # 分屏期间字幕挪到下半屏课件的下面
    sy = "+".join("between(t,%.3f,%.3f)" % (b["start"], b["end"]) for b in splits)
    sy = "'%d*gte(%s,1)':eval=frame" % (SPLIT_SUB_DY, sy) if sy else "0"
    for j, c in enumerate(p["cues"]):
        inputs += ["-loop", "1", "-framerate", str(FPS), "-t", "%.4f" % L, "-i",
                   L_.sub("%s_sub%d" % (name, j), (seg.get("sub_breaks") or {}).get(str(j), c["text"]))]
        tag = "[s%d]" % j
        fc.append("%s[%d:v]overlay=x=0:y=%s:enable='between(t,%.3f,%.3f)'%s"
                  % (last, k, sy, c["start"], c["end"] - 0.001, tag))
        last, k = tag, k + 1
    fc.append("%sformat=yuv420p[out]" % last)
    clip = os.path.join(bdir, "clips", name + ".mp4")
    run(inputs + ["-filter_complex", ";".join(fc), "-map", "[out]", "-an", "-frames:v", str(n),
                  "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                  "-pix_fmt", "yuv420p", clip])
    wav = os.path.join(bdir, "clips", name + ".wav")
    run(["-i", p["clip"], "-vn", "-af", "atrim=start=%.4f,asetpts=PTS-STARTPTS,aresample=%d,apad"
         % (p["t0"], AR), "-ac", "2", "-ar", str(AR), "-c:a", "pcm_s16le",
         "-t", "%.6f" % L, wav + ".tmp.wav"])
    exact_wav(wav + ".tmp.wav", wav, n * SPF)
    if peak_db(wav) < -40:          # 口播段不可能是静音：宁可报错也不静默出一支哑片
        raise SystemExit("%s 抽出的人声几乎是静音（峰值 %.1f dB）——查片段音轨或抽音参数"
                         % (seg["id"], peak_db(wav)))
    return clip, wav


def peak_db(path):
    import array
    with wave.open(path, "rb") as r:
        a = array.array("h", r.readframes(r.getnframes()))
    pk = max((abs(x) for x in a), default=0)
    return 20 * math.log10(pk / 32768.0) if pk else -120.0


def face_rgb(img_bgr):
    """人脸中下部（避开头发、眼镜）的平均 RGB；检测不到返回 None。"""
    import cv2
    casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    fs = casc.detectMultiScale(gray, 1.1, 6, minSize=(80, 80))
    if not len(fs):
        return None
    x, y, w, h = max(fs, key=lambda f: f[2] * f[3])
    roi = img_bgr[y + int(h * .45):y + int(h * .85), x + int(w * .2):x + int(w * .8)]
    return roi.reshape(-1, 3).mean(0)[::-1]


def face_target_of(profile):
    import cv2
    import numpy as np
    im = cv2.imdecode(np.fromfile(os.path.join(profile["_dir"], profile["portrait"]), np.uint8), cv2.IMREAD_COLOR)
    t = face_rgb(im)
    if t is None:
        raise SystemExit("定妆照里检测不到人脸，grade.auto 用不了")
    return t


def auto_grade(clip, t0, L, target, strength):
    """在片段里抽 3 帧量脸部肤色，按通道算 gamma 把它拉向定妆照肤色。
    strength<1 留余量（全量对齐时背景会一起发白）；gamma 限在 1.0～1.7，只提亮不压暗。"""
    import cv2
    import math as m
    vals = []
    for k in (0.25, 0.5, 0.75):
        tmp = os.path.join(os.path.dirname(clip), "_grade_probe.png")
        run(["-ss", "%.3f" % (t0 + L * k), "-i", clip, "-frames:v", "1", tmp])
        import numpy as np
        im = cv2.imdecode(np.fromfile(tmp, np.uint8), cv2.IMREAD_COLOR)   # cv2.imread 读不了中文路径
        os.remove(tmp)
        f = face_rgb(im) if im is not None else None
        if f is not None:
            vals.append(f)
    if not vals:
        print("  ？ %s 片段里没检测到人脸，本段不调色" % os.path.basename(clip))
        return {"gamma_r": 1.0, "gamma_g": 1.0, "gamma_b": 1.0, "face": None}
    cur = [sum(v[i] for v in vals) / len(vals) for i in range(3)]
    out = {"face": [round(c) for c in cur], "target": [round(c) for c in target]}
    for i, ch in enumerate("rgb"):
        c, t = min(max(cur[i] / 255.0, 0.05), 0.98), min(max(target[i] / 255.0, 0.05), 0.98)
        gam = m.log(c) / m.log(t)                 # (c)^(1/gam) = t
        out["gamma_" + ch] = round(min(1.7, max(1.0, 1 + strength * (gam - 1))), 3)
    return out


def _open_crop(src, crop, mode="RGB"):
    """crop=[x0,y0,x1,y1] 按原图宽高的比例给（0~1）；None 取整张。"""
    from PIL import Image
    im = Image.open(src).convert(mode)
    if crop:
        x0, y0, x1, y1 = crop
        im = im.crop((int(x0 * im.width), int(y0 * im.height), int(x1 * im.width), int(y1 * im.height)))
    return im


def _rounded_paste(canvas, img, xy, r=24):
    from PIL import Image, ImageDraw, ImageFilter
    x, y = xy
    W, H = canvas.size
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle((x, y + 10, x + img.width, y + img.height + 10), r, fill=90)
    canvas.paste(Image.new("RGB", (W, H), (90, 60, 30)), (0, 0), sh.filter(ImageFilter.GaussianBlur(18)))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, img.width - 1, img.height - 1), r, fill=255)
    canvas.paste(img, (x, y), m)


def cutout_frame(src, dst, crop=None):
    """课件透明底插图 → 米色底 1080×1920，宽 88%、偏上（下方留给字幕）。"""
    from PIL import Image
    im = _open_crop(src, crop, "RGBA")
    W, H = 1080, 1920
    s = min(W * 0.88 / im.width, H * 0.52 / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    cv = Image.new("RGBA", (W, H), CREAM + (255,))
    cv.alpha_composite(im, ((W - im.width) // 2, int(H * 0.40 - im.height / 2)))
    cv.convert("RGB").save(dst)
    return dst


def split_panel(src, crop, dst):
    """分屏底板：下半屏（960 起）米色，课件页（或页面局部）圆角放在 990~1580 之间；上半屏由讲解员盖住。"""
    from PIL import Image, ImageDraw
    im = _open_crop(src, crop)
    W, H = 1080, 1920
    s = min((W - 60) / im.width, 590 / im.height)
    im = im.resize((int(im.width * s), int(im.height * s)), Image.LANCZOS)
    cv = Image.new("RGB", (W, H), CREAM)
    ImageDraw.Draw(cv).rectangle((0, SPLIT_H - 4, W, SPLIT_H + 4), fill=(217, 138, 95))
    _rounded_paste(cv, im, ((W - im.width) // 2, 990 + (590 - im.height) // 2))
    cv.save(dst)
    return dst


def pan_strip(src, crop, h, dst):
    """横摇底图：裁出的一条放大到 h 高、米色底 1920 高、竖向居中偏上；返回 (路径, 条宽)。"""
    from PIL import Image
    im = _open_crop(src, crop)
    bw = max(1080, int(im.width * h / im.height))
    im = im.resize((bw, h), Image.LANCZOS)
    cv = Image.new("RGB", (bw, 1920), CREAM)
    cv.paste(im, (0, 560))
    cv.save(dst)
    return dst, bw


def contain_frame(src, dst, crop=None):
    """横版图 → 1080×1920 竖版底图：同图放大高斯模糊铺底，原图等宽居中（圆角＋投影），不裁一个字。"""
    from PIL import Image, ImageDraw, ImageFilter
    im = _open_crop(src, crop)
    W, H = 1080, 1920
    s = max(W / im.width, H / im.height)
    bg = im.resize((int(im.width * s) + 1, int(im.height * s) + 1), Image.LANCZOS)
    bg = bg.crop(((bg.width - W) // 2, (bg.height - H) // 2, (bg.width - W) // 2 + W, (bg.height - H) // 2 + H))
    bg = bg.filter(ImageFilter.GaussianBlur(36))
    bg = Image.blend(bg, Image.new("RGB", (W, H), (251, 245, 234)), 0.35)
    fw = W - 2 * 48
    fg = im.resize((fw, int(im.height * fw / im.width)), Image.LANCZOS)
    x, y = 48, int(H * 0.40 - fg.height / 2)            # 略偏上：下方留给字幕条
    sh = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sh).rounded_rectangle((x, y + 14, x + fg.width, y + fg.height + 14), 28, fill=110)
    bg.paste(Image.new("RGB", (W, H), (60, 40, 20)), (0, 0), sh.filter(ImageFilter.GaussianBlur(22)))
    mask = Image.new("L", fg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, fg.width - 1, fg.height - 1), 28, fill=255)
    bg.paste(fg, (x, y), mask)
    bg.save(dst)
    return dst


def exact_wav(src, dst, samples):
    """把 PCM 截/补到恰好 samples 个样本（逐样本对齐视频帧）。"""
    with wave.open(src, "rb") as r:
        ch, sw = r.getnchannels(), r.getsampwidth()
        data = r.readframes(samples)
    need = samples * ch * sw
    data = data[:need] + b"\x00" * max(0, need - len(data))
    with wave.open(dst, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(sw)
        w.setframerate(AR)
        w.writeframes(data)
    os.remove(src)


def render_end(L_, sc, bdir):
    n = int(round(float((sc["meta"].get("end") or {}).get("hold", END_HOLD)) * FPS))
    png = L_.shot("end", end_spec(sc))
    clip = os.path.join(bdir, "clips", "99_end.mp4")
    run(["-loop", "1", "-framerate", str(FPS), "-i", png, "-frames:v", str(n), "-vf", "format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", clip])
    wav = os.path.join(bdir, "clips", "99_end.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(AR)
        w.writeframes(b"\x00\x00\x00\x00" * (n * SPF))
    return clip, wav, n / float(FPS)


OPEN_HOLD = 1.5                  # 片头首页停留（秒）


def opening_png(L_, sc, out):
    """片头首页图（meta.opening），另存 <课次>-首页.png 供单独使用；没配 opening 返回 None。"""
    o = dict(sc["meta"].get("opening") or {})
    if not o:
        return None
    img = S.resolve(o["illus"])
    if S.md5_of(img) != o.get("md5"):
        raise SystemExit("片头插图 md5 对不上：%s（先跑 check_script.py --pin）" % o["illus"])
    o["illus"] = furl(img)
    png = L_.shot("opening", {"layer": "opening", "opening": o})
    dst = os.path.join(out, "%s-首页.png" % sc["meta"]["unit"])
    shutil.copyfile(png, dst)
    return png


def render_opening(png, bdir):
    """首页图 1.5 秒：1.00→1.04 缓推，无声；帧数×1600 样本截齐（同片尾卡）。"""
    n = int(round(OPEN_HOLD * FPS))
    clip = os.path.join(bdir, "clips", "00_opening.mp4")
    run(["-loop", "1", "-framerate", str(FPS), "-i", png, "-vf",
         "scale=2160:3840,zoompan=z='1+0.04*on/%d':x='(iw-iw/zoom)/2':y='(ih-ih/zoom)/2':d=%d:s=1080x1920:fps=%d,"
         "format=yuv420p" % (n, n, FPS),
         "-frames:v", str(n), "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", clip])
    wav = os.path.join(bdir, "clips", "00_opening.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(AR)
        w.writeframes(b"\x00\x00\x00\x00" * (n * SPF))
    return clip, wav, n / float(FPS)


def attach_cover(mp4, img):
    """把 img 作为 attached_pic 封面嵌进 mp4（流复制，不重编码）。
    不嵌时 Windows 缩略图取片长约 10% 处那一帧（2026-09-28 四上五落在写字照片上）。"""
    if not os.path.exists(img):
        return
    jpg = mp4[:-4] + "._cover.jpg"
    run(["-i", img, "-vf", "scale=720:-2", "-q:v", "3", jpg])
    tmp = mp4[:-4] + "._tmp.mp4"
    run(["-i", mp4, "-i", jpg, "-map", "0", "-map", "1", "-c", "copy",
         "-disposition:v:1", "attached_pic", "-movflags", "+faststart", tmp])
    os.replace(tmp, mp4)
    os.remove(jpg)
    print("  封面已嵌入：%s" % os.path.basename(img))


BGM_LEVEL = -24.0   # BGM 在片头片尾、停顿处的响度（dBFS RMS）；人声 ≈ -12，说话时再由侧链压低约 8~10 dB


def bgm_gain(path, target):
    """量曲子前 60 秒的 RMS（dBFS），返回把它拉到 target 的增益 dB。
    曲库曲子响度差很大（实测 Pixabay 两首约 -23 dBFS），固定增益会让音乐时有时无。"""
    import numpy as np
    r = subprocess.run([ff(), "-v", "error", "-t", "60", "-i", path, "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                       capture_output=True)
    a = np.frombuffer(r.stdout, np.int16).astype(float) / 32768
    if not len(a):
        raise SystemExit("读不了背景音乐：%s" % path)
    rms = 20 * math.log10(math.sqrt(float((a ** 2).mean())) + 1e-9)
    g = max(-30.0, min(12.0, target - rms))
    print("  BGM 原响度 %.1f dBFS → 目标 %.1f，增益 %+.1f dB" % (rms, target, g))
    return g


def concat_wavs(wavs, dst):
    with wave.open(dst, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(AR)
        for p in wavs:
            with wave.open(p, "rb") as r:
                w.writeframes(r.readframes(r.getnframes()))


def cover(L_, sc, p, out):
    t = p["t0"] + min(p["info"]["speech_start"] - p["t0"] + 0.8, p["L"] / 2)
    frame = os.path.join(out, "_build", "cover_frame.png")
    run(["-ss", "%.3f" % t, "-i", p["clip"], "-frames:v", "1", "-vf",
         "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920", frame])
    meta = sc["meta"]
    ov = L_.shot("cover", {"layer": "cover", "title": meta.get("title", ""),
                           "subtitle": (meta.get("end") or {}).get("subtitle", "")})
    run(["-i", frame, "-i", ov, "-filter_complex", "[0:v][1:v]overlay=0:0", "-frames:v", "1", "-q:v", "2",
         os.path.join(out, "%s-封面.jpg" % meta["unit"])])


def main():
    ap = argparse.ArgumentParser(description="宣传片成片（讲解员口播版）")
    ap.add_argument("line")
    ap.add_argument("unit")
    ap.add_argument("--sample", type=int, default=0, help="只渲前 N 段（闸门 B 样片，不带片尾）")
    ap.add_argument("--only", help="只渲这些段（逗号分隔，按脚本顺序；样片，不带片尾）")
    ap.add_argument("--opening-only", action="store_true", help="只出片头首页图（-首页.png），不渲视频")
    ap.add_argument("--bgm", help="背景音乐文件（须有商用授权）")
    ap.add_argument("--bgm-level", type=float, default=BGM_LEVEL, help="BGM 无人声处的目标响度（dBFS RMS）；脚本先量曲子再算增益")
    a = ap.parse_args()

    sc, _ = S.load_script(a.line, a.unit)
    out = S.out_dir(a.line, a.unit)
    segs = sc["segments"][:a.sample] if a.sample else sc["segments"]
    if a.only:
        want = set(a.only.split(","))
        segs = [s for s in segs if s["id"] in want]
    sample = bool(a.sample or a.only)
    if a.opening_only:
        L_ = Layers(sc, out)
        try:
            png = opening_png(L_, sc, out)
        finally:
            L_.close()
        print("✓ %s" % (os.path.relpath(os.path.join(out, "%s-首页.png" % sc["meta"]["unit"]), S.ROOT)
                          if png else "脚本 meta 没配 opening"))
        return
    bdir = os.path.join(out, "_build")
    if os.path.isdir(os.path.join(bdir, "clips")):
        shutil.rmtree(os.path.join(bdir, "clips"))
    os.makedirs(os.path.join(bdir, "clips"))

    plans = plan(sc, out, segs)
    L_ = Layers(sc, out)
    vids, wavs, total = [], [], 0.0
    try:
        png = None if sample else opening_png(L_, sc, out)
        if png:
            c, w, d = render_opening(png, bdir)
            vids.append(c)
            wavs.append(w)
            total += d
        for i, p in enumerate(plans):
            c, w = render_seg(L_, p, i + 1, bdir)
            vids.append(c)
            wavs.append(w)
            total += p["L"]
            gr = p.get("grade") or {}
            if p.get("fixes"):
                print("    防闪：%s" % "；".join(p["fixes"]))
            print("  ✓ %s %.2fs（穿插 %d）%s" % (p["seg"]["id"], p["L"], len(p["brolls"]),
                  ("  调色 脸%s→%s gamma %.2f/%.2f/%.2f" % (gr["face"], gr["target"], gr["gamma_r"],
                   gr["gamma_g"], gr["gamma_b"])) if gr.get("face") else ""), flush=True)
        if not sample:
            c, w, d = render_end(L_, sc, bdir)
            vids.append(c)
            wavs.append(w)
            total += d
            cover(L_, sc, next((p for p in plans if p["seg"]["id"] == sc["meta"].get("cover_seg")), plans[0]), out)
    finally:
        L_.close()

    with open(os.path.join(bdir, "_clips.txt"), "w", encoding="utf-8") as f:
        for c in vids:
            f.write("file '%s'\n" % c.replace("\\", "/"))
    run(["-f", "concat", "-safe", "0", "-i", "_clips.txt", "-c", "copy", "_video.mp4"], cwd=bdir)
    concat_wavs(wavs, os.path.join(bdir, "_voice.wav"))

    name = "%s-宣传片%s.mp4" % (a.unit, "-样片" if sample else "")
    args = ["-i", "_video.mp4", "-i", "_voice.wav"]
    if a.bgm:
        args += ["-stream_loop", "-1", "-i", os.path.abspath(a.bgm)]
        fo = max(total - 1.8, 0)
        args += ["-filter_complex",
                 "[1:a]asplit=2[v1][v2];"
                 "[2:a]aresample=48000,silenceremove=start_periods=1:start_threshold=-50dB,asetpts=PTS-STARTPTS,"
                 "atrim=0:%.3f,volume=%.1fdB,"
                 "afade=t=in:d=0.8,afade=t=out:st=%.3f:d=1.8[b];"
                 "[b][v1]sidechaincompress=threshold=0.05:ratio=4:attack=20:release=400[bd];"
                 "[bd][v2]amix=inputs=2:normalize=0:duration=first[a]"
                 % (total, bgm_gain(a.bgm, a.bgm_level), fo),
                 "-map", "0:v", "-map", "[a]"]
    else:
        args += ["-map", "0:v", "-map", "1:a"]
    args += ["-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", str(AR),
             "-movflags", "+faststart", "-t", "%.3f" % total, name]
    run(args, cwd=bdir)
    dst = os.path.join(out, name)
    shutil.move(os.path.join(bdir, name), dst)
    if not sample:                              # 内嵌封面：资源管理器与多数播放器首先显示它，不再随机取一帧
        art = os.path.join(out, "%s-首页.png" % a.unit)
        attach_cover(dst, art if os.path.exists(art) else os.path.join(out, "%s-封面.jpg" % a.unit))

    probe = S.ffmpeg_path().ffprobe()
    r = subprocess.run([probe, "-v", "error", "-show_entries",
                        "stream=codec_type,width,height,r_frame_rate:format=duration",
                        "-of", "json", dst], capture_output=True, text=True)
    info = json.loads(r.stdout or "{}")
    dur = float(info.get("format", {}).get("duration", 0))
    print("\n✓ %s" % os.path.relpath(dst, S.ROOT))
    print("  %.2f 秒（时间轴 %.2f，偏差 %.3f）· %.1f MB" % (dur, total, abs(dur - total), os.path.getsize(dst) / 1e6))
    S.save_json({"total_sec": round(total, 3),
                 "segments": [{"id": p["seg"]["id"], "t0": p["t0"], "sec": p["L"], "cues": p["cues"], "grade": p.get("grade"),
                               "brolls": [{k: b[k] for k in ("src", "start", "end")} for b in p["brolls"]]}
                              for p in plans]},
                os.path.join(bdir, "_时间轴.json"))


if __name__ == "__main__":
    main()
