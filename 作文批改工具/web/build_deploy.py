# -*- coding: utf-8 -*-
"""部署打包：把中文路径下的源，收进全 ASCII 的 api/ 部署包。

    PYTHONUTF8=1 python 作文批改工具/web/build_deploy.py

**每次 vercel 部署前必须先跑这个**，否则线上跑的是上一次打包的标准包。

为什么要打包（不是多此一举）：
  服务本地跑时，标准包在 ../标准包/、build_prompt.py 在 ../，都是中文路径。
  Vercel 部署根是 web/，够不到上一级；而且标准包文件名里有中文与全角引号
  （小小“动物园”.json、我和＿＿过一天.json），要经 git → Vercel 构建机 →
  Lambda zip 三道手，任何一道对非 ASCII 文件名处理不一致就静默少一课。
  所以这里合并成单个 _packs.json，线上不依赖任何中文文件名。

产出（都在 _bundle/ 下，都是生成物、已 gitignore、勿手改）：
  _packs.json        14 个标准包合并成一个数组，顺序不重要（服务端自己排）
  _build_prompt.py   build_prompt.py 的副本，判断规则仍只有源那一份

改标准包或 build_prompt.py 之后没重跑本脚本，线上不会报错、只会继续用旧的。
"""
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent
PACK_DIR = TOOL_ROOT / "标准包"
OUT = HERE / "_bundle"


def main():
    OUT.mkdir(exist_ok=True)
    packs, bad = [], []
    for f in sorted(PACK_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            bad.append(f"{f.name}：{e}")
            continue
        if not d.get("lesson_id"):
            bad.append(f"{f.name}：没有 lesson_id")
            continue
        packs.append(d)

    if bad:
        print("✗ 标准包有问题，没打包（一个包坏掉整个服务起不来）：")
        for b in bad:
            print("   " + b)
        return 1
    if not packs:
        print(f"✗ {PACK_DIR} 下一个标准包都没读到")
        return 1

    ids = [d["lesson_id"] for d in packs]
    if len(set(ids)) != len(ids):
        dup = [i for i in set(ids) if ids.count(i) > 1]
        print("✗ lesson_id 重复：" + "、".join(dup) + "（前端会只剩一课，且不报错）")
        return 1

    (OUT / "_packs.json").write_text(
        json.dumps(packs, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(TOOL_ROOT / "build_prompt.py", OUT / "_build_prompt.py")

    size = (OUT / "_packs.json").stat().st_size
    print(f"✓ 打包 {len(packs)} 课 → _bundle/_packs.json（{size/1024:.0f} KB）")
    print("  " + "、".join(d["meta"]["topic"] for d in packs))
    unverified = [d["meta"]["topic"] for d in packs
                  if not (d.get("source") or {}).get("verified_by_human")]
    if unverified:
        print(f"\n⚠ 其中 {len(unverified)} 课的判据还没人对着详案逐句核过"
              f"（verified_by_human=false）。")
        print("  判据抄错一句，那个班的批语会整批跟着错，且从产出上看不出来。")
        print("  核对凭据在 作文批改工具/标准包核对清单/。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
