# -*- coding: utf-8 -*-
"""同步习作作文批改辅助工具 · 服务端（单文件 FastAPI）

启动：
    PYTHONUTF8=1 python 作文批改工具/web/server/main.py

四条硬约束（改代码前先看，都是方案里定死的）：
1. 密钥只在服务端。前端任何时候不接触 api_key，也不直连模型网关。
2. 不落盘。学生作文原图与全文一律不写文件、不进日志；只累计匿名计数。
   这条**只管服务端，且不因前端而松动**：前端会把批语与压缩图存进老师手机的
   IndexedDB（批语一直留着供他回看；图在一份批完时即丢，没批完的才留一天），
   那是老师自己的设备、不回传，
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
# 部署包目录。Vercel 的部署根是 web/，够不到上一级的中文源目录（标准包、
# build_prompt.py），所以由 build_deploy.py 预先把两者收进这里、全 ASCII 命名。
# 本地跑时这些文件可能不存在，一律回退读中文源——本地行为不变。
# ⚠ 不要叫 api/：Vercel 把 /api 当成「一个文件一个端点」的旧式文件路由目录。
BUNDLE = HERE.parent / "_bundle"


def load_config():
    cfg = {
        "api_key": "",
        "base_url": "https://aihubmix.com/v1",
        "grade_model": "gpt-4o",
        "rate_limit_per_hour": 120,
        "max_image_mb": 4,   # 别调过 4：Vercel 函数请求体硬限 4.5MB（含 multipart
                             # 开销），超过在平台层就 413，我们的提示轮不到。
                             # 前端已压到长边 1600、约 300KB，这个值只是兜底。
        "trust_proxy": False,
    }
    f = HERE / "config.json"
    if f.exists():
        cfg.update({k: v for k, v in json.loads(f.read_text(encoding="utf-8")).items()
                    if not k.startswith("_")})
    if os.environ.get("AIHUBMIX_API_KEY"):
        cfg["api_key"] = os.environ["AIHUBMIX_API_KEY"]
    # 线上不放 config.json（密钥只走环境变量），所以 trust_proxy 也得有个环境变量
    # 入口，否则托管平台上它永远是 false。⚠ 只在确知前面有反代时才开，见 _client_ip。
    if os.environ.get("LJ_TRUST_PROXY", "").strip().lower() in ("1", "true", "yes"):
        cfg["trust_proxy"] = True
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
    if not src.exists():                      # 线上：见 BUNDLE 注释
        src = BUNDLE / "_build_prompt.py"
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


def sort_key(d):
    """选课页排序键 ＝ grade_of 三元组 ＋ 版本序。

    同一年级同一单元并存新旧两套教材题目时（2026 秋四上·二《小小“动物园”》→
    《我的家人》是首例），grade_of 三元组完全相同，`ds.sort` 稳定排序就退化成
    glob 顺序（本地）或 _packs.json 的数组顺序（线上）——**旧题可能排在现行题
    前面，且不报错**。故补第四位：现行与无标注的排前，legacy 排后。
    """
    return grade_of(d) + (1 if (d.get("edition") or {}).get("status") == "legacy" else 0,)


def grade_label(g, ab):
    if g > 6:
        return "其他"
    return f'{_CN_NUM[g]}{"上" if ab == 0 else "下"}'


def load_packs():
    """按 (年级, 上下册, 单元) 排序装载。顺序即前端选课页的顺序。"""
    ds = []
    if PACK_DIR.is_dir():
        for f in PACK_DIR.glob("*.json"):
            d = json.loads(f.read_text(encoding="utf-8"))
            d["_stem"] = f.stem
            ds.append(d)
    else:                                     # 线上：见 BUNDLE 注释
        ds = json.loads((BUNDLE / "_packs.json").read_text(encoding="utf-8"))
    ds.sort(key=sort_key)
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
        # 版本标注 {status, note}：同一年级同一单元并存新旧两套教材题目时才有
        # （2026 秋四上·二换题后首例）。**只进选课页的徽章**——不进 label、不进
        # topic，因为那两个会印到发给家长的点评卡上。绝大多数课次没有此字段，
        # 下发 None、前端不渲染徽章。status 供排序（见 sort_key），note 供显示，
        # 两者解耦：改文案不影响排序。
        "edition": d.get("edition") or None,
        "genre": m.get("genre", ""),
        "core_technique": d.get("core_technique", ""),
        # display_text＝界面显示的规范维度名；text 是学生当堂听过的原话（逐字铁律，
        # 只供提示词与逐字核对，不上屏）。老包没有 display_text，前端回退到 text。
        "three_checks": [{"no": c["no"], "text": c["text"],
                          "display_text": c.get("display_text") or c["text"]}
                         for c in d["three_checks"]],
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
  "paragraph_count": "稿纸上一共几个自然段，填数字。**先数这个，再往下写 transcript**——一开始转写就顾不上分段了。短得一行都不满的段落最容易漏，开头那一段尤其要看清。",
  "transcript": "整篇作文的逐字转写。按稿纸原样抄，**包括你认为写错的字**，不要顺手改通顺；看不清的字写成 [?]。**分段必须照抄**：稿纸是方格纸，新起一段有两个看得见的标志——这一段的头一行**空出前两格**，而上一段的末行**右边空着没写满**。见到这两个标志就是新的一段，转写里用空行隔开。**必须分成 paragraph_count 段**——「分段」那一项就是照这里的换行判的，段数点错了，那一项跟着说错。这一项是给程序核对引用用的，不会给老师看。",
  "student_name": "稿纸姓名栏上的名字；栏空着或看不清就填空字符串",
  "unclear": ["看不清的句子，连同上下文；没有就空数组"],
  "checks": [
    {"no": 1, "verdict": "达成｜部分达成｜未达成｜不适用",
     "evidence": "学生原文里的句子，一字不差", "comment": "一句话说清为什么这样判"}
  ],
  "whole_piece": {
    "completeness": {"verdict": "完整｜基本完整｜未写完｜仅有开头", "note": "20字内。判得不好说**断在哪一句**；判「完整」说**具体怎么完整的**，如「开头点出人物，中间一件事，结尾收住」"},
    "order":        {"verdict": "清晰｜有跳跃｜混乱", "note": "20字内。判得不好说**哪一处跳了**；判「清晰」说**怎么个清楚法**，如「按事情发生的先后讲，没有跳」"},
    "paragraph":    {"verdict": "清晰｜该分未分｜通篇一段", "note": "20字内。判得不好说**该在哪儿另起一段**；判「清晰」说**怎么分的**，如「一段一件事」。**不要报具体段数**，你常数错"},
    "detail":       {"verdict": "重点突出｜主次平均｜重点过简｜不适用", "note": "20字内，写重点几句、写别处几句"},
    "flow":         {"verdict": "通顺｜个别不畅｜多处不通", "note": "20字内。判得不好说**绕的是哪一句**；判「通顺」说**怎么个顺法**，如「短句为主，一句一件事」"}
  },
  "language": {
    "issues": [
      {"kind": "同起头｜口水词｜动词笼统",
       "detail": "连着哪几句／全篇几次；要有数字",
       "quote": "原句一字不差。口水词类给次数即可，这里留空；引不出来也留空，不要硬造"}
    ],
    "overall": "一句话、30字内，只说这三样：句子长短／爱用哪个词／有没有写到对话和动作。**不许评通顺不通顺**（那是上一行的事，重复说等于没说），也不许写「读起来轻松愉快」这类观感。**生动、优美、细腻、流畅、活泼、精彩、丰富、到位、感染力，这些词一个都不许出现，换近义词绕开也不行**；说不出具体的就写「就是平常说话的样子，没什么大毛病」"
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
whole_piece 那五项**一项都不能少，verdict 与 note 都必填**（漏掉整项，老师那一行就成了「—」）。
判得好的项也要写 note，说清好在哪儿——**不许留空**。
whole_piece 与 language **都不影响 band**，band 只由三条判据定。
language.issues 可以是空数组——这一篇没毛病就空着，凑毛病比不判还糟。

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

每行＝一个学生：姓名｜档位｜三条判据的判定｜结构四项｜语言毛病｜亮点数｜点评卡引用的句子

@RESULTS@

## 怎么看

- **三层账要分开说，别混成一锅。** 判据卡住的是「这次课教的没学会」；
  结构卡住的（未写完、顺序混乱、通篇一段、主次平均）和语言卡住的（句子不通、
  口水词扎堆、动词笼统）是「更底下的地基」——**地基的人数多时，讲评课先讲地基，
  本课技法往后放**。
- **结构的账和语言的账也要分开。** 一个班「通篇一段」的人多，和「然后满篇飞」的人多，
  是两件事、两种练法，合着说老师没法备课。
- 亮点为零的人数也要报：**一个班多数人写不出一句自己的话，比判据不达标更值得警惕。**
- 讲评课念谁的，优先挑「有亮点」的，别只挑档位高的。

## 输出

只输出一个 JSON 对象，不要解释文字、不要代码块围栏：

{
  "overall": "两三句话说清这个班这次整体怎么样，要有具体数字",
  "whole_piece_summary": "地基这一层的账，结构与语言分两句说：结构——多少人未写完、多少人顺序有跳、多少人通篇一段、多少人主次平均；语言——多少人句子不通、最扎堆的口水词是哪个几人有、多少人一个亮点也没有。各点一两个名字",
  "common_problems": [
    {"problem": "共性问题", "layer": "判据｜结构｜语言",
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
        raise HTTPException(502, "模型输出被截断（max_tokens 不足），JSON 不完整。"
                                 "请调大 call_model 的 max_tokens 后重试。")
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
            raise HTTPException(502, "模型未返回可解析的 JSON：" + t[:300])
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
    for g in (d.get("language") or {}).get("issues") or []:
        one(g, "quote")          # 口水词类留空，one() 会自己跳过
    one(d, "quoted_sentence")
    sc = d.get("showcase") or {}
    if sc:
        one(sc, "paragraph")
    return fixed, suspect



# 口水词表。与 build_prompt.judging_rules 第 6 条列的那五个词一一对应，改一处要改两处。
FILLERS = ("然后", "就", "很", "非常", "特别")

# 放在谁身上都成立的空夸词。trim_verdict_tail 与 run_regression 的机检共用这一张
#（回归脚本从 srv 取，不自己另写一份）。
# ⚠ 与 judging_rules 里给模型看的那串**有意不同**：给模型的宁可宽（连「丰富」都禁），
# 机检宁可严（只查「内容丰富」）——「建议丰富表达」是具体建议，不是空夸，别误伤。
EMPTY_WORDS = ("生动", "优美", "细腻", "流畅", "活泼", "精彩", "内容丰富", "到位", "感染力")


def recount_fillers(d):
    """口水词整类由程序处理：从 transcript 数，到 3 次就补一条毛病。

    模型数不准（同一张稿纸两次跑出「然后4」和「然后5」）；更麻烦的是它数得出 4 次、
    整体评价里也写了「多用“然后”串联」，却照样把 issues 留空。既然计数由程序做，
    判定就一并接过来——与 enforce_grade_rules 同一个判断：能算出来的别交给模型。

    ⚠ **只在到线时报那一条，不下发五个词的完整计数**（0827 用户要求去掉）：
    罗列「然后0／就0／很2」像调试信息，不是评价栏该有的东西。数字只出现在真有问题的那条里。"""
    t = d.get("transcript") or ""
    lg = d.get("language")
    if not t or not isinstance(lg, dict):
        return
    counts = {w: t.count(w) for w in FILLERS}

    # 数到线了就由程序把这条毛病补上，不等模型报。实测它数得出「然后 4 次」、
    # 甚至在整体评价里写「多用“然后”串联」，却照样把 issues 留空——判定和计数
    # 是同一件事，计数既然已经由程序做了，判定也一并接过来。
    over = [(w, n) for w, n in counts.items() if n >= 3]
    if not over:
        return
    issues = lg.get("issues")
    if not isinstance(issues, list):
        issues = lg["issues"] = []
    if not any(isinstance(x, dict) and x.get("kind") == "口水词" for x in issues):
        issues.insert(0, {"kind": "口水词",
                          "detail": "、".join(f"“{w}”{n} 次" for w, n in over)
                                    + "——一篇里反复用同一个词",
                          "quote": ""})


def check_paragraphs(d):
    """转写段数与模型自报段数对不上就标可疑。

    分段是这一层里唯一靠转写还原的项，实测不稳：同一张三段稿纸，三次跑出 3/3/2 段，
    被并掉的总是开头那个不满一行的短段。并掉之后它会一本正经地判「全文两段，分段恰当」——
    **错的结论比没有结论更伤**，所以宁可告诉老师这项没把握。"""
    t = d.get("transcript") or ""
    w = d.get("whole_piece")
    n = d.get("paragraph_count")
    if not t or not isinstance(w, dict) or not isinstance(w.get("paragraph"), dict):
        return
    try:
        n = int(n)
    except (TypeError, ValueError):
        return
    got = len([x for x in t.split(chr(10)) if x.strip()])

    # 转写和它自报的段数都说只有一段，那就是通篇一段，不该由它判。
    # 实测同一张一段到底的稿纸，一轮判「通篇一段」（对）、一轮判「清晰」（错）。
    # 两个来源都说 1 段才强制——只有转写说 1 段时可能是转写把分段丢了，那种交给下面标可疑。
    if got <= 1 and n <= 1 and len(t) >= 80:
        if w["paragraph"].get("verdict") != "通篇一段":
            w["paragraph"]["verdict"] = "通篇一段"
            w["paragraph"]["note"] = "按事情的先后，至少分成两三段。"
        return

    if got != n:
        w["paragraph"]["suspect"] = True
        w["paragraph"]["note"] = (f"（它数到 {n} 段，转写却只分出 {got} 段，"
                                  f"这一项没把握，你对着原稿看一眼。）"
                                  + str(w["paragraph"].get("note") or ""))


def trim_verdict_tail(d):
    """剥掉 note 末尾那句「……，结构完整」「……，读起来流畅」式的收尾。

    取消「判得好就留空」之后冒出来的新形态：模型会在具体说明后面再补一句把判定重说
    一遍（「有开头点人，中间描述，结尾以问题收尾，结构完整。」）——这正是用户最早
    抱怨的重复。规则里明写禁止，三张基准稿纸仍中两张，所以这里确定性地剥掉。

    只剥「最后一个逗号之后、且含判定词、且很短」的收尾总结；判定词出现在开头的
    （「结尾未写完，最后一句停在……」）不动——剥了句子就不通了。"""
    w = d.get("whole_piece")
    if not isinstance(w, dict):
        return
    for v in w.values():
        if not isinstance(v, dict):
            continue
        vd, nt = str(v.get("verdict") or ""), str(v.get("note") or "")
        if not vd or not nt:
            continue
        body = nt.rstrip("。．.！!　 ")
        i = max(body.rfind("，"), body.rfind("；"))
        if i <= 0:
            continue
        tail = body[i + 1:]
        # 尾巴上挂的要么是判定复读（「……，结构完整」），要么是空话（「……，读起来流畅」）
        if (vd in tail or any(x in tail for x in EMPTY_WORDS)) and len(tail) <= max(len(vd), 4) + 3:
            v["note"] = body[:i] + "。"


def enforce_grade_rules(pack, d):
    """按学段强制覆写模型判不得的项。

    三年级不判详略——这条由课次唯一决定，不该指望模型听话。实测：规则里明写
    「本项不判、直接记不适用」，gpt-4o 照旧判「重点突出」并编出「8句/4句」。
    而这一栏一旦开始说空话，整层的可信度就跟着塌。与「引用一字不差靠工程不靠
    提示词」是同一个判断：能由课次算出来的，就别交给模型。"""
    if not (pack.get("meta", {}).get("grade_volume") or "").startswith("三年级"):
        return
    w = d.get("whole_piece")
    if isinstance(w, dict):
        w["detail"] = {"verdict": "不适用", "note": "本学段不评。"}


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
                       "comment": f'（mock）第{c["no"]}条「{c.get("display_text") or c["text"]}」的判断说明。'})
    bands = list(pack.get("bands", {}).keys()) or ["基础过关"]
    q = anchors[i % len(anchors)]

    # 三年级不判详略，mock 也照着走，好让前端的「不适用」中性色真被测到
    low = (pack.get("meta", {}).get("grade_volume") or "").startswith("三年级")
    whole = {
        "completeness": {"verdict": ["完整", "基本完整", "未写完", "仅有开头"][i % 4],
                         "note": "（mock）开头点出人物，中间一件事，结尾收住。" if i % 4 == 0
                                 else "（mock）第三件事写到一半停住。"},
        "order": {"verdict": ["清晰", "有跳跃", "混乱"][i % 3],
                  "note": "（mock）按事情发生的先后讲，没有跳。" if i % 3 == 0
                          else "（mock）第二件事插在第一件中间。"},
        "paragraph": {"verdict": ["清晰", "该分未分", "通篇一段"][i % 3],
                      "note": "（mock）三段，一段一件事。" if i % 3 == 0
                              else "（mock）两件事挤在同一段里。"},
        "detail": {"verdict": "不适用" if low else
                   ["重点突出", "主次平均", "重点过简"][i % 3],
                   "note": "（mock）本学段不评。" if low else
                           "（mock）重点 6 句，别处 3 句。"},
        "flow": {"verdict": ["通顺", "个别不畅", "多处不通"][(i + 1) % 3],
                 "note": "（mock）短句为主，一句一件事。" if (i + 1) % 3 == 0
                 else "（mock）“又回来了又跑过去”这句绕。"},
    }
    if i % 4 == 0:   # 让前端「这一项没把握」那条红字分支在演示模式下也看得到
        whole["paragraph"]["suspect"] = True
        whole["paragraph"]["note"] = ("（mock）它数到 3 段，转写却只分出 2 段，"
                                      "这一项没把握，你对着原稿看一眼。")
    # 每三篇留一篇一条毛病也没有——「允许判没问题」是规则里明写的，前端得能显示空的样子。
    # 与空亮点那篇错开，好让「有亮点无毛病」「无亮点有毛病」两种组合都被看到。
    language = {
        "issues": [] if i % 3 == 1 else [
            {"kind": "口水词", "detail": "（mock）“然后”全篇 5 次", "quote": ""},
            {"kind": "动词笼统", "detail": "（mock）这一处本可以写出具体动作", "quote": q},
        ][: 1 + i % 2],
        "overall": ["（mock）就是平常说话的样子，没什么大毛病。",
                    "（mock）句子偏短，一句一件事，读着利索。",
                    "（mock）爱用长句，有两处绕了一下。"][i % 3],
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
        "language": language,
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
                        .get("verdict") in ("未写完", "仅有开头"))
    nohl = sum(1 for r in results if not (r.get("highlights") or []))
    return {
        "overall": f"（mock 假数据）全班 {n} 份，主特点抓住的过半，卡在「写具体」这一步的偏多。",
        "whole_piece_summary": (f"（mock）{unfinished} 人未写完或仅有开头，"
                                f"{nohl} 人一句自己的话也没写出来——地基这一层比本课技法更急。"),
        "common_problems": [
            {"problem": "并列罗列多个特点，没有主特点", "layer": "判据",
             "how_many": f"约 {max(1, n // 3)} 人",
             "why": "构思表填了五行，就照着五行各写一句",
             "how_to_fix": "讲评课上拿两篇对着念，让学生自己听出哪一篇有主角"},
            {"problem": "写到一半停住", "layer": "结构",
             "how_many": f"{unfinished} 人",
             "why": "开头铺得太长，写到主体没时间了",
             "how_to_fix": "当堂限时三分钟只写结尾，练「先把话说完」"},
            {"problem": "“然后”当连接词用，一段里三四个", "layer": "语言",
             "how_many": f"约 {max(1, n // 4)} 人",
             "why": "按事情发生的顺序想到哪写到哪，句子之间只会用「然后」搭",
             "how_to_fix": "拿一段有四个「然后」的当堂删干净，让学生听删完是不是更清楚"},
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


# 访问口令：环境变量 LJ_ACCESS_CODE。为空＝不设防（本地开发默认如此）。
#
# 为什么需要它，而不是只靠 _rate_ok 的频率限制：那个桶在内存里，单进程时够用，
# **上了 Serverless（Vercel）就形同虚设**——每个实例一个桶、冷启动即清零，
# 打一次就换一个实例的话根本累计不起来。而链接一旦发给加盟商就会被转发，
# 谁拿到谁能烧我们的模型额度。口令挡的是这个：链接外泄了，没口令也用不了。
#
# 挡住全部 /api/*，只放行 /api/health（前端要靠它判断该不该弹口令框）。
# 课次列表也挡——判据（「先看三条」）是这工具的核心，不该谁点开链接都能抄走。
ACCESS_CODE = os.environ.get("LJ_ACCESS_CODE", "").strip()


@app.middleware("http")
async def _gate(request: Request, call_next):
    if (ACCESS_CODE
            and request.url.path.startswith("/api/")
            and request.url.path != "/api/health"
            and request.headers.get("x-access-code", "").strip() != ACCESS_CODE):
        return JSONResponse({"error": "口令有误，或尚未输入口令"}, status_code=401)
    return await call_next(request)


@app.get("/api/health")
def health():
    return {"ok": True, "mock": MOCK, "model": CFG["grade_model"],
            "lessons": len(PACKS), "rate_limit_per_hour": CFG["rate_limit_per_hour"],
            # 前端据此决定要不要弹口令框；也是线上确认「口令真的配上了」的唯一途径
            "auth": bool(ACCESS_CODE)}


@app.get("/api/auth-check")
def auth_check():
    """口令对不对。本身不做事——能走到这里就说明过了上面那道中间件。"""
    return {"ok": True}


@app.get("/api/lessons")
def lessons():
    return [public_view(d) for d in PACKS.values()]


@app.get("/api/lessons/{lesson_id}")
def lesson(lesson_id: str):
    d = PACKS.get(lesson_id)
    if not d:
        raise HTTPException(404, "未找到该课次的标准包")
    return public_view(d)


@app.post("/api/grade")
async def grade(request: Request,
                lesson_id: str = Form(...),
                prev_heads: str = Form("[]"),
                image: UploadFile = File(...)):
    pack = PACKS.get(lesson_id)
    if not pack:
        raise HTTPException(404, "未找到该课次的标准包")
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(429, "本小时批改次数已达上限，请稍后再试（防盗刷限额）")

    raw = await image.read()
    if len(raw) > CFG["max_image_mb"] * 1024 * 1024:
        raise HTTPException(413, f'图片超过 {CFG["max_image_mb"]}MB，请压缩后重新上传')

    if MOCK:
        return mock_grade(pack)

    heads = json.loads(prev_heads or "[]")
    b64 = base64.b64encode(raw).decode()
    msgs = build_messages(pack, b64, image.content_type or "image/jpeg", heads)
    out = parse_json(await call_model(msgs))

    # 引用一字不差这条不能靠模型自觉：拿它自己的 transcript 把每处引用对回原文，
    # 对不上的标 suspect 交给老师留意（见 fix_quotes 的注释）。
    fixed, suspect = fix_quotes(out)
    recount_fillers(out)          # 这两道都必须在 transcript 被 pop 掉之前
    check_paragraphs(out)
    trim_verdict_tail(out)
    enforce_grade_rules(pack, out)
    out["quote_check"] = {"fixed": fixed, "suspect": suspect}
    # transcript 只用于校验，不下发——老师手上有原稿，不需要看打字版
    out.pop("transcript", None)
    out.pop("paragraph_count", None)   # 与 transcript 同样只用于校验，不下发

    # 原图与 base64 到此为止：不落盘、不进日志
    return out


@app.post("/api/diagnose")
async def diagnose(request: Request, body: dict):
    pack = PACKS.get(body.get("lesson_id"))
    if not pack:
        raise HTTPException(404, "未找到该课次的标准包")
    # 这一条也是真实模型调用（max_tokens 6000），跟 /api/grade 共用同一个桶。
    # 原先只有 grade 挂了限额，diagnose 完全裸奔，是个盗刷缺口。
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(429, "本小时调用次数已达上限，请稍后再试（防盗刷限额）")
    results = body.get("results") or []
    if not results:
        raise HTTPException(400, "尚无批改结果")
    if MOCK:
        return mock_diagnose(pack, results)

    lines = []
    for r in results:
        cs = "；".join(f'{c["no"]}{c["verdict"]}' for c in r.get("checks", []))
        w = r.get("whole_piece") or {}
        wp = "／".join(f'{k}:{(w.get(v) or {}).get("verdict", "?")}'
                      for k, v in (("完整", "completeness"), ("顺序", "order"),
                                   ("分段", "paragraph"), ("详略", "detail"),
                                   ("通顺", "flow")))
        li = (r.get("language") or {}).get("issues") or []
        lg = "／".join(x.get("kind", "?") for x in li) or "无"
        lines.append(f'- {r.get("student_name") or "（无名）"}｜{r.get("band", "")}'
                     f'｜{cs}｜{wp}｜语言:{lg}｜亮点{len(r.get("highlights") or [])}'
                     f'｜引用：{r.get("quoted_sentence", "")}')
    prompt = (DIAGNOSE_RULES
              .replace("@PACK@", render_pack(pack))
              .replace("@RESULTS@", "\n".join(lines)))
    return parse_json(await call_model([{"role": "user", "content": prompt}], max_tokens=6000))


@app.exception_handler(HTTPException)
async def http_err(request, exc):
    return JSONResponse({"error": exc.detail}, status_code=exc.status_code)


# 本地跑时由这个进程一并供前端；线上（Vercel）前端走 CDN、函数包里没有 frontend/，
# 而 StaticFiles 指向不存在的目录会直接抛异常、整个函数 500，所以先判断。
class NoCacheStatic(StaticFiles):
    """前端文件一律带 Cache-Control: no-cache。

    StaticFiles 缺省只发 etag/last-modified、不发 Cache-Control，浏览器于是走
    启发式缓存：改完 app.js、重启服务、刷新页面，拿到的仍是磁盘里的旧脚本，且
    从界面上看只像是「改动没生效」（2026-08-29 实测踩过，transferSize=0）。
    no-cache 不是不缓存——仍带 etag 条件请求，没变就 304，几乎不费流量。
    """

    def file_response(self, *a, **kw):
        resp = super().file_response(*a, **kw)
        resp.headers["Cache-Control"] = "no-cache"
        return resp


if FRONTEND.is_dir():
    app.mount("/", NoCacheStatic(directory=str(FRONTEND), html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    print("标准包 " + str(len(PACKS)) + " 课：" +
          "、".join(p["meta"]["topic"] for p in PACKS.values()))
    print("模式：" + ("MOCK（未配密钥，返回假数据）"
                     if MOCK else "真实调用 " + CFG["grade_model"]))
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
