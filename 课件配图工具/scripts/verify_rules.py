# -*- coding: utf-8 -*-
"""五项待验规则的验证脚本（PRD §7 开发前置）· 双通道。

用《猜猜他是谁》打样清单的最小验证集（定妆 A / P6 / P16 / 剪影转制，另借 P13 测数量）
把五条经验规则在指定生图通道上跑一遍，逐项给结论，供写入规则库。

⚠ **每条结论都只对它被测出来的那条通道成立**。豆包上测得的结论换到 Gemini 一律作废，
反之亦然——PRD §7 说「Gemini 的经验迁到豆包必须重验」，反过来同样成立。
故 `--provider` 换通道时输出目录也跟着换，两边结论各存各的、不互相覆盖。

  T1 头身比控制      —— 文本写死比例 vs 参考图传递，哪个真起作用
  T2 禁止式表述      —— 「恰好 N 个」正向 vs 「不要超过 N 个」禁止式
  T3 局部编辑可靠性  —— 形状/风格类（剪影转制、改衣服颜色）vs 数量类
  T4 画面内中文      —— 主动要求渲染中文书名 / 禁区句是否挡得住背景杂字
  T5 多参考图权重    —— 定妆图与风格锚同挂谁主导，能否用文字指派角色

用法：
  python scripts/verify_rules.py --provider gemini      # 在 Gemini 上全跑
  python scripts/verify_rules.py --provider doubao      # 在豆包上全跑
  python scripts/verify_rules.py --only T1 T3           # 只跑指定项
  python scripts/verify_rules.py --reuse --outdir <目录> # 复用已有图，只重算结论（不再计费生图）
  python scripts/verify_rules.py --no-judge             # 只出图不做机器判读（人工看图）

产物：验证输出/<时间戳>/  下逐项子目录 + 结果.json + 验证报告.md
密钥只从环境变量 / .env 读，见 ark_client.py。
"""
import argparse
import datetime
import json
import pathlib
import re
import sys
import traceback

from imgclient import make_client
from measure_ratio import measure

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parents[1]

# ---- 打样清单 §一 的通用风格前缀（逐字取用）----
PREFIX = ("儿童水彩插画风格，柔和笔触，明快干净的配色，暖黄色调光线，"
          "主体人物为8到9岁的中国小学生，头身比约1比4.5，"
          "背景适度留白，画面中不出现任何文字。")
# 去掉头身比那一句，用于 T1 的对照组
PREFIX_NO_RATIO = ("儿童水彩插画风格，柔和笔触，明快干净的配色，暖黄色调光线，"
                   "主体人物为8到9岁的中国小学生，"
                   "背景适度留白，画面中不出现任何文字。")

CHAR = ("一个8岁的中国男孩，短而蓬松的深棕色头发，戴一副圆框黑边眼镜，"
        "穿浅蓝色圆领毛衣、内搭白色衬衫领")



class Ctx:
    """一次运行的上下文：输出目录、图片清单、结论表。"""

    def __init__(self, outdir, client, reuse=False, judge=True, samples=None):
        self.outdir = pathlib.Path(outdir)
        self.client = client
        self.reuse = reuse
        self.judge_on = judge
        self.samples = samples
        self.shots = []
        self.results = []

    def n(self, key, default):
        """该组跑几张：`--samples` 给了就全局覆盖，否则用各组自己的缺省。"""
        return self.samples or default

    def shot(self, tag, prompt, ratio="1:1", images=None, seed=None):
        """生成一张图并落盘，返回本地路径。--reuse 时命中已有文件就不再调 API。"""
        sub, name = tag.split("/", 1)
        dest = self.outdir / sub / (name + ".jpg")
        if self.reuse and dest.exists():
            print(f"  [复用] {tag}")
            self.shots.append({"tag": tag, "path": str(dest), "prompt": prompt,
                               "ratio": ratio, "refs": [str(i) for i in (images or [])],
                               "reused": True})
            return dest
        print(f"  [生成] {tag} ({ratio}){' ←参考' + str(len(images)) + '张' if images else ''}")
        data = self.client.generate(prompt, ratio=ratio, images=images, seed=seed)
        self.client.save(data, dest)
        self.shots.append({"tag": tag, "path": str(dest), "prompt": prompt, "ratio": ratio,
                           "refs": [str(i) for i in (images or [])], "reused": False})
        return dest

    def ask(self, images, question):
        if not self.judge_on:
            return {"_skipped": "已关闭机器判读"}
        print(f"  [判读] {[pathlib.Path(i).name for i in images]}")
        return self.client.judge(images, question)

    def record(self, tid, item, gemini, method, observed, verdict, rule):
        self.results.append({"编号": tid, "待验项": item, "Gemini 结论": gemini,
                             "做法": method, "观察": observed,
                             "豆包结论": verdict, "建议入库规则": rule})
        print(f"  == {tid} 结论：{verdict}")


