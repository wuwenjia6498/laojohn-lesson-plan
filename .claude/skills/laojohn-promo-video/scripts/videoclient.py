# -*- coding: utf-8 -*-
r"""视频生成 + 转写客户端（宣传片线讲解员口播用）。

    make_video(provider=None)   →  .generate(prompt, refs, seconds, ratio, resolution) → mp4 bytes
    transcribe(wav_path)        →  {"text", "segments":[{start,end,text}]} 或 {"_error": …}

通道（`VIDEO_PROVIDER` 一个环境变量切，缺省 aihubmix）：
  aihubmix  AiHubMix 新异步协议 `/ai/v1/videos`（2026-09-27 实测）。
            ⚠ 旧的 `/v1/videos` 对 minimax-h3 直接 400「legacy protocol」；
            ⚠ 账号须先在控制台开通「异步任务」，否则 403 async_not_enabled；
            ⚠ 不认 `generate_audio` 字段（schema_violation）——H3 本就自带声音，不传。
            实测产物：768×1344、24fps、AAC 32kHz 双声道，4 秒片约 2 分钟出。
  minimax   MiniMax 官方 `/v2/video_generation`（退路；需 MINIMAX_API_KEY）。

参考素材一律 base64 data URL 内联（两家都认；单请求上限 64MB，人像+场景+10 秒 wav 远够）。

密钥：AIHUBMIX_API_KEY 走 imgclient 的同一套三级回退（环境变量 → 课件配图工具\.env →
picture-writing 的 imggen.config.json），importlib 载入、不复制（CLAUDE.md §3）。

失败纪律（同 ttsclient）：生成失败抛 RuntimeError 带服务端原文，**绝不落空片冒充成功**；
转写失败返回 `_error`，上层按「未知」处理、不当「不通过」。
"""
import base64
import importlib.util
import json
import mimetypes
import os
import time

import requests

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".."))
IMGCLIENT = os.path.join(ROOT, "课件配图工具", "scripts", "imgclient.py")


