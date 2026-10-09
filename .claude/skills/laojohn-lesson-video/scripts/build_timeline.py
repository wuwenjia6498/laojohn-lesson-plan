# -*- coding: utf-8 -*-
r"""备课视频链第 6 步：配音清单 + 分镜单 → 时间轴 / 字幕 / ffmpeg concat 清单。**纯推导。**

    PYTHONUTF8=1 python build_timeline.py <课次> [--head-sec 6] [--tail-sec 5]

产出（全部在 `写作课备课视频输出\<课次>\`，都是产物、不入库）：
    _时间轴.json   逐句 start/end，供核查
    sub.srt        字幕（**文件名固定 ASCII**，见下）
    _audio.txt     ffmpeg concat 的音频清单
    _frames.txt    ffmpeg concat 的画面清单

**时长全部来自音频实测，零估算。** 每页画面停留时长 = 该页各句音频之和 + 句间静音
+ 页末静音，这三样都是实体 wav 片段，所以画面切换点与音频采样严格对齐、不会漂。

两个必须这么做的细节：

1. **停顿做成实体静音片段塞进 concat 列表**，不用 `adelay`/`apad`。这样音频总长与
   时间轴逐样本一致，字幕边界是算出来的、不是估出来的。

2. **字幕固定叫 `sub.srt`（纯 ASCII）**。ffmpeg 的 `subtitles=` 滤镜里，盘符冒号会被
   当成滤镜参数分隔符，中文路径在某些构建下也会失败。渲染时 cwd 切到产物目录、
   只传这个相对文件名，最省事。交付时再改成中文名。

跨页 shot（详案里写 `〖PPT 第19-20页〗`）：该页旁白时长按页数均分到两帧，
画面照样逐页推进。
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root  # noqa: E402

# 单条字幕**折行**的阈值。0921 从 20 提到 24：一行 24 字在 1920 宽上只占六成，
# 放得下；而 20 的时候 21~24 字的句子全被折成两行，多出来的折点没标点可落，
# 只能在词中间断（实测 142 条折行里 35 条断在词中，「爸/爸」这种最难看）。
SUB_MAX = 24
LINE_MAX = 26         # 折行后**每一行**的字数上限，防止一行顶满画面


def ts(sec):
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return "%02d:%02d:%02d,%03d" % (h, m, s, ms)


# 避头尾：这些字符不能出现在行首（中文排版基本规则）。
# 0921 成片实测：片尾一句折成「…填“更好了 / ”“更方便了”的学生…」，
# **闭引号被甩到了下一行开头**——逐句看字幕文件看不出来，只有看成片才发现。
NO_LINE_START = "，、：；。！？）】」』”’…—》〉"
NO_LINE_END = "（【「『“‘《〈"
# ⚠ **引号一个都不许起行**（0921 用户定，开闭都算），所以开引号也进 NO_LINE_START。
# 只做避头尾是不够的：把闭引号拉回上一行之后，下一行就改成以开引号起头了
# （`…填“更好了” / “更方便了”的学生…`），两条规则会互相顶牛。
# 所以不再「推着切点挪」，改成**枚举全部切点、取第一个两侧都合法的**。
# 在引号块内部折是允许的——那样行首是普通字，不违规。
NO_LINE_START += "“‘"


def _han(c):
    return "一" <= c <= "龥"


def wrap(text, sub_max=None, line_max=None):
    """长句折成两行显示，不改时间轴。

    切点规则：行首不许是标点或任何引号，行尾不许是开引号／开括号。
    满足这两条的位置里，取**离中点最近**的一个；落在逗号句号之后的给 6 字折扣，
    好让切点尽量跟着自然停顿走。一个合法位置都没有就不折（整句全是引号块时）。

    `sub_max`/`line_max` 缺省取模块常量（横屏备课视频）；竖屏宣传片
    （laojohn-promo-video）经薄壳传入更窄的值。**只加参数、不动缺省**。
    """
    sub_max = SUB_MAX if sub_max is None else sub_max
    line_max = LINE_MAX if line_max is None else line_max
    if len(text) <= sub_max:
        return text
    mid = len(text) // 2
    best = None
    for c in range(1, len(text)):
        if text[c] in NO_LINE_START or text[c - 1] in NO_LINE_END:
            continue
        score = abs(c - mid) - (6 if text[c - 1] in "，、：。" else 0)
        # 两侧都是汉字＝多半断在词中间（「便利」断成「便 / 利」）。
        # 给个惩罚，有别的合法切点时就会绕开；实在没有也不硬拦——
        # 中文分词这里不值得引依赖，这条近似够用。
        if _han(text[c - 1]) and _han(text[c]):
            score += 4
        # 重罚超宽的那一行：避词惩罚会把切点推到很偏的位置，
        # 实测出现过 39 字的一行（几乎顶满画面）。只要有不超宽的切点就必选它。
        if max(c, len(text) - c) > line_max:
            score += 100
        if best is None or score < best[0]:
            best = (score, c)
    if best is None:
        return text
    cut = best[1]
    return text[:cut] + "\n" + text[cut:]


def main():
    ap = argparse.ArgumentParser(description="时间轴与字幕")
    ap.add_argument("unit")
    ap.add_argument("--head-sec", type=float, default=6.0, help="片头静场秒数")
    ap.add_argument("--tail-sec", type=float, default=5.0, help="片尾静场秒数")
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    out = src.out_dir
    with open(os.path.join(out, a.unit + "-分镜单.json"), encoding="utf-8") as f:
        sl = json.load(f)
    mpath = os.path.join(out, "_配音清单.json")
    if not os.path.exists(mpath):
        raise SystemExit("没有配音清单，先跑 synth_voice.py")
    with open(mpath, encoding="utf-8") as f:
        man = json.load(f)

    sil = man.get("silence") or {"sentence": 0.25, "page": 0.80}
    by_shot = {}
    for m in man["lines"]:
        by_shot.setdefault(m["shot"], []).append(m)
    for v in by_shot.values():
        v.sort(key=lambda x: x["i"])

    missing = [s["id"] for s in sl["shots"] if s["id"] not in by_shot]
    if missing:
        raise SystemExit("这几页没有音频，先补合成：%s\n"
                         "  python synth_voice.py \"%s\" --only %s"
                         % (",".join(missing), a.unit, ",".join(missing)))

    ac = sl["meta"].get("align_check") or {}
    # 片头/片尾页现在多半已由 build_shotlist 的 s00/s99 认领（有旁白），
    # 只有仍然没人认的页才补静场——否则这两页会出现两次。
    owned = {p for s in sl["shots"] for p in s["pages"]}
    head_pages = [p for p in (ac.get("head_unused") or []) if p not in owned]
    tail_pages = [p for p in (ac.get("tail_unused") or []) if p not in owned]

    audio, frames, cues, segs = [], [], [], []
    t = 0.0
    sil_s = "audio/_sil_sentence.wav"
    sil_p = "audio/_sil_page.wav"

    def add_silence_frames(pages, seconds):
        """片头封面 / 片尾 THE END：没有旁白，给固定静场，音轨补等长静音。"""
        nonlocal t
        if not pages:
            return
        each = seconds / float(len(pages))
        for p in pages:
            fr = "frames/p%02d.png" % p
            if not os.path.exists(os.path.join(out, fr)):
                continue
            frames.append((fr, each))
            n = int(round(each / sil["page"]))
            for _ in range(max(1, n)):
                audio.append(sil_p)
            segs.append({"shot": "-", "page": p, "start": round(t, 3),
                         "end": round(t + each, 3)})
            t += max(1, n) * sil["page"]

    add_silence_frames(head_pages, a.head_sec)

    for sh in sl["shots"]:
        lines = by_shot[sh["id"]]
        start = t
        for k, m in enumerate(lines):
            audio.append(m["file"])
            cues.append({"start": t, "end": t + m["sec"], "text": m["text"],
                         "shot": sh["id"], "i": m["i"]})
            t += m["sec"]
            if k < len(lines) - 1:
                audio.append(sil_s)
                t += sil["sentence"]
        audio.append(sil_p)
        t += sil["page"]
        dur = t - start
        per = dur / float(len(sh["pages"]))       # 跨页 shot：时长均分到各帧
        for j, p in enumerate(sh["pages"]):
            fr = "frames/p%02d.png" % p
            frames.append((fr, per))
            segs.append({"shot": sh["id"], "page": p,
                         "start": round(start + j * per, 3),
                         "end": round(start + (j + 1) * per, 3)})

    add_silence_frames(tail_pages, a.tail_sec)

    with open(os.path.join(out, "_audio.txt"), "w", encoding="utf-8", newline="\n") as f:
        for x in audio:
            f.write("file '%s'\n" % x.replace("\\", "/"))
    with open(os.path.join(out, "_frames.txt"), "w", encoding="utf-8", newline="\n") as f:
        for fr, d in frames:
            f.write("file '%s'\nduration %.3f\n" % (fr, d))
        if frames:
            # concat demuxer 的已知怪癖：最后一帧必须再写一行，否则被吞掉
            f.write("file '%s'\n" % frames[-1][0])

    with open(os.path.join(out, "sub.srt"), "w", encoding="utf-8", newline="\n") as f:
        for n, c in enumerate(cues, 1):
            f.write("%d\n%s --> %s\n%s\n\n"
                    % (n, ts(c["start"]), ts(c["end"]), wrap(c["text"])))

    tl = {"total_sec": round(t, 3), "size": "1920x1080", "fps": 30,
          "silence": sil, "provider": man.get("provider"), "voice": man.get("voice"),
          "speed": man.get("speed"), "rate_cps_measured": man.get("rate_cps_measured"),
          "head_sec": a.head_sec, "tail_sec": a.tail_sec,
          "segments": segs, "cues": [dict(c, start=round(c["start"], 3),
                                          end=round(c["end"], 3)) for c in cues]}
    with open(os.path.join(out, "_时间轴.json"), "w",
              encoding="utf-8", newline="\n") as f:
        json.dump(tl, f, ensure_ascii=False, indent=2)

    print("%s：%d 帧 / %d 句字幕 / %d 个音频片段"
          % (a.unit, len(frames), len(cues), len(audio)))
    print("总时长 **%.1f 分钟**（语音 %.1f + 停顿与静场 %.1f）"
          % (t / 60, sum(m["sec"] for m in man["lines"]) / 60,
             (t - sum(m["sec"] for m in man["lines"])) / 60))
    print("实测语速 %s 字/秒（通道 %s / 音色 %s / 语速 %s）"
          % (man.get("rate_cps_measured"), man.get("provider"),
             man.get("voice"), man.get("speed")))
    lo, hi = 15, 25
    if not (lo <= t / 60 <= hi):
        print("⚠ 不在 %d–%d 分钟区间，"
              "按 narration-style.md §五 的压缩阶梯处理" % (lo, hi))
    print("✓ _时间轴.json / sub.srt / _audio.txt / _frames.txt")


if __name__ == "__main__":
    main()
