# -*- coding: utf-8 -*-
r"""讲解员档案：一次建、所有宣传片复用（借自 B 站 BV17q416fEBH 的「角色与场景档案」思路）。

    PYTHONUTF8=1 python build_presenter.py init    <名> --portrait <人像> --scene <场景> [--pronoun she|he]
    PYTHONUTF8=1 python build_presenter.py voice   <名> [--takes 2]
    PYTHONUTF8=1 python build_presenter.py confirm <名> --voice-from <试音 mp4> --by <人>

落盘 `品牌资产\宣传片讲解员\<名>\`：角色.jpg、场景.jpg、音色参考.wav、档案.json、_试音\。
这些是 AI 生成物、重渲不出，**入库**（同写作课海报插画口径，CLAUDE.md §8）；_试音\ 不入库。

三步各自的理由：
  init     多模态读人像/场景 → 英文外观描述、场景描述、场景里能做的动作（提示词的素材）。
           人看过、能改：档案.json 是纯文本，描述不准直接改。
  voice    不带音色参考、只凭人像生成 1～N 条试音口播——**声音就是 H3 自己给的**
           （用户 2026-09-27 定「模型自带声音」）。听哪条顺耳就用哪条。
  confirm  选中的试音抽音轨 → 音色参考.wav；此后每段口播都带它，锁住同一副嗓子
           （H3 没有 voice_id，这是官方给的唯一一致性手段）。写 confirmed_by——
           load_presenter 之后的生成环节只认定过妆的档案。
"""
import argparse
import datetime
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _shared as S  # noqa: E402
import videoclient  # noqa: E402

DEFAULT_ACTIONS = {
    "nod": "gives a small, understanding nod",
    "lean_in": "leans slightly toward the camera as if sharing something important",
    "open_palm": "raises one hand at chest height with an open palm in a gentle explaining gesture",
    "count": "counts off on the fingers of one hand at chest height",
    "smile": "breaks into a warm, reassuring smile",
    "tilt_head": "tilts the head slightly with a thoughtful, questioning look",
}
TRY_LINE = ["家长您好，孩子写作文总觉得没东西可写？", "其实，是还没学会把一件事写清楚。"]
ANALYZE = """You are preparing a reusable character-and-scene profile for an AI talking-head video model.
Image 1 is the presenter portrait, image 2 is the environment the presenter will sit in.
Return strict JSON with English values:
{"appearance_en": "one sentence: apparent age, gender, hairstyle, glasses if any, clothing and colors, temperament",
 "scene_en": "one sentence: key furniture, props, palette and lighting of image 2",
 "voice_en": "a suitable voice for this person, e.g. 'a calm, clear mid-pitched female Mandarin voice'",
 "delivery_en": "3-5 words for speaking manner fitting the temperament",
 "scene_actions": {"snake_case_key": "a short action the seated presenter can do with an object that is really
   in image 2, starting with a verb, e.g. 'picks up an open lined notebook from the table and tilts it toward the camera'"}}
Give 2-3 scene_actions. Describe only what is visible; do not invent objects. No readable text may be shown."""


def pdir(name):
    return os.path.join(S.PRESENTER_BASE, name)


def load(name):
    p = os.path.join(pdir(name), "档案.json")
    if not os.path.exists(p):
        raise SystemExit("还没建档：%s（先跑 init）" % p)
    import json
    with open(p, encoding="utf-8") as f:
        prof = json.load(f)
    prof["_dir"] = pdir(name)
    return prof


def save(prof):
    d = prof.pop("_dir")
    S.save_json(prof, os.path.join(d, "档案.json"))
    prof["_dir"] = d


