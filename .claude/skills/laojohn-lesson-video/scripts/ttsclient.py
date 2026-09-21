# -*- coding: utf-8 -*-
r"""TTS 多通道客户端。**真源**，链上脚本 importlib 薄壳调用，禁复制。

照 `课件配图工具\scripts\imgclient.py` 的形写：工厂 + PROVIDERS 表 + 三级密钥回退
（环境变量 → scripts\.env → picture-writing 的 imggen.config.json），base_url 与音色 id
全部配置化、不写死。换通道只改一个环境变量 `TTS_PROVIDER`。

    from ttsclient import make_tts
    t = make_tts()                       # 缺省 aihubmix
    r = t.synth("这一页你要做的是……", "audio/s03_01.wav")
    r["sec"]                             # 实测时长（读 wav 头算，不信 API 自报）

两条与 imgclient 同构的纪律：

1. **落盘统一 24kHz 单声道 16bit wav**（各家返回 mp3/wav/pcm 不一，一律过 ffmpeg 转）。
   为什么非 wav 不可：成片时音频是用 concat demuxer 拼的，mp3 片段每段首尾有编码器
   padding，几百段拼下来会累积成几百毫秒漂移——20 分钟的片子到片尾字幕就明显对不上，
   而且这种误差极难定位。统一 wav 从根上消灭它。

2. **失败返回 `{"_error": …}`，绝不落一段静音冒充成功。** 静音会一路混进成片，
   直到有人看完 20 分钟才发现。同 imgclient 的 `_error`/`_raw` 口径。

通道现状（2026-09-21）：
  volc      火山豆包语音合成模型2.0。**现行交付通道，已开通正式版**：
            后付费 0.0003 元/字、不限字数、并发 10、99 款音色。
            cluster 用 volcano_tts（大模型 *_uranus_bigtts 音色也是这个值）。
            实测 5.1~5.3 字/秒，speed 用 1.0。
            ⚠ 它与仓内 ARK_API_KEY 不是同一套凭证，是独立产品线。
  aihubmix  OpenAI 兼容 /v1/audio/speech，复用现有 AIHUBMIX_API_KEY、零开通。
            ⚠ 只有六个 OpenAI 英文音色，念中文洋腔且只有 3.5 字/秒——**只当应急备胎**。
  minimax   纯 HTTP，未接。
"""
import hashlib
import json
import os
import subprocess
import time
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ffmpeg_path  # noqa: E402

TARGET_RATE = 24000

# 讲解风格指令（走 V3 的 additions.context_texts）。**这是把「念稿」变成「讲课」的开关**——
# 火山 2.0 不支持 <prosody>/<emphasis>，SSML 只有 <break>，语气只能靠这条自然语言指令。
# 想整体换语气就改这里；单课次覆盖用环境变量 VOLC_TTS_INSTRUCTION。
DEFAULT_INSTRUCTION = (
    "像老师在课堂上讲解那样说话："
    "语气自然、亲切，有讲解感，"
    "不要像照着稿子一字一句顺读。"
    "适当带一点思考感和接续感，像是边想边讲，"
    "偶尔可以有一点点自然的迟疑，"
    "讲到重点稍微放慢、加重，"
    "普通内容自然带过，句子之间留自然的停顿和呼吸。"
    "整体清楚流畅，但不要过度丝滑，"
    "也不要刻意结巴或表演感太强。")
# ⚠ 0921 第一次把用户那段要求转成指令时，**把「偶尔一点点自然的重复、迟疑或接续感，
# 让人感觉是在边想边讲」整句漏掉了**——七条要求只传了五条半，漏的正是最难的那条。
# 0922 补回（「重复」没写进去：让 TTS 自造重复词容易变成结巴，
# 真要重复得写在旁白文本里）。
_HERE = os.path.dirname(os.path.abspath(__file__))


def _load_env():
    """三级回退，与 CLAUDE.md §1 的密钥承载约定一致。回退时**显式打印**——
    静默回退会在那个文件被挪走时变成难查的故障（imgclient 踩过，这里照抄它的做法）。"""
    for fn in (os.path.join(_HERE, ".env"), os.path.join(_HERE, "tts.config.json")):
        if not os.path.exists(fn):
            continue
        try:
            if fn.endswith(".json"):
                with open(fn, encoding="utf-8") as f:
                    for k, v in json.load(f).items():
                        os.environ.setdefault(k.upper(), str(v))
            else:
                with open(fn, encoding="utf-8") as f:
                    for ln in f:
                        ln = ln.strip()
                        if ln and not ln.startswith("#") and "=" in ln:
                            k, v = ln.split("=", 1)
                            os.environ.setdefault(k.strip(), v.strip().strip('"'))
        except Exception as e:
            print("  [密钥] 读 %s 失败：%r" % (fn, e))


