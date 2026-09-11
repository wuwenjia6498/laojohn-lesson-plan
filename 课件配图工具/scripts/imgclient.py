# -*- coding: utf-8 -*-
"""生图/判读客户端 · 双通道可插拔（豆包 Seedream ／ AiHubMix 上的 Gemini）。

为什么保留两条通道而不是换掉：**规则库里的每一条都绑定在某个通道上**。
T1–T5 五项、以及整课跑批查出的 A/B 两条，全部是在豆包上测出来的；换 Gemini
就得逐条重验——这正是 PRD §7 当初说「Gemini 的经验迁到豆包必须重验」的同一个道理，
反过来一样成立。留着两条通道，`--provider` 一换就能跑同一套验证做对照。

选通道：环境变量 `IMAGE_PROVIDER=doubao|gemini`（缺省 gemini），或调用方显式传参。

密钥纪律：只从环境变量 / `.env` 读，任何脚本不得写死。
  · 豆包：`ARK_API_KEY`
  · Gemini：`AIHUBMIX_API_KEY`；本仓早有此约定（见 CLAUDE.md §1「密钥承载约定」），
    故若本工具的 .env 里没有，会**显式提示着**回退到
    `.claude/skills/laojohn-picture-writing/scripts/imggen.config.json`（同一个账号的 key，
    停用归档后在 `.claude/skills-parked/` 下，两处都会找；
    已 gitignored）。回退时一定打印来源——静默回退会在那个文件被挪走时变成难查的故障。
"""
import base64
import io
import json
import mimetypes
import os
import pathlib
import time

import requests

ROOT = pathlib.Path(__file__).resolve().parents[1]
REPO = ROOT.parent
# 2026-09-10 起看图写话 skill 停用归档到 .claude/skills-parked/（见 CLAUDE.md §3），两处都试、取先存在的
_PW_CANDIDATES = [REPO / f".claude/{d}/laojohn-picture-writing/scripts/imggen.config.json"
                  for d in ("skills", "skills-parked")]
PW_CONFIG = next((c for c in _PW_CANDIDATES if c.exists()), _PW_CANDIDATES[0])


def load_dotenv(path=None):
    p = pathlib.Path(path) if path else ROOT / ".env"
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def _aihubmix_key(verbose=True):
    k = os.environ.get("AIHUBMIX_API_KEY", "").strip()
    if k:
        return k
    if PW_CONFIG.exists():
        try:
            k = json.loads(PW_CONFIG.read_text(encoding="utf-8")).get("api_key", "").strip()
        except Exception:
            k = ""
        if k:
            if verbose:
                print(f"  [密钥] AIHUBMIX_API_KEY 未设，回退取自 {PW_CONFIG.name}（同账号）")
            return k
    raise SystemExit("缺少 AIHUBMIX_API_KEY（放进 课件配图工具/.env 或环境变量），拒绝启动。")