JSON_ONLY = "只回一个 JSON 对象，不要任何解释文字、不要 markdown 代码块。"


def judge_failed(obs):
    """判读是否整体失败——失败必须当场喊出来，绝不能当成「判定不通过」。

    两种失败都要拦，它们都是「未知」而不是「否定」：
      _error  请求本身挂了（2026-08-27 账户欠费，判读全返 403，各项 verdict 照常
              取值取到 None，报告白纸黑字写出「剪影转制不过」「书名有错字」，与实际图相反）；
      _raw    回了内容但没解析成 JSON（模型在字符串里打真实换行，JSON 非法）。
              同日实测把一张书名逐字全对的图算成有错字，T4 一度显示 4/5。
    第二种是我补第一道闸门时漏掉的口子——同一类错误犯两次，故两者一并拦在这里。
    """
    txt = json.dumps(obs, ensure_ascii=False)
    n_err, n_raw = txt.count('"' + "_error" + '"'), txt.count('"' + "_raw" + '"')
    if not n_err and not n_raw:
        return None
    if n_err:
        m = re.search('"' + "_error" + '"' + r':\s*"([^"]{0,120})', txt)
        why = "判读请求失败 %d 处（%s…）" % (n_err, m.group(1) if m else "原因未知")
    else:
        why = "判读结果 %d 处未能解析成 JSON（落进 _raw）" % n_raw
    return "⚠ %s，本项不出结论——图已在盘，修好后 --reuse 重跑即可" % why

def prepare_base(ctx):
    """定妆 A（打样清单 §二 逐字 prompt，半身像）——T3/T5 都要用它当参考图。"""
    p = (PREFIX + " " + CHAR + "；正面半身像，微笑时眼睛眯成两条弯弯的缝，"
         "右手抬起用食指轻推眼镜；纯浅色背景")
    return ctx.shot("00-基准/定妆A-半身", p, "1:1")


