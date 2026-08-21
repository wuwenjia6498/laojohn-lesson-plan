# -*- coding: utf-8 -*-
"""同步习作作文批改辅助工具 · 服务端（单文件 FastAPI）

启动：
    PYTHONUTF8=1 python 作文批改工具/web/server/main.py

四条硬约束（改代码前先看，都是方案里定死的）：
1. 密钥只在服务端。前端任何时候不接触 api_key，也不直连模型网关。
2. 不落盘。学生作文原图与全文一律不写文件、不进日志；只累计匿名计数。
   这条**只管服务端，且不因前端而松动**：前端会把批语与压缩图存进老师手机的
   IndexedDB（批语一直留着供他回看、图只留一天），那是老师自己的设备、不回传，
   服务端不知情也拿不到。服务端这一侧永远是收到即用、用完即弃。
3. 判据的唯一源是详案 → 标准包 JSON。本文件不新增任何判据；渲染逻辑
   importlib 载入 build_prompt.py 的 render_pack()，与 Phase 0 共用一份。
4. 必带频率限制，见 _rate_ok()。防的是密钥被盗刷。

无密钥时自动进 mock 模式：接口照常返回结构完整的假数据，供前端跑通流程。
"""
import base64
import importlib.util
import json
import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent.parent
PACK_DIR = TOOL_ROOT / "标准包"
FRONTEND = HERE.parent / "frontend"