def _aihubmix_key():
    _load_env()
    k = os.environ.get("AIHUBMIX_API_KEY")
    if k:
        return k
    # 与 imgclient 同一条回退链：picture-writing 的 gitignored config（同账号同一把钥匙）
    root = _HERE
    for _ in range(8):
        root = os.path.dirname(root)
        cand = os.path.join(root, ".claude", "skills", "laojohn-picture-writing",
                            "scripts", "imggen.config.json")
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as f:
                k = (json.load(f) or {}).get("api_key")
            if k:
                print("  [密钥] AIHUBMIX_API_KEY 未设，"
                      "回退取自 imggen.config.json（同账号）")
                return k
    return None


def to_wav(raw_bytes, out_path, src_ext="mp3"):
    """把任意格式的音频字节转成 24kHz 单声道 16bit wav。转换失败就抛，不留半成品。"""
    tmp = out_path + ".raw." + src_ext
    with open(tmp, "wb") as f:
        f.write(raw_bytes)
    try:
        ffmpeg_path.run(["-i", tmp, "-ac", "1", "-ar", str(TARGET_RATE),
                         "-c:a", "pcm_s16le", out_path])
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


class _BaseTTS(object):
    name = "base"

    def __init__(self):
        self.usage = {"calls": 0, "chars": 0, "seconds": 0.0, "cached": 0}
        self.voice = None
        self.speed = 1.0

    def _synth_bytes(self, text, voice, speed):
        raise NotImplementedError

    def synth(self, text, out_path, voice=None, speed=None, cache=True):
        """一句一次。缓存键＝md5(通道+音色+语速+文本)，文本没变就不重复合成——省钱关键。"""
        voice = voice or self.voice
        speed = self.speed if speed is None else speed
        if cache and os.path.exists(out_path):
            try:
                return {"file": out_path, "sec": ffmpeg_path.wav_seconds(out_path),
                        "chars": len(text), "cached": True}
            except Exception:
                pass
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        # 网络抖动重试：一整批两百来句里总会撞上几次 ConnectionReset，
        # 不重试的话那几句就得事后 --only 捞回来。退避 2/5 秒，够躲开瞬时断流。
        raw, ext, last = None, "mp3", None
        for attempt in range(3):
            try:
                raw, ext = self._synth_bytes(text, voice, speed)
                break
            except Exception as e:
                last = e
                if attempt < 2:
                    time.sleep(2 if attempt == 0 else 5)
        if raw is None:
            return {"_error": "%s 合成失败（试了 3 次）：%r" % (self.name, last)}
        if not raw:
            return {"_error": "%s 返回空音频" % self.name}
        try:
            to_wav(raw, out_path, ext)
        except Exception as e:
            return {"_error": "转 wav 失败：%r" % e}
        sec = ffmpeg_path.wav_seconds(out_path)
        self.usage["calls"] += 1
        self.usage["chars"] += len(text)
        self.usage["seconds"] += sec
        return {"file": out_path, "sec": sec, "chars": len(text), "cached": False}

    def voices(self):
        return []


class OpenAICompatTTS(_BaseTTS):
    """AiHubMix / 任何 OpenAI 兼容网关的 /v1/audio/speech。"""
    name = "aihubmix"
    VOICES = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    def __init__(self):
        _BaseTTS.__init__(self)
        self.base = os.environ.get("AIHUBMIX_BASE_URL", "https://aihubmix.com/v1")
        self.model = os.environ.get("TTS_MODEL", "gpt-4o-mini-tts")
        self.voice = os.environ.get("TTS_VOICE", "nova")
        self.key = _aihubmix_key()
        if not self.key:
            raise SystemExit("没有 AIHUBMIX_API_KEY（环境变量 / "
                             "scripts\\.env / imggen.config.json 都没找到）")

    def _synth_bytes(self, text, voice, speed):
        import requests
        body = {"model": self.model, "voice": voice, "input": text,
                "response_format": "mp3", "speed": speed}
        ins = os.environ.get("TTS_INSTRUCTIONS")
        if ins and "4o" in self.model:       # 只有 gpt-4o-*-tts 认 instructions
            body["instructions"] = ins
        r = requests.post(self.base.rstrip("/") + "/audio/speech",
                          headers={"Authorization": "Bearer " + self.key,
                                   "Content-Type": "application/json"},
                          json=body, timeout=180)
        if r.status_code != 200:
            raise RuntimeError("%d: %s" % (r.status_code, r.text[:300]))
        return r.content, "mp3"

    def voices(self):
        return self.VOICES