def t1_head_body(ctx):
    """T1 头身比：文本控制 vs 参考图传递。半身像量不出比例，故本项用全身站立像。

    每档跑两张。单张比不出结论——同一 prompt 两次之间本来就有零点几头的波动，
    必须先看清组内波动有多大，才能判断组间那点差异是不是真的。
    """
    body = "；正面全身站立像，双臂自然下垂，完整入镜含双脚，纯浅色背景，无其他人物"
    ref = ctx.outdir / "00-基准" / "定妆A-半身.jpg"
    arms = {
        "1a-文本写1比4.5": (PREFIX + " " + CHAR + body, None),
        "1b-文本写1比7": (PREFIX.replace("头身比约1比4.5", "头身比约1比7") + " " + CHAR + body, None),
        "1c-不写比例挂定妆A": (PREFIX_NO_RATIO + " " + CHAR + body, [ref]),
    }
    q = ("看这张全身像。" + JSON_ONLY +
         ' 格式：{"是否全身入镜含双脚":true/false,"画面里人物个数":整数,'
         '"看上去更像":"幼童体型/学龄儿童体型/少年或成人体型"}')
    obs, ratios = {}, {}
    for name, (prompt, refs) in arms.items():
        rs, per = [], []
        for i in range(1, ctx.n("T1", 2) + 1):
            f = ctx.shot(f"T1-头身比/{name}-{i}", prompt, "3:4", images=refs, seed=200 + i)
            m = measure(f)                       # 像素量测，不问视觉模型
            per.append({"样本": i, "像素量测": m, "视觉判读": ctx.ask([f], q)})
            if m and isinstance(m.get("头身比"), (int, float)):
                rs.append(m["头身比"])
        obs[name] = per
        ratios[name] = rs

    def avg(k):
        """取中位数不取均值：单个量测炸掉就能把均值拖走。

        ⚠ 实测 Gemini 的 1b-4 被量成 6.1 头身（目测其实约 4.5），把该组均值整个带偏；
        根因是它背景有片淡晕染，没到拒答阈值却已经把颈线判歪。中位数扛得住这种离群，
        但**扛得住不等于测得准**——离群率本身要报出来，见下面的可靠性判断。
        """
        v = sorted(ratios[k])
        if not v:
            return None
        n = len(v)
        return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2

    a, b, c = avg("1a-文本写1比4.5"), avg("1b-文本写1比7"), avg("1c-不写比例挂定妆A")
    spread = max((max(v) - min(v)) for v in ratios.values() if len(v) > 1) if any(
        len(v) > 1 for v in ratios.values()) else 0
    if a and b:
        text_gap = abs(b - a)
        # 判「文本有效」要同时过两关：① 组间差大于组内波动 ② **方向对**。
        # ⚠ 只比绝对值会把「反着动」判成有效——实测 Gemini 上写 1:7（更修长）反而得到
        #    更小的读数，方向完全相反。方向错的变化不是控制，是噪声，甚至更糟。
        big_enough = text_gap > spread
        right_way = b > a                    # 写 1:7 应当比写 1:4.5 得到更大的头身比
        if big_enough and right_way:
            tail = "有效"
        elif big_enough and not right_way:
            tail = ("**方向相反**——写更修长的 1:7 反而得到更矮胖的读数，"
                    "说明文本没在控制比例（读数变化另有来源，如取景/构图变了）")
        else:
            tail = "无效（差异淹没在噪声里，写什么都出同一档）"
        verdict = ("文本组：写 1:4.5 得 %.2f 头、写 1:7 得 %.2f 头，差 %.2f，"
                   "而同一 prompt 重跑的组内波动就有 %.2f —— 文本控制%s" % (
                       a, b, text_gap, spread, tail))
        if c:
            verdict += ("；不写比例改挂定妆 A 得 %.2f 头，较文本组移动 %.2f —— 参考图%s"
                        % (c, abs(c - a), "确实在传递比例" if abs(c - a) > spread else "影响也不显著"))
    else:
        verdict = "量测失败（人物未全身入镜或背景不纯），须人工目测"
    verdict = judge_failed(obs) or verdict
    # 量测可靠性自检：拒答太多或极差过大，就不该拿这批数字下结论
    n_ok = sum(len(v) for v in ratios.values())
    n_all = sum(len(v) for v in obs.values())
    widest = max((max(v) - min(v)) for v in ratios.values() if len(v) > 1) if any(
        len(v) > 1 for v in ratios.values()) else 0
    if n_ok < n_all * 0.7 or widest > 1.5:
        verdict = ("⚠ 量测不可靠，本项不出结论：%d/%d 张可量（其余因背景不纯拒答），"
                   "组内极差最大 %.2f 头——单张量测已被证实会炸（如把 4.5 头身量成 6.1）。"
                   "该通道的图背景常带装饰晕染，本像素量测法在此失效，"
                   "须改用干净背景重出、或换非像素的测量手段。原始读数：%s"
                   % (n_ok, n_all, widest,
                      {k: [round(x, 2) for x in v] for k, v in ratios.items()}))
    ctx.record("T1", "头身比控制", "prompt 文本无效，靠参考图",
               "三档各两张：文本写 1:4.5 / 文本写 1:7 / 不写比例但挂定妆 A；头身比用像素量测",
               obs, verdict,
               "头身比不写进 prompt（写了也不动），一律靠定妆图参考传递；"
               "且定妆图的取景会带偏比例——比例基准必须是全身定妆图，不能拿半身像当参考。")


