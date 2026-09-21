# -*- coding: utf-8 -*-
r"""备课视频链第 7 步：帧 + 音频 + 字幕 → mp4。**确定性，全靠 ffmpeg。**

    PYTHONUTF8=1 python render_video.py <课次> [--no-subs] [--sample 2] [--crf 21] [--fps 30]

两步走：先把音频片段拼成一条音轨，再把画面序列与音轨合成、顺带烧字幕与水印。

`--sample N` 只渲前 N 个环节出样片（闸门 B）——20 分钟全渲一次要几分钟，
先出 5 分钟样片给人看过再全量，比返工便宜。

四个必须知道的坑：

0. **字幕滤镜前面必须有 `fps=N`，否则字幕整个不出现**（2026-09-21 踩中，查了半天）。
   concat demuxer 喂进来的是「每页一帧」——`duration` 只告诉容器这一帧显示多久，
   滤镜链实际只见到 25 帧。`subtitles` 按帧 PTS 取字幕，于是整页只会烧上该页起始
   那一刻的一条（多半是空的），成片看起来就像字幕功能压根没生效。
   ⚠ 用输出端的 `-r 30` 代替不行——那是滤镜链之后的事。
   ⚠ 也别急着怀疑 libass 或中文字体：拿 `-f lavfi -i color=white` 单测一下就知道
   滤镜本身是好的。另外 `-ss 10 -i file` 抽帧验证会误导你（输入 seek 重置时间戳，
   抽出来的帧按 0 秒匹配字幕），要验证请把 `-ss` 放在 `-i` 之后。

1. **音频片段必须是同采样率/声道/位深的 wav**（ttsclient 已强制 24kHz 单声道 16bit）。
   若用 mp3 片段 `-c copy` 拼接，每段首尾的编码器 padding 会累积成几百毫秒漂移，
   20 分钟的片子到片尾字幕就明显对不上，而且这种误差极难定位。

2. **`_frames.txt` 的最后一帧要重复写一行**（build_timeline 已做），否则 concat
   demuxer 会把它吞掉。

3. **`subtitles=` 滤镜的路径**：盘符冒号会被当成滤镜参数分隔符，中文路径在某些构建下
   也会失败。这里把 cwd 切到产物目录、只传 `sub.srt` 这个纯 ASCII 相对名。

**软字幕不做**（`-c:s mov_text` 能塞进 mp4，但移动端播放器普遍不显示，等于没做）。
交付主版是硬烧字幕那一份——微信/企业微信的内置播放器不认外挂 srt。
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root  # noqa: E402
import ffmpeg_path  # noqa: E402

WATERMARK = "\u5185\u90e8\u5907\u8bfe\u4f7f\u7528 \u00b7 \u8bf7\u52ff\u5916\u4f20"
SLIDE_H = 1080          # \u8bfe\u4ef6\u753b\u9762\u533a\u9ad8\u5ea6\uff0c\u96f6\u906e\u6321
BAR_H = 152             # \u5e95\u90e8\u5b57\u5e55\u5e26\uff1b\u6539\u5b83\u5fc5\u987b\u91cd\u7b97 SUB_SIZE / SUB_MARGIN\uff08\u89c1 main \u91cc\u7684\u6ce8\u91ca\uff09
OUT_W, OUT_H = 1920, SLIDE_H + BAR_H     # 1920x1232\uff0c\u9ad8\u662f 16 \u7684\u500d\u6570\uff0cH.264 \u6700\u7701
BAR_COLOR = "0xF2F2F0"  # \u6d45\u7070\u767d\uff0c\u8ddf\u8bfe\u4ef6\u7684\u6d45\u8272\u8c03\u4e00\u81f4\uff1b\u6df1\u8272\u5e26\u4f1a\u5728\u5e95\u90e8\u5272\u51fa\u4e00\u6761\u786c\u8fb9
SUB_SIZE = 14
SUB_MARGIN = 10


def font_file():
    """drawtext 要真字体文件路径。雅黑在 Windows 上是固定位置。"""
    for p in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msyhbd.ttc",
              r"C:\Windows\Fonts\simhei.ttf"):
        if os.path.exists(p):
            return p.replace("\\", "/").replace(":", r"\:")
    return None


def run_in(cwd, args, timeout=3600):
    exe = ffmpeg_path.ffmpeg()
    r = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y"] + list(args),
                       cwd=cwd, capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg \u5931\u8d25\uff1a\n%s" % (r.stderr or "")[-900:])


def main():
    ap = argparse.ArgumentParser(description="\u5408\u6210\u5907\u8bfe\u89c6\u9891")
    ap.add_argument("unit")
    ap.add_argument("--no-subs", action="store_true", help="\u4e0d\u70e7\u5b57\u5e55")
    ap.add_argument("--no-watermark", action="store_true")
    ap.add_argument("--sample", type=int, default=0,
                    help="\u53ea\u6e32\u524d N \u9875\u51fa\u6837\u7247\uff08\u95f8\u95e8 B\uff09")
    ap.add_argument("--crf", type=int, default=21)
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    out = src.out_dir
    tl_path = os.path.join(out, "_\u65f6\u95f4\u8f74.json")
    if not os.path.exists(tl_path):
        raise SystemExit("\u6ca1\u6709\u65f6\u95f4\u8f74\uff0c\u5148\u8dd1 build_timeline.py")
    with open(tl_path, encoding="utf-8") as f:
        tl = json.load(f)

    alist, flist = "_audio.txt", "_frames.txt"
    suffix = ""
    if a.sample:
        # 样片：按帧数截断两份清单。音频按段落时长反推更麻烦，这里直接用
        # 时间轴里第 N 帧的结束时刻去 -t 截音轨，效果一样且不会错位。
        segs = tl["segments"][:a.sample]
        cut = segs[-1]["end"] if segs else 60.0
        suffix = "-\u6837\u7247"
    voice = os.path.join(out, "_voice.m4a")
    print("%s\uff1a\u62fc\u97f3\u8f68\uff08%d \u4e2a\u7247\u6bb5\uff09..." % (a.unit, len(tl["segments"])),
          flush=True)
    args = ["-f", "concat", "-safe", "0", "-i", alist]
    if a.sample:
        args += ["-t", "%.3f" % cut]
    args += ["-c:a", "aac", "-b:a", "128k", "-ar", "44100", "_voice.m4a"]
    run_in(out, args)

    name = "%s-\u5907\u8bfe\u89c6\u9891%s.mp4" % (a.unit, suffix)
    vf = ["scale=1920:1080:force_original_aspect_ratio=decrease",
          # 底部加一条字幕带，**不要把字幕叠在课件上**。
          # 课件底部常有本页的关键论点（实测 p09 那行「这不叫特点」正是全页结论），
          # 任何叠加都会盖住它。加带之后课件 1080 高零遮挡，字幕有专属区域。
          # 参数是算出来的，不是试出来的，改一个要跟着改另一个：
          #   字幕最多两行（build_timeline 的 wrap 只折一次），
          #   实际字号 = FontSize / 384 * 输出高（384 是 srt 的 PlayResY），
          #   要求 MarginV_px + 两行高 ≤ BAR_H，否则第一行会顶进课件区。
          #   现值：BAR_H=152、输出高 1232（16 的倍数，H.264 最省）、
          #   FontSize=14 → 44.9px、两行约 108px、MarginV=10 → 32px，余量 12px。
          "pad=%d:%d:0:0:color=%s" % (OUT_W, OUT_H, BAR_COLOR),
          # ⚠ **fps 必须在 subtitles 之前**，而且不能靠输出端的 -r 代替。
          # concat demuxer 喂进来的是「每页一帧」——duration 只告诉容器这帧显示多久，
          # 滤镜链实际只见到 25 帧。字幕滤镜按帧 PTS 取字幕，于是整页只会烧上该页
          # 起始那一刻的一条（多半是空的），看起来就像「字幕完全没生效」。
          # 先 fps=N 把它展开成连续帧，每帧才有自己的时间戳。
          "fps=%d" % a.fps,
          "format=yuv420p"]
    if not a.no_subs and os.path.exists(os.path.join(out, "sub.srt")):
        # 浅色字幕带上用深灰字，**不描边、不加底框**。
        # 原先是 BorderStyle=3（不透明底框）叠在画面上，就是那块生硬的灰褐方块。
        vf.append("subtitles=sub.srt:force_style="
                  "'FontName=Microsoft YaHei,FontSize=%d,Bold=1,"
                  "PrimaryColour=&H00333333,OutlineColour=&H00FFFFFF,"
                  "BorderStyle=1,Outline=0,Shadow=0,MarginV=%d'"
                  % (SUB_SIZE, SUB_MARGIN))
    ff = font_file()
    if not a.no_watermark and ff:
        # y 用 SLIDE_H 而不是 h：h 现在是 1232，用它会把水印扔进字幕带里
        vf.append("drawtext=fontfile='%s':text='%s':fontsize=20:"
                  "fontcolor=white@0.72:box=1:boxcolor=black@0.28:boxborderw=6:"
                  "x=w-tw-28:y=%d-th-24" % (ff, WATERMARK, SLIDE_H))

    print("  \u5408\u6210\u753b\u9762%s..."
          % ("\uff08\u5e26\u5b57\u5e55\uff09" if not a.no_subs else ""), flush=True)
    args = ["-f", "concat", "-safe", "0", "-i", flist, "-i", "_voice.m4a",
            "-vf", ",".join(vf), "-r", str(a.fps),
            "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
            "-c:a", "copy", "-shortest", "-movflags", "+faststart", name]
    run_in(out, args)

    p = os.path.join(out, name)
    mb = os.path.getsize(p) / 1e6
    exe = ffmpeg_path.ffprobe()
    r = subprocess.run([exe, "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", p],
                       capture_output=True, text=True)
    dur = float((r.stdout or "0").strip() or 0)
    print("\n\u2713 %s" % os.path.relpath(p, root))
    print("  %.1f \u5206\u949f\uff0c%.0f MB\uff0c%dx%d\uff08\u8bfe\u4ef6 %d + \u5b57\u5e55\u5e26 %d\uff09\uff0c%dfps crf%d"
          % (dur / 60, mb, OUT_W, OUT_H, SLIDE_H, BAR_H, a.fps, a.crf))
    if a.sample:
        print("  \uff08\u6837\u7247\uff1a\u53ea\u6e32\u4e86\u524d %d \u5e27\uff0c\u4e0d\u4e0e\u6574\u7247\u65f6\u957f\u6bd4\u5bf9\uff09" % a.sample)
    else:
        drift = abs(dur - tl["total_sec"])
        print("  \u65f6\u95f4\u8f74\u9884\u671f %.1f \u5206\u949f\uff0c\u5b9e\u9645\u504f\u5dee %.2f \u79d2%s"
              % (tl["total_sec"] / 60, drift,
                 "" if drift < 1.0 else "  \u2190 \u504f\u5dee\u504f\u5927\uff0c\u67e5\u97f3\u9891\u7247\u6bb5\u683c\u5f0f\u662f\u5426\u7edf\u4e00"))
    if not a.sample:
        print("  \u6293\u4e09\u5904\u6838\u97f3\u753b\u5b57\u540c\u6b65\uff1a2 \u5206\u949f / %d \u5206\u949f / \u7ed3\u5c3e"
              "\uff08**\u672b\u9875\u5fc5\u67e5\uff0c\u6f02\u79fb\u662f\u7d2f\u79ef\u7684**\uff09" % int(dur / 60 / 2))


if __name__ == "__main__":
    main()
