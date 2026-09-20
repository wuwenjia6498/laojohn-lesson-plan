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
import asyncio
import base64
import importlib.util
import json
import os
import re
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import List, Optional

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


# 0917 起主模型换成豆包（用户拍板）。同一张真稿 + 三篇基准实测：判据方向全对、引用逐字全中、
# 姓名全对、盘点方面数与人工一致；gpt-4o 会把稿纸上没有的东西脑补进转写。
# ⚠ doubao-seed 系列默认开思考——一篇 3000～6000 推理 token、2-1-pro 直接超时，
# 必须带 thinking=disabled；换回非豆包模型时把 model_extra 清成 {}，别把这个键发给别家。
DEFAULT_MODEL = "doubao-seed-2-1-pro"
DEFAULT_MODEL_EXTRA = {"thinking": {"type": "disabled"}}


def load_config():
    cfg = {
        "api_key": "",
        "base_url": "https://aihubmix.com/v1",
        "grade_model": DEFAULT_MODEL,
        "model_extra": dict(DEFAULT_MODEL_EXTRA),
        "proofread": True,   # 独立错别字校对层（只给老师看）。换回会自动纠错的模型（gpt-4o）必须关
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
    # 线上没有 config.json，模型也得有环境变量入口；模型专属参数走 LJ_MODEL_EXTRA（见 model_extra）
    if os.environ.get("LJ_GRADE_MODEL", "").strip():
        cfg["grade_model"] = os.environ["LJ_GRADE_MODEL"].strip()
    if os.environ.get("LJ_PROOFREAD", "").strip().lower() in ("0", "false", "no", "off"):
        cfg["proofread"] = False
    # 线上不放 config.json（密钥只走环境变量），所以 trust_proxy 也得有个环境变量
    # 入口，否则托管平台上它永远是 false。⚠ 只在确知前面有反代时才开，见 _client_ip。
    if os.environ.get("LJ_TRUST_PROXY", "").strip().lower() in ("1", "true", "yes"):
        cfg["trust_proxy"] = True
    return cfg


CFG = load_config()
MOCK = not CFG["api_key"]
# 错别字校对层开关。它建立在「模型读稿保真」之上（0917 豆包 2-1-pro 实测成立），
# gpt-4o 会把自己脑补出来的字报成学生的错——模型能用 LJ_GRADE_MODEL 随手换，这层就得能随手关。
PROOFREAD = bool(CFG.get("proofread", True)) and not MOCK
PROOF_WAIT = 60      # 主批改回来之后最多再等校对多少秒（正常 15 秒左右就完了）

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
GRADE_RULES = """你是老约翰同步习作课的批改助手。老师会发来一个学生手写稿纸的照片（通常一张；写得长的学生会用续页，那就是两三张，按页序发给你，是同一篇作文），你按下面的标准判断，输出 JSON。

## 一、你的边界（先记住）

1. **不批错别字、不批标点、不批卷面。** 稿纸上写错的字、用拼音代替的字，转写和引用里**照原样抄**，但在任何批语、点评卡、亮点说明里**一个字都不要提**——这一层归老师当面看稿，不归你。
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
  "transcript": "整篇作文的逐字转写。**有续页时把各页按顺序接着抄成一篇**，页与页之间不要加任何标记。按稿纸原样抄，**包括你认为写错的字**，不要顺手改通顺；看不清的字写成 [?]。**分段必须照抄**：稿纸是方格纸，新起一段有两个看得见的标志——这一段的头一行**空出前两格**，而上一段的末行**右边空着没写满**。见到这两个标志就是新的一段，转写里用空行隔开。**必须分成 paragraph_count 段**——「分段」那一项就是照这里的换行判的，段数点错了，那一项跟着说错。这一项是给程序核对引用用的，不会给老师看。",
  "student_name": "稿纸姓名栏上的名字；栏空着或看不清就填空字符串",
  "unclear": ["看不清的句子，连同上下文；没有就空数组"],
  "pinyin_fixes": [{"pinyin": "稿纸上用拼音代替汉字的那一处，照原样抄（含声调，如 kù）", "char": "按上下文应该是哪个字（如 裤）", "sure": true}],
  "survey": {
    "aspects": [{"name": "方面名，如「跑步快」「外貌」「借笔给我」", "sentences": 0}],
    "total_sentences": 0,
    "scenes": [{"what": "哪个方面的哪件事", "quote": "最像画面的那一句，一字不差",
                "has": ["动作", "神态", "对话", "声音", "前后变化"]}],
    "topic_sequence": ["按稿纸上的句序，一句一项，写这句讲的是哪个方面（用上面的方面名）。**照原文的先后抄，不许把同一个方面的句子归并到一处、也不许重排成顺的**——这一串就是用来看他有没有说到别处又折回来的"]
  },
  "checks": [
    {"no": 1, "verdict": "达成｜部分达成｜未达成｜不适用",
     "evidence": "学生原文里最像的那一句，一字不差",
     "quotes": ["再列 1～3 句原文，一字不差：判达成列做到了的句子，判没达成列出问题的那几句（写散了的、只有结论没画面的）"],
     "comment": "一句话说清为什么这样判",
     "advice": "怎么改。只在部分达成／未达成时写：哪几句该删、压成一句或挪到结尾带一笔，哪一处该展开，用课上讲的哪种写法展开，末尾给一句为这个孩子写的示范（≤40 字，前面标「比如可以写成：」）。达成留空；不适用只写「先把第 N 条做到」"}
  ],
  "whole_piece": {
    "completeness": {"verdict": "完整｜基本完整｜未写完｜仅有开头", "note": "20字内。判得不好说**断在哪一句**；判「完整」说**具体怎么完整的**，如「开头点出人物，中间一件事，结尾收住」"},
    "order":        {"verdict": "清晰｜有跳跃｜混乱", "note": "20字内。判得不好说**哪一处跳了**；判「清晰」说**怎么个清楚法**，如「按事情发生的先后讲，没有跳」"},
    "paragraph":    {"verdict": "清晰｜该分未分｜通篇一段（数不准时程序会改成「不适用」）", "note": "20字内。判得不好说**该在哪儿另起一段**；判「清晰」说**怎么分的**，如「一段一件事」。**不要报具体段数**，你常数错"},
    "detail":       {"verdict": "重点突出｜主次平均｜重点过简｜不适用", "note": "20字内，写重点几句、写别处几句"},
    "flow":         {"verdict": "通顺｜个别不畅｜多处不通", "note": "20字内。判得不好说**绕的是哪一句**；判「通顺」说**怎么个顺法**，照这一篇的样子说（一句一件事／爱用「因为……所以」／长短句搭着来），**别每篇都写「短句为主，一句一句顺下来」**",
                     "demo_from": "原文里连着的一段，一字不差、不拼接：有不通的句子就抄那一句；都通但通篇短句就抄两三句连着的短句（≤50 字）；本来就长短搭着来可留空。**别和 issues 里「用词不当」引的是同一句**——同一句在两处各改一遍，老师会以为是两个毛病；只有那一句可挑时，这里留空，让用词那条去说
                     "demo_to": "把 demo_from 改写后的样子：不通的改顺；短句连成一个长句（用「一边……一边」「……的时候」「因为……所以」「……得……」，或把动作、样子、心情并进一句）。只说他原来那个意思，不添情节，≤60 字，不出现空夸词。demo_from 空则这里也空"}
  },
  "language": {
    "issues": [
      {"kind": "口水词｜用词重复｜用词不当｜同起头｜动词笼统｜修辞不当",
       "detail": "前四类是数出来的：连着哪几句／全篇几次，要有数字，格式如「“开心”4 次」。口水词**只数规则里给的那五个词**；用词重复是五个之外的实词，人称、人名、「的」「了」「是」这类虚词不算（程序会拿转写重数一遍，数不够 3 次的整条删）。后两类是读出来的、不带数字：用词不当写清**是哪个词、为什么搁在这儿不合适**（词义不对／搭配不上／程度过头／大词小用），**只说词不说字，写错的字一个也不许提**；修辞不当写清他把什么比成了什么、是**不像**还是**老套**还是**过头**",
       "quote": "原句一字不差。口水词与用词重复引**用得最密的那一句**；引不出来就留空，不要硬造。**用词不当与修辞不当必须引出那一句**——引不出来就不报（程序会把没有原句的这两类整条删掉）",
       "fix": "这条毛病怎么改，用这孩子自己的句子示范：口水词→那一句去掉口水词重写；用词重复→给两三个替换词、并把一处改成样子；用词不当→给一两个能替换的词、再把那一句改出来；同起头→把两三句换成不同开头；动词笼统→把那个动作或样子写具体；修辞不当→不是删掉比喻，而是从他写的这个人这件事里找一样东西来打比方，或直接把样子写出来。写成「可以改成：……」，改后句 40 字以内，不出现空夸词"}
    ],
    "overall": "一句话、30字内，只说这四样里的一样：句子长短／用词（爱用哪个词、准不准）／有没有写到对话和动作／有没有用比喻拟人这类写法（用了才说、说清像在哪儿或哪儿不像，没用就说别的三样、**不要写「没有用修辞」**）。**不许评通顺不通顺**（那是上一行的事，重复说等于没说），也不许写「读起来轻松愉快」这类观感。**生动、优美、细腻、流畅、活泼、精彩、丰富、到位、感染力，这些词一个都不许出现，换近义词绕开也不行**；说不出具体的就写「就是平常说话的样子，没什么大毛病」"
  },
  "highlights": [
    {"quote": "孩子自己写得好的那一句，一字不差", "why": "具体好在哪",
     "kind": "好词｜句式｜修辞｜观察｜真心话"}
  ],
  "band": "三档标准里的档位名之一",
  "focus": "给老师的综合评价，两三句、60～90 字：这篇总体写成了什么样、最拿得出手的是哪一处（点原句或原处）、整体最大的短板。不复述判据栏的逐条结论，短板只说整体形态、不再列方面清单。**生动、优美、细腻、流畅、活泼、精彩、丰富、到位、感染力这些词一个都不许出现**，换近义词绕开也不行",
  "teacher_note": "建议写进稿纸「老师批改」栏的一句话，30 字以内",
  "showcase": {"suitable": true, "paragraph": "适合当范例念的那一段原文", "point": "用来讲哪一点"},
  "quoted_sentence": "点评卡里引用的那一句，与稿纸一字不差",
  "parent_card": "给家长的点评卡文案，150 字以内"
}

**survey 是判三条判据的依据，先写它、再写 checks，不给老师看。**
aspects 要把全文写到的方面一个不漏地列出来（哪怕只有半句也算一个）；
sentences 是这个方面占了几句，加起来该与 total_sentences 相当。
scenes 只收**真有画面**的：“她跑步很快”“她很热心”这类结论句不是画面，不许列；
has 里只填这一处**真有**的那几样，一样都没有就给空数组——
把结论句当画面列进来，第②条就会跟着判松，这是本工具最常见的判错。

pinyin_fixes 只收稿纸上**确实写成拼音**的字，没有就空数组；拿不准是哪个字的 sure 填 false。
它**只用于给家长的点评卡把拼音换回正字**（家长看不懂孩子写的 kù子），不进任何批语，
转写与老师看的引用仍照原样保留拼音。写错的汉字（别字）不在此列，不要写进来。

highlights 可以是空数组——这一篇确实没有出彩的地方，就空着，不要硬凑。
whole_piece 那五项**一项都不能少，verdict 与 note 都必填**（漏掉整项，老师那一行就成了「—」）。
判得好的项也要写 note，说清好在哪儿——**不许留空**。
whole_piece 与 language **都不影响 band**，band 只由三条判据定。
**有任何一条判据不是「达成」，就不能给最高那一档**——有一条只判到「部分达成」还给最高档，
等于自己说自己的话不算数。（程序会按这条核一遍，不合就给你降下来。）
language.issues 可以是空数组——这一篇没毛病就空着，凑毛病比不判还糟。
**用词不当、修辞不当各最多一条**（挑最值得跟老师说的那一处），两类都必须带 quote。
**全篇没用比喻拟人的，不许报修辞不当**，也不许在任何一栏写「缺少修辞」「建议多用比喻」——
硬凑出来的比喻比不用还糟，这一条是本工具的红线。

**先写 transcript，再判断**。后面所有引用都必须能在 transcript 里**逐字找到**——
程序会拿它们去 transcript 里比对，对不上的会被标成可疑。
"""

ANTI_SAME_TMPL = """
## 六、别跟前面几篇撞句式（重要）

老师这一批要批二三十份，发到同一个家长群。下面是本批已经写过的点评卡开头，你这一篇的开头不许与它们同一个套路（不许同样的起手词、同样的句式）：

{heads}

每一篇都要从这个孩子自己写的内容说起，第一句就落到他的原句上。
"""


MAX_PAGES = 3   # 稿纸一页 + 续页一页是常态，留一页余量；再多多半是拍错了

MULTI_PAGE_NOTE = (
    "这一份学生作文共 {n} 页，下面按页序给出。第 2 页起是续页，**接着上一页的末尾往下读，"
    "是同一篇作文的后半部分，不是另一篇**；续页开头不空两格也不算新起一段。"
    "姓名以第 1 页姓名栏为准。转写与所有引用都要覆盖全部页。"
)


def build_messages(pack, images, prev_heads):
    """images：[(base64, mime), ...]，按页序；一页就是长度为 1 的列表。

    ⚠ 0906 起签名从 (pack, image_b64, mime, prev_heads) 改成这样——smoke_real.py 与
    run_regression.py 都已同步；再有别的调用方，传单张就包成 [(b64, mime)]。
    """
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
        {"role": "user", "content": _pages_content(images, "按上面的要求批改，只输出 JSON。")},
    ]


