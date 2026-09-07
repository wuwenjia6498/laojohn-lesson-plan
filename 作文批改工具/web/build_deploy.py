# -*- coding: utf-8 -*-
"""部署打包：把中文路径下的源，收进全 ASCII 的部署包——**只收人工确认过的标准包**。

    PYTHONUTF8=1 python 作文批改工具/web/build_deploy.py [--dry-run] [--yes]

**每次 vercel 部署前必须先跑这个**，否则线上跑的是上一次打包的标准包。

闸门口径（2026-09-07 用户拍板）：
  只打包 source.verified_by_human 为 true 的包；false 的一律不进 _packs.json，
  已在线的也会随下次部署下线。确认动作只走 ../confirm_pack.py（会先跑 validate、
  查核对清单凭据，再写确认人与日期），手改 JSON 翻 true 会被 validate E26 拦。
  本脚本**没有** --allow-unverified 之类逃生口：未确认不上，这就是全部规则。
  写盘前会列出「本次新上线 / 本次下线 / 内容有改动 / 不变」并要求敲 y——
  这一眼是防「忘了确认、一部署把线上全清空」的最后一道。--yes 只跳过提问，
  不跳过闸门；--dry-run 只看清单不写盘。

为什么要打包（不是多此一举）：
  服务本地跑时，标准包在 ../标准包/、build_prompt.py 在 ../，都是中文路径。
  Vercel 部署根是 web/，够不到上一级；而且标准包文件名里有中文与全角引号
  （小小“动物园”.json、我和＿＿过一天.json），要经 git → Vercel 构建机 →
  Lambda zip 三道手，任何一道对非 ASCII 文件名处理不一致就静默少一课。
  所以这里合并成单个 _packs.json，线上不依赖任何中文文件名。

产出（都在 _bundle/ 下，都是生成物、已 gitignore、勿手改）：
  _packs.json        已确认的标准包合并成一个数组，顺序不重要（服务端自己排）
  _build_prompt.py   build_prompt.py 的副本，判断规则仍只有源那一份

改标准包或 build_prompt.py 之后没重跑本脚本，线上不会报错、只会继续用旧的。
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent
PACK_DIR = TOOL_ROOT / "标准包"
OUT = HERE / "_bundle"


def _label(d):
    m = d.get("meta") or {}
    return f'{m.get("grade_volume", "?")}·{m.get("unit", "?")}《{m.get("topic", "?")}》（{d["lesson_id"]}）'


def _canon(d):
    return json.dumps(d, ensure_ascii=False, sort_keys=True)


def load_previous():
    """上一次打包件里的包，按 lesson_id。没有就当线上为空。"""
    f = OUT / "_packs.json"
    if not f.exists():
        return {}
    try:
        return {d["lesson_id"]: d for d in json.loads(f.read_text(encoding="utf-8"))}
    except Exception as e:  # noqa: BLE001
        print(f"⚠ 读不了上一次的 _packs.json（{e}），变化清单按线上为空算")
        return {}


def main():
    ap = argparse.ArgumentParser(description="打包已确认的标准包到 _bundle/")
    ap.add_argument("--dry-run", action="store_true", help="只列清单，不写盘")
    ap.add_argument("--yes", action="store_true", help="跳过 y/N 提问（不跳过闸门）")
    a = ap.parse_args()

    OUT.mkdir(exist_ok=True)
    loaded, bad = [], []
    for f in sorted(PACK_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            bad.append(f"{f.name}：{e}")
            continue
        if not d.get("lesson_id"):
            bad.append(f"{f.name}：没有 lesson_id")
            continue
        loaded.append(d)

    # 格式检查在分组之前：坏包不因为没上线就放过，它坏在目录里迟早要上。
    if bad:
        print("✗ 标准包有问题，没打包（一个包坏掉整个服务起不来）：")
        for b in bad:
            print("   " + b)
        return 1
    if not loaded:
        print(f"✗ {PACK_DIR} 下一个标准包都没读到")
        return 1
    ids = [d["lesson_id"] for d in loaded]
    if len(set(ids)) != len(ids):
        dup = [i for i in set(ids) if ids.count(i) > 1]
        print("✗ lesson_id 重复：" + "、".join(dup) + "（前端会只剩一课，且不报错）")
        return 1

    # ---- 闸门 ----
    packs = [d for d in loaded if (d.get("source") or {}).get("verified_by_human") is True]
    held = [d for d in loaded if d not in packs]
    if held:
        print(f"未确认，不打包（{len(held)} 课）：")
        for d in held:
            print("   · " + _label(d))
    if not packs:
        print(f"\n✗ 0 个包已确认，拒绝出空包（那会把线上全部课次清空）。")
        print("  先逐包核对后跑 ../confirm_pack.py <包名> --by <确认人>，再回来打包。")
        return 1

    # ---- 与上一次打包件比对 ----
    prev = load_previous()
    cur = {d["lesson_id"]: d for d in packs}
    added = [cur[i] for i in cur if i not in prev]
    removed = [prev[i] for i in prev if i not in cur]
    changed = [cur[i] for i in cur if i in prev and _canon(cur[i]) != _canon(prev[i])]
    same = [i for i in cur if i in prev and _canon(cur[i]) == _canon(prev[i])]
    print(f"\n相对上一次打包件（{len(prev)} 课）的变化：")
    for title, group in (("本次新上线", added), ("本次下线", removed), ("内容有改动", changed)):
        print(f"  {title}（{len(group)}）" + ("" if group else "：无"))
        for d in group:
            print("     · " + _label(d))
    print(f"  不变（{len(same)}）")
    print(f"\n打包后线上共 {len(packs)} 课：")
    print("   " + "、".join(d["meta"]["topic"] for d in packs))

    if a.dry_run:
        print("\n--dry-run：未写盘。")
        return 0
    if not a.yes:
        # stdin 不是终端（被 agent / 管道调用）时不提问：input() 在有些宿主里
        # 收不到 EOF 会一直挂着。这种场景要写盘就必须显式 --yes。
        if not sys.stdin.isatty():
            print("\n非交互环境，不提问也不写盘；看过上面清单确认无误请加 --yes。")
            return 1
        try:
            ans = input("\n确认写入打包件？[y/N] ").strip().lower()
        except EOFError:
            ans = ""
        if ans != "y":
            print("已取消，未写盘。")
            return 1

    (OUT / "_packs.json").write_text(
        json.dumps(packs, ensure_ascii=False), encoding="utf-8")
    shutil.copyfile(TOOL_ROOT / "build_prompt.py", OUT / "_build_prompt.py")
    size = (OUT / "_packs.json").stat().st_size
    print(f"\n✓ 打包 {len(packs)} 课 → _bundle/_packs.json（{size/1024:.0f} KB）"
          f"；未确认 {len(held)} 课未打包。下一步：vercel --prod")
    return 0


if __name__ == "__main__":
    sys.exit(main())
