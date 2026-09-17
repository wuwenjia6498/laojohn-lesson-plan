# -*- coding: utf-8 -*-
"""真实模型链路自测：拿一份稿纸照片跑一次真调用，把该核的四件当场核给你看。

    PYTHONUTF8=1 python 作文批改工具/web/server/smoke_real.py <稿纸照片> [续页照片...] [课次id]

多页作文把各页按顺序都传进来（0906 起支持，与线上 /api/grade 同一条 build_messages 路径）；
参数里凡是存在的文件都当页，剩下那个当课次 id。

需要先配好密钥（环境变量 AIHUBMIX_API_KEY 或 server/config.json）。
不启服务、不经前端，直接打模型——排查时先跑它，能把「前端问题」和
「模型问题」分开。跑完不留任何文件。
"""
import asyncio
import base64
import importlib.util
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("srv", HERE / "main.py")
srv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)


async def run(img_paths, lesson_id):
    if srv.MOCK:
        print("✗ 没读到密钥，现在是 mock 模式，这次自测没意义。")
        print("  先 export AIHUBMIX_API_KEY=... 或填好 server/config.json。")
        return 1
    pack = srv.PACKS.get(lesson_id) if lesson_id else list(srv.PACKS.values())[0]
    if not pack:
        print("✗ 没有这一课的标准包。现有：" + "、".join(srv.PACKS))
        return 1

    raws = [Path(p).read_bytes() for p in img_paths]
    print(f'课次：{pack["meta"]["topic"]}　模型：{srv.CFG["grade_model"]}　'
          f'图：{len(raws)} 页 ' + "+".join(f"{len(r)/1024:.0f}KB" for r in raws))
    # 与 /api/grade 同一个函数：主批改 + 并发的错别字校对 + 整条后处理链（0917）
    t0 = time.perf_counter()
    try:
        d = await srv.grade_pipeline(
            pack, [(base64.b64encode(r).decode(), "image/jpeg") for r in raws], [],
            on_raw=lambda t: print("\n—— 原始返回 ——\n" + t[:1500]))
    except Exception as e:
        # HTTPException 的 str() 是空的，原因在 .detail 里——不打出来就只剩一个冒号
        print(f"\n✗ 批改失败：{getattr(e, 'detail', None) or repr(e)}")
        return 1
    print(f"\n（整条链用时 {time.perf_counter() - t0:.0f} 秒，含并发的错别字校对）")

    print("")
    print("—— 兜底之后（老师看到的）——")
    print("  判据：" + "　".join(str(c.get("no")) + str(c.get("verdict"))
                               for c in d.get("checks") or [])
          + "　档位：" + str(d.get("band")))
    for c in d.get("checks") or []:
        for q in c.get("quotes") or []:
            print("     原文 " + str(c.get("no")) + "：" + str(q))
        if c.get("advice"):
            print("     怎么改 " + str(c.get("no")) + "：" + str(c.get("advice")))
    w = d.get("whole_piece") or {}
    print("  结构：" + "／".join(k + ":" + str((w.get(k) or {}).get("verdict"))
                              for k in ("completeness", "order", "paragraph", "detail", "flow")))
    print("  分段那一栏：" + str((w.get("paragraph") or {}).get("note") or ""))
    print("  本篇要点：" + str(d.get("focus") or ""))
    hits = srv.collect_empty_words(d)
    print("  空夸词：" + ("无" if not hits else "✗ 仍有 " + "、".join(hits)))
    qc = d.get("quote_check") or {}
    print("  引用校对：对回原文 " + str(qc.get("fixed")) + " 处，可疑 " + str(qc.get("suspect"))
          + " 处，家长侧拼音换正字 " + str(qc.get("pinyin_fixed")) + " 处")
    tc = d.get("typos_check")
    ty = d.get("typos") or []
    if tc is None:
        print("  错别字：（校对层关着）")
    elif tc.get("status") != "ok":
        print("  错别字：✗ 没跑成（" + str(tc.get("reason")) + "）——老师看到的是「没跑成」，不是「没有」")
    else:
        print("  错别字：确定 " + str(tc.get("sure")) + "／待核 " + str(tc.get("unsure"))
              + "／守门丢弃 " + str(tc.get("dropped")))
        for t in ty:
            print("     - " + str(t.get("kind")) + " 「" + str(t.get("wrong")) + "」→「" + str(t.get("right")) + "」"
                  + ("" if t.get("sure") else "（待核）") + " ｜ " + str(t.get("sentence")))
    print("  引用句：" + str(d.get("quoted_sentence") or ""))
    print("  点评卡：" + str(d.get("parent_card") or ""))
    left = srv.PINYIN_TOKEN.findall(str(d.get("parent_card") or ""))
    print("  点评卡残留拼音：" + ("无" if not left else "✗ " + "、".join(left)))

    print("\n—— 该核的四件 ——")
    ok = True
    nos = [c.get("no") for c in d.get("checks", [])]
    want = [c["no"] for c in pack["three_checks"]]
    print(f'1. 三条判据齐不齐：{nos}　{"✓" if nos == want else "✗ 期望 " + str(want)}')
    ok &= nos == want

    q = (d.get("quoted_sentence") or "").strip()
    card = d.get("parent_card") or ""
    hit = bool(q) and q[:12] in card
    print(f'2. 点评卡里真引了那一句：{"✓" if hit else "✗ quoted_sentence 没出现在 parent_card 里"}')
    ok &= hit

    n = len(card.strip())
    print(f'3. 点评卡字数：{n} 字　{"✓" if n <= 170 else "✗ 超了，模板要求 150 字以内"}')

    name = d.get("student_name", "")
    print(f'4. 姓名：{name or "（空——稿纸没写或没读到，留空是对的，编一个才是错的）"}')

    print("\n—— 还要你自己看的（机器判不了）——")
    print("· 引用的句子是不是与稿纸一字不差；错别字栏列的每一条对着稿纸核一遍，尤其待核那几条")
    print("· 三条判据的判定，跟你自己读这篇的判断合不合")
    print(f'· 批语像不像人话：{d.get("teacher_note", "")}')
    return 0 if ok else 1


if __name__ == "__main__":
    argv = sys.argv[1:]
    # --model <id>：临时换模型试一次（评估用），不动 config；模型专属参数走环境变量 LJ_MODEL_EXTRA
    if "--model" in argv:
        k = argv.index("--model")
        srv.CFG["grade_model"] = argv[k + 1]
        argv = argv[:k] + argv[k + 2:]
    if not argv:
        print(__doc__)
        sys.exit(1)
    paths = [a for a in argv if Path(a).exists()]
    rest = [a for a in argv if not Path(a).exists()]
    sys.exit(asyncio.run(run(paths, rest[0] if rest else None)))