def load_config():
    cfg = {
        "api_key": "",
        "base_url": "https://aihubmix.com/v1",
        "grade_model": "gpt-4o",
        "rate_limit_per_hour": 120,
        "max_image_mb": 8,
        "trust_proxy": False,
    }
    f = HERE / "config.json"
    if f.exists():
        cfg.update({k: v for k, v in json.loads(f.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")})
    if os.environ.get("AIHUBMIX_API_KEY"):
        cfg["api_key"] = os.environ["AIHUBMIX_API_KEY"]
    return cfg


CFG = load_config()
MOCK = not CFG["api_key"]

# 生产环境必须显式声明 LJ_ENV=prod。
# 无密钥时自动进 mock 在本地开发很方便，部署时却是最危险的一处：忘配密钥，
# 服务照常起、接口照常返回**结构完整的假批语**，一声不吭——老师会把假批语
# 当真的转给家长。所以生产模式下无密钥直接拒绝启动。
PROD = os.environ.get("LJ_ENV", "").strip().lower() in ("prod", "production")
if PROD and MOCK:
    raise SystemExit(
        "\n[启动中止] LJ_ENV=prod 但没有配密钥。\n"
        "生产环境不允许 mock——那会给所有老师发结构完整的假批语，而且不报错。\n"
        "请设环境变量 AIHUBMIX_API_KEY，或在 config.json 里填 api_key。\n"
    )


def _load_prompt_module():
    """importlib 载入 build_prompt —— 标准包渲染与判断规则都与 Phase 0 共用一份。"""
    src = TOOL_ROOT / "build_prompt.py"
    spec = importlib.util.spec_from_file_location("build_prompt", src)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BP = _load_prompt_module()
render_pack = BP.render_pack


_CN_NUM = "零一二三四五六"
_LID = re.compile(r"^(\d)([ab])-u(\d+)")            # 如 3a-u1 = 三年级上册第 1 单元
_GRADE_VOL = re.compile(r"^([一二三四五六])年级([上下])册")   # meta 兜底


def grade_of(d):
    """解析出 (年级, 上下册, 单元) 三个数值，用于排序与分组。

    **不要拿文件名排序**——中文数字「第十单元」会排到「第二单元」前面，册次顺序
    也不保证。两课时看不出来，课次一多就乱。lesson_id 本身就带着可排序的数值。
    """
    m = _LID.match(d.get("lesson_id") or "")
    if m:
        return int(m.group(1)), (0 if m.group(2) == "a" else 1), int(m.group(3))
    # lesson_id 命名不合规时退回 meta.grade_volume，仍排不出就丢到最后、不打乱前面
    m = _GRADE_VOL.match((d.get("meta") or {}).get("grade_volume", ""))
    if m:
        return _CN_NUM.index(m.group(1)), (0 if m.group(2) == "上" else 1), 99
    return 99, 9, 999


def grade_label(g, ab):
    if g > 6:
        return "其他"
    return f'{_CN_NUM[g]}{"上" if ab == 0 else "下"}'


def load_packs():
    """按 (年级, 上下册, 单元) 排序装载。顺序即前端选课页的顺序。"""
    ds = []
    for f in PACK_DIR.glob("*.json"):
        d = json.loads(f.read_text(encoding="utf-8"))
        d["_stem"] = f.stem
        ds.append(d)
    ds.sort(key=grade_of)
    return {d["lesson_id"]: d for d in ds}


PACKS = load_packs()


def public_view(d):
    """下发给前端的精简版。加盟商侧不接触详案全文，也不需要完整标准包——
    前端只要够显示「这次判哪三条」「哪些不判」即可，其余留在服务端拼提示词。"""
    m = d["meta"]
    g, ab, unit = grade_of(d)
    return {
        "lesson_id": d["lesson_id"],
        "grade_key": f"{g}{'ab'[ab] if ab < 2 else 'x'}",
        "grade_label": grade_label(g, ab),
        "unit_label": m.get("unit", ""),
        "label": f'{m["grade_volume"]}·{m["unit"]}《{m["topic"]}》',
        "topic": m["topic"],
        "genre": m.get("genre", ""),
        "core_technique": d.get("core_technique", ""),
        "three_checks": [{"no": c["no"], "text": c["text"]} for c in d["three_checks"]],
        "bands": list(d.get("bands", {}).keys()),
        "not_in_scope": (d.get("not_in_scope") or {}).get("items", []),
        "verified": bool(d.get("source", {}).get("verified_by_human")),
    }


_hits = defaultdict(deque)


def _client_ip(request):
    """限额按谁计。

    直连时用 request.client.host。**上了反向代理，那个值会变成反代自己的 IP，
    全站共用一个桶、限额等于失效**，所以要看 X-Forwarded-For。但这个头客户端
    可以随便伪造（伪造一下就能绕过限额），只有确知前面有反代时才可信——故用
    trust_proxy 显式开启，默认关。开启后取最左一跳，那是最初的客户端。
    """
    if CFG.get("trust_proxy"):
        first = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if first:
            return first
    return request.client.host if request.client else "?"


def _rate_ok(ip):
    q = _hits[ip]
    now = time.time()
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= CFG["rate_limit_per_hour"]:
        return False
    q.append(now)
    return True


# 判断规则与点评卡要求都从 build_prompt 取，与 Phase 0 的提示词共用同一份措辞。
# 本文件只负责套上「输出 JSON」这层壳——**不要在这里另写一套判断规则**，
# 两处各写一份必然分叉，且分叉不报错，只会让加盟商手上那份和线上判得不一样。
GRADE_RULES = """你是老约翰同步习作课的批改助手。老师会发来一张学生手写稿纸的照片，你按下面的标准判断，输出 JSON。

## 一、你的边界（先记住）

1. **不批错别字、不批标点、不批卷面。** 你读照片时会不自觉地把写错的字读通顺（学生写“高心”你会读成“高兴”），所以字词与格式这一层一个字也不要提，交给老师当面看稿。
2. **不许编造学生没写的内容。** 凡是你引用的句子，必须与稿纸一字不差；哪里看不清就放进 unclear，不要替他补一个通顺的说法。
3. **不打分、不排名。** band 只是内部参考档位，不出现在给家长的文案里。
4. 三条判据只用下面第二节列出的那三条，不要自己另立标准。

## 二、这次习作的标准

@PACK@

## 三、怎么判

@JUDGING@

## 四、给家长的点评卡（parent_card）

@CARD@

## 五、输出格式

只输出一个 JSON 对象，不要任何解释文字、不要代码块围栏：

{
  "transcript": "整篇作文的逐字转写。按稿纸原样抄，**包括你认为写错的字**，不要顺手改通顺；看不清的字写成 [?]。这一项是给程序核对引用用的，不会给老师看。",
  "student_name": "稿纸姓名栏上的名字；栏空着或看不清就填空字符串",
  "unclear": ["看不清的句子，连同上下文；没有就空数组"],
  "checks": [
    {"no": 1, "verdict": "达成｜部分达成｜未达成｜不适用",
     "evidence": "学生原文里的句子，一字不差", "comment": "一句话说清为什么这样判"}
  ],
  "whole_piece": {
    "completeness": {"verdict": "完整｜基本完整｜没写完｜只开了个头", "note": "一句话说清怎么看出来的"},
    "order":        {"verdict": "清楚｜有跳跃｜乱", "note": "一句话"},
    "flow":         {"verdict": "顺｜个别别扭｜多处不通", "note": "一句话"}
  },
  "highlights": [
    {"quote": "孩子自己写得好的那一句，一字不差", "why": "具体好在哪",
     "kind": "好词｜句式｜修辞｜观察｜真心话"}
  ],
  "band": "三档标准里的档位名之一",
  "focus": "这一篇最值得跟家长说的那一件事，一句话",
  "teacher_note": "建议写进稿纸「老师批改」栏的一句话，30 字以内",
  "showcase": {"suitable": true, "paragraph": "适合当范例念的那一段原文", "point": "用来讲哪一点"},
  "quoted_sentence": "点评卡里引用的那一句，与稿纸一字不差",
  "parent_card": "给家长的点评卡文案，150 字以内"
}

highlights 可以是空数组——这一篇确实没有出彩的地方，就空着，不要硬凑。
whole_piece 三项**不影响 band**，band 只由三条判据定。

**先写 transcript，再判断**。后面所有引用都必须能在 transcript 里**逐字找到**——
程序会拿它们去 transcript 里比对，对不上的会被标成可疑。
"""

ANTI_SAME_TMPL = """
## 六、别跟前面几篇撞句式（重要）

老师这一批要批二三十份，发到同一个家长群。下面是本批已经写过的点评卡开头，你这一篇的开头不许与它们同一个套路（不许同样的起手词、同样的句式）：

{heads}

每一篇都要从这个孩子自己写的内容说起，第一句就落到他的原句上。
"""


def build_messages(pack, image_b64, mime, prev_heads):
    # 用 replace 不用 format：输出格式那段里全是 JSON 大括号，format 会把它们当占位符
    sys_prompt = (GRADE_RULES
                  .replace("@PACK@", render_pack(pack))
                  .replace("@JUDGING@", BP.judging_rules(pack))
                  .replace("@CARD@", BP.parent_card_rules()))
    if prev_heads:
        sys_prompt += ANTI_SAME_TMPL.format(
            heads="\n".join(f"- {h}" for h in prev_heads[-12:]))
    return [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": [
            {"type": "text", "text": "这是一份学生稿纸，按上面的要求批改，只输出 JSON。"},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{image_b64}"}},
        ]},
    ]


DIAGNOSE_RULES = """你是老约翰同步习作课的教研助手。下面是一个班这次习作的批改结果汇总。
请据此写班级共性诊断，供老师准备下一次讲评课。

## 这次习作的标准

@PACK@

## 全班批改结果

每行＝一个学生：姓名｜档位｜三条判据的判定｜整篇三项｜亮点数｜点评卡引用的句子

@RESULTS@

## 怎么看

- **三条判据的账和整篇的账要分开说。** 判据卡住的是「这次课教的没学会」，
  整篇卡住的（没写完、顺序乱、句子不通）是「更底下的地基」——地基的人数多时，
  讲评课先讲地基，本课技法往后放。
- 亮点为零的人数也要报：**一个班多数人写不出一句自己的话，比判据不达标更值得警惕。**
- 讲评课念谁的，优先挑「有亮点」的，别只挑档位高的。

## 输出

只输出一个 JSON 对象，不要解释文字、不要代码块围栏：

{
  "overall": "两三句话说清这个班这次整体怎么样，要有具体数字",
  "whole_piece_summary": "整篇层面的账：多少人没写完、多少人顺序有跳、多少人句子不通、多少人一个亮点也没有；各点一两个名字",
  "common_problems": [
    {"problem": "共性问题", "layer": "判据｜整篇",
     "how_many": "多少人", "why": "根子上是哪一步没做到",
     "how_to_fix": "讲评课上怎么讲这一点，要具体到一个可操作的活动"}
  ],
  "showcase_plan": [{"name": "学生名", "read_what": "念哪一段", "teach_what": "用来讲哪一点"}],
  "next_lesson_slots": "填进详案末尾「习作讲评指导环节」空槽的话，直接可抄"
}
"""


# max_tokens 要给足：gemini-2.5-flash 一类 thinking 模型的思考 token 也计入 completion，
# 0820 实测批一篇正文 1390 token、思考另占 1785，3000 就会从 JSON 中间断掉。
async def call_model(messages, max_tokens=8000):
    url = CFG["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CFG["grade_model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    headers = {"Authorization": f'Bearer {CFG["api_key"]}',
               "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=180) as cli:
        r = await cli.post(url, json=payload, headers=headers)
        if r.status_code != 200:
            raise HTTPException(502, f"模型网关返回 {r.status_code}：{r.text[:300]}")
        data = r.json()
    ch = data["choices"][0]
    # 截断了要明说。0820 实测：加了 whole_piece/highlights/focus 之后 1600 不够，
    # JSON 从中间断掉，报出来却是「没有返回可解析的 JSON」，会让人往提示词上找错。
    if ch.get("finish_reason") == "length":
        raise HTTPException(502, "模型输出被截断（max_tokens 不够），JSON 不完整。"
                                 "调大 call_model 的 max_tokens 再试。")
    return ch["message"]["content"]


def parse_json(text):
    """模型偶尔会裹代码块围栏或加前言，剥掉再解析。"""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t, flags=re.S)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, flags=re.S)
        if not m:
            raise HTTPException(502, "模型没有返回可解析的 JSON：" + t[:300])
        return json.loads(m.group(0))


# ---------------------------------------------------------------------------
# 引用校正：让「引用一字不差」由程序保证，而不是靠模型自觉
#
# 0820 实测：gemini-2.5-flash 与 gpt-4o **都会**在复述时不自觉改写原句——漏字
# （「可是过了一会儿」→「可是一会儿」）、加字（「说：」→「他说：」）、把全角逗号
# 写成半角、用省略号把相隔很远的两处拼成一句。提示词按不住，这是模型的复述本能。
#
# 解法：要模型先输出整篇 transcript，再拿它当基准，把每一处引用**对回原文**：
# 逐字找得到就原样留；去标点后找得到，就用 transcript 里的真实片段替换掉模型写的
# 版本；仍找不到的标 suspect，前端显红让老师留意。
#
# transcript 只在服务端用于校验，**不下发给前端**——老师手上有原稿，不需要看打字版。
# ---------------------------------------------------------------------------

_PUNCT = re.compile(r"[\s，。、；：？！“”‘’（）《》…—·,.;:?!\"'()\[\]]")


def _bare(s):
    return _PUNCT.sub("", str(s or ""))


def _locate(quote, transcript):
    """在 transcript 里定位这段引用，返回原文里的真实片段；定位不到返回 None。"""
    q = str(quote or "").strip()
    if not q:
        return ""
    if q in transcript:
        return q
    bq, bt = _bare(q), _bare(transcript)
    if not bq or bq not in bt:
        return None
    # 去标点后能对上：把 bare 下标映射回原串下标，取回带标点的真实片段
    idx, pos = [], 0
    for ch in transcript:
        if not _PUNCT.match(ch):
            idx.append(pos)
        pos += 1
    st = bt.index(bq)
    return transcript[idx[st]: idx[st + len(bq) - 1] + 1]


def _locate_fuzzy(quote, transcript, cover=0.85, span=1.4):
    """漏字改字的救场：拿匹配块把引用对回原文。

    模型最常见的错法不是凭空编，而是复述时漏掉一两个字（「可是过了一会儿」→
    「可是一会儿」）、多一个字（「说：」→「他说：」）。这种去标点也对不上，
    但**绝大多数字仍按顺序对得上**，取首尾匹配块之间那一段原文即可。

    两个门槛缺一不可：
    - `cover` 总匹配率——大部分字都要对得上，防止把不相干的句子硬「校正」成原文；
    - `span` 区间长度——**省略号跨接就是靠这条拒掉的**：把相隔很远的两处拼成
      一句时，首尾块之间会横跨大段原文，区间远长于引用本身。
    """
    import difflib
    bq, bt = _bare(quote), _bare(transcript)
    if len(bq) < 6 or not bt:
        return None
    blocks = [b for b in difflib.SequenceMatcher(None, bt, bq, autojunk=False)
              .get_matching_blocks() if b.size > 0]
    if not blocks or sum(b.size for b in blocks) < len(bq) * cover:
        return None
    a, b = blocks[0].a, blocks[-1].a + blocks[-1].size
    if (b - a) > len(bq) * span:
        return None
    idx, pos = [], 0
    for ch in transcript:
        if not _PUNCT.match(ch):
            idx.append(pos)
        pos += 1
    return transcript[idx[a]: idx[b - 1] + 1]


def fix_quotes(d):
    """就地校正 d 里所有引用字段。返回 (校正数, 可疑数)。"""
    t = d.get("transcript") or ""
    fixed = suspect = 0
    if not t:
        return 0, 0

    def one(obj, key):
        nonlocal fixed, suspect
        v = obj.get(key)
        if not v:
            return
        real = _locate(v, t) or _locate_fuzzy(v, t)
        if real is None:
            obj[key + "_suspect"] = True
            suspect += 1
        elif real != v:
            obj[key] = real
            fixed += 1

    for c in d.get("checks") or []:
        one(c, "evidence")
    for h in d.get("highlights") or []:
        one(h, "quote")
    one(d, "quoted_sentence")
    sc = d.get("showcase") or {}
    if sc:
        one(sc, "paragraph")
    return fixed, suspect



_MOCK_N = {"i": 0}


def mock_grade(pack):
    """假数据也要走真结构：档位轮换、依赖判据会真的记「不适用」、点评卡开头各不相同、
    整篇三项与亮点数量都轮换——否则前端的依赖显示、空亮点分支、同质化提示全测不出来。"""
    _MOCK_N["i"] += 1
    i = _MOCK_N["i"]
    names = ["林小满", "周予安", "陈知遥", "何以晴", "许南舟", "叶昭"]
    opens = ["孩子写的这一句我读了两遍——", "这一篇里最打眼的是这句——",
             "先说他写得最像样的地方——", "有一处细节看得出他真观察了——"]
    anchors = pack.get("model_essay_anchor_sentences") or ["（示例句）"]
    checks = []
    for c in pack["three_checks"]:
        v = ["达成", "部分达成", "未达成"][(i + c["no"]) % 3]
        dep = c.get("depends_on")
        if dep and any(x["no"] == dep and x["verdict"] == "未达成" for x in checks):
            v = "不适用"
        checks.append({"no": c["no"], "verdict": v,
                       "evidence": anchors[c["no"] % len(anchors)],
                       "comment": f'（mock）第{c["no"]}条「{c["text"]}」的判断说明。'})
    bands = list(pack.get("bands", {}).keys()) or ["基础过关"]
    q = anchors[i % len(anchors)]

    whole = {
        "completeness": {"verdict": ["完整", "基本完整", "没写完", "只开了个头"][i % 4],
                         "evidence": q, "note": "（mock）完整性说明。"},
        "order": {"verdict": ["清楚", "有跳跃", "乱"][i % 3],
                  "evidence": q, "note": "（mock）顺序说明。"},
        "flow": {"verdict": ["顺", "个别别扭", "多处不通"][(i + 1) % 3],
                 "evidence": q, "note": "（mock）通顺度说明。"},
    }
    # 每三篇留一篇没有亮点：硬凑亮点是假话，前端与提示词都得能处理空的情况
    highlights = [] if i % 3 == 2 else [
        {"quote": anchors[k % len(anchors)],
         "why": "（mock）这一处好在写出了当时的样子，不是下结论。",
         "kind": ["观察", "句式", "好词", "真心话"][(i + k) % 4]}
        for k in range(1 + i % 2)
    ]

    return {
        "student_name": names[i % len(names)],
        "unclear": [] if i % 4 else ["（mock）这一句有两个字看不清"],
        "checks": checks,
        "whole_piece": whole,
        "highlights": highlights,
        "band": bands[i % len(bands)],
        "focus": "（mock）这一篇最值得说的是他写的那个动作细节。",
        "teacher_note": "（mock）这处细节写得实在，再多写一件事就更好了。",
        "showcase": {"suitable": i % 3 == 0, "paragraph": q, "point": "写具体"},
        "quoted_sentence": q,
        "parent_card": (f"（mock 假数据）{opens[i % len(opens)]}“{q}”。"
                        "这一句好在没有停在结论上，而是把当时的样子写了出来，"
                        "正是这次课上练的那一招。下次可以试着再为这个地方补一件小事，"
                        "人物就更立得住了。"),
        "_mock": True,
    }


def mock_diagnose(pack, results):
    n = len(results)
    unfinished = sum(1 for r in results
                     if (r.get("whole_piece") or {}).get("completeness", {})
                        .get("verdict") in ("没写完", "只开了个头"))
    nohl = sum(1 for r in results if not (r.get("highlights") or []))
    return {
        "overall": f"（mock 假数据）全班 {n} 份，主特点抓住的过半，卡在「写具体」这一步的偏多。",
        "whole_piece_summary": (f"（mock）{unfinished} 人没写完或只开了个头，"
                                f"{nohl} 人一句自己的话也没写出来——地基这一层比本课技法更急。"),
        "common_problems": [
            {"problem": "并列罗列多个特点，没有主特点", "layer": "判据",
             "how_many": f"约 {max(1, n // 3)} 人",
             "why": "构思表填了五行，就照着五行各写一句",
             "how_to_fix": "讲评课上拿两篇对着念，让学生自己听出哪一篇有主角"},
            {"problem": "写到一半停住", "layer": "整篇",
             "how_many": f"{unfinished} 人",
             "why": "开头铺得太长，写到主体没时间了",
             "how_to_fix": "当堂限时三分钟只写结尾，练「先把话说完」"},
        ],
        "showcase_plan": [{"name": r.get("student_name", ""),
                           "read_what": (r.get("highlights") or [{}])[0].get("quote")
                                        or r.get("quoted_sentence", ""),
                           "teach_what": "写具体"}
                          for r in results if (r.get("highlights") or [])][:3],
        "next_lesson_slots": "（mock）讲评课空槽的话填这里。",
        "_mock": True,
    }


app = FastAPI(title="老约翰 · 同步习作批改助手")


@app.get("/api/health")
def health():
    return {"ok": True, "mock": MOCK, "model": CFG["grade_model"],
            "lessons": len(PACKS), "rate_limit_per_hour": CFG["rate_limit_per_hour"]}


@app.get("/api/lessons")
def lessons():
    return [public_view(d) for d in PACKS.values()]


@app.get("/api/lessons/{lesson_id}")
def lesson(lesson_id: str):
    d = PACKS.get(lesson_id)
    if not d:
        raise HTTPException(404, "没有这一课的标准包")
    return public_view(d)


@app.post("/api/grade")
async def grade(request: Request,
                lesson_id: str = Form(...),
                prev_heads: str = Form("[]"),
                image: UploadFile = File(...)):
    pack = PACKS.get(lesson_id)
    if not pack:
        raise HTTPException(404, "没有这一课的标准包")
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(429, "这一小时批得太多了，歇一会儿再来（防盗刷用的限额）")

    raw = await image.read()
    if len(raw) > CFG["max_image_mb"] * 1024 * 1024:
        raise HTTPException(413, f'图片超过 {CFG["max_image_mb"]}MB，请在手机上压一压再传')

    if MOCK:
        return mock_grade(pack)

    heads = json.loads(prev_heads or "[]")
    b64 = base64.b64encode(raw).decode()
    msgs = build_messages(pack, b64, image.content_type or "image/jpeg", heads)
    out = parse_json(await call_model(msgs))

    # 引用一字不差这条不能靠模型自觉：拿它自己的 transcript 把每处引用对回原文，
    # 对不上的标 suspect 交给老师留意（见 fix_quotes 的注释）。
    fixed, suspect = fix_quotes(out)
    out["quote_check"] = {"fixed": fixed, "suspect": suspect}
    # transcript 只用于校验，不下发——老师手上有原稿，不需要看打字版
    out.pop("transcript", None)

    # 原图与 base64 到此为止：不落盘、不进日志
    return out


@app.post("/api/diagnose")
async def diagnose(request: Request, body: dict):
    pack = PACKS.get(body.get("lesson_id"))
    if not pack:
        raise HTTPException(404, "没有这一课的标准包")
    # 这一条也是真实模型调用（max_tokens 6000），跟 /api/grade 共用同一个桶。
    # 原先只有 grade 挂了限额，diagnose 完全裸奔，是个盗刷缺口。
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(429, "这一小时用得太多了，歇一会儿再来（防盗刷用的限额）")
    results = body.get("results") or []
    if not results:
        raise HTTPException(400, "还没有批改结果")
    if MOCK:
        return mock_diagnose(pack, results)

    lines = []
    for r in results:
        cs = "；".join(f'{c["no"]}{c["verdict"]}' for c in r.get("checks", []))
        w = r.get("whole_piece") or {}
        wp = "／".join(f'{k}:{(w.get(v) or {}).get("verdict", "?")}'
                      for k, v in (("完整", "completeness"), ("顺序", "order"), ("通顺", "flow")))
        lines.append(f'- {r.get("student_name") or "（无名）"}｜{r.get("band", "")}'
                     f'｜{cs}｜{wp}｜亮点{len(r.get("highlights") or [])}'
                     f'｜引用：{r.get("quoted_sentence", "")}')
    prompt = (DIAGNOSE_RULES
              .replace("@PACK@", render_pack(pack))
              .replace("@RESULTS@", "\n".join(lines)))
    return parse_json(await call_model([{"role": "user", "content": prompt}], max_tokens=6000))


@app.exception_handler(HTTPException)
async def http_err(request, exc):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("标准包 " + str(len(PACKS)) + " 课：" +
          "、".join(p["meta"]["topic"] for p in PACKS.values()))
    print("模式：" + ("MOCK（未配密钥，返回假数据）"
                     if MOCK else "真实调用 " + CFG["grade_model"]))
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
