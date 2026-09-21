# -*- coding: utf-8 -*-
r"""备课视频链第 5 步：旁白稿 → 逐句音频 + 配音清单。**闸门 A 之后才准跑。**

    PYTHONUTF8=1 python synth_voice.py <课次> [--provider volc] [--voice X] [--speed 1.0]
                                        [--only s03] [--no-audit]

**逐句合成，不整页合成**——全方案最关键的一个设计决定，一次解决三件事：
  ① 字幕边界＝音频实测边界，**零漂移，根本不需要 TTS 返回字级时间戳**
     （选型时不必为这项能力付溢价；AiHubMix 那条通道就不返回）
  ② 某句念错只重合成那一句
  ③ 句间插实体静音片段，听感更像人讲课（而不是用 adelay 事后加，见 render_video 的说明）

**闸门**：校验旁白稿 `meta.audit` 存在、且 plan/shotlist/narration 三个 md5 与当前一致。
对不上拒绝执行——TTS 花钱，不能拿旧审核放行改过的稿子。逃生口只有 `--no-audit` 一个，
且会打印告警。
"""
import argparse
import hashlib
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root, md5  # noqa: E402
from audit_narration import narration_digest  # noqa: E402
import ffmpeg_path  # noqa: E402

SIL = {"sentence": 0.25, "page": 0.80}

# 按语块分级语速（V3 的 speech_rate，单位是百分比偏移，0 为常速）。
# 真实讲课就是这个起伏：交代位置、过渡带一带，
# 讲到「为什么这么设计」和「学生会卡在哪」自然会慢下来。
# 幅度刻意取小（±6）——大了就成了表演。
# 0922 用户要「整体偏快一点」：给所有角色加一个全局基准偏移，
# 角色之间的相对起伏（±6）不动——快的是整体节奏，不是把起伏抹平。
RATE_BASE = 10
ROLE_RATE = {k: v + RATE_BASE for k, v in
             {"locate": 6, "bridge": 6, "do": 0, "why": -6, "risk": -6,
              "end": 0}.items()}