def _pages_content(images, lead_text):
    """user 消息里「多页说明 + 逐页图」这一段。主批改与错别字校对共用，
    多页稿纸的口径（续页接着读、姓名以第 1 页为准）两边才一致。"""
    n = len(images)
    content = [{"type": "text", "text": (
        "这是一份学生稿纸，" + lead_text if n == 1
        else MULTI_PAGE_NOTE.format(n=n) + " " + lead_text)}]
    for i, (b64, mime) in enumerate(images, 1):
        if n > 1:
            content.append({"type": "text", "text": f"第 {i} 页："})
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    return content


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
  口水词扎堆、动词笼统、用词不当、比喻不贴切）是「更底下的地基」——**地基的人数多时，讲评课先讲地基，
  本课技法往后放**。
- **结构的账和语言的账也要分开。** 一个班「通篇一段」的人多，和「然后满篇飞」的人多，
  是两件事、两种练法，合着说老师没法备课。
- 亮点为零的人数也要报：**一个班多数人写不出一句自己的话，比判据不达标更值得警惕。**
- 讲评课念谁的，优先挑「有亮点」的，别只挑档位高的。

## 输出

只输出一个 JSON 对象，不要解释文字、不要代码块围栏：

{
  "overall": "两三句话说清这个班这次整体怎么样，要有具体数字",
  "whole_piece_summary": "地基这一层的账，结构与语言分两句说：结构——多少人未写完、多少人顺序有跳、多少人通篇一段、多少人主次平均；语言——多少人句子不通、最扎堆的口水词是哪个几人有、多少人用词或比喻不合适、多少人一个亮点也没有。各点一两个名字",
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
def model_extra():
    raw = os.environ.get("LJ_MODEL_EXTRA")
    if raw:
        try:
            v = json.loads(raw)
            if isinstance(v, dict):
                return v
        except json.JSONDecodeError:
            pass
    v = CFG.get("model_extra")
    return v if isinstance(v, dict) else {}


async def call_model(messages, max_tokens=8000):
    url = CFG["base_url"].rstrip("/") + "/chat/completions"
    payload = {
        "model": CFG["grade_model"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.7,
        "response_format": {"type": "json_object"},
    }
    # 模型专属参数原样并进请求体。0917 评估豆包时的发现：doubao-seed 系列默认开思考，
    # 一篇 3000～6000 个推理 token、批一篇要 40～120 秒，2-1-pro/turbo 干脆超时；
    # 带上 {"thinking": {"type": "disabled"}} 就回到 18～38 秒。这类开关各家名字不同，
    # 所以不写死，跟 grade_model 一样放 config；环境变量 LJ_MODEL_EXTRA（JSON）优先，
    # 给回归脚本换着试用。
    payload.update(model_extra())
    headers = {"Authorization": f'Bearer {CFG["api_key"]}',
               "Content-Type": "application/json"}
    # 0917 实测网关偶发 SSL: UNEXPECTED_EOF（连着几次并发时），重试一下就过；
    # 只重试「没连上」这一类，模型答了但答错的不重试（那是内容问题，重试是撞运气）
    async with httpx.AsyncClient(timeout=180) as cli:
        # 0917 回归里主批改连着 3 次 ConnectError（SSL EOF 是一阵一阵的），3/6 秒的退避不够跨过去；
        # 改 4 次、退避 3/6/12 秒。只对「没连上」重试，模型答了但答错的不重试。
        for attempt in range(4):
            try:
                r = await cli.post(url, json=payload, headers=headers)
                break
            except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.ReadTimeout) as e:
                if attempt == 3:
                    raise HTTPException(502, f"模型网关连不上（已重试 4 次）：{type(e).__name__}")
                await asyncio.sleep(3 * 2 ** attempt)
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
        pass
    # 0917 实测豆包偶尔连着吐两个 JSON 对象（{...}{...}），贪婪正则一把抓到「Extra data」；
    # 改用 raw_decode 从第一个 { 起取第一个完整对象，后面多出来的一律不要。
    i = t.find("{")
    if i < 0:
        raise HTTPException(502, "模型未返回可解析的 JSON：" + t[:300])
    try:
        obj, _ = json.JSONDecoder().raw_decode(t[i:])
        return obj
    except json.JSONDecodeError as e:
        raise HTTPException(502, f"模型返回的 JSON 解析失败（{e.msg}）：" + t[:300])


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
        # quotes 是并列的几句原文，逐句校对；对不上的在 quotes_suspect 同位标 True 交前端标红
        qs = c.get("quotes")
        if isinstance(qs, list):
            out, flags = [], []
            for q in qs:
                if not isinstance(q, str) or not q.strip():
                    continue
                tmp = {"q": q.strip()}
                one(tmp, "q")
                out.append(tmp["q"]); flags.append(bool(tmp.get("q_suspect")))
            c["quotes"], c["quotes_suspect"] = out, flags
    for h in d.get("highlights") or []:
        one(h, "quote")
    for g in (d.get("language") or {}).get("issues") or []:
        one(g, "quote")          # 口水词类留空，one() 会自己跳过
    one(d, "quoted_sentence")
    sc = d.get("showcase") or {}
    if sc:
        one(sc, "paragraph")
    fl = (d.get("whole_piece") or {}).get("flow")
    if isinstance(fl, dict):
        one(fl, "demo_from")     # 语句示范的「原句」是连着的两三句，同样要逐字对得上
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

    # 模型会自己往口水词表里加词：实测 0917 把「她」报成口水词（全篇 9 次）——
    # 而这一课恰恰要求全篇只用「他／她」，等于把作业要求判成毛病。表是固定的五个词，
    # 不在表里的一律清掉（计数既然由程序做，词表也由程序说了算）。
    issues0 = lg.get("issues")
    if isinstance(issues0, list):
        lg["issues"] = [x for x in issues0
                        if not (isinstance(x, dict) and x.get("kind") == "口水词"
                                and not any(w in str(x.get("detail") or "") for w in FILLERS))]

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
                          "quote": "", "fix": ""})    # 程序补的这条没有改法：不替模型编一句