def t2_negative(ctx):
    """T2 禁止式表述：正向数值 vs 禁止式，两条探针。

    ⚠ 场景描述里不能把人物逐个点名。第一版照搬了 P13 的 prompt（眼镜男孩＋马尾女孩＋
    前景两个男孩），数量被逐个点名重复锁定，两个臂都出四个人——测的其实是场景描述，
    不是那句数量话术。故这里改成不点名个体的通用场景，让数量只由待测的那一句承担。

    探针一（数量）：「画面中恰好三个孩子」 vs 「不要超过三个、不要出现第四个」
    探针二（禁物）：只给禁止式、没有正向替代——风格卡的「通用禁区」整栏都是这种句子，
                    它到底管不管用，比数量更该问。
    """
    base = (" 围坐在一张木色课桌旁讨论，桌上放着白纸和铅笔，明亮的教室，木色课桌")
    pos = PREFIX + " 画面中恰好三个8到9岁的中国小学生" + base
    neg = (PREFIX + " 一群8到9岁的中国小学生" + base +
           "；不要画超过三个孩子，不要出现第四个孩子，也不要少于三个孩子")
    ban = (PREFIX + " 画面中恰好三个8到9岁的中国小学生" + base +
           "；画面里不要出现红领巾，不要出现任何红色的领巾或领结")
    shots = {}
    for i in range(1, ctx.n("T2", 5) + 1):
        shots[f"2a-正向恰好三个-{i}"] = ctx.shot(f"T2-禁止式/2a-正向恰好三个-{i}", pos, "1:1", seed=300 + i)
        shots[f"2b-禁止式不超过三个-{i}"] = ctx.shot(f"T2-禁止式/2b-禁止式不超过三个-{i}", neg, "1:1", seed=300 + i)
        shots[f"2c-禁物禁止红领巾-{i}"] = ctx.shot(f"T2-禁止式/2c-禁物禁止红领巾-{i}", ban, "1:1", seed=300 + i)
    q = ("数一数画面里一共有几个孩子（含背对镜头、只露半身的都算），并看有没有红领巾。" +
         JSON_ONLY + ' 格式：{"孩子人数":整数,"是否出现红领巾或红色领巾":true/false}')
    obs = {k: ctx.ask([v], q) for k, v in shots.items()}

    def cnt(prefix):
        return [obs[k].get("孩子人数") for k in obs if k.startswith(prefix)]

    a, b = cnt("2a"), cnt("2b")
    na, nb = len(a), len(b)
    hit_a, hit_b = a.count(3), b.count(3)
    ban = [k for k in obs if k.startswith("2c")]
    ban_hit = sum(1 for k in ban if obs[k].get("是否出现红领巾或红色领巾") is False)
    # ⚠ 分母一律用 len()，别写死样本数——改了 ctx.n 却漏改这里，会让 5/5 全中印成「不稳」
    verdict = ("数量：正向命中 %d/%d（实得 %s），禁止式命中 %d/%d（实得 %s）——%s；"
               "纯禁止（禁红领巾）命中 %d/%d——禁止式%s" % (
                   hit_a, na, a, hit_b, nb, b,
                   "两种写法都能锁住数量" if hit_a == na and hit_b == nb else
                   "禁止式不如正向可靠" if hit_b < hit_a else
                   "正向也不稳，数量类须逐张勾验",
                   ban_hit, len(ban), "在「去掉某样东西」上有效" if ban_hit == len(ban) else
                   "在「去掉某样东西」上不可靠"))
    verdict = judge_failed(obs) or verdict
    ctx.record("T2", "禁止式表述", "无效，只认正向数值",
               "不点名个体的通用场景：正向「恰好三个」/ 禁止式「不超过三个」各两张；"
               "另加一条纯禁止式「不要出现红领巾」两张", obs, verdict,
               "组装级规则：数量一律写「画面中恰好 N 个」；"
               "风格卡「通用禁区」这类纯禁止句按本项实测结论决定是否保留、并逐张勾验。")


