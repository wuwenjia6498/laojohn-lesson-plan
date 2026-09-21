# -*- coding: utf-8 -*-
r"""备课视频链第 8 步：交付包。**只复制不生成。**

    PYTHONUTF8=1 python package_video.py <课次> [--out <目录>]

产出 `写作课备课视频输出\<课次>\_交付包\`：
    <课次>-备课视频.mp4        硬烧字幕版，微信直接发
    <课次>-字幕.srt            外挂备份（本地播放器用）
    备课视频使用说明.md         这是什么／怎么用／三件先说清楚
    版本注记.md                 详案 md5 与出片日期 —— 详案改版要重出片，
                                得让老师对得上自己手里那份是不是最新的

交付范式同 `writing-correction-tool-0818`：**加盟商只拿成品，不装环境、不接触详案全文。**

三条内容红线在旁白生成阶段就由判据与机检把住了（禁把学生答案讲成标准答案、
禁具体学生姓名与内部称谓、**禁替总部承诺师训／班型／课时费／效果数据**），
这里只负责把「内部备课使用、请勿外传」写进说明。
"""
import argparse
import datetime
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from video_link import Sources, project_root, md5  # noqa: E402

README = """# {unit} · 备课视频使用说明

## 这是什么

这节课的**备课视频**：画面就是你手里那份课件，逐页推进；旁白讲的是
「这一页你要讲什么／为什么这么设计／学生容易卡在哪」。

它不是示范课录音，不会把课堂上的话一句句念给你听——那些详案里都有。
它讲的是详案和课件上**看不出来**的那一层：哪里必须守住、哪里可以按班情放开、
学生最容易卡在哪一步。

全长约 {minutes} 分钟。

## 怎么用

1. **上课前一晚看一遍**，手边放着详案和学生单。
2. 听到「这一步必须守住」的地方，回到详案对应环节标一下。
3. 听到「学生容易……」的地方，想一想自己班上谁会这样。

看完再翻一遍详案，比直接读详案快。

## 三件先说清楚

- **视频里的时间是标称时长**，实际课堂按班情浮动，不必掐表。
- **旁白讲的是这一版详案**。详案改版后视频会重出，见《版本注记》，
  对不上就找总部要新的。
- **内部备课使用，请勿外传。** 视频里含教材页面与课件内容。

---
出片日期：{date}
"""

NOTE = """# {unit} · 版本注记

| 项 | 值 |
|---|---|
| 出片日期 | {date} |
| 详案 md5 | `{plan_md5}` |
| 画面源 | {visual}（{kind}） |
| 配音 | {provider} / {voice} / 语速 {speed} |
| 全长 | {minutes} 分钟 |
| 旁白审稿 | {audit} |

**详案改版后必须重出片**：旁白是按上面那个 md5 的详案写的，详案改了、
视频还是旧的，老师会照着讲错。重出后把本文件一起换掉。
"""


def main():
    ap = argparse.ArgumentParser(description="备课视频交付包")
    ap.add_argument("unit")
    ap.add_argument("--out")
    a = ap.parse_args()

    root = project_root()
    src = Sources.of(a.unit, root)
    out = src.out_dir
    pkg = a.out or os.path.join(out, "_交付包")
    os.makedirs(pkg, exist_ok=True)

    mp4 = os.path.join(out, a.unit + "-备课视频.mp4")
    if not os.path.exists(mp4):
        raise SystemExit("没有成片，先跑 render_video.py：%s" % mp4)
    with open(os.path.join(out, "_时间轴.json"), encoding="utf-8") as f:
        tl = json.load(f)
    with open(os.path.join(out, a.unit + "-分镜单.json"), encoding="utf-8") as f:
        sl = json.load(f)
    npath = os.path.join(out, a.unit + "-旁白稿.json")
    audit = "未记账"
    if os.path.exists(npath):
        with open(npath, encoding="utf-8") as f:
            au = (json.load(f).get("meta") or {}).get("audit")
        if au:
            audit = "%s / %s（issues %d）" % (au.get("by"), au.get("at"),
                                                      len(au.get("issues") or []))
    minutes = "%.0f" % (tl["total_sec"] / 60)
    date = datetime.date.today().isoformat()
    vs = sl["meta"].get("visual_source") or {}

    shutil.copy2(mp4, os.path.join(pkg, os.path.basename(mp4)))
    srt = os.path.join(out, "sub.srt")
    if os.path.exists(srt):
        shutil.copy2(srt, os.path.join(pkg, a.unit + "-字幕.srt"))
    with open(os.path.join(pkg, "备课视频使用说明.md"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write(README.format(unit=a.unit, minutes=minutes, date=date))
    with open(os.path.join(pkg, "版本注记.md"),
              "w", encoding="utf-8", newline="\n") as f:
        f.write(NOTE.format(unit=a.unit, date=date,
                            plan_md5=md5(src.plan_md),
                            visual=os.path.basename(vs.get("path", "?")),
                            kind=vs.get("kind", "?"),
                            provider=tl.get("provider"), voice=tl.get("voice"),
                            speed=tl.get("speed"), minutes=minutes, audit=audit))

    n = len(os.listdir(pkg))
    mb = sum(os.path.getsize(os.path.join(pkg, x)) for x in os.listdir(pkg)) / 1e6
    print("✓ %s：%d 件，%.0f MB" % (os.path.relpath(pkg, root), n, mb))
    if audit == "未记账":
        print("⚠ 旁白稿没过闸门 A 就出了片——"
              "对外发之前补上 "
              "audit_narration.py --by <人>，并重出版本注记")


if __name__ == "__main__":
    main()