# 「用词重复」不算这些：人称、人名之外最常见的虚词。模型报「他」「我」「的」这类就是把
# 作业要求或语法本身判成毛病，与口水词表里「不许报『她』」同一个道理。
REPEAT_STOP = set("他她它我你您的了着过是在有和与跟把被给也都又还就很非常特别然后这那个一不没")
REPEAT_STOP |= {"我们", "他们", "她们", "你们", "它们", "咱们", "这个", "那个", "这样", "那样",
                "自己", "什么", "因为", "所以", "但是", "可是", "虽然", "如果", "一个", "一下"}
REPEAT_MIN = 3
REPEAT_MIN_SINGLE = 5   # 单字（“好”“笑”）在别的词里到处出现，转写里数出 3 次多半是「很好」「好人」凑的，门槛提高
_QUOTED_WORD = re.compile(r"[“「\"']([^“”「」\"']{1,6})[”」\"']")


def verify_repeats(d):
    """「用词重复」那一类由程序复核：模型报的词拿 transcript 重数，数不够 3 次、
    或落在人称／虚词／学生姓名上的，整条删掉；数得够的把 detail 里的次数换成程序数的。

    与 recount_fillers 同一个判断：能算出来的别交给模型。口水词那五个词是封闭表，
    程序能自己补条目；重复实词是开放集，程序补不了、但能核——所以这里只做减法。"""
    t = d.get("transcript") or ""
    lg = d.get("language")
    if not t or not isinstance(lg, dict) or not isinstance(lg.get("issues"), list):
        return
    name = str(d.get("student_name") or "").strip()
    keep = []
    for x in lg["issues"]:
        if not (isinstance(x, dict) and x.get("kind") == "用词重复"):
            keep.append(x)
            continue
        m = _QUOTED_WORD.search(str(x.get("detail") or ""))
        w = m.group(1).strip() if m else ""
        if (not w or w in REPEAT_STOP or w in FILLERS or (name and w in name)
                or not _HAS_CJK.search(w)):
            continue
        n = t.count(w)
        if n < (REPEAT_MIN_SINGLE if len(w) == 1 else REPEAT_MIN):
            continue
        x["detail"] = f"“{w}”全篇 {n} 次"
        keep.append(x)
    lg["issues"] = keep


# 「读出来」的那两类毛病（不是数出来的）：判的是这个词、这个比喻搁在这儿合不合适。
# 程序核不了它们判得对不对，但能核**有没有落在一句真的原文上**——这两类不像口水词
# 那样能靠计数自证，老师只能对着被引的那一句看；引不出原句、或引的句子与稿纸对不上，
# 这条就没法核，留着只会让老师白翻一遍稿纸。
JUDGED_KINDS = ("用词不当", "修辞不当")