def cmd_init(a):
    d = pdir(a.name)
    os.makedirs(d, exist_ok=True)
    for src, dst in ((a.portrait, "角色.jpg"), (a.scene, "场景.jpg")):
        shutil.copyfile(src, os.path.join(d, dst))
    img = videoclient._imgclient().make_client("gpt-image")
    r = img.judge([os.path.join(d, "角色.jpg"), os.path.join(d, "场景.jpg")], ANALYZE)
    if "_error" in r or "_raw" in r:
        raise SystemExit("多模态分析失败（未知，不是否定）：%s" % (r.get("_error") or r.get("_raw", "")[:300]))
    actions = dict(DEFAULT_ACTIONS)
    actions.update(r.get("scene_actions") or {})
    prof = {"name": a.name, "pronoun": a.pronoun, "portrait": "角色.jpg", "scene": "场景.jpg",
            "voice": None, "appearance_en": r["appearance_en"], "scene_en": r["scene_en"],
            "voice_en": r.get("voice_en", ""), "delivery_en": r.get("delivery_en", "warm and sincere"),
            "actions": actions,
            "md5": {"portrait": S.md5_of(os.path.join(d, "角色.jpg")),
                    "scene": S.md5_of(os.path.join(d, "场景.jpg"))},
            "confirmed_by": None, "_dir": d}
    save(prof)
    print("✓ 档案已建：%s" % os.path.join(d, "档案.json"))
    for k in ("appearance_en", "scene_en", "voice_en", "delivery_en"):
        print("  %s: %s" % (k, prof[k]))
    print("  actions: %s" % ", ".join(actions))
    print("下一步：看一遍描述，不准就直接改 档案.json；然后跑 voice 出试音。")


def cmd_voice(a):
    import h3_prompt
    prof = load(a.name)
    prof["voice"] = None                      # 试音不带音色参考：要听的就是模型自己的声音
    seg = {"id": "try", "lines": TRY_LINE, "camera": "medium close-up", "action": ["smile"]}
    dur = h3_prompt.seconds_for(seg["lines"])
    text = h3_prompt.build(prof, seg, dur)
    tdir = os.path.join(prof["_dir"], "_试音")
    os.makedirs(tdir, exist_ok=True)
    v = videoclient.make_video()
    for i in range(a.takes):
        tid, data = v.generate(text, h3_prompt.refs_of(prof), seconds=dur)
        fn = os.path.join(tdir, "试音_%s.mp4" % tid[-6:])
        with open(fn, "wb") as f:
            f.write(data)
        print("  ✓ %s" % fn)
    print("去听，选一条顺耳的：confirm %s --voice-from <那条 mp4> --by <你>" % a.name)


def cmd_confirm(a):
    prof = load(a.name)
    ff = S.ffmpeg_path().ffmpeg()
    dst = os.path.join(prof["_dir"], "音色参考.wav")
    # H3 参考音频限 2~15 秒、WAV/MP3；抽单声道 24kHz，去首尾静音
    r = subprocess.run([ff, "-hide_banner", "-loglevel", "error", "-y", "-i", a.voice_from, "-vn",
                        "-ac", "1", "-ar", "24000", "-af",
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                        "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                        "-t", "14", dst], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("抽音轨失败：%s" % r.stderr[-500:])
    prof["voice"] = "音色参考.wav"
    prof.setdefault("md5", {})["voice"] = S.md5_of(dst)
    prof["voice_source"] = os.path.basename(a.voice_from)
    prof["confirmed_by"] = a.by
    prof["confirmed_at"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    save(prof)
    print("✓ 定妆完成：%s（音色参考取自 %s）" % (a.name, prof["voice_source"]))


def main():
    ap = argparse.ArgumentParser(description="宣传片讲解员档案")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("name")
    p.add_argument("--portrait", required=True)
    p.add_argument("--scene", required=True)
    p.add_argument("--pronoun", default="she", choices=("she", "he"))
    p = sub.add_parser("voice")
    p.add_argument("name")
    p.add_argument("--takes", type=int, default=2)
    p = sub.add_parser("confirm")
    p.add_argument("name")
    p.add_argument("--voice-from", required=True)
    p.add_argument("--by", required=True)
    a = ap.parse_args()
    if a.cmd == "init" and not re.match(r"^[\w一-鿿-]+$", a.name):
        raise SystemExit("名字只用中文/字母/数字")
    {"init": cmd_init, "voice": cmd_voice, "confirm": cmd_confirm}[a.cmd](a)


if __name__ == "__main__":
    main()
