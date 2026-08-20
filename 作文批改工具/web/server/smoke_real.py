# -*- coding: utf-8 -*-
"""真实模型链路自测：拿一张稿纸照片跑一次真调用，把该核的四件当场核给你看。

    PYTHONUTF8=1 python 作文批改工具/web/server/smoke_real.py <稿纸照片> [课次id]

需要先配好密钥（环境变量 AIHUBMIX_API_KEY 或 server/config.json）。
不启服务、不经前端，直接打模型——排查时先跑它，能把「前端问题」和
「模型问题」分开。跑完不留任何文件。
"""
import asyncio
import base64
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("srv", HERE / "main.py")
srv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(srv)


async def run(img_path, lesson_id):
    if srv.MOCK:
        print("✗ 没读到密钥，现在是 mock 模式，这次自测没意义。")
        print("  先 export AIHUBMIX_API_KEY=... 或填好 server/config.json。")
        return 1
    pack = srv.PACKS.get(lesson_id) if lesson_id else list(srv.PACKS.values())[0]
    if not pack:
        print("✗ 没有这一课的标准包。现有：" + "、".join(srv.PACKS))
        return 1

    raw = Path(img_path).read_bytes()
    print(f'课次：{pack["meta"]["topic"]}　模型：{srv.CFG["grade_model"]}　'
          f'图：{len(raw)/1024:.0f}KB')
    msgs = srv.build_messages(pack, base64.b64encode(raw).decode(), "image/jpeg", [])
    text = await srv.call_model(msgs)

    print("\n—— 原始返回 ——")
    print(text[:1500])

    try:
        d = srv.parse_json(text)
    except Exception as e:
        print(f"\n✗ JSON 解析失败：{e}")
        return 1

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
    print("· 引用的句子是不是与稿纸一字不差（模型会把错别字读通顺）")
    print("· 三条判据的判定，跟你自己读这篇的判断合不合")
    print(f'· 批语像不像人话：{d.get("teacher_note", "")}')
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    sys.exit(asyncio.run(run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)))