def tidy_language(d):
    """语言块整形，都是确定性的：判断类毛病（用词不当／修辞不当）没有对得上的原句就整条删；
    每条毛病的 fix 剥掉「可以改成：」后面空着的空承诺；
    语句示范 demo_from／demo_to 缺一半就两个一起清（只剩原句等于没示范，只剩改句对不上原稿）。"""
    lg = d.get("language")
    if isinstance(lg, dict) and isinstance(lg.get("issues"), list):
        keep, seen = [], {}
        for x in lg["issues"]:
            k = x.get("kind") if isinstance(x, dict) else None
            if k in JUDGED_KINDS:
                # 引不出原句、或引的句子与稿纸对不上，这条老师没法核，留着只是让他白翻稿纸
                if not str(x.get("quote") or "").strip() or x.get("quote_suspect"):
                    continue
                # 每类只留一条。实测模型一篇报到两条（用词不当 2 ＋ 修辞不当 2），
                # 四条语言毛病压在一栏里，老师看不过来，也把讲评的重点冲散了——
                # 提示词里写了「最多一条」它不守，那就由程序截，与口水词计数同一个判断。
                seen[k] = seen.get(k, 0) + 1
                if seen[k] > 1:
                    continue
            keep.append(x)
        lg["issues"] = keep
        for x in lg["issues"]:
            if not isinstance(x, dict):
                continue
            fx = _DANGLING_EXAMPLE.sub("", str(x.get("fix") or "").strip()).rstrip("，；, ")
            fx = re.sub(r"^(可以改成|可以写成|改成)[：:]\s*$", "", fx)
            if fx and not fx.endswith(("。", "！", "？", "”", "」")):
                fx += "。"
            x["fix"] = fx
    fl = (d.get("whole_piece") or {}).get("flow")
    if isinstance(fl, dict):
        a, b = str(fl.get("demo_from") or "").strip(), str(fl.get("demo_to") or "").strip()
        if not a or not b or fl.get("demo_from_suspect"):
            # 原句对不上转写就整个示范不要：示范的前提是老师能在稿纸上找到那几句
            for k in ("demo_from", "demo_to", "demo_from_suspect"):
                fl.pop(k, None)
        else:
            fl["demo_from"], fl["demo_to"] = a, b


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
        # 两处数不一致＝这一项它没数准。原先把「它数到 N 段、转写只分出 M 段」原样写给老师、
        # 请他对着原稿核——实测那就是一行红字噪音：分段老师一眼就看见，不需要工具提醒他去看，
        # 而「没把握」三个字还会连累旁边几项的可信度。
        # 改成不判段数，给内容上的建议：几个方面就该分几段，方面数取自 survey 的话题序列
        # （话题它数得准，段数它数不准——判定就落在数得准的那个上）。
        # 不报数字：方面个数判据①已经说过一次，这里再报一个（且常常对不上）只会自相矛盾；
        # 也不说「一个方面一段」——对一篇本该压到一两个特点的作文，那是反向建议。
        w["paragraph"] = {"verdict": "不适用", "note": "分段看原稿；一件事一段，说完一件再另起。"}


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


FOCUS_MIN_ASPECTS = 3      # 方面到这个数就不可能是「围绕一条线写」了
FOCUS_MAX_SHARE = 0.5      # 写得最多的那个方面占不到全篇一半，就不是主次分明


def _survey_stats(d):
    """从 survey 里算出：方面个数、写得最多的那个占多少。算不出就返回 None。"""
    sv = d.get("survey")
    if not isinstance(sv, dict):
        return None
    asp = [a for a in (sv.get("aspects") or []) if isinstance(a, dict)]
    if len(asp) < 2:
        return None

    def n(a):
        try:
            return int(a.get("sentences") or 0)
        except (TypeError, ValueError):
            return 0

    counts = [n(a) for a in asp]
    if max(counts) <= 0:
        return None
    try:
        total = int(sv.get("total_sentences") or 0)
    except (TypeError, ValueError):
        total = 0
    total = max(total, sum(counts))          # 它自报的总句数偏小时以分项之和为准
    top = max(counts)
    return {"n": len(asp), "top": top, "total": total, "share": top / total,
            "top_name": str(asp[counts.index(top)].get("name") or "").strip(),
            "names": [str(a.get("name") or "").strip() for a in asp]}


def enforce_focus_check(pack, d):
    """标了 check_kind="focus" 的那条判据（问「集中不集中」的），按它自己数的盘点兜底。

    实测 0917 真稿：一篇写了外貌、爱笑、识字少、跑步快、上课积极、调皮、乐于助人
    七个方面的作文，模型照样把「主特点明确集中」判成达成，理由是「跑步快多次提到」——
    找到一处支持证据就不回头看全篇了。judge_by 里明写「并列罗列视为没抓住」也拦不住，
    因为这不是判据没写清，是执行时不做全篇盘点。方面个数与句数它已经数在 survey 里，
    判定就照它自己的数字来——与 recount_fillers 同一个判断：能算出来的别交给模型。

    只降一档到「部分达成」、不直接判未达成：盘点的数字出自模型，宁可保守，
    同时打 suspect 让老师对着原稿看一眼。
    """
    st = _survey_stats(d)
    if not st or st["n"] < FOCUS_MIN_ASPECTS or st["share"] >= FOCUS_MAX_SHARE:
        return
    nos = {c["no"] for c in pack.get("three_checks") or []
           if c.get("check_kind") == "focus"}
    if not nos:
        return
    for c in d.get("checks") or []:
        if not isinstance(c, dict) or c.get("no") not in nos:
            continue
        if c.get("verdict") != "达成":
            continue
        c["verdict"] = "部分达成"
        c["suspect"] = True
        head = "、".join(x for x in st["names"][:4] if x)
        # 不点「写得最多的是哪个方面」——模型判的主特点常是另一个，点了名老师会看糊涂；
        # 老师要的信息是「铺了几个方面、没有哪个占住全篇」。
        c["comment"] = (f'（全篇写到 {st["n"]} 个方面：{head}……，'
                        f'占得最多的一个也才 {st["top"]}／{st["total"]} 句，算不上集中。）'
                        + str(c.get("comment") or ""))


VERDICT_ORDER = ("未达成", "部分达成", "达成")


def enforce_concrete_check(pack, d):
    """标了 check_kind="concrete" 的判据（问「写没写具体」的），按盘点里真有画面的处数封顶。

    判据的 judge_by 早就写着门槛（一处也没有→未达成；只有一处且没展开→部分达成），
    模型照旧放宽：0917 两次回归里 B 篇「只有一处、一两句带过」一次判部分达成、
    一次判达成——同一份稿纸、同一套规则，全看这一轮它怎么想。画面处数已经数在
    survey.scenes 里（结论句不许列、一问一答只算一处，都在提示词里说死了），
    照它自己数的封顶即可。

    只封顶、不抬升：它判得比门槛还低是它自己的判断，不动。
    """
    nos = {c["no"] for c in pack.get("three_checks") or []
           if c.get("check_kind") == "concrete"}
    sv = d.get("survey")
    if not nos or not isinstance(sv, dict) or not isinstance(sv.get("scenes"), list):
        return
    good = [[h for h in (x.get("has") or []) if str(h).strip()]
            for x in sv["scenes"] if isinstance(x, dict)]
    good = [h for h in good if h]
    if len(good) >= 2:
        return
    # 只有一处、但这一处动作／神态／对话凑齐了三样以上＝「一处写透了」，
    # 各课 judge_by 都认这是达成，不封
    if len(good) == 1 and len(set(good[0])) >= 3:
        return
    cap = "未达成" if not good else "部分达成"
    for c in d.get("checks") or []:
        if not isinstance(c, dict) or c.get("no") not in nos:
            continue
        v = c.get("verdict")
        # 「不适用」（依赖的那条没成立）不在这个梯子上，不碰
        if v not in VERDICT_ORDER or VERDICT_ORDER.index(v) <= VERDICT_ORDER.index(cap):
            continue
        c["verdict"] = cap
        c["suspect"] = True
        c["comment"] = (f'（全篇真有画面的地方只有 {len(good)} 处。）'
                        + str(c.get("comment") or ""))


