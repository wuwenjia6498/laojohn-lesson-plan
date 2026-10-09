# 汇总五批标签 + 35 条重写特征：校验词表与格式，写 style_tags.json、替换源 md 对应行
import json, os, pathlib, re, sys, collections
D = pathlib.Path(__file__).resolve().parent
pkg = pathlib.Path(os.environ["USERPROFILE"])/".claude/skills/handdraw-style-prompter"
ref = pkg/"skills/handdraw-style-prompter/references"
VOCAB = {"媒介": ({"钢笔线描","铅笔彩铅","水彩","水墨","平涂色块","版画肌理","蜡笔粉彩","数码厚涂","三维","拼贴"},1,2),
 "年龄感": ({"低幼","小学","少年","成人"},1,3),
 "题材": ({"日常生活","校园","童话奇幻","自然动物","历史古风","科普图解","冒险探险","幽默漫画","城市街景","诗意抒情"},1,3),
 "基调": ({"温暖","明快","安静","幽默","忧郁","神秘","暗黑"},1,2),
 "色彩": ({"鲜艳","柔和淡雅","低饱和","黑白单色"},1,1), "人物造型": ({"Q版大头","卡通比例","修长比例","几何抽象","写实比例","少人物"},1,1)}
ITEMS = ["线条","上色","色板","人物","头发","表情","动作","质感","背景"]
LEAK = re.compile(r"避免|不要|不准|禁止|[A-Za-z]{2,}|天空|蓝天|拥抱|依偎|丸子|马尾|辫|方框|边框")
fit = json.loads((ref/"edu_fit.json").read_text(encoding="utf-8"))
bad, tags, new_traits, mism = [], {}, {}, {}
for i in range(1, 6):
    want = [x for x in json.loads((D/f"in{i}.json").read_text(encoding="utf-8"))]
    got = json.loads((D/f"out{i}.json").read_text(encoding="utf-8"))
    if [x["number"] for x in got] != [x["number"] for x in want]: bad.append(f"out{i} 编号不符")
    for w, g in zip(want, got):
        n = g["number"]; t = {}
        for f, (words, lo, hi) in VOCAB.items():
            v = g.get(f); vals = [v] if isinstance(v, str) else (v or [])
            if not lo <= len(vals) <= hi or any(x not in words for x in vals): bad.append(f"{n}.{f} 越界：{v}")
            t[f] = v
        fe = fit[n]; t["写作课招生"] = {"档": fe["tier"], "理由": fe["reason"]}
        tags[n] = t
        if g.get("mismatch"): mism[n] = g["mismatch"]
        if w["rewrite"]:
            tr = (g.get("new_traits") or "").strip()
            heads = re.findall(r"(?:^|；)\s*([^：；]{1,4})：", tr)
            if heads != ITEMS: bad.append(f"{n} 重写特征九项不齐：{heads}")
            if LEAK.search(tr): bad.append(f"{n} 重写特征含禁用或泄漏：{LEAK.findall(tr)}")
            if len(tr) > 260: bad.append(f"{n} 过长 {len(tr)}")
            new_traits[n] = tr
        elif g.get("new_traits"): bad.append(f"{n} 不该重写却给了 new_traits")
print("标签", len(tags), "重写", len(new_traits), "问题", len(bad)); print("\n".join(bad[:60]))
print("对不上：", json.dumps(mism, ensure_ascii=False, indent=0))
for f in VOCAB:
    c = collections.Counter(x for t in tags.values() for x in ([t[f]] if isinstance(t[f], str) else t[f]))
    print(f, dict(c.most_common()))
json.dump({"tags": tags, "new_traits": new_traits, "mismatch": mism}, open(D/"merged.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
