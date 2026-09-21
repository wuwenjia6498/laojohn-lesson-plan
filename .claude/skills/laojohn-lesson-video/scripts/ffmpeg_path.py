# -*- coding: utf-8 -*-
r"""ffmpeg / ffprobe 定位。单一源，链上各脚本 import。

发现顺序（**禁硬编码盘符**——项目在移动硬盘，CLAUDE.md §1）：
    1. 环境变量 FFMPEG_EXE / FFPROBE_EXE（显式覆盖，最高优先）
    2. PATH 里的 ffmpeg
    3. <项目根>\工具\ffmpeg\bin\ffmpeg.exe（便携版，整目录 gitignore）
    4. 都没有 → 抛异常，消息里直接给安装命令

⚠ **Playwright 自带的那个 ffmpeg 不能用**，别去试（2026-09-21 实测）：
`%LOCALAPPDATA%\ms-playwright\ffmpeg-1011\ffmpeg-win64.exe` 是 `--disable-everything`
构建，只有 libvpx VP8 编码器、只有 webm muxer，**没有 libx264、没有 aac、没有 mp4**。
本脚本主动跳过它，免得有人把它加进 PATH 之后链路在最后一步才炸。
"""
import os
import shutil
import subprocess

INSTALL_HINT = (
    "本机没有 ffmpeg。两条路任选：\n"
    "  1) winget install --id Gyan.FFmpeg -e\n"
    "  2) 下载 ffmpeg-release-essentials.zip 解压到 <项目根>\\工具\\ffmpeg\\"
    "（整目录已 gitignore）\n"
    "⇒ 别用 Playwright 自带的 ms-playwright\\ffmpeg-*\\ffmpeg-win64.exe："
    "它是 disable-everything 构建，只有 VP8/webm，出不了 mp4。"
)


class FFmpegMissing(Exception):
    pass


def _project_root(start=None):
    p = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isdir(os.path.join(p, "写作课详案输出")):
            return p
        up = os.path.dirname(p)
        if up == p:
            return None
        p = up


def _looks_crippled(exe):
    """Playwright 那个阉割版的指纹：编码器列表里没有 libx264。"""
    try:
        r = subprocess.run([exe, "-hide_banner", "-encoders"],
                           capture_output=True, text=True, timeout=20)
        return "libx264" not in (r.stdout or "")
    except Exception:
        return True


def find(name="ffmpeg", root=None):
    env = os.environ.get(name.upper() + "_EXE")
    if env and os.path.exists(env):
        return env
    hit = shutil.which(name)
    if hit and "ms-playwright" not in hit.replace("/", "\\").lower():
        return hit
    # winget 装的 Gyan.FFmpeg：它把别名放进 %LOCALAPPDATA%\Microsoft\WinGet\Links，
    # 但那条 PATH 要重开 shell 才生效——装完当场跑会找不到。直接认这个目录。
    la = os.environ.get("LOCALAPPDATA")
    if la:
        cand = os.path.join(la, "Microsoft", "WinGet", "Links", name + ".exe")
        if os.path.exists(cand):
            return cand
    r = root or _project_root()
    if r:
        cand = os.path.join(r, "工具", "ffmpeg", "bin", name + ".exe")
        if os.path.exists(cand):
            return cand
        cand = os.path.join(r, "工具", "ffmpeg", name + ".exe")
        if os.path.exists(cand):
            return cand
    raise FFmpegMissing(INSTALL_HINT)


def ffmpeg(root=None):
    exe = find("ffmpeg", root)
    if _looks_crippled(exe):
        raise FFmpegMissing("找到的 ffmpeg 没有 libx264 编码器：%s\n%s"
                            % (exe, INSTALL_HINT))
    return exe


def ffprobe(root=None):
    try:
        return find("ffprobe", root)
    except FFmpegMissing:
        exe = find("ffmpeg", root)
        cand = os.path.join(os.path.dirname(exe), "ffprobe.exe")
        if os.path.exists(cand):
            return cand
        raise


def run(args, root=None, timeout=600):
    """跑一条 ffmpeg 命令；失败时把 stderr 尾部带出来——ffmpeg 的真正原因永远在最后几行。"""
    exe = find("ffmpeg", root)
    r = subprocess.run([exe, "-hide_banner", "-loglevel", "error", "-y"] + list(args),
                       capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError("ffmpeg 失败：%s" % (r.stderr or "")[-600:])
    return r


def wav_seconds(path):
    """wav 时长：标准库读头算，零依赖、不信任何 API 自报的时长。"""
    import wave
    with wave.open(path, "rb") as w:
        return w.getnframes() / float(w.getframerate())


if __name__ == "__main__":
    try:
        print("ffmpeg  %s" % ffmpeg())
        print("ffprobe %s" % ffprobe())
    except FFmpegMissing as e:
        print(e)
        raise SystemExit(1)