def check_order_by_sequence(d):
    """叙述顺序照 survey 那串话题序列核：说到别处又回头讲同一个方面，就是有跳跃。

    实测 0917：模型自己把序列列成 外貌→性格→跑步快→性格→乐于助人，回头仍判「清晰」，
    note 还写「按外貌、性格、特长、品质顺序清晰展开」——序列里明明折回去过。
    序列既然已经列出来了，查重复是纯算术，不该再交给它。

    末项不参与查重：结尾回扣开头（写完事再点一句题）是首尾呼应，不是跳跃。
    """
    seq = [str(x).strip() for x in ((d.get("survey") or {}).get("topic_sequence") or [])
           if str(x).strip()]
    w = d.get("whole_piece")
    if len(seq) < 3 or not isinstance(w, dict) or not isinstance(w.get("order"), dict):
        return
    if w["order"].get("verdict") != "清晰":
        return
    compact = [t for i, t in enumerate(seq) if i == 0 or t != seq[i - 1]]
    body = compact[:-1]          # 末项是结尾，回扣开头算呼应
    back = next((t for i, t in enumerate(body) if t in body[:i]), None)
    if not back:
        return
    w["order"]["verdict"] = "有跳跃"
    w["order"]["suspect"] = True
    w["order"]["note"] = f"说到别处又回头讲{back}，同一件事该写在一处。"


def cap_band(pack, d):
    """档位不得高于三条判据撑得住的高度。

    三档标准的文字本身就是判据达成度的描述（最高档＝特点非常突出、有具体的画面或小事），
    所以判据只判到「部分达成」却给最高档，是自相矛盾。实测 0917：三条判松了不算，
    band 还给了最高档，老师一眼看去像是这篇没问题。
    """
    names = list(pack.get("bands") or {})
    if len(names) < 2 or not d.get("band"):
        return
    verdicts = [c.get("verdict") for c in (d.get("checks") or []) if isinstance(c, dict)]
    if "未达成" in verdicts:
        cap = 0
    elif "部分达成" in verdicts:
        cap = len(names) - 2
    else:
        return
    if d["band"] in names and names.index(d["band"]) > cap:
        d["band"] = names[cap]


# 给人看的成句文案，空夸词最爱长在这几处（whole_piece 的 note 另有 trim_verdict_tail 管）
NL2 = chr(10) * 2

EMPTY_FIELDS = ("focus", "teacher_note", "parent_card")

REPAIR_RULES = """你是老约翰习作批改助手的文字校对。下面每一条都是刚写好的批语，
里面用了空夸词（生动、优美、细腻、流畅、活泼、精彩、内容丰富、到位、感染力）——
这类词安在谁身上都成立，写了等于没写。把每一条改写一遍：

- **只改用了空词的那半句**，其余一字不动；
- 把空词换成**具体说的是哪一句、哪一处**（哪个动作、哪句对话、哪个画面）；
  说不出具体的就把那半句删掉，宁可短——**换个近义词绕开不算改**
  （漂亮、传神、鲜活、栩栩如生同样不许）；
- **引号里的句子是学生原文，一个字都不许动**，加字、改标点都不行；
- **parent_card 里引的那句学生原话必须原样留着**，不许删、不许换成别的句子；
- 字数不许超过原文；parent_card 仍是跟家长说话的口气，不出现档位、分数。

原样返回一个 JSON 对象：键用我给你的那几个键，值是改写后的文案，一个键都不许少。"""


def _empty_hits(text):
    return [w for w in EMPTY_WORDS if w in str(text or "")]


def collect_empty_words(d):
    """把命中空夸词的字段收成 {路径: 原文}，路径用点号，回写时照原路找回去。"""
    out = {}
    for k in EMPTY_FIELDS:
        if _empty_hits(d.get(k)):
            out[k] = d[k]
    sc = d.get("showcase")
    if isinstance(sc, dict) and _empty_hits(sc.get("point")):
        out["showcase.point"] = sc["point"]
    for i, h in enumerate(d.get("highlights") or []):
        if isinstance(h, dict) and _empty_hits(h.get("why")):
            out[f"highlights.{i}.why"] = h["why"]
    for i, g in enumerate((d.get("language") or {}).get("issues") or []):
        if isinstance(g, dict) and _empty_hits(g.get("fix")):
            out[f"language.issues.{i}.fix"] = g["fix"]
    fl = (d.get("whole_piece") or {}).get("flow")
    if isinstance(fl, dict) and _empty_hits(fl.get("demo_to")):
        out["whole_piece.flow.demo_to"] = fl["demo_to"]
    return out


def _purpose(d, path):
    """这条批语是写给谁看的、干什么用的。键名（highlights.0.why）看着像代码，
    不说清用途模型会整条跳过——0917 实测漏的就是它。"""
    if path == "focus":
        return "给老师看的「本篇讲评要点」，两三句的综合评价：总体怎么样、最拿得出手的一处、整体最大的短板"
    if path == "teacher_note":
        return "抄进稿纸「老师批改」栏的一句话，30 字以内，说给学生看的"
    if path == "parent_card":
        return "发到家长群的点评卡，跟家长说话的口气，150 字以内"
    if path == "showcase.point":
        return "这一段拿到讲评课上范读，用来讲哪一点"
    if path.startswith("highlights."):
        i = int(path.split(".")[1])
        q = ((d.get("highlights") or [{}])[i] or {}).get("quote") or ""
        return "说明学生这一句好在哪——他写的原句是「" + q + "」，就照着这一句说具体"
    if path.startswith("language.issues."):
        i = int(path.split(".")[2])
        g = ((d.get("language") or {}).get("issues") or [{}])[i] or {}
        return ("给老师看的改法示范：这孩子的毛病是「" + str(g.get("kind") or "") + "：" + str(g.get("detail") or "")
                + "」，用他自己的句子改一遍，写成「可以改成：……」")
    if path == "whole_piece.flow.demo_to":
        q = ((d.get("whole_piece") or {}).get("flow") or {}).get("demo_from") or ""
        return "把学生原句「" + q + "」改顺、或连成一个长句的示范，只说他原来那个意思"
    return "给老师看的一句批语"


def _write_back(d, path, val):
    if path in EMPTY_FIELDS:
        d[path] = val
    elif path == "showcase.point":
        d["showcase"]["point"] = val
    elif path.startswith("highlights."):
        d["highlights"][int(path.split(".")[1])]["why"] = val
    elif path.startswith("language.issues."):
        d["language"]["issues"][int(path.split(".")[2])]["fix"] = val
    elif path == "whole_piece.flow.demo_to":
        d["whole_piece"]["flow"]["demo_to"] = val