class _Base:
    """两条通道的公共部分：用量账、落盘、判读（都走 OpenAI 兼容 chat）。"""

    def __init__(self):
        self.usage = {"calls": 0, "images": 0, "output_tokens": 0,
                      "vision_calls": 0, "vision_tokens": 0}

    @staticmethod
    def save(data, dest):
        """落盘并统一成 JPEG。

        ⚠ 两条通道返回的格式不一样：方舟给 JPEG，Gemini 给 PNG（单张 6MB）。
        全流程的路径假设都是 `.jpg`，若把 PNG 原样写进 .jpg，扩展名就在说谎——
        文件能看，但凡按后缀判类型的地方都会踩空。故在此统一转码，把差异挡在客户端里。
        """
        from PIL import Image
        dest = pathlib.Path(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        if data[:3] == bytes((0xFF, 0xD8, 0xFF)):   # 已是 JPEG
            dest.write_bytes(data)
        else:
            Image.open(io.BytesIO(data)).convert("RGB").save(dest, "JPEG", quality=92)
        return dest

    @staticmethod
    def _b64(path, max_side=None):
        from PIL import Image
        p = pathlib.Path(path)
        if not max_side:
            mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
            return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()
        im = Image.open(p).convert("RGB")
        if max(im.size) > max_side:
            r = max_side / max(im.size)
            im = im.resize((int(im.width * r), int(im.height * r)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=88)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    def judge(self, image_paths, question, timeout=400, retries=2):
        """多模态判读（判读失败绝不能被上层当成「判定不通过」，见 judge_failed 闸门）。"""
        content = [{"type": "image_url", "image_url": {"url": self._b64(p, 1024)}}
                   for p in image_paths]
        content.append({"type": "text", "text": question})
        body = {"model": self.vision_model, "temperature": 0,
                "messages": [{"role": "user", "content": content}]}
        body.update(self.vision_extra)
        for i in range(retries):
            try:
                r = requests.post(f"{self.chat_base}/chat/completions",
                                  headers={"Authorization": f"Bearer {self.chat_key}",
                                           "Content-Type": "application/json"},
                                  json=body, timeout=timeout)
                break
            except requests.exceptions.RequestException as e:
                if i == retries - 1:
                    return {"_error": f"判读请求失败：{e!r}"}
                time.sleep(3)
        self.usage["vision_calls"] += 1
        if r.status_code != 200:
            return {"_error": f"{r.status_code}: {r.text[:300]}"}
        j = r.json()
        self.usage["vision_tokens"] += (j.get("usage") or {}).get("total_tokens", 0)
        txt = j["choices"][0]["message"]["content"].strip()
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            txt = txt[4:] if txt.startswith("json") else txt
        try:
            return json.loads(txt)
        except Exception:
            pass
        try:
            return json.loads(_escape_raw_newlines(txt))
        except Exception:
            return {"_raw": txt}

    def chat(self, prompt, system=None, model=None, timeout=600, retries=2,
             max_tokens=16000, as_json=True):
        """纯文本对话通道——给拆解器用，与多模态 judge 分开。

        故意不复用 judge：judge 每次都塞图、且默认 temperature=0 配短答；
        拆解要吐一份上千行的 JSON，两者的超时、token 上限、失败语义都不一样。
        失败同样只返回 _error / _raw，绝不自己编一个「空结果」蒙混过去——
        本项目已两次栽在「未知被当成否定」上（403 全挂、JSON 里的真实换行）。
        """
        msgs = ([{"role": "system", "content": system}] if system else []) +                [{"role": "user", "content": prompt}]
        body = {"model": model or self.text_model, "temperature": 0.2,
                "messages": msgs, "max_tokens": max_tokens}
        if as_json:
            body["response_format"] = {"type": "json_object"}
        for i in range(retries):
            try:
                r = requests.post(f"{self.chat_base}/chat/completions",
                                  headers={"Authorization": f"Bearer {self.chat_key}",
                                           "Content-Type": "application/json"},
                                  json=body, timeout=timeout)
                break
            except requests.exceptions.RequestException as e:
                if i == retries - 1:
                    return {"_error": f"对话请求失败：{e!r}"}
                time.sleep(3)
        self.usage.setdefault("text_calls", 0)
        self.usage["text_calls"] += 1
        if r.status_code != 200:
            return {"_error": f"{r.status_code}: {r.text[:400]}"}
        j = r.json()
        u = j.get("usage") or {}
        self.usage.setdefault("text_tokens", 0)
        self.usage["text_tokens"] += u.get("total_tokens", 0)
        ch = (j.get("choices") or [{}])[0]
        # 截断标志各家网关叫法不一：OpenAI 是 length，Anthropic 是 max_tokens，
        # 经 AiHubMix 转发时还可能是别的。只认一个就会漏 —— 实测漏过一次：
        # 输出在第二条规格处断掉，finish_reason 不是 length，于是没报截断、
        # 落进 _raw 当成「解析失败」，指向完全错的方向。
        fr = str(ch.get("finish_reason") or ch.get("stop_reason") or "")
        if fr in ("length", "max_tokens", "MAX_TOKENS", "content_filter"):
            return {"_error": f"输出被截断（finish_reason={fr}，max_tokens={max_tokens}），"
                              f"结果不完整——调高上限或拆批重跑，别拿半截 JSON 往下走"}
        txt = (ch.get("message") or {}).get("content", "").strip()
        if not as_json:
            return {"text": txt}
        if txt.startswith("```"):
            txt = txt.split("```")[1]
            txt = txt[4:] if txt.startswith("json") else txt
        try:
            return json.loads(txt)
        except Exception:
            pass
        try:
            return json.loads(_escape_raw_newlines(txt))
        except Exception:
            return {"_raw": txt}


def _escape_raw_newlines(txt):
    """把 JSON 字符串字面量内部的真实换行/制表符转义掉，字符串外的原样保留。

    ⚠ 别删：模型逐字抄两行书封时会在字符串里打真实换行，JSON 非法 → 落进 _raw →
    上层 .get() 取不到值就走进否定分支，实测把「书名逐字全对」的图算成了有错字。
    """
    BS = chr(92)
    MAP = {chr(10): BS + "n", chr(13): BS + "r", chr(9): BS + "t"}
    out, in_str, esc = [], False, False
    for ch in txt:
        if esc:
            out.append(ch); esc = False; continue
        if in_str and ch == BS:
            out.append(ch); esc = True; continue
        if ch == chr(34):
            in_str = not in_str; out.append(ch); continue
        if in_str and ch in MAP:
            out.append(MAP[ch]); continue
        out.append(ch)
    return "".join(out)


class DoubaoClient(_Base):
    """火山方舟 Seedream。文生图/参考生图/图像编辑同一入口，带 image 即为参考或编辑。"""

    name = "doubao"
    # 画幅→像素。方舟要具体像素；不给会自作主张挑一个比例
    RATIO = {"1:1": "2048x2048", "3:4": "1728x2304", "4:3": "2304x1728", "16:9": "2304x1296"}

    def __init__(self):
        super().__init__()
        load_dotenv()
        self.key = os.environ.get("ARK_API_KEY", "").strip()
        if not self.key:
            raise SystemExit("缺少 ARK_API_KEY，拒绝启动。")
        self.base = os.environ.get("ARK_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3").rstrip("/")
        self.model = os.environ.get("ARK_IMAGE_MODEL", "doubao-seedream-5-0-pro-260628")
        self.vision_model = os.environ.get("ARK_VISION_MODEL", "doubao-seed-2-1-pro-260628")
        self.text_model = os.environ.get("ARK_TEXT_MODEL", self.vision_model)
        self.chat_base, self.chat_key = self.base, self.key
        # 判读一律关思考：定性勾验开思考只换来十倍耗时（实测 180s 超时过）
        self.vision_extra = {"thinking": {"type": "disabled"}}

    def generate(self, prompt, ratio="1:1", images=None, seed=None, timeout=300):
        body = {"model": self.model, "prompt": prompt, "size": self.RATIO[ratio],
                "response_format": "url", "watermark": False}
        if seed is not None:
            body["seed"] = seed
        if images:
            refs = [self._as_ref(x) for x in images]
            body["image"] = refs if len(refs) > 1 else refs[0]
        for i in range(2):
            try:
                r = requests.post(f"{self.base}/images/generations",
                                  headers={"Authorization": f"Bearer {self.key}",
                                           "Content-Type": "application/json"},
                                  json=body, timeout=timeout)
                break
            except requests.exceptions.RequestException as e:
                if i == 1:
                    raise RuntimeError(f"生图请求失败：{e!r}")
                time.sleep(5)
        self.usage["calls"] += 1
        if r.status_code != 200:
            raise RuntimeError(f"生图失败 {r.status_code}: {r.text[:500]}")
        j = r.json()
        u = j.get("usage") or {}
        self.usage["images"] += u.get("generated_images", 0)
        self.usage["output_tokens"] += u.get("output_tokens", 0)
        import urllib.request
        with urllib.request.urlopen(j["data"][0]["url"], timeout=120) as resp:
            return resp.read()

    def _as_ref(self, x):
        s = str(x)
        if s.startswith(("http://", "https://", "data:")):
            return s
        return self._b64(s)


class GeminiClient(_Base):
    """AiHubMix 上的 Gemini 生图（Nano Banana 系）。

    ⚠ 与豆包不是同一种调用：gemini-*-image-preview **没有 images.generate**，
    走原生 google-genai 客户端 + `base_url=<gemini_base_url>`，画幅用
    `aspect_ratio`(1:1/3:4/4:3…) + `image_size`(1K/2K/4K)，不是像素串。
    这条是本仓 laojohn-picture-writing 已跑通的口径，照搬、不另造。
    参考图作为 `types.Part.from_bytes` 与 prompt 一起塞进 contents。
    """

    name = "gemini"
    RATIO = {"1:1": "1:1", "3:4": "3:4", "4:3": "4:3", "16:9": "16:9"}
    _seed_warned = False

    def __init__(self):
        super().__init__()
        load_dotenv()
        self.key = _aihubmix_key()
        self.gemini_base = os.environ.get("AIHUBMIX_GEMINI_BASE", "https://aihubmix.com/gemini")
        self.chat_base = os.environ.get("AIHUBMIX_BASE_URL", "https://aihubmix.com/v1").rstrip("/")
        self.chat_key = self.key
        self.model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
        self.vision_model = os.environ.get("AIHUBMIX_VISION_MODEL", "gpt-4o")
        # 拆解是长文理解任务，与判图分开配：判图看的是一张图，拆解要通读详案
        self.text_model = os.environ.get("AIHUBMIX_TEXT_MODEL", "gpt-4o")
        self.image_size = os.environ.get("GEMINI_IMAGE_SIZE", "2K")
        self.vision_extra = {}          # AiHubMix 是 OpenAI 兼容，别把方舟的 thinking 传过来
        self._client = None

    def _c(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=self.key,
                                        http_options={"base_url": self.gemini_base})
        return self._client

    def generate(self, prompt, ratio="1:1", images=None, seed=None, timeout=300):
        from google.genai import types
        parts = []
        for x in (images or []):
            p = pathlib.Path(x)
            mime = mimetypes.guess_type(p.name)[0] or "image/jpeg"
            parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))
        contents = ([*parts, prompt] if parts else prompt)
        last = None
        for i in range(2):
            try:
                cfg = dict(response_modalities=["TEXT", "IMAGE"],
                           image_config=types.ImageConfig(
                               aspect_ratio=self.RATIO[ratio], image_size=self.image_size))
                if seed is not None:
                    cfg["seed"] = seed
                try:
                    conf = types.GenerateContentConfig(**cfg)
                except TypeError:
                    # SDK 不认 seed 就明说，别把参数悄悄吃掉——静默忽略参数是最难查的一类故障
                    if not GeminiClient._seed_warned:
                        print("  [提示] 本版 google-genai 不支持 seed，本通道的样本为独立随机抽样")
                        GeminiClient._seed_warned = True
                    cfg.pop("seed", None)
                    conf = types.GenerateContentConfig(**cfg)
                resp = self._c().models.generate_content(
                    model=self.model, contents=contents, config=conf)
                break
            except Exception as e:
                last = e
                if i == 1:
                    raise RuntimeError(f"生图请求失败：{last!r}")
                time.sleep(5)
        self.usage["calls"] += 1
        data = _gemini_bytes(resp)
        if not data:
            raise RuntimeError(f"Gemini 返回里没有图片（可能被安全策略拦下）：{str(resp)[:300]}")
        self.usage["images"] += 1
        um = getattr(resp, "usage_metadata", None)
        if um is not None:
            self.usage["output_tokens"] += getattr(um, "total_token_count", 0) or 0
        return data


def _gemini_bytes(resp):
    """从 genai 响应里取第一张图字节，兼容多种 SDK 形态。"""
    cands = getattr(resp, "candidates", None) or []
    parts = []
    if cands:
        parts = getattr(getattr(cands[0], "content", None), "parts", None) or []
    if not parts:
        parts = getattr(resp, "parts", None) or []
    for part in parts:
        inline = getattr(part, "inline_data", None)
        if inline is not None:
            d = getattr(inline, "data", None)
            if isinstance(d, (bytes, bytearray)):
                return bytes(d)
            if isinstance(d, str):
                return base64.b64decode(d)
    return None


PROVIDERS = {"doubao": DoubaoClient, "gemini": GeminiClient}


def make_client(provider=None):
    load_dotenv()
    name = (provider or os.environ.get("IMAGE_PROVIDER") or "gemini").lower()
    if name not in PROVIDERS:
        raise SystemExit(f"未知通道 {name}，可选：{'/'.join(PROVIDERS)}")
    return PROVIDERS[name]()