def _imgclient():
    spec = importlib.util.spec_from_file_location("imgclient", IMGCLIENT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def aihubmix_key():
    m = _imgclient()
    m.load_dotenv()
    return m._aihubmix_key()


def data_url(path):
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    if path.lower().endswith(".wav"):
        mime = "audio/wav"
    with open(path, "rb") as f:
        return "data:%s;base64,%s" % (mime, base64.b64encode(f.read()).decode())


def _kind(path):
    ext = os.path.splitext(path)[1].lower()
    if ext in (".wav", ".mp3"):
        return "audio"
    if ext in (".mp4", ".mov"):
        return "video"
    return "image"


class AihubmixVideo(object):
    name = "aihubmix"
    POLL = 15

    def __init__(self):
        self.key = aihubmix_key()
        self.base = os.environ.get("AIHUBMIX_VIDEO_BASE", "https://aihubmix.com/ai/v1/videos")
        self.model = os.environ.get("PROMO_VIDEO_MODEL", "minimax-h3")
        self.h = {"Authorization": "Bearer " + self.key}

    def submit(self, prompt, refs=(), seconds=10, ratio="9:16", resolution="768P"):
        body = {"model": self.model, "prompt": prompt, "duration": int(seconds),
                "aspect_ratio": ratio, "resolution": resolution}
        if refs:
            body["input_references"] = [{"type": _kind(p) + "_url", "url": data_url(p)} for p in refs]
        r = requests.post(self.base, headers=self.h, json=body, timeout=180)
        if r.status_code != 200:
            raise RuntimeError("提交失败 %s：%s" % (r.status_code, r.text[:800]))
        j = r.json()
        if not j.get("id"):
            raise RuntimeError("提交返回里没有任务 id：%s" % str(j)[:500])
        return j["id"]

    def wait(self, task_id, timeout=1500, log=print):
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(self.POLL)
            try:
                r = requests.get(self.base + "/" + task_id, headers=self.h, timeout=60)
                j = r.json()
            except (requests.RequestException, ValueError) as e:
                log("    轮询出错（重试）：%r" % e)
                continue
            st = j.get("status")
            if st == "completed":
                out = (j.get("output") or [{}])[0]
                url = out.get("content_url") or (self.base + "/" + task_id + "/content")
                return self._download(url)
            if st in ("failed", "cancelled"):
                raise RuntimeError("生成%s：%s" % (st, json.dumps(j.get("error"), ensure_ascii=False)))
        raise RuntimeError("等了 %d 秒还没出片（任务 %s，可稍后用 --resume 续取）" % (timeout, task_id))

    def _download(self, url):
        r = requests.get(url, headers=self.h, timeout=300)
        if r.status_code != 200 or r.content[4:8] != b"ftyp":
            raise RuntimeError("下载失败 %s：%s" % (r.status_code, r.text[:300] if r.status_code != 200 else "不是 mp4"))
        return r.content

    def generate(self, prompt, refs=(), seconds=10, ratio="9:16", resolution="768P", log=print):
        tid = self.submit(prompt, refs, seconds, ratio, resolution)
        log("    任务 %s 已提交" % tid)
        return tid, self.wait(tid, log=log)


class MinimaxVideo(AihubmixVideo):
    """MiniMax 官方 v2（退路）。content 数组带 role，参考生成走 reference_*。"""
    name = "minimax"

    def __init__(self):
        self.key = os.environ.get("MINIMAX_API_KEY")
        if not self.key:
            raise SystemExit("minimax 通道需要 MINIMAX_API_KEY")
        self.base = os.environ.get("MINIMAX_BASE", "https://api.minimax.io")
        self.model = os.environ.get("PROMO_VIDEO_MODEL", "MiniMax-H3")
        self.h = {"Authorization": "Bearer " + self.key}

    def submit(self, prompt, refs=(), seconds=10, ratio="9:16", resolution="768P"):
        content = [{"type": "text", "text": prompt}]
        for p in refs:
            k = _kind(p)
            content.append({"type": k + "_url", k + "_url": {"url": data_url(p)},
                            "role": "reference_" + k})
        body = {"model": self.model, "content": content, "duration": int(seconds),
                "ratio": ratio, "resolution": resolution}
        r = requests.post(self.base + "/v2/video_generation", headers=self.h, json=body, timeout=180)
        j = r.json() if r.content else {}
        if r.status_code != 200 or not j.get("task_id"):
            raise RuntimeError("提交失败 %s：%s" % (r.status_code, r.text[:800]))
        return j["task_id"]

    def wait(self, task_id, timeout=1500, log=print):
        t0 = time.time()
        while time.time() - t0 < timeout:
            time.sleep(self.POLL)
            try:
                j = requests.get(self.base + "/v2/query/video_generation/" + task_id,
                                 headers=self.h, timeout=60).json().get("task", {})
            except (requests.RequestException, ValueError) as e:
                log("    轮询出错（重试）：%r" % e)
                continue
            st = j.get("status")
            if st == "succeeded":
                r = requests.get(j["content"]["url"], timeout=300)
                if r.status_code != 200:
                    raise RuntimeError("下载失败 %s" % r.status_code)
                return r.content
            if st in ("failed", "cancelled"):
                raise RuntimeError("生成%s：%s" % (st, json.dumps(j, ensure_ascii=False)[:500]))
        raise RuntimeError("等了 %d 秒还没出片（任务 %s）" % (timeout, task_id))


PROVIDERS = {"aihubmix": AihubmixVideo, "minimax": MinimaxVideo}


def make_video(provider=None):
    name = (provider or os.environ.get("VIDEO_PROVIDER") or "aihubmix").lower()
    if name not in PROVIDERS:
        raise SystemExit("未知视频通道 %s，可选：%s" % (name, "/".join(PROVIDERS)))
    return PROVIDERS[name]()


def transcribe(wav_path, language="zh", prompt=None):
    """AiHubMix whisper-1，verbose_json 带分段时间。失败回 `_error`（上层当「未知」）。"""
    try:
        with open(wav_path, "rb") as f:
            r = requests.post("https://aihubmix.com/v1/audio/transcriptions",
                              headers={"Authorization": "Bearer " + aihubmix_key()},
                              data={"model": os.environ.get("PROMO_ASR_MODEL", "whisper-1"),
                                    "language": language, "response_format": "verbose_json",
                                    "timestamp_granularities[]": "segment",
                                    **({"prompt": prompt} if prompt else {})},
                              files={"file": (os.path.basename(wav_path), f, "audio/wav")},
                              timeout=180)
        if r.status_code != 200:
            return {"_error": "转写 %s：%s" % (r.status_code, r.text[:300])}
        j = r.json()
        return {"text": j.get("text", ""),
                "segments": [{"start": s["start"], "end": s["end"], "text": s["text"]}
                             for s in j.get("segments") or []]}
    except Exception as e:  # 网络/解析一律当「未知」
        return {"_error": repr(e)}