class VolcTTS(_BaseTTS):
    r"""火山豆包语音合成 **V3 单向流式**。⚠ 与仓内 ARK_API_KEY 不是同一套凭证。

    **为什么是 V3 而不是 V1**（2026-09-21 查文档后改）：官方在 V1 文档里写明
    「不支持"豆包语音合成模型2.0"的音色，如需使用推荐使用 v3 接口」——
    而我们用的 `*_uranus_bigtts` 正是 2.0 音色。V1 实测能出声，但属于不受支持的组合；
    更要紧的是 **2.0 的两样能力只有 V3 给**：

    - `additions.context_texts`：**用自然语言给模型下指令**（文档原话示例：
      「你可以说慢一点吗？」「嗯，你的语气再欢乐一点」）。这是让配音从「念稿」
      变成「讲课」的唯一开关，SSML 做不到——SSML 只有 `<break>`，没有
      `<prosody>`/`<emphasis>`。
    - `additions.section_id`：多次串行合成共享上下文。我们是逐句合成，没有它
      每句都是独立起调、整片语气会碎；给全片一个固定 id，语气才连得住。

    两个踩过的坑：
    1. **`additions` 是 JSON 字符串不是对象**（和 V1 的 `extra_param` 一样）。
       直接传 dict 会收到 `cannot unmarshal object into ... of type string`。
    2. **`X-Api-Resource-Id` 必须是 `seed-tts-2.0`** —— 它同时决定模型版本、
       可用音色和计费商品。传 1.0 就调不到 2.0 的音色。

    响应是逐行 JSON（`{"code":0,"data":"<base64 mp3 片段>"}`），要把所有 data 拼起来。
    """
    name = "volc"
    RESOURCE_ID = "seed-tts-2.0"

    def __init__(self):
        _BaseTTS.__init__(self)
        _load_env()
        self.appid = os.environ.get("VOLC_TTS_APPID")
        self.token = os.environ.get("VOLC_TTS_TOKEN")
        self.voice = os.environ.get("VOLC_TTS_VOICE", "zh_male_yuanboxiaoshu_uranus_bigtts")
        self.base = os.environ.get(
            "VOLC_TTS_BASE", "https://openspeech.bytedance.com/api/v3/tts/unidirectional")
        # 讲解风格指令：整片共用一条，改它就能整体换语气
        self.instruction = os.environ.get("VOLC_TTS_INSTRUCTION", DEFAULT_INSTRUCTION)
        # 会话 id：同一支片子的所有句子共用，模型才会把语气接住
        self.section_id = os.environ.get("VOLC_TTS_SECTION_ID", "")
        # speech_rate 是 [-50,100] 的整数偏移，0 为常速——与 V1 的 speed_ratio 不是一回事
        self.rate = 0
        if not (self.appid and self.token):
            raise SystemExit(
                "火山语音需要 VOLC_TTS_APPID + VOLC_TTS_TOKEN（"
                "语音技术控制台单独开通，"
                "**不是** 方舟的 ARK_API_KEY）")

    def _synth_bytes(self, text, voice, speed):
        import base64
        import uuid
        import requests
        adds = {}
        if self.instruction:
            adds["context_texts"] = [self.instruction]
        if self.section_id:
            adds["section_id"] = self.section_id
        audio = {"format": "mp3", "sample_rate": TARGET_RATE}
        if self.rate:
            audio["speech_rate"] = int(self.rate)
        body = {"user": {"uid": "laojohn-lesson-video"},
                "req_params": {"text": text, "speaker": voice, "audio_params": audio}}
        if adds:
            # ⚠ 必须序列化成字符串，传 dict 会被 Go 端拒绝
            body["req_params"]["additions"] = json.dumps(adds, ensure_ascii=False)
        r = requests.post(self.base, json=body, timeout=180, stream=True,
                          headers={"X-Api-App-Id": self.appid,
                                   "X-Api-Access-Key": self.token,
                                   "X-Api-Resource-Id": self.RESOURCE_ID,
                                   "X-Api-Request-Id": str(uuid.uuid4()),
                                   "Content-Type": "application/json"})
        if r.status_code != 200:
            raise RuntimeError("%d: %s" % (r.status_code, r.text[:300]))
        chunks, err = [], None
        for raw in r.iter_lines():
            if not raw:
                continue
            s = raw.decode("utf-8", "replace")
            if s.startswith("data:"):
                s = s[5:].strip()
            if not s.startswith("{"):
                continue
            try:
                j = json.loads(s)
            except ValueError:
                continue
            code = j.get("code")
            # ⚠ 20000000 不是错误，是**流正常结束**的标志（message 就是 "OK"）。
            # 把它当错误会让每次合成都「失败」，而数据其实已经收齐了。
            if code == 20000000:
                break
            if code not in (0, None):
                err = "%s %s" % (code, j.get("message"))
                break
            d = j.get("data")
            if d:
                chunks.append(base64.b64decode(d))
        if err:
            raise RuntimeError(err[:300])
        if not chunks:
            raise RuntimeError("V3 没返回音频分片")
        return b"".join(chunks), "mp3"


