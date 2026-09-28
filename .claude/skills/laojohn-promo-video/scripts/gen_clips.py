# -*- coding: utf-8 -*-
r"""宣传片链：按 storyboard 逐段生成讲解员口播片段（**花钱的一步**）+ ASR 核对。

    PYTHONUTF8=1 python gen_clips.py <线> <课次> [--sample N | --only s1,s3] [--retries 1]

前置（缺一就拒绝，不花一分钱）：
    闸门 A  脚本 meta.audit 与当前脚本一致（check_script.py --by）
    定妆    讲解员档案 confirmed_by 非空、带音色参考（build_presenter.py confirm）
    闸门 P  storyboard.json 的 approved.hashes 覆盖本次要生成的每一段（h3_prompt.py --by）

缓存：片段文件名带提示词哈希（`_clips\s3_<hash>.mp4`），提示词/参考素材不变就不重生；
改了哪段的台词或动作，只有那一段哈希变、只重生那一段。

ASR 核对（真实性红线不豁免——模型可能念错、漏字、加字）：
    抽音轨 → whisper 转写 → 与脚本台词去标点逐字比相似度
    ≥ PASS_SIM  通过；<  判「念错」，自动重生（--retries 次，默认 1）；仍不过就停下报人
    转写接口失败 → 记「未知」，片段保留、不重生、不当「不通过」，成片前须人耳听过
另用 silencedetect 量出开口/收口时间（渲染时掐掉首尾空白、按字数比例分配字幕时间）。
"""
import argparse
import difflib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _shared as S  # noqa: E402
import h3_prompt  # noqa: E402
import videoclient  # noqa: E402

PASS_SIM = 0.85
ASR_HINT = "以下是普通话口播，使用简体中文。"
# whisper 常吐繁体：只收本线台词里会出现的常用字，够比对用即可（不是通用繁简转换）
T2S = str.maketrans("寫這樣總後結經過帶讀麼說話間關鍵詳細們課當堂習給聽樣認識見聲東嗎還會學種開覺時裡為從發現趣動應體驗掃碼預約試嚴長對論題點讓兩篇記誰幾選決細節節",
                    "写这样总后结经过带读么说话间关键详细们课当堂习给听样认识见声东吗还会学种开觉时里为从发现趣动应体验扫码预约试严长对论题点让两篇记谁几选决细节节")


def norm(t):
    return re.sub(r"[，。？！、：；“”‘’,.?!:;\s·]", "", t.translate(T2S))


def ff():
    return S.ffmpeg_path().ffmpeg()


def speech_bounds(mp4):
    """silencedetect 量开口/收口（秒）。量不到就返回整段。"""
    r = subprocess.run([ff(), "-hide_banner", "-i", mp4, "-af", "silencedetect=n=-38dB:d=0.25",
                        "-f", "null", "-"], capture_output=True, text=True)
    dur = float(re.search(r"Duration: (\d+):(\d+):([\d.]+)", r.stderr).groups()[2]) + \
        60 * float(re.search(r"Duration: (\d+):(\d+):", r.stderr).group(2))
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    lo = ends[0] if starts and starts[0] < 0.05 and ends else 0.0
    hi = starts[-1] if starts and (len(starts) > len(ends) or ends[-1] >= dur - 0.05) else dur
    return round(lo, 3), round(hi, 3), round(dur, 3)


def asr_check(mp4, lines):
    wav = mp4[:-4] + "_16k.wav"
    subprocess.run([ff(), "-hide_banner", "-loglevel", "error", "-y", "-i", mp4, "-vn", "-ac", "1",
                    "-ar", "16000", wav], check=True)
    r = videoclient.transcribe(wav, prompt=ASR_HINT)
    os.remove(wav)
    if "_error" in r:
        return {"verdict": "unknown", "asr_error": r["_error"]}
    sim = difflib.SequenceMatcher(None, norm("".join(lines)), norm(r["text"])).ratio()
    return {"verdict": "pass" if sim >= PASS_SIM else "misread", "sim": round(sim, 3),
            "asr_text": r["text"], "asr_segments": r["segments"]}


