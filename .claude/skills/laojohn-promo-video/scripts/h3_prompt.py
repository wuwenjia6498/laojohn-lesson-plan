# -*- coding: utf-8 -*-
r"""讲解员口播段 → MiniMax H3 参考生成（Ref2VA）六段式提示词。**确定性拼装，不调模型。**

    PYTHONUTF8=1 python h3_prompt.py <线> <课次>             # 写 _prompts\sNN.txt + storyboard.json（闸门 P 给人看）
    PYTHONUTF8=1 python h3_prompt.py <线> <课次> --by <人>   # 人看过后记账；gen_clips 只生成记过账的哈希

格式唯一源＝MiniMax 官方 h3-prompt-writing（用户级 skill）的 references/ref-en.txt：
六段按序 subject_definitions / summary / retention_analysis / detailed_description /
overall_soundscape / non_diegetic_music；描写用英文，台词保留中文放 `<d>[Chinese] …</d>`；
说话人写 `<Subject 1> (S1)`；段内切镜写 `[Shot N] At MM:SS.mmm, …`。

参考素材标签按 refs 顺序固定（refs_of 与提示词标签一一对应，改一边必改另一边）：
    <Picture 1> 讲解员人像   <Picture 2> 场景   <Audio 1> 音色参考

版本沿革（2026-09-27 同日四轮，用户逐版对比后定）：
  · 第三版的表演写法用户判「最自然」——段内 1～2 镜（shots）、每镜给区域 station、景别 framing、
    机位运动 move、动作节拍 beats（「说到某词时做某动作」），本版沿用。
  · 投屏墙（第三版）用户否：「不符合真实场景」；海报与课件首页改由 render_promo 以穿插剪进来。
  · 悬浮信息卡（第四版，纸片/全息）用户否：「什么信息都没有，很奇怪」——模型画不出真内容，不再用。
"""
import hashlib
import math
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _shared as S  # noqa: E402

CHARS_PER_SEC = 4.5          # H3 中文口播实测约 4～4.5 字/秒；第三版这套节奏用户认可，不改
PAD_SEC = 1.2                # 开口前 + 收尾的余量
LEAD_SEC = 0.6               # 开口前那一小段（算段内切镜时间点用）
FRAMINGS = {
    "close-up": ("a close-up framing the presenter from the upper chest up, natural 50mm portrait perspective "
                 "with the camera about one meter away, no wide-angle distortion"),
    "medium close-up": ("a medium close-up framing the presenter from mid-torso up, natural 50mm portrait "
                        "perspective with the camera about 1.5 meters away, face clearly readable"),
    "three-quarter": ("a medium close-up from a 45-degree side angle, the presenter's body turned partly away "
                      "from the camera and the face still clearly visible"),
}
MOVES = {
    "push": "slowly pushes in",
    "handheld": "floats with a gentle, natural handheld sway",
    "track": "tracks sideways slowly with the presenter",
    "pull": "slowly pulls back",
    "still": "holds steady",
}
RULES = ("Keep the presenter's face sharp, brightly lit and clearly visible in every shot; only close and "
         "medium-close framings. No subtitles, captions, logos, watermarks, screens or floating graphics; any "
         "paper or book in view shows no readable writing.")
LIGHT = ("Bright, soft, even frontal key light from a large diffused source just above the camera fully "
         "illuminates the face with the same bright, airy, high-key exposure and fair skin tone as <Picture 1>; "
         "no shadow across the face, no underexposure, no dim or moody look.")
ACTING = ("a lively, warm, genuinely engaged delivery with a natural conversational rhythm; the eyebrows, eyes "
          "and hands animate the words, with big natural smiles and small head movements, never stiff")


def plen(t):
    return len(re.sub(r"[，。？！、：；“”‘’,.?!:;\s]", "", t))


def seconds_for(lines):
    n = sum(plen(ln) for ln in lines)
    return max(4, min(15, int(math.ceil(n / CHARS_PER_SEC + PAD_SEC))))


def spoken(lines):
    """台词进 <d>：去掉弯引号（口播里不念引号），句末补中文句号。"""
    t = re.sub(r"[“”‘’\"']", "", "".join(lines))
    if t and t[-1] not in "。？！":
        t += "。"
    return t


def ts(t):
    m = int(t) // 60
    return "%02d:%06.3f" % (m, t - m * 60)


def act_text(profile, key):
    return profile.get("actions", {}).get(key, key)          # 键不在档案里就按英文原话用