class MinimaxTTS(_BaseTTS):
    name = "minimax"

    def __init__(self):
        _BaseTTS.__init__(self)
        _load_env()
        self.key = os.environ.get("MINIMAX_API_KEY")
        self.group = os.environ.get("MINIMAX_GROUP_ID")
        self.model = os.environ.get("MINIMAX_TTS_MODEL", "speech-01-turbo")
        self.voice = os.environ.get("MINIMAX_TTS_VOICE", "female-tianmei")
        self.base = os.environ.get("MINIMAX_BASE", "https://api.minimax.chat/v1/t2a_v2")
        if not (self.key and self.group):
            raise SystemExit("MiniMax 需要 MINIMAX_API_KEY + MINIMAX_GROUP_ID")

    def _synth_bytes(self, text, voice, speed):
        import requests
        r = requests.post("%s?GroupId=%s" % (self.base, self.group),
                          headers={"Authorization": "Bearer " + self.key,
                                   "Content-Type": "application/json"},
                          json={"model": self.model, "text": text,
                                "stream": False,
                                "voice_setting": {"voice_id": voice, "speed": speed},
                                "audio_setting": {"format": "mp3",
                                                  "sample_rate": TARGET_RATE}},
                          timeout=180)
        j = r.json()
        hexed = ((j.get("data") or {}).get("audio")) or ""
        if not hexed:
            raise RuntimeError(str(j)[:300])
        return bytes.fromhex(hexed), "mp3"


PROVIDERS = {"aihubmix": OpenAICompatTTS, "volc": VolcTTS, "minimax": MinimaxTTS}


def make_tts(provider=None):
    # ⚠ **必须先 _load_env()**：选通道要读 TTS_PROVIDER，而这个值多半写在
    # tts.config.json 里。原先只在各通道 __init__ 里加载配置，等于「先选通道、后读配置」，
    # config 里的 TTS_PROVIDER 永远读不到，于是静默落回默认的 aihubmix。
    # 2026-09-21 踩中：换好火山音色跑全量，188 句全是用 OpenAI 英文音色合成的，
    # 直到看见报错前缀写着 aihubmix 才发现——**失败信息里的通道名是唯一的破绽**。
    _load_env()
    name = (provider or os.environ.get("TTS_PROVIDER") or "aihubmix").lower()
    if name not in PROVIDERS:
        raise SystemExit("未知通道 %s，可选：%s"
                         % (name, "/".join(PROVIDERS)))
    return PROVIDERS[name]()


def key_of(provider, voice, speed, text, extra=""):
    """缓存键。**extra 必须把指令与语速偏移包进去**：
    不包的话，改了讲解指令重跑会全部命中旧缓存，
    听着没变化还以为指令没生效。"""
    h = hashlib.md5(("%s|%s|%s|%s|%s" % (provider, voice, speed, extra, text)).encode("utf-8"))
    return h.hexdigest()[:12]


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="TTS 通道试听")
    ap.add_argument("--provider")
    ap.add_argument("--voice")
    ap.add_argument("--text", default="这一页是第三环节的开头，"
                                      "屏幕上是两段对照的话。"
                                      "你先把两段都读出来，"
                                      "读完不要急着说哪段好，"
                                      "让学生自己挑。")
    ap.add_argument("--out", default="tts_sample.wav")
    a = ap.parse_args()
    t = make_tts(a.provider)
    print("通道 %s，音色 %s，可选 %s"
          % (t.name, a.voice or t.voice, t.voices() or "（见各家文档）"))
    r = t.synth(a.text, a.out, voice=a.voice, cache=False)
    if "_error" in r:
        print("✗ %s" % r["_error"])
        raise SystemExit(1)
    print("✓ %s，%.2f 秒，%d 字 → %.2f 字/秒"
          % (r["file"], r["sec"], r["chars"], r["chars"] / r["sec"]))