def t3_edit(ctx):
    """T3 局部编辑：形状/风格类（剪影转制、改毛衣色）vs 数量类（三人改两人）。

    样本数按「这条结论有多反直觉」分配：剪影/改色与旧规则一致且肉眼一望即知，各 3 张；
    数量类是推翻旧规则的那一条（Gemini 判它不可靠），加到 5 张。
    """
    base = ctx.outdir / "00-基准" / "定妆A-半身.jpg"
    src = ctx.outdir / "T2-禁止式" / "2a-正向恰好三个-1.jpg"   # 取 T2 的三人图当底
    n_shape, n_count = ctx.n("T3形状", 3), ctx.n("T3数量", 5)
    sil = [ctx.shot(f"T3-局部编辑/3a-剪影转制-{i}",
                    "把参考图中的男孩转为深蓝色（#3D4A6B）纯剪影胸像，"
                    "只保留外轮廓，发型轮廓与推眼镜的姿势完全保持不变，"
                    "五官、衣服花纹一律不画，背景纯白，画面中不出现任何文字",
                    "1:1", images=[base], seed=400 + i) for i in range(1, n_shape + 1)]
    col = [ctx.shot(f"T3-局部编辑/3b-改毛衣颜色-{i}",
                    "参考图中的男孩，只把浅蓝色毛衣改成砖红色，"
                    "发型、眼镜、姿势、表情、背景全部保持不变",
                    "1:1", images=[base], seed=410 + i) for i in range(1, n_shape + 1)]
    cnt = [ctx.shot(f"T3-局部编辑/3c-三人改两人-{i}",
                    "参考图中围坐的孩子改成画面中恰好两个孩子，"
                    "去掉最左边那一个，其余人物、桌面物品、构图与画风保持不变",
                    "1:1", images=[src], seed=420 + i) for i in range(1, n_count + 1)
           ] if src.exists() else []
    q_sil = ("判断第二张图（第一张是原图）。" + JSON_ONLY +
             ' 格式：{"是否纯单色剪影":true/false,"是否画了五官":true/false,'
             '"发型轮廓是否与第一张一致":true/false,"是否有推眼镜姿势":true/false}')
    q_col = ("对比两张图（第一张原图，第二张修改后）。" + JSON_ONLY +
             ' 格式：{"毛衣颜色":"颜色词","发型是否改变":true/false,"眼镜是否改变":true/false,'
             '"姿势是否改变":true/false,"背景是否改变":true/false}')
    q_cnt = ("数一数第二张图里一共有几个孩子，并与第一张对比。" + JSON_ONLY +
             ' 格式：{"修改后孩子人数":整数,"原图孩子人数":整数,"画风是否保持":true/false,'
             '"构图是否大体保持":true/false}')
    obs = {"3a-剪影转制": [ctx.ask([base, f], q_sil) for f in sil],
           "3b-改毛衣颜色": [ctx.ask([base, f], q_col) for f in col],
           "3c-三人改两人": [ctx.ask([src, f], q_cnt) for f in cnt]}
    ok_sil = sum(1 for r in obs["3a-剪影转制"]
                 if r.get("是否纯单色剪影") and r.get("发型轮廓是否与第一张一致")
                 and not r.get("是否画了五官"))
    ok_col = sum(1 for r in obs["3b-改毛衣颜色"]
                 if not r.get("发型是否改变") and not r.get("姿势是否改变")
                 and not r.get("背景是否改变"))
    ok_cnt = sum(1 for r in obs["3c-三人改两人"] if r.get("修改后孩子人数") == 2)
    verdict = ("剪影转制 %d/%d；改色保真 %d/%d；数量类（三人→两人）%d/%d —— 形状/风格类%s，数量类%s"
               % (ok_sil, len(sil), ok_col, len(col), ok_cnt, len(cnt),
                  "可靠" if ok_sil == len(sil) and ok_col == len(col) else "有失手",
                  "可靠" if cnt and ok_cnt == len(cnt) else
                  "基本可用但会失手（%d/%d）" % (ok_cnt, len(cnt)) if cnt else "未测"))
    verdict = judge_failed(obs) or verdict
    ctx.record("T3", "局部编辑可靠性", "形状/风格可靠、数量不可靠",
               "定妆A→剪影 ×%d / 定妆A→改毛衣色 ×%d / 三人图→两人 ×%d"
               % (len(sil), len(col), len(cnt)), obs, verdict,
               "校验级规则：剪影转制与颜色、材质类改动走图像编辑通道；"
               "人数增减按实测命中率决定是否放行，放行也须逐张数人数。")


# T4 的中文渲染按字数分档，用来找「能放开到多长」的边界
# ⚠ 字数一律从目标字串实算，不要手写——第一版手写成 11/24，实际是 10/18，
#    而这几个数字正是本项要量的东西，写错等于结论错。
# 分档看的是**最长单串**，不是画面上的总字数：五个字排两行和十八个字排两行，
# 难的从来不是总量而是一串里连着几个字不能错。
CN_TIERS = [
    ("短标题", ["猜猜他是谁", "人物图鉴"],
     "封面上部印着黑色宋体中文书名「猜猜他是谁」，"
     "书名下方印一行较小的中文「人物图鉴」，字迹清晰端正"),
    ("中句", ["今天我们来猜猜他是谁"],
     "封面上部印着一行黑色宋体中文「今天我们来猜猜他是谁」，排成一行，字迹清晰端正"),
    ("长句", ["写一个人，要抓住他和别人不一样的地方"],
     "封面上部印着黑色宋体中文「写一个人，要抓住他和别人不一样的地方」，"
     "排成两行，字迹清晰端正"),
]


