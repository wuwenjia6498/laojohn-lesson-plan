# -*- coding: utf-8 -*-
"""标准包上线确认：人工核对过的包才允许打包上线，确认动作只走这条命令。

    PYTHONUTF8=1 python 作文批改工具/confirm_pack.py <包名|lesson_id|路径> --by <确认人> [--on YYYY-MM-DD] [--note 备注]
    PYTHONUTF8=1 python 作文批改工具/confirm_pack.py <包名> --revoke [--note 撤销原因]
    PYTHONUTF8=1 python 作文批改工具/confirm_pack.py --list

语义（2026-09-07 用户拍板）：
  source.verified_by_human = true  ＝「判据已人工逐句核对 **且** 允许上线」。
  web/build_deploy.py 只打包为 true 的包；false 的一律不进线上，已在线的也会在
  下次部署时下线。所以「先不上传某课」＝不确认它，不需要另立清单。

确认前置门（缺一拒绝，脚本不给逃生口）：
  1. 标准包核对清单/<包名>-核对清单.md 必须存在——与 validate_packs.py E26 同一判据，
     无凭据不许标已核。
  2. validate_packs.py 对这个包跑到 0 FAIL。详案是活文档，判据抄的是当日原话，
     详案改过之后 C15/C16 会报「查无此句」——这正是人工核对该抓的事，包没跟上
     详案就不许上线。

写回三处：包的 source 块（verified_by_human / verified_by / verified_on / verified_note，
其余键一字不动，末尾换行按原样保留）、核对清单第 3 行表头的 **false/true** 标记。
JSON 手改 verified_by_human 为 true 而不带 verified_by / verified_on，validate E26 会 FAIL。

本文件源码不写字面弯引号（Write 工具会把它规范化成 ASCII，见项目记忆
write-tool-normalizes-curly-quotes）。
"""
import argparse
import datetime as _dt
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACK_DIR = HERE / "标准包"
CHECKLIST_DIR = HERE / "标准包核对清单"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# 核对清单第 3 行里的标记，只认这一处；改动只替换这个片段，行内其余文字不动。
HEADER_RE = re.compile(r"`verified_by_human`: \*\*(?:false|true)\*\*(?:（[^）]*）)?")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def read_pack(path):
    raw = path.read_text(encoding="utf-8")
    return json.loads(raw), raw.endswith("\n")


def write_pack(path, d, trailing_nl):
    out = json.dumps(d, ensure_ascii=False, indent=2)
    if trailing_nl:
        out += "\n"
    path.write_text(out, encoding="utf-8")


def all_packs():
    return sorted(PACK_DIR.glob("*.json"))


def resolve(name):
    """接受三种写法：路径、文件 stem、lesson_id。找不到或歧义都退出。"""
    p = Path(name)
    if p.suffix == ".json" and p.exists():
        return p.resolve()
    stem = p.stem if p.suffix == ".json" else name
    cands = [f for f in all_packs() if f.stem == stem]
    if not cands:
        for f in all_packs():
            try:
                d, _ = read_pack(f)
            except Exception:  # noqa: BLE001
                continue
            if d.get("lesson_id") == name:
                cands.append(f)
    if not cands:
        print("没有这个包：" + name)
        print("  可用写法：文件名（不带 .json）、lesson_id、或路径。--list 看全部。")
        sys.exit(1)
    if len(cands) > 1:
        print("匹配到多个包，说不清是哪一个：" + "、".join(f.name for f in cands))
        sys.exit(1)
    return cands[0]


def checklist_of(path):
    return CHECKLIST_DIR / (path.stem + "-核对清单.md")


def run_validate(path):
    """importlib 复用 validate_packs.check_pack，规则只有那一份。返回 Report。"""
    v = _load("validate_packs", HERE / "validate_packs.py")
    srv = v._load("main", v.SERVER / "main.py")
    bp = v._load("build_prompt", HERE / "build_prompt.py")
    return v.check_pack(path, srv, bp, {})


def update_checklist_header(path, new_mark):
    """改核对清单第 3 行的 **false/true** 标记。匹配不到只报警，不乱写。"""
    cl = checklist_of(path)
    if not cl.exists():
        print("  ⚠ 核对清单不存在，表头未改：" + cl.name)
        return
    text = cl.read_text(encoding="utf-8")
    new_text, n = HEADER_RE.subn("`verified_by_human`: " + new_mark, text, count=1)
    if n == 0:
        print("  ⚠ 核对清单表头里找不到 `verified_by_human`: **false/true** 标记，未改：" + cl.name)
        return
    cl.write_text(new_text, encoding="utf-8")
    print("  ✓ 核对清单表头已改：" + cl.name)