async def repair_empty_words(d):
    """空夸词命中就把那几句发回模型重写一遍——只重写这几句，不重批整篇。

    为什么非得加这一道：规则里从 0827 起就写着这些词一个都不许出现，0917 又把它从
    「整篇语言那一栏」升成管全部字段的铁律，实测照样漏（基准 C 篇的点评卡写出
    「生动地写出了他的慌乱」「栩栩如生」）。夸人的话是模型最难忍住不套模板的地方，
    提示词治不住；这里又不能像口水词那样由程序算——删掉那个词句子就不通了。
    所以走「命中再回炉」：一次纯文本调用、几百 token，只在真命中时才发生。

    两轮：第一轮常漏掉 highlights 里那句短评（键名看着像代码，它整条跳过），
    带上用途再问一次就改了。两轮还改不掉就原样留着——坏文案好过乱改，
    更好过空着一栏。
    """
    if MOCK:
        return 0
    ref = str(d.get("quoted_sentence") or "")
    n = 0
    for _ in range(2):
        hits = collect_empty_words(d)
        if not hits:
            break
        payload = {path: {"这一条是干什么的": _purpose(d, path), "现在写的": text}
                   for path, text in hits.items()}
        user = json.dumps(payload, ensure_ascii=False, indent=1)
        if ref:
            user += NL2 + "（这篇引用的学生原句是：" + ref + "　——它一个字都不能动。）"
        try:
            got = parse_json(await call_model(
                [{"role": "system", "content": REPAIR_RULES},
                 {"role": "user", "content": user}], max_tokens=2000))
        except Exception:      # noqa: BLE001 —— 校对失败不该连累整篇批改
            return n
        changed = 0
        for path, val in (got or {}).items():
            if isinstance(val, dict):     # 它照着我给的结构回了一层，取里面那句
                val = val.get("现在写的") or val.get("改写后") or ""
            if not (path in hits and isinstance(val, str) and val.strip()
                    and not _empty_hits(val)):
                continue
            # 点评卡里那句学生原话是整张卡的立身之本，回炉把它改没了就宁可不改——
            # 带一个空夸词的卡，好过一张引不出原文的卡（smoke_real 第 2 件核的就是它）。
            if path == "parent_card" and ref and _bare(ref)[:12] not in _bare(val):
                continue
            _write_back(d, path, val.strip())
            changed += 1
        n += changed
        if not changed:                   # 一轮一处没改动，再问也是同样的答案
            break
    return n

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


PINYIN_TOKEN = re.compile(r"[A-Za-züüÜāáǎàēéěè"
                          r"īíǐìōóǒòūúǔù"
                          r"ǖǘǚǜ]+")
CJK = re.compile(r"^[一-鿿]{1,2}$")


def apply_pinyin_fixes(d):
    """家长侧（parent_card / quoted_sentence）把学生用拼音代替的字换回正字。

    0917 换豆包后引用真的一字不差了，于是点评卡上会印出「粉色的kù子」——对老师这是
    保真，对家长是看不懂。用户拍板：**只在家长侧、只换拼音代字**；别字（经长）不动，
    老师看的 evidence / highlights / showcase 仍照原样。
    换哪个字由模型给（pinyin_fixes），换不换、换在哪由程序定：只换 sure=true 的、
    拼音串真在转写里出现过的、正字是 1～2 个汉字的——三道都过才动手。
    """
    fixes = d.get("pinyin_fixes")
    t = d.get("transcript") or ""
    if not isinstance(fixes, list) or not t:
        return 0
    pairs = []
    for f in fixes:
        if not isinstance(f, dict) or f.get("sure") is False:
            continue
        py, ch = str(f.get("pinyin") or "").strip(), str(f.get("char") or "").strip()
        if not py or not ch or not PINYIN_TOKEN.fullmatch(py) or not CJK.match(ch) or py not in t:
            continue
        pairs.append((py, ch))
    if not pairs:
        return 0
    pairs.sort(key=lambda x: -len(x[0]))          # 长串先换，免得 zěn 吃掉 zěnme 的一半
    n = 0
    for key in ("parent_card", "quoted_sentence"):
        v = d.get(key)
        if not isinstance(v, str) or not v:
            continue
        new = v
        for py, ch in pairs:
            new = new.replace(py, ch)
        if new != v:
            d[key] = new
            n += 1
    return n


# ---------------------------------------------------------------------------
# 独立错别字校对层（0917 立）
#
# 与主批改分开发一次纯校对调用，同一张图、各自的 system prompt，并发跑。
# 为什么不并进主批改：主批改的边界第 1 条是「批语里一个字不提错别字」，那条要继续守；
# 校对层的产物只给老师看，走自己的字段 typos，不进判据、档位、批语、点评卡。
# 为什么现在能做：豆包 2-1-pro 读的是学生写下的字（kù子、经长原样），埋字稿 8/8、0 误报；
# gpt-4o 会把自己脑补的字报成学生的错，所以这层跟着 PROOFREAD 开关走，换模型先关它。
# ---------------------------------------------------------------------------

TYPO_KINDS = ("别字", "拼音代字", "的地得")
_HAS_CJK = re.compile(r"[\u4e00-\u9fff]")
_CLAUSE_SPLIT = re.compile(r"[。！？；\n]")

PROOF_RULES = """你是小学语文老师的助手，只做一件事：核对学生手写稿纸上的错别字。不评价内容，不评价写法。

第一步，把全文逐字转写：照稿纸原样抄，写错的字、用拼音代替的字、的地得用错的地方都原样保留，
看不清的字写成 [?]；有续页就接着上一页抄成一篇。

第二步，逐句挑错，**只收下面三类**：
- 别字：写成了另一个字（座在→坐在、蓝球→篮球、以经→已经）；
- 拼音代字：不会写、用拼音代了汉字（kù子→裤子）；
- 的地得：三个字用混了（跑的很快→跑得很快）。

**标点、格式、空格、繁简、语句通不通顺，一律不报**——那些不归你。

纪律：
- 宁可漏报，不许把写得潦草但其实没错的字报成错字；看不清的字不报；
- 拿不准是哪个字的，照样列出来，sure 填 false；
- wrong 与 right 都给**词组**而不是单字（「跑的」→「跑得」，不要「的」→「得」），拼音代字的 wrong 照抄拼音含声调；
- sentence 是这一处所在的整句，与稿纸一字不差。

只输出一个 JSON 对象，不要任何解释：
{"transcript": "全文逐字转写", "typos": [{"kind": "别字｜拼音代字｜的地得", "sentence": "所在整句原样", "wrong": "稿纸上写的", "right": "应写的", "sure": true}]}
没有错别字就 "typos": []。"""


async def proofread_typos(images):
    """独立的一次纯校对调用。**任何失败都吞掉**、返回 status=failed——校对层是附加的，
    不许连累主批改；只放行取消（主批改失败时会取消它）。"""
    msgs = [{"role": "system", "content": PROOF_RULES},
            {"role": "user", "content": _pages_content(images, "只做错别字校对，只输出 JSON。")}]
    try:
        d = parse_json(await call_model(msgs, max_tokens=4000))
    except asyncio.CancelledError:
        raise
    except Exception as e:      # noqa: BLE001
        return {"status": "failed", "reason": type(e).__name__}
    items = None
    if isinstance(d, list):
        items = d
    elif isinstance(d, dict):
        for k in ("typos", "errors", "items"):
            if isinstance(d.get(k), list):
                items = d[k]
                break
    # 它明确回了、只是没有列表：算 ok 且空，不算失败
    return {"status": "ok", "items": items or []}


def _sure_flag(v):
    if isinstance(v, bool):
        return v
    t = str(v if v is not None else "").strip().lower()
    if t in ("true", "1", "确定", "是", "yes", "sure"):
        return True
    return False          # 缺省也算拿不准：宁可多进「待核」，不许把拿不准的当确定


def _clause_with(text, needle):
    for c in _CLAUSE_SPLIT.split(text):
        if needle in c:
            return c.strip()
    return None