def t4_chinese(ctx):
    """T4 画面内中文：能不能渲染、能渲染到多长、禁区句能不能挡住背景杂字。

    ⚠ 只测一句短标题不足以放开规则。「书名五个字对了」推不出「一句话也对」——
    画面内文字一旦放开就会有人拿去印长句，故必须先量出字数边界再写规则。
    """
    sil = ctx.outdir / "T3-局部编辑" / "3a-剪影转制-1.jpg"
    refs = [sil] if sil.exists() else None
    book_base = (PREFIX.replace("，画面中不出现任何文字", "") +
                 " 一本白色封面的书册微微向左倾斜，带轻微投影；"
                 "封面画面为一个深蓝色男孩剪影站在绿色教室黑板前，黑板带木色边框和粉笔槽；")
    q_b = ("逐字读出这张书封图上印的全部中文，一个字都不要漏、不要猜、不要补全成通顺的话；"
           "笔画不成字的写成「乱码」。" + JSON_ONLY +
           ' 格式：{"画面上的文字":"逐字照抄","是否有错字漏字或乱码":true/false}')
    obs, tiers = {}, {}
    for idx, (name, target, desc) in enumerate(CN_TIERS):
        nchar = max(len(x) for x in target)
        n = ctx.n("T4短标题" if idx == 0 else "T4长文", 5 if idx == 0 else 3)
        tag = ["4a-书封渲染中文", "4c-中句", "4d-长句"][idx]
        rs = []
        for i in range(1, n + 1):
            f = ctx.shot(f"T4-画面内中文/{tag}-{i}", book_base + desc, "3:4",
                         images=refs, seed=430 + idx * 10 + i)
            rs.append(ctx.ask([f], q_b))
        obs[f"{tag}（{name}·最长单串{nchar}字·目标{"+".join(target)}）"] = rs
        tiers[name] = (sum(1 for r in rs if r.get("是否有错字漏字或乱码") is False), len(rs))

    nb = ctx.n("T4禁区", 3)
    runs = [ctx.shot(f"T4-画面内中文/4b-禁区句挡杂字-{i}",
                     PREFIX + " 一个8岁的中国女孩在红色塑胶跑道上奔跑，跑道有白色分道线，"
                     "背景是浅色树影和学校操场看台；她有一头蓬松的深棕色卷发，"
                     "跑动中卷发向上跳起、形状像一团小火苗，"
                     "她一边跑一边抬起右手把头发往耳朵后面塞；"
                     "穿白色短袖校服、系红色领结、深蓝色百褶短裙；表情开朗大笑",
                     "3:4", seed=460 + i) for i in range(1, nb + 1)]
    q_r = ("看这张图里有没有任何文字（含背景招牌、衣服上的字母、水印）。" + JSON_ONLY +
           ' 格式：{"是否出现文字":true/false,"出现的文字内容":"照抄，没有则空字符串"}')
    obs["4b-禁区句挡杂字"] = [ctx.ask([f], q_r) for f in runs]
    ok_ban = sum(1 for r in obs["4b-禁区句挡杂字"] if r.get("是否出现文字") is False)

    verdict = ("主动渲染中文按字数分档：" +
               "、".join("%s(最长单串%d字) %d/%d" % (n, max(len(x) for x in t), tiers[n][0], tiers[n][1])
                        for n, t, _ in CN_TIERS) +
               "；禁区句挡杂字 %d/%d" % (ok_ban, len(runs)))
    verdict = judge_failed(obs) or verdict
    ctx.record("T4", "画面内中文", "不可靠，一律版式层承担",
               "书封渲染中文按 %s 字三档各跑数张找边界；另跑 P16 跑道场景查背景杂字"
               % "/".join(str(max(len(x) for x in t)) for _, t, _ in CN_TIERS),
               obs, verdict,
               "默认仍关闭画面内文字、由 PPT 版式承担（版式的字可改，生成的字不可改）；"
               "规则库开一个按字数的场景级开关，阈值取实测全对的最高一档，且每张逐字勾验。")