def build(profile, seg, dur):
    stations = profile.get("stations") or {}
    he = profile.get("pronoun") == "he"
    sub, pos = ("he", "his") if he else ("she", "her")
    shots = seg.get("shots") or [{"station": None, "framing": "close-up", "move": "push", "from_line": 0}]
    lines = seg["lines"]

    subj = ["<Subject 1> is the presenter in <Picture 1>: %s" % profile["appearance_en"],
            "<Subject 2> is the room in <Picture 2>: %s" % profile["scene_en"],
            "<Audio 1> is the voice-timbre reference for <Subject 1> (S1)."]
    summary = ("[reference generation + audio reference] A %d-second vertical 9:16 clip in which <Subject 1> "
               "moves naturally within <Subject 2> and speaks directly to parents through the camera in %d "
               "shot%s, using <Audio 1> as the voice-timbre reference."
               % (dur, len(shots), "s" if len(shots) > 1 else ""))
    shot_ids = ", ".join("[Shot %d]" % (i + 1) for i in range(len(shots)))
    ret = ["<Subject 1> (appears in %s): fully_preserved - face, hairstyle, glasses, clothing, and the bright "
           "facial exposure and skin tone of <Picture 1> are retained." % shot_ids,
           "<Subject 2> (appears in %s): partially_preserved - the room's furniture, palette and lighting are "
           "retained; different areas of the same room are shown as the presenter moves." % shot_ids,
           "<Audio 1>: reference - the presenter follows <Audio 1>'s voice timbre without copying its words or "
           "signal."]
    voice = "in the voice timbre referenced from <Audio 1>"

    total = float(sum(plen(ln) for ln in lines)) or 1.0
    starts = [s.get("from_line", 0) for s in shots]
    body = ["The target video is a realistic, brightly lit vertical clip with natural skin texture and shallow "
            "depth of field. %s %s" % (RULES, LIGHT)]
    for i, s in enumerate(shots):
        a = starts[i]
        b = starts[i + 1] if i + 1 < len(shots) else len(lines)
        t0 = LEAD_SEC + (dur - PAD_SEC) * sum(plen(ln) for ln in lines[:a]) / total
        where = (stations.get(s.get("station") or "") or {}).get("en") or "seated in front of <Subject 2>"
        framing = FRAMINGS.get(s.get("framing", "close-up"), FRAMINGS["close-up"])
        move = MOVES.get(s.get("move", "push"), s.get("move") or MOVES["push"])
        if i == 0:
            txt = "[Shot 1] %s, eye-level. " % (framing[0].upper() + framing[1:])
        else:
            txt = "[Shot %d] At %s, the shot cuts to %s, eye-level. " % (i + 1, ts(t0), framing)
        txt += "<Subject 1> is %s. The camera %s. " % (where, move)
        seg_lines = lines[a:b]
        if seg_lines:
            look = ("glances aside and back to the lens" if s.get("framing") == "three-quarter"
                    else "looks straight into the lens")
            txt += ("<Subject 1> (S1) %s and says %s, with %s, <d>[Chinese] %s</d> "
                    % (look, voice, ACTING, spoken(seg_lines)))
        for bt in s.get("beats", []):
            cue = ("As %s says \u201c%s\u201d" % (sub, bt["word"])) if bt.get("word") else "While speaking"
            txt += "%s, <Subject 1> %s. " % (cue, act_text(profile, bt["do"]))
        if i == len(shots) - 1:
            txt += ("After the last line %s closes %s lips and holds a warm, bright smile toward the lens until "
                    "the clip ends at %s." % (sub, pos, ts(dur)))
        body.append(txt.strip())
    parts = [("subject_definitions", "\n".join(subj)), ("summary", summary),
             ("retention_analysis", "\n".join(ret)), ("detailed_description", "\n".join(body)),
             ("overall_soundscape", "Quiet indoor room tone with faint soft ambience and soft footsteps or "
                                    "fabric rustle when the presenter moves; no other voices."),
             ("non_diegetic_music", "N/A")]
    return "\n\n".join("%s:\n%s" % (k, v) for k, v in parts)


def refs_of(profile):
    """参考素材顺序＝提示词标签顺序：人像、场景、音色。"""
    d = profile["_dir"]
    r = [os.path.join(d, profile["portrait"]), os.path.join(d, profile["scene"])]
    if profile.get("voice"):
        r.append(os.path.join(d, profile["voice"]))
    return r


def storyboard(sc, profile, out):
    pdir = os.path.join(out, "_prompts")
    os.makedirs(pdir, exist_ok=True)
    rows = []
    for seg in sc["segments"]:
        dur = seg.get("seconds") or seconds_for(seg["lines"])
        text = build(profile, seg, dur)
        with open(os.path.join(pdir, seg["id"] + ".txt"), "w", encoding="utf-8") as f:
            f.write(text)
        refs = refs_of(profile)
        h = hashlib.md5((text + "|" + "|".join(S.md5_of(p) for p in refs)).encode()).hexdigest()[:12]
        rows.append({"id": seg["id"], "seconds": dur, "lines": seg["lines"],
                     "prompt": "_prompts/%s.txt" % seg["id"], "hash": h,
                     "clip": "_clips/%s_%s.mp4" % (seg["id"], h)})
    sb = {"presenter": profile["name"], "model": os.environ.get("PROMO_VIDEO_MODEL", "minimax-h3"),
          "segments": rows, "total_seconds": sum(r["seconds"] for r in rows)}
    S.save_json(sb, os.path.join(out, "storyboard.json"))
    return sb


def main():
    import argparse
    import datetime
    import json
    ap = argparse.ArgumentParser(description="H3 提示词 + storyboard")
    ap.add_argument("line")
    ap.add_argument("unit")
    ap.add_argument("--by", help="闸门 P：人看过提示词后记账")
    a = ap.parse_args()
    sc, _ = S.load_script(a.line, a.unit)
    profile = S.load_presenter(sc["meta"]["presenter"])
    out = S.out_dir(a.line, a.unit)
    sb_path = os.path.join(out, "storyboard.json")
    prev = (json.load(open(sb_path, encoding="utf-8")).get("approved") or {}) if os.path.exists(sb_path) else {}
    sb = storyboard(sc, profile, out)
    sb["approved"] = prev or None
    if a.by:
        sb["approved"] = {"by": a.by, "at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                          "hashes": [r["hash"] for r in sb["segments"]]}
    S.save_json(sb, sb_path)
    if a.by:
        print("闸门 P 已记账：%s（%d 段）" % (a.by, len(sb["segments"])))
    for r in sb["segments"]:
        print("  %s  %2ds  %s" % (r["id"], r["seconds"], "".join(r["lines"])))
    print("合计 %d 秒口播，%d 段（约 $%.1f）→ storyboard.json、_prompts\\"
          % (sb["total_seconds"], len(sb["segments"]), sb["total_seconds"] * 0.08))


if __name__ == "__main__":
    main()