def cmd_list():
    rows = []
    for f in all_packs():
        try:
            d, _ = read_pack(f)
        except Exception as e:  # noqa: BLE001
            rows.append(("坏包", f.stem, "", "", repr(e)))
            continue
        src = d.get("source") or {}
        ok = src.get("verified_by_human") is True
        rows.append(("已确认" if ok else "未确认", d.get("lesson_id", "?"), f.stem,
                     src.get("verified_by", ""), src.get("verified_on", "")))
    n_ok = sum(1 for r in rows if r[0] == "已确认")
    print("标准包上线确认状态（已确认 " + str(n_ok) + " / " + str(len(rows)) + "，只有已确认的会被 build_deploy.py 打包）\n")
    for st, lid, stem, by, on in rows:
        tail = ("  " + by + " · " + on) if by else ""
        print("  " + st + "  " + lid.ljust(32) + " " + stem + tail)
    return 0


def cmd_confirm(path, by, on, note):
    if not by or not by.strip():
        print("--by 确认人不能为空：留痕就是为了知道谁核的。")
        return 1
    on = on or _dt.date.today().isoformat()
    if not DATE_RE.match(on):
        print("--on 应为 YYYY-MM-DD，实为 " + on)
        return 1
    d, nl = read_pack(path)
    print("确认上线：" + path.stem + "（" + str(d.get("lesson_id")) + "）")

    cl = checklist_of(path)
    if not cl.exists():
        print("  ✗ 拒绝：找不到核对清单 " + cl.name)
        print("    无凭据不许标已核。先按 标准包抽取规程.md §八 补清单并逐句核对。")
        return 1

    rep = run_validate(path)
    if rep.fails:
        rep.dump()
        print("\n  ✗ 拒绝：validate_packs.py 有 " + str(len(rep.fails)) + " 条 FAIL。")
        print("    C15/C16「查无此句」＝判据没跟上改过的详案，先把包改到与详案逐字一致再确认。")
        return 1
    if rep.warns:
        rep.dump()
        print("  （以上只是 WARN，人眼看过即可，不挡确认）")

    src = d.setdefault("source", {})
    src["verified_by_human"] = True
    src["verified_by"] = by.strip()
    src["verified_on"] = on
    if note:
        src["verified_note"] = note
    write_pack(path, d, nl)
    print("  ✓ 已写入：verified_by_human=true · " + by.strip() + " · " + on)
    update_checklist_header(path, "**true**（核对人：" + by.strip() + " · " + on + "）")

    # 写完再过一遍 E26，确保这份包以「已确认」身份仍能通过闸门。
    rep2 = run_validate(path)
    if rep2.fails:
        rep2.dump()
        print("  ✗ 写回后校验反而失败，请检查上面 FAIL。")
        return 1
    print("  下一步：web/build_deploy.py 打包（会列出本次上线/下线清单）→ vercel --prod")
    return 0


def cmd_revoke(path, note):
    d, nl = read_pack(path)
    src = d.setdefault("source", {})
    was = src.get("verified_by_human") is True
    src["verified_by_human"] = False
    src.pop("verified_by", None)
    src.pop("verified_on", None)
    if note:
        src["verified_note"] = note
    write_pack(path, d, nl)
    print(("撤销确认：" if was else "本来就未确认，已按未确认写回：") + path.stem)
    update_checklist_header(path, "**false**")
    print("  下次 build_deploy.py 打包时这一课不再上线（已在线的会下线）。")
    return 0


def main():
    ap = argparse.ArgumentParser(description="标准包上线确认 / 撤销 / 状态")
    ap.add_argument("pack", nargs="?", help="包名（文件名不带 .json）、lesson_id 或路径")
    ap.add_argument("--by", help="确认人（确认时必填）")
    ap.add_argument("--on", help="确认日期 YYYY-MM-DD，缺省今天")
    ap.add_argument("--note", help="备注；撤销时写原因")
    ap.add_argument("--revoke", action="store_true", help="撤销确认（下次部署即下线）")
    ap.add_argument("--list", action="store_true", help="列出全部包的确认状态")
    a = ap.parse_args()

    if a.list:
        return cmd_list()
    if not a.pack:
        ap.print_help()
        return 1
    path = resolve(a.pack)
    if a.revoke:
        return cmd_revoke(path, a.note)
    return cmd_confirm(path, a.by, a.on, a.note)


if __name__ == "__main__":
    sys.exit(main())