def t5_multiref(ctx):
    """T5 多参考图权重：定妆图（人物）+ 异风格锚（风格）同挂，谁主导、能否文字指派。

    风格锚故意做成与水彩明显不同的厚涂油画，否则「风格听谁的」无从分辨。
    场景取 P6（跨页一致性检验页），顺带看主角色三要素是否守得住。
    """
    base = ctx.outdir / "00-基准" / "定妆A-半身.jpg"
    anchor = ctx.shot("T5-多参考图/5-锚图-厚涂油画教室",
                      "厚涂油画风格，浓重笔触，深沉的暗绿与褐色调，强烈明暗对比，"
                      "一间空教室的内景，木色课桌、绿色黑板、侧窗透进冷光，"
                      "没有人物，画面中不出现任何文字", "1:1")
    p6 = ("挂参考图中的同一个男孩，坐在靠窗的木色课桌前，左手边是绿色黑板一角，"
          "窗外暖阳光洒进教室，他右手食指轻推圆框眼镜，眯眼微笑看向画面外")
    assign = ("人物形象参考第一张图（发型、眼镜、毛衣完全照第一张），"
              "画面风格参考第二张图（笔触与色调照第二张）。")
    # a/b 带水彩风格前缀：测「文本风格描述 vs 风格锚图」谁说了算
    a = ctx.shot("T5-多参考图/5a-带风格前缀-不指派", PREFIX + " " + p6, "3:4", images=[base, anchor])
    b = ctx.shot("T5-多参考图/5b-带风格前缀-文字指派", PREFIX + " " + assign + p6, "3:4",
                 images=[base, anchor])
    # c/d 去掉风格前缀：文本不再插手，才测得出「定妆图 vs 风格锚」两张参考之间谁主导
    bare = "8到9岁的中国小学生，背景适度留白，画面中不出现任何文字。"
    c = ctx.shot("T5-多参考图/5c-无风格前缀-不指派", bare + " " + p6, "3:4", images=[base, anchor])
    d = ctx.shot("T5-多参考图/5d-无风格前缀-文字指派", bare + " " + assign + p6, "3:4",
                 images=[base, anchor])
    q = ("第一张是人物定妆图，第二张是风格锚图（厚涂油画），第三张是生成结果。" + JSON_ONLY +
         ' 格式：{"结果画风更像":"水彩/厚涂油画/两者之间",'
         '"人物是否与定妆图同一个孩子":true/false,"发型一致":true/false,'
         '"圆框眼镜一致":true/false,"浅蓝毛衣一致":true/false}')
    names = {"5a-带前缀-不指派": a, "5b-带前缀-指派": b,
             "5c-无前缀-不指派": c, "5d-无前缀-指派": d}
    obs = {k: ctx.ask([base, anchor, v], q) for k, v in names.items()}
    st = {k: obs[k].get("结果画风更像") for k in names}
    id_ok = sum(1 for k in names if obs[k].get("人物是否与定妆图同一个孩子"))
    verdict = ("带水彩文本前缀时：不指派→「%s」、指派→「%s」（文本前缀%s压过油画锚图）；"
               "去掉风格前缀后：不指派→「%s」、指派→「%s」（两张参考之间%s）；"
               "人物同一性 %d/4 守住。" % (
                   st["5a-带前缀-不指派"], st["5b-带前缀-指派"],
                   "能" if "水彩" in str(st["5a-带前缀-不指派"]) else "未能",
                   st["5c-无前缀-不指派"], st["5d-无前缀-指派"],
                   "文字指派改变了结果" if st["5c-无前缀-不指派"] != st["5d-无前缀-指派"]
                   else "文字指派没改变结果",
                   id_ok))
    verdict = judge_failed(obs) or verdict
    ctx.record("T5", "多参考图权重", "（Gemini 未测）",
               "定妆图 + 异风格锚（厚涂油画）同挂跑 P6，四张：带/不带水彩文本前缀 × 指派/不指派。"
               "⚠ 只跑带前缀那两张会把「文本 vs 锚图」和「锚图 vs 定妆图」混成一件事", obs, verdict,
               "组装级规则：多参考图须在 prompt 内显式写明「人物参考第 N 张、风格参考第 M 张」；"
               "若无效则改为定妆图单挂 + 风格靠前缀文本承担。")