def main():
    ap = argparse.ArgumentParser(description="讲解员口播片段生成")
    ap.add_argument("line")
    ap.add_argument("unit")
    ap.add_argument("--sample", type=int, default=0, help="只生成前 N 段（闸门 B 样片）")
    ap.add_argument("--only", help="只生成这些段，逗号分隔")
    ap.add_argument("--retries", type=int, default=1, help="念错时自动重生次数")
    a = ap.parse_args()

    sc, _ = S.load_script(a.line, a.unit)
    audit = (sc.get("meta") or {}).get("audit") or {}
    if audit.get("script_md5") != S.script_digest(sc):
        raise SystemExit("闸门 A 未过：脚本没人审过或审后改过——先 check_script.py --by <人>")
    prof = S.load_presenter(sc["meta"]["presenter"])
    if not prof.get("confirmed_by") or not prof.get("voice"):
        raise SystemExit("讲解员「%s」还没定妆（缺音色参考）——先 build_presenter.py confirm" % prof["name"])
    out = S.out_dir(a.line, a.unit)
    sb_path = os.path.join(out, "storyboard.json")
    sb = h3_prompt.storyboard(sc, prof, out) if not os.path.exists(sb_path) else json.load(
        open(sb_path, encoding="utf-8"))
    fresh = h3_prompt.storyboard(sc, prof, out)        # 以现行脚本重算，防 storyboard 过期
    ok_hash = set((sb.get("approved") or {}).get("hashes") or [])
    rows = fresh["segments"]
    if a.sample:
        rows = rows[:a.sample]
    if a.only:
        want = set(a.only.split(","))
        rows = [r for r in rows if r["id"] in want]
    unapproved = [r["id"] for r in rows if r["hash"] not in ok_hash]
    if unapproved:
        fresh["approved"] = sb.get("approved")
        S.save_json(fresh, sb_path)
        raise SystemExit("闸门 P 未过：%s 的提示词没人确认过（或改过）——看 storyboard.json 后跑 "
                         "h3_prompt.py %s %s --by <人>" % ("、".join(unapproved), a.line, a.unit))
    fresh["approved"] = sb.get("approved")

    v = videoclient.make_video()
    os.makedirs(os.path.join(out, "_clips"), exist_ok=True)
    spent = 0
    for r in rows:
        refs = h3_prompt.refs_of(prof)
        mp4 = os.path.join(out, r["clip"])
        meta_fn = mp4[:-4] + ".json"
        if os.path.exists(mp4) and os.path.exists(meta_fn):
            info = json.load(open(meta_fn, encoding="utf-8"))
            print("  = %s 已有（%s）" % (r["id"], info.get("verdict")))
            r.update(status=info.get("verdict"))
            continue
        with open(os.path.join(out, r["prompt"]), encoding="utf-8") as f:
            prompt = f.read()
        for attempt in range(a.retries + 1):
            print("  → %s  %ds  第 %d 次" % (r["id"], r["seconds"], attempt + 1), flush=True)
            tid, data = v.generate(prompt, refs, seconds=r["seconds"],
                                   log=lambda m: print(m, flush=True))
            spent += r["seconds"]
            with open(mp4, "wb") as f:
                f.write(data)
            info = dict(task=tid, attempt=attempt + 1, **asr_check(mp4, r["lines"]))
            info["speech_start"], info["speech_end"], info["duration"] = speech_bounds(mp4)
            print("    %s  相似度 %s  开口 %.2f～%.2f / %.2f 秒  %s" % (
                info["verdict"], info.get("sim", "—"), info["speech_start"], info["speech_end"],
                info["duration"], info.get("asr_text", info.get("asr_error", ""))), flush=True)
            if info["verdict"] != "misread":
                break
            if attempt < a.retries:
                os.replace(mp4, mp4[:-4] + ".misread%d.mp4" % (attempt + 1))
        S.save_json(info, meta_fn)
        r.update(status=info["verdict"])
    S.save_json(fresh, sb_path)
    bad = [r["id"] for r in rows if r.get("status") == "misread"]
    unk = [r["id"] for r in rows if r.get("status") == "unknown"]
    print("\n本次生成约 %d 秒（≈ $%.1f）。" % (spent, spent * 0.08))
    if bad:
        print("  ✗ 仍念错：%s——改台词（换掉难念的词）或 --only 再生" % "、".join(bad))
    if unk:
        print("  ？ 转写失败未核：%s——成片前人耳听一遍" % "、".join(unk))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