def verify_typos(d):
    """把校对层的原始结果守门成老师能直接用的清单。三道门：只收三类、句子必须对回转写、
    错字必须真在那句里。对不上的丢、计数进 dropped，不替它猜。

    放在 postprocess 里 transcript 被 pop 之前调用。
    """
    chk = d.get("typos_check")
    if not isinstance(chk, dict):
        return
    if chk.get("status") != "ok":
        d["typos"] = None
        return
    t = d.get("transcript") or ""
    raw = d.get("typos")
    if not t:
        d["typos"] = None
        chk.update(status="failed", reason="no_transcript")
        return
    if not isinstance(raw, list):
        raw = []
    kept, dropped, seen = [], 0, set()
    for x in raw:
        if not isinstance(x, dict) or x.get("kind") not in TYPO_KINDS:
            dropped += 1
            continue
        wrong = str(x.get("wrong") or "").strip()
        right = str(x.get("right") or "").strip()
        if (not wrong or not right or _bare(wrong) == _bare(right)
                or len(wrong) > 8 or len(right) > 8
                or not (_HAS_CJK.search(wrong + right) or PINYIN_TOKEN.search(wrong))):
            dropped += 1
            continue
        sent = str(x.get("sentence") or "").strip()
        real = (_locate(sent, t) or _locate_fuzzy(sent, t)) if sent else None
        if not real:
            # 句子对不回去，但错字串本身在转写里只出现一次：拿它所在的小句救场
            real = _clause_with(t, wrong) if (len(wrong) >= 2 and t.count(wrong) == 1) else None
        if not real:
            dropped += 1
            continue
        if wrong.lower() not in real.lower():
            dropped += 1
            continue
        if len(real) > 60:
            real = _clause_with(real, wrong) or real
        key = (real, wrong, right)
        if key in seen:
            continue
        seen.add(key)
        kept.append({"kind": x["kind"], "sentence": real, "wrong": wrong, "right": right,
                     "sure": _sure_flag(x.get("sure"))})
    sure = [k for k in kept if k["sure"]]
    unsure = [k for k in kept if not k["sure"]]
    d["typos"] = (sure + unsure)[:20]
    chk.update(dropped=dropped, sure=len(sure), unsure=len(unsure))


_DANGLING_EXAMPLE = re.compile(r"[，。；\s]*(比如可以写成|可以写成|比如)[：:]\s*$")


def ensure_checks(pack, d):
    """三条判据一条不能少。0917 真稿实测：①判了未达成，模型就把②③整个省掉了——
    界面上那两行会消失，老师以为工具只有一条判据。缺的按标准包补：依赖的那条没成立就记
    「不适用」（这本来就是规则），否则记「不适用」并说明这次没判到，让老师知道是漏而不是无。"""
    have = {c.get("no"): c for c in (d.get("checks") or []) if isinstance(c, dict)}
    out = []
    for pc in pack.get("three_checks") or []:
        no = pc["no"]
        if no in have:
            out.append(have[no])
            continue
        if pc.get("check_kind") == "derived":
            out.append({"no": no, "verdict": "", "evidence": "", "comment": "", "advice": ""})
            continue
        dep = pc.get("depends_on")
        dep_v = (have.get(dep) or {}).get("verdict") if dep else None
        if dep and dep_v in ("未达成", "部分达成", "不适用"):
            out.append({"no": no, "verdict": "不适用", "evidence": "",
                        "comment": f"第 {dep} 条没成立，本条不适用。", "advice": f"先把第 {dep} 条做到。"})
        else:
            out.append({"no": no, "verdict": "不适用", "evidence": "",
                        "comment": "这一条模型这次没判到（不是「没问题」），重批一次或自己看稿。",
                        "advice": "", "suspect": True})
    d["checks"] = out


def derive_checks(pack, d):
    """标了 check_kind="derived" 的判据（judge_by 写着「前两条的结果检验，不单独判」）由程序推：
    取其它判据里最低的一档（未达成＜部分达成＜达成，「不适用」跳过；一档都没有就未达成）。
    0917 真稿实测：让模型自己判，它要么整条省掉，要么硬拿结尾套话「你们猜猜她是谁？」当依据——
    一条本来就不该单独判的尺子，交给它只会多出一处不稳。放在 focus/concrete 兜底之后、cap_band 之前，
    这样推出来的档跟着已经压过的①②走。"""
    kinds = {c["no"]: c.get("check_kind") for c in pack.get("three_checks") or []}
    checks = [c for c in (d.get("checks") or []) if isinstance(c, dict)]
    src = [c for c in checks if kinds.get(c.get("no")) != "derived"]
    for c in checks:
        if kinds.get(c.get("no")) != "derived":
            continue
        rated = [c2.get("verdict") for c2 in src if c2.get("verdict") in VERDICT_ORDER]
        worst = min(rated, key=VERDICT_ORDER.index) if rated else "未达成"
        desc = "、".join("①②③"[int(c2.get("no", 1)) - 1] + str(c2.get("verdict") or "")
                        for c2 in src if c2.get("verdict"))
        c.update(verdict=worst, evidence="", quotes=[], quotes_suspect=[], advice="",
                 comment=f"由前两条推出（{desc}），不单独判。")
        c.pop("suspect", None)


def tidy_advice(pack, d):
    """把 checks[].advice 整成老师能直接看的样子，规则都是确定性的：
    达成的不该有 advice（有就清掉）；不适用的缺 advice 就按 depends_on 补一句「先把第 N 条做到」；
    末尾挂着「比如可以写成：」却没写示范句的（0917 真稿实测出现过一次），把那截空承诺剥掉——
    留着一个冒号在屏幕上，比没有示范句更难看。"""
    dep = {c["no"]: c.get("depends_on") for c in pack.get("three_checks") or []}
    for c in d.get("checks") or []:
        if not isinstance(c, dict):
            continue
        v, adv = c.get("verdict"), str(c.get("advice") or "").strip()
        if v == "达成":
            adv = ""
        elif v == "不适用" and not adv:
            n = dep.get(c.get("no"))
            adv = f"先把第 {n} 条做到。" if n else ""
        adv = _DANGLING_EXAMPLE.sub("", adv).rstrip("，；, ")
        if adv and not adv.endswith(("。", "！", "？", "”", "」")):
            adv += "。"
        c["advice"] = adv


async def postprocess(pack, d):
    """批完之后的整条后处理链（/api/grade 与 smoke_real.py 共用这一份）。

    抽出来是因为自测脚本原先只看模型原始返回：那不是老师看到的东西，几道兜底
    都在这条链上。两处各写一遍链，迟早改一处忘另一处，自测就测不到真实结果。
    顺序有讲究：引用先对回原文（后面几道要拿它当依据），再按盘点降判据、
    按判据压档位，最后才是空夸词回炉——回炉会动到文案，所以完了要重校一次引用。
    """
    fixed, suspect = fix_quotes(d)
    recount_fillers(d)          # 这两道都必须在 transcript 被 pop 掉之前
    verify_repeats(d)           # 「用词重复」拿转写重数，数不够的删
    check_paragraphs(d)
    trim_verdict_tail(d)
    enforce_grade_rules(pack, d)
    ensure_checks(pack, d)           # 三条一条不能少，缺的按标准包补
    enforce_focus_check(pack, d)     # 先按盘点把判据降下来
    enforce_concrete_check(pack, d)  # 写没写具体，按盘点里真有画面的处数封顶
    derive_checks(pack, d)           # 结果检验型判据由①②推出，跟着压过的档走
    check_order_by_sequence(d)       # 叙述顺序照话题序列核一遍
    cap_band(pack, d)                # 再按判据把档位压下来，顺序不能反
    if await repair_empty_words(d):
        f2, s2 = fix_quotes(d)       # 回炉可能碰到引号里的原文（fix_quotes 幂等）
        fixed, suspect = fixed + f2, suspect + s2
    tidy_advice(pack, d)             # 判据「怎么改」整形：达成清空、不适用补句、剥掉空承诺
    tidy_language(d)                 # 毛病改法与语句示范整形：剥空承诺、示范缺一半就整个不要
    verify_typos(d)                  # 错别字清单守门，要用 transcript，得在 pop 之前
    d["quote_check"] = {"fixed": fixed, "suspect": suspect,
                        "pinyin_fixed": apply_pinyin_fixes(d)}   # 家长侧拼音换正字，放在所有引用校对之后
    # 模型拿不准（sure=false）的拼音会留在卡上——不替它猜字（猜错等于把一个字安到孩子头上），
    # 但要让老师在点「生成图片」前看见：这一处得他手改
    left = PINYIN_TOKEN.findall(str(d.get("parent_card") or ""))
    if left:
        d["quote_check"]["pinyin_left"] = left
    # transcript 只用于校验，不下发——老师手上有原稿，不需要看打字版；
    # survey 是判判据的依据，判完就没用了
    for k in ("transcript", "paragraph_count", "survey", "pinyin_fixes"):
        d.pop(k, None)
    return d