def load_tts():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ttsclient.py")
    spec = importlib.util.spec_from_file_location("ttsclient", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def make_silence(path, seconds):
    if os.path.exists(path):
        return
    ffmpeg_path.run(["-f", "lavfi", "-i",
                     "anullsrc=r=%d:cl=mono" % 24000,
                     "-t", "%.3f" % seconds, "-c:a", "pcm_s16le", path])


def gate(doc, src, spath, allow):
    a = doc.get("meta", {}).get("audit")
    if not a:
        if allow:
            print("  ⚠ --no-audit：未经审稿就合成。"
                  "旁白是对外件，正式出片前必须补上 "
                  "audit_narration.py --by <人>")
            return
        raise SystemExit(
            "旁白稿没过闸门 A。先通读 "
            "<课次>-旁白稿.md，再跑：\n"
            "  python audit_narration.py \"%s\" --by <你的名字>\n"
            "（issues 非空也能放行，闸门守的是「审过」）"
            % doc["meta"]["course"])
    bad = []
    if a.get("plan_md5") != md5(src.plan_md):
        bad.append("详案改过了")
    if a.get("shotlist_md5") != md5(spath):
        bad.append("分镜单改过了")
    if a.get("narration_md5") != narration_digest(doc):
        bad.append("旁白稿审完又改过")
    if bad:
        if allow:
            print("  ⚠ --no-audit 绕过：%s" % "、".join(bad))
            return
        raise SystemExit("审核记账对不上：%s\n"
                         "  重跑 audit_narration.py --by <人> 重新记账"
                         % "、".join(bad))
    print("  闸门 A 通过：%s / %s（issues %d 条）"
          % (a.get("by"), a.get("at"), len(a.get("issues") or [])))


def main():
    ap = argparse.ArgumentParser(description="逐句 TTS 合成")
    ap.add_argument("unit")
    ap.add_argument("--provider")
    ap.add_argument("--voice")
    ap.add_argument("--speed", type=float, default=1.0)
    ap.add_argument("--only", help="只合成这几页")
    ap.add_argument("--no-audit", action="store_true", help="跳过闸门 A（唯一逃生口）")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    npath = os.path.join(src.out_dir, a.unit + "-旁白稿.json")
    spath = os.path.join(src.out_dir, a.unit + "-分镜单.json")
    with open(npath, encoding="utf-8") as f:
        doc = json.load(f)
    gate(doc, src, spath, a.no_audit)

    tm = load_tts()
    cli = tm.make_tts(a.provider)
    voice = a.voice or cli.voice
    adir = os.path.join(src.out_dir, "audio")
    os.makedirs(adir, exist_ok=True)
    make_silence(os.path.join(adir, "_sil_sentence.wav"), SIL["sentence"])
    make_silence(os.path.join(adir, "_sil_page.wav"), SIL["page"])

    # 开跑前把通道/音色打出来。2026-09-21 踩过：config 里的 TTS_PROVIDER 没生效、
    # 整批 188 句用错了通道，一路合成完才从报错前缀里看出来。这行是最便宜的哨兵。
    print("  通道 %s · 音色 %s · 语速 %s"
          % (cli.name, voice, a.speed), flush=True)

    # 会话 id：同一课次全片共用。逐句合成没它的话，
    # 每句都是独立起调，整片语气会碎成一段一段。
    if hasattr(cli, "section_id") and not cli.section_id:
        cli.section_id = "lv-" + hashlib.md5(a.unit.encode("utf-8")).hexdigest()[:12]
    instr = getattr(cli, "instruction", "") or ""
    if instr:
        print("  讲解指令：%s…" % instr[:34], flush=True)

    only = set(x.strip() for x in a.only.split(",")) if a.only else None
    manifest, failed = [], []
    total_sec, n_new, n_cached = 0.0, 0, 0
    for s in doc["shots"]:
        if only and s["id"] not in only:
            continue
        for ln in s.get("lines") or []:
            rate = ROLE_RATE.get(ln.get("role"), 0)
            if hasattr(cli, "rate"):
                cli.rate = rate
            # extra 把指令与语速偏移包进缓存键，
            # 否则改了指令重跑会全部命中旧缓存
            key = tm.key_of(cli.name, voice, a.speed, ln["text"],
                            "%s|%d" % (instr, rate))
            out = os.path.join(adir, "%s_%02d_%s.wav" % (s["id"], ln["i"], key))
            r = cli.synth(ln["text"], out, voice=voice, speed=a.speed,
                          cache=not a.no_cache)
            if "_error" in r:
                print("  ✗ %s#%d %s" % (s["id"], ln["i"], r["_error"][:120]))
                failed.append("%s#%d" % (s["id"], ln["i"]))
                continue
            if r.get("cached"):
                n_cached += 1
            else:
                n_new += 1
            total_sec += r["sec"]
            manifest.append({"shot": s["id"], "i": ln["i"], "role": ln.get("role"),
                             "text": ln["text"], "chars": ln["chars"],
                             "file": os.path.relpath(r["file"], src.out_dir).replace("\\", "/"),
                             "sec": round(r["sec"], 3)})
        print("  %s · %d 句 · 累计 %.1f 分钟"
              % (s["id"], len(s.get("lines") or []), total_sec / 60), flush=True)

    chars = sum(m["chars"] for m in manifest)
    rate = chars / total_sec if total_sec else 0
    mpath = os.path.join(src.out_dir, "_配音清单.json")
    old = []
    if os.path.exists(mpath) and only:
        with open(mpath, encoding="utf-8") as f:
            old = [m for m in json.load(f).get("lines", [])
                   if m["shot"] not in only]
    allm = sorted(old + manifest, key=lambda m: (m["shot"], m["i"]))
    with open(mpath, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"provider": cli.name, "voice": voice, "speed": a.speed,
                   "rate_cps_measured": round(rate, 2),
                   "silence": SIL,
                   "usage": cli.usage,
                   "totals": {"lines": len(allm),
                              "chars": sum(m["chars"] for m in allm),
                              "seconds": round(sum(m["sec"] for m in allm), 1)},
                   "lines": allm}, f, ensure_ascii=False, indent=2)

    tot = sum(m["sec"] for m in allm)
    pages = len({m["shot"] for m in allm})
    pad = pages * SIL["page"] + max(0, len(allm) - pages) * SIL["sentence"]
    print("\n%d 句（新 %d / 缓存 %d），%d 字，"
          "语音 %.1f 分钟 + 停顿 %.1f 分钟 = **%.1f 分钟**"
          % (len(allm), n_new, n_cached, sum(m["chars"] for m in allm),
             tot / 60, pad / 60, (tot + pad) / 60))
    print("实测语速 %.2f 字/秒（写进配音清单，"
          "下次算字数预算用它）" % rate)
    print("✓ %s" % os.path.relpath(mpath, root))
    if failed:
        print("✗ %d 句失败：%s" % (len(failed), ",".join(failed[:10])))
        raise SystemExit(1)


if __name__ == "__main__":
    main()