TESTS = {"T1": t1_head_body, "T2": t2_negative, "T3": t3_edit, "T4": t4_chinese, "T5": t5_multiref}


def write_report(ctx, outdir):
    (outdir / "结果.json").write_text(json.dumps(
        {"通道": ctx.client.name, "模型": ctx.client.model,
         "判读模型": ctx.client.vision_model,
         "用量": ctx.client.usage, "结论": ctx.results, "图片清单": ctx.shots},
        ensure_ascii=False, indent=2), encoding="utf-8")
    L = [f"# 五项待验规则 · 验证报告（通道：{ctx.client.name}）", "",
         "> ⚠ 本报告的每条结论**只对上面这条通道成立**，换通道须整套重验。", "",
         f"- 生图模型：`{ctx.client.model}`",
         f"- 判读模型：`{ctx.client.vision_model}`（机器判读只作初筛，结论以人工看图为准）",
         f"- 用量（**仅本轮**；`--reuse` 复用的图不重复计费）：新生成 "
         f"{ctx.client.usage['images']} 张 / 输出 {ctx.client.usage['output_tokens']} tokens；"
         f"判读 {ctx.client.usage['vision_calls']} 次",
         f"- 本目录累计留存 {len(list(outdir.rglob('*.jpg')))} 张图（含各项对照组与废版）", "",
         "| 编号 | 待验项 | Gemini 结论 | 豆包结论 |", "|---|---|---|---|"]
    for r in ctx.results:
        L.append("| %s | %s | %s | %s |" % (r["编号"], r["待验项"], r["Gemini 结论"], r["豆包结论"]))
    L += ["", "## 逐项详情", ""]
    for r in ctx.results:
        L += [f"### {r['编号']} · {r['待验项']}", "",
              f"- **做法**：{r['做法']}", f"- **豆包结论**：{r['豆包结论']}",
              f"- **建议入库规则**：{r['建议入库规则']}", "",
              "```json", json.dumps(r["观察"], ensure_ascii=False, indent=2), "```", ""]
    (outdir / "验证报告.md").write_text("\n".join(L), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="豆包 Seedream 五项待验项验证")
    ap.add_argument("--only", nargs="*", choices=list(TESTS), help="只跑指定项")
    ap.add_argument("--reuse", action="store_true", help="复用已存在的图，不重复生图")
    ap.add_argument("--no-judge", action="store_true", help="不做机器判读")
    ap.add_argument("--outdir", help="指定输出目录（默认 验证输出/<通道>-<时间戳>/）")
    ap.add_argument("--provider", choices=["gpt-image", "gemini", "doubao"],
                    help="生图通道（缺省读 .env 的 IMAGE_PROVIDER）。结论只对所测通道成立")
    ap.add_argument("--samples", type=int,
                    help="覆盖各组样本数（不给则用各组缺省：T2=5、T3形状=3、T3数量=5、"
                         "T4短标题=5、T4长文=3、T4禁区=3）")
    args = ap.parse_args()

    client = make_client(args.provider)
    outdir = pathlib.Path(args.outdir) if args.outdir else (
        ROOT / "验证输出" / f"{client.name}-{datetime.datetime.now().strftime('%Y%m%d-%H%M')}")
    outdir.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(outdir, client, reuse=args.reuse, judge=not args.no_judge,
              samples=args.samples)
    print(f"输出目录：{outdir}\n生图模型：{client.model}\n")

    todo = args.only or list(TESTS)
    # T2 的四人图是 T3c 的输入；T3a 的剪影是 T4a 的参考——按固定序跑
    todo = [t for t in TESTS if t in todo]
    print("[准备] 定妆 A（T1c/T2/T3/T5 共用参考图）")
    prepare_base(ctx)
    for tid in todo:
        print(f"\n[{tid}]")
        try:
            TESTS[tid](ctx)
        except Exception as e:
            traceback.print_exc()
            ctx.record(tid, tid, "-", "-", {"_error": repr(e)}, f"运行失败：{e}", "-")
    write_report(ctx, outdir)
    print(f"\n完成。用量 {client.usage}\n报告：{outdir / '验证报告.md'}")


if __name__ == "__main__":
    main()