async def grade_pipeline(pack, images, heads, on_raw=None):
    """一份稿纸从发模型到老师能看的整条链：主批改 + 并发的错别字校对 + postprocess。

    /api/grade、run_regression.py、smoke_real.py 三处都走这一个函数——run_regression 此前
    手抄了一份后处理链，几个月下来悄悄少了六道兜底，回归测的早就不是线上行为了。

    并发不用 gather：主批改 3 秒就 502 的时候，不该陪着校对再等十几秒；
    所以先起校对 task，等主批改，主批改失败就取消校对再抛。
    """
    msgs = build_messages(pack, images, heads)
    task = asyncio.create_task(proofread_typos(images)) if PROOFREAD else None
    try:
        raw = await call_model(msgs)
    except BaseException:
        if task:
            task.cancel()
        raise
    if on_raw:
        on_raw(raw)
    out = parse_json(raw)
    if task:
        try:
            proof = await asyncio.wait_for(task, PROOF_WAIT)
        except Exception as e:      # noqa: BLE001 —— 含超时；校对失败不连累主批改
            proof = {"status": "failed", "reason": type(e).__name__}
        out["typos"] = proof.get("items")
        out["typos_check"] = {"status": proof.get("status", "failed"),
                              **({"reason": proof["reason"]} if proof.get("reason") else {})}
    await postprocess(pack, out)
    return out


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
                       "quotes": [anchors[(c["no"] + 1) % len(anchors)]],
                       "comment": f'（mock）第{c["no"]}条「{c.get("display_text") or c["text"]}」的判断说明。',
                       "advice": ("" if v == "达成" else
                                  f'先把第{c["depends_on"]}条做到' if v == "不适用" and c.get("depends_on") else
                                  f'（mock）「{anchors[(c["no"] + 1) % len(anchors)][:12]}…」这一句只是结论，'
                                  f'围绕它补一个看得见的动作。比如可以写成：他一听下课铃就蹿了出去。')})
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
        "flow": {"demo_from": q if i % 3 != 1 else "",
                 "demo_to": "（mock）他一边把笔往我桌上推，一边头也不抬地说。" if i % 3 != 1 else "",
                 "verdict": ["通顺", "个别不畅", "多处不通"][(i + 1) % 3],
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
            {"kind": "口水词", "detail": "（mock）“然后”全篇 5 次", "quote": q,
             "fix": "（mock）可以改成：把“然后”去掉，让先后顺序自己带出来。"},
            {"kind": "动词笼统", "detail": "（mock）这一处本可以写出具体动作", "quote": q,
             "fix": "（mock）可以改成：他把那支笔往我桌上一推，头也不抬。"},
            # 「读出来」的那两类也进 mock：前端要能显示它们，也好看出没有数字的 detail 长什么样
            {"kind": "用词不当", "detail": "（mock）“慈祥”用来说批评时的样子不合适", "quote": q,
             "fix": "（mock）可以改成：换成“板着脸”“沉着脸”，写成“他沉着脸把本子递回来”。"},
            {"kind": "修辞不当", "detail": "（mock）“像天上的星星”这个比方谁都写得出，看不出他自己看见了什么",
             "quote": q,
             "fix": "（mock）可以改成：从这件事里找个东西打比方——“他的眼睛亮得像刚擦过的玻璃珠”。"},
        ][: 1 + i % 4],
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
        "focus": "（mock）整篇能看出他在围绕一个特点写，最拿得出手的是那个动作细节；短板是别的段落还停在结论句上，没把画面写出来。",
        "teacher_note": "（mock）这处细节写得实在，再多写一件事就更好了。",
        "showcase": {"suitable": i % 3 == 0, "paragraph": q, "point": "写具体"},
        "quoted_sentence": q,
        "parent_card": (f"（mock 假数据）{opens[i % len(opens)]}“{q}”。"
                        "这一句好在没有停在结论上，而是把当时的样子写了出来，"
                        "正是这次课上练的那一招。下次可以试着再为这个地方补一件小事，"
                        "人物就更立得住了。"),
        # 错别字校对层三态轮换 + 每五份一次「没跑成」，前端四种形态都能看到
        "typos": (None if i % 5 == 0 else
                  [] if i % 3 == 0 else
                  [{"kind": "别字", "sentence": anchors[0], "wrong": "座", "right": "坐", "sure": True}]
                  if i % 3 == 1 else
                  [{"kind": "别字", "sentence": anchors[0], "wrong": "以经", "right": "已经", "sure": True},
                   {"kind": "拼音代字", "sentence": anchors[1 % len(anchors)], "wrong": "kù", "right": "裤", "sure": True},
                   {"kind": "的地得", "sentence": anchors[2 % len(anchors)], "wrong": "跑的", "right": "跑得", "sure": False}]),
        "typos_check": ({"status": "failed", "reason": "mock"} if i % 5 == 0
                        else {"status": "ok", "dropped": 0}),
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
                image: Optional[UploadFile] = File(None),
                images: List[UploadFile] = File([])):
    # 一份作文可以是多页（稿纸 + 续页）：前端按页序以多个同名 `images` 字段上传。
    # 旧的单字段 `image` 仍收——两种都给时以 `images` 为准，一个都没给才报错。
    pack = PACKS.get(lesson_id)
    if not pack:
        raise HTTPException(404, "未找到该课次的标准包")
    if not _rate_ok(_client_ip(request)):
        raise HTTPException(429, "本小时批改次数已达上限，请稍后再试（防盗刷限额）")

    pages = images or ([image] if image else [])
    if not pages:
        raise HTTPException(400, "没有收到稿纸照片")
    if len(pages) > MAX_PAGES:
        raise HTTPException(400, f"一份作文最多 {MAX_PAGES} 页，请检查是否把别人的稿纸拍进来了")
    raws = [await f.read() for f in pages]
    # 限的是一份的总量：Vercel 请求体硬限 4.5MB 是按整个请求算的，不是按张算
    if sum(map(len, raws)) > CFG["max_image_mb"] * 1024 * 1024:
        raise HTTPException(413, f'照片合计超过 {CFG["max_image_mb"]}MB，请压缩后重新上传')

    if MOCK:
        return mock_grade(pack)

    heads = json.loads(prev_heads or "[]")
    images = [(base64.b64encode(r).decode(), f.content_type or "image/jpeg")
              for r, f in zip(raws, pages)]
    out = await grade_pipeline(pack, images, heads)

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
