# -*- coding: utf-8 -*-
r"""gen_illustration.py —— 单元海报中央插画：json.illustration.subject → 提示词 → 生图 → 判读 → 落盘（两段式第 2b 步）

    PYTHONUTF8=1 python gen_illustration.py <data.json> [--provider gemini|doubao] [--ratio 4:3|1:1|3:4]
        [--seed N] [--force] [--no-judge]

生图/判读客户端复用 课件配图工具\scripts\imgclient.py（importlib 薄壳、禁复制；密钥只从环境变量 / 课件配图工具\.env /
picture-writing 的 imggen.config.json 读，本脚本不碰密钥）。**CLI 覆盖参数默认 None**：ratio 取 --ratio → json → "4:3"。

流程与闸门（画面口径 2026-09-20 改：主体＝本课情境画面、可有人物，只禁文字；`illustration.no_people` 为真才禁人）：
  1. subject 为空或仍是【…待…】占位 ⇒ 拒启动（exit 2）。已有正式图且无 --force ⇒ 跳过（exit 0）。
  2. 先落 <课次>-插画.候选.jpg；判读四问（has_text / has_person / bg_cream / subject_ok）。
     · has_text 为真（或 no_people 时 has_person 为真）⇒ 硬失败：追加负面词重生 1 次；仍失败 ⇒ 保留候选、exit 3（渲染脚本会留空区，不阻断）。
     · bg_cream / subject_ok 为假 ⇒ 只警告。
     · 判读请求失败或回包不是 JSON ⇒ **未知，不是不通过**（照 课件配图工具\scripts\verify_rules.py 的 judge_failed 闸门）：
       保留候选、verdict=unknown、exit 0 并提示人工看图后手动改名转正。
  3. 通过 ⇒ 候选 replace 成 <课次>-插画.jpg（旧图在通过前不动），提示词写 <课次>-插画-提示词.txt，回执回写 json。
图服从文字：规格（subject）是事实源，绝不反过来用图改 json 里的文案。风格口径唯一源 references/illustration-prompt.md。

风格编号（2026-09-20 接入用户级 skill handdraw-style-prompter，274 个带编号的手绘风格）：
  json.illustration.style 或 --style 给编号（001–274）⇒ 提示词改为「风格名称 + 参考作者 + 核心风格特征 + 主体 + 本工具固定约束 +
  参考图隔离声明」，并把该编号的参考图作为 images 传给生图（对 Gemini 该库判定为能力未知 ⇒ 特征+参考图双保险）。
  不给编号 ⇒ 沿用 STYLE_PREFIX 通用水彩前缀（向后兼容）。索引读 assets/handdraw/styles.json（仓内副本），参考图先找
  assets/handdraw/refs/<编号>.webp，没有就从用户级包拷一份进来（入库，同事机器不装风格库也能重生）；两处都没有 ⇒ 报错回退通用前缀。
  特征只保留正向描述（含「避免/不要/不准/禁止」的分句过滤掉，照该库 positive_traits 口径）。
"""
import argparse
import datetime
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402

STYLE_PREFIX = (
    "暖色手绘插画，柔和铅笔线条加水彩平涂，光线柔和，浅奶油色背景（色值 #FFF6E3，画面四周渐淡融入背景、留白干净）。"
    "画面："
)
RETRY_SUFFIX = "。特别注意：画面中绝对不要出现任何文字、字母或数字。"
HANDDRAW_ASSETS = Path(__file__).resolve().parents[1] / "assets" / "handdraw"
HANDDRAW_USER_PKG = Path.home() / ".claude" / "skills" / "handdraw-style-prompter"   # 用户级包，可能不存在
# 本工具的固定约束（无论走不走编号风格都要有）：构图/底色/无人无字/纸面空白
FIXED_CONSTRAINTS = ("浅奶油色背景（色值 #FFF6E3，画面四周渐淡融入背景、留白干净），主体集中在画面中央。"
                     "画面中如有人物，为中国小学生或教师，形象简洁亲切、不夸张。"
                     "没有任何文字、字母、数字、水印、品牌标志；黑板、纸张、屏幕、标签一律保持空白，不得出现任何可辨认的文字或符号。")
NO_PEOPLE = "画面里没有人、没有手、没有拟人角色。"
NEG_SUFFIX = "。" + FIXED_CONSTRAINTS
# 参考图隔离声明（照 handdraw-style-prompter SKILL.md 原文）
REF_ISOLATION = ("所附图片仅用于参考画风。只提取参考图的风格特征，例如线条、笔触、媒介、材质、色彩倾向和整体视觉语言；"
                 "不要使用、复制或延续参考图中的任何主体、人物、动物、服装、道具、动作、姿态、场景、背景、构图、布局、文字或故事。"
                 "最终画面内容完全以用户提供的主题为准。")
JUDGE_Q = (
    "只看这张插画，只回一个 JSON 对象，键与含义："
    "has_text＝画面里是否出现任何文字/字母/数字（true/false）；"
    "has_person＝是否出现人、手或人形角色（true/false）；"
    "bg_cream＝背景主色是否为浅奶油/米白色（true/false）；"
    "subject_ok＝画面是否包含下列物件——{subject}（true/false）；"
    "notes＝一句话说明。只回 JSON，不要解释文字、不要 markdown 代码块。"
)


def load_client(provider):
    real = Path(__file__).resolve().parents[4] / "课件配图工具" / "scripts" / "imgclient.py"
    if not real.exists():
        sys.exit("找不到生图客户端：%s" % real)
    spec = importlib.util.spec_from_file_location("imgclient_real", real)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.make_client(provider)


def judge_failed(obs):
    """判读整体失败 ⇒ 返回原因串（未知，不是否定）；正常 ⇒ None。"""
    if not isinstance(obs, dict):
        return "判读回包不是对象"
    if "_error" in obs:
        return "判读请求失败（%s）" % str(obs["_error"])[:120]
    if "_raw" in obs:
        return "判读结果未能解析成 JSON"
    return None


def _positive_traits(traits):
    """只留正向可见特征（照风格库 resolve_reference.positive_traits 口径，不复制其文件）。"""
    if not traits:
        return ""
    kept = []
    for part in re.split(r"[；;。\n]+", traits):
        part = part.strip(" ，,、：:。；;\t")
        if not part or any(w in part for w in ("避免", "不要", "不准", "禁止")):
            continue
        if re.search(r"无(?:写实纹理|精细材质|真实纹理)", part):
            continue
        kept.append(part)
    return "；".join(kept)


def resolve_style(number):
    """编号 → {number, name, reference, traits, ref_path}；索引读仓内副本，参考图缺则从用户级包拷进仓。"""
    num = "%03d" % int(number)
    idx = HANDDRAW_ASSETS / "styles.json"
    if not idx.exists():
        idx = HANDDRAW_USER_PKG / "skills" / "handdraw-style-prompter" / "references" / "styles.json"
    if not idx.exists():
        raise FileNotFoundError("风格索引不存在（仓内 assets/handdraw/styles.json 与用户级风格库都没有）")
    rec = next((r for r in json.loads(idx.read_text(encoding="utf-8")) if r.get("number") == num), None)
    if not rec:
        raise ValueError("风格编号 %s 不在索引里（001–274）" % num)
    refs = HANDDRAW_ASSETS / "refs"
    local = next((p for p in (refs / (num + "_grid.webp"), refs / (num + ".webp")) if p.exists()), None)
    if local is None:
        start = ((int(num) - 1) // 200) * 200 + 1
        bucket = HANDDRAW_USER_PKG / "images" / "individual" / ("%03d-%03d" % (start, start + 199))
        src = next((p for p in (bucket / (num + "_grid.webp"), bucket / (num + ".webp")) if p.exists()), None)
        if src is None:
            raise FileNotFoundError("编号 %s 的参考图既不在仓内 refs/ 也不在用户级风格库（%s）" % (num, bucket))
        refs.mkdir(parents=True, exist_ok=True)
        local = refs / src.name
        shutil.copyfile(src, local)
        print("  [风格] 参考图首次使用，已拷进仓：%s（请随 json 一并提交）" % local.name)
    return {"number": num, "name": rec.get("generation_name", ""), "reference": rec.get("reference", ""),
            "traits": _positive_traits(rec.get("traits", "")), "ref_path": str(local)}


def build_prompt(subject, retry=False, style=None, no_people=False):
    subj = subject.strip().rstrip("。")
    extra = NO_PEOPLE if no_people else ""
    if style:
        p = ("风格名称：#%s · %s。参考作者/风格名称：%s。" % (style["number"], style["name"], style["reference"] or "（索引未标）")
             + ("核心风格特征：%s。" % style["traits"] if style["traits"] else "")
             + "主题：" + subj + "。" + FIXED_CONSTRAINTS + extra + REF_ISOLATION)
    else:
        p = STYLE_PREFIX + subj + NEG_SUFFIX + extra
    return p + RETRY_SUFFIX if retry else p


def run(data_path, provider=None, ratio=None, seed=None, force=False, no_judge=False, style_no=None):
    data_path = Path(data_path)
    data = C.load_json(data_path)
    ill = data.setdefault("illustration", {})
    subject = (ill.get("subject") or "").strip()
    if not subject or C.PH_RE.search(subject):
        sys.exit("illustration.subject 为空或仍是占位，先按 references/illustration-prompt.md 填实（exit 2）")
    cid = data.get("course", {}).get("id") or data_path.stem.replace("-习作海报", "")
    final = data_path.parent / ("%s-插画.jpg" % cid)
    cand = data_path.parent / ("%s-插画.候选.jpg" % cid)
    prompt_file = data_path.parent / ("%s-插画-提示词.txt" % cid)
    if final.exists() and not force:
        print("已有插画：%s（重生加 --force；人工换图直接覆盖此文件即可）" % final.name)
        return 0
    eff_ratio = ratio or ill.get("ratio") or "4:3"
    style = None
    eff_style = style_no or ill.get("style")
    if eff_style:
        try:
            style = resolve_style(eff_style)
            print("[风格] #%s · %s（参考图 %s）" % (style["number"], style["name"], Path(style["ref_path"]).name))
        except (FileNotFoundError, ValueError) as e:
            print("  ⚠ 风格编号未生效，回退通用前缀：%s" % e, file=sys.stderr)

    client = load_client(provider)
    verdict, obs = None, None
    for attempt in (0, 1):
        prompt = build_prompt(subject, retry=bool(attempt), style=style, no_people=bool(ill.get("no_people")))
        print("[生图 %d/2] %s · %s" % (attempt + 1, client.name, eff_ratio))
        img = client.generate(prompt, ratio=eff_ratio, seed=seed,
                              images=[style["ref_path"]] if style else None)
        client.save(img, cand)
        prompt_file.write_text(prompt + "\n", encoding="utf-8")
        if no_judge:
            verdict = "skipped"
            break
        obs = client.judge([str(cand)], JUDGE_Q.format(subject=subject))
        why = judge_failed(obs)
        if why:
            verdict = "unknown"
            print("  ⚠ %s——候选已在盘（%s），请人工看图，通过即手动改名为 %s" % (why, cand.name, final.name), file=sys.stderr)
            break
        # 文字＝硬失败；人物只在 illustration.no_people 为真时才算硬失败（2026-09-20 改：画面取详案情境，默认允许人物）
        hard = bool(obs.get("has_text")) or (bool(ill.get("no_people")) and bool(obs.get("has_person")))
        if not obs.get("bg_cream", True):
            print("  [警告] 判读称背景不是浅奶油色：%s" % obs.get("notes", ""), file=sys.stderr)
        if not obs.get("subject_ok", True):
            print("  [警告] 判读称主体物件不全：%s" % obs.get("notes", ""), file=sys.stderr)
        if not hard:
            verdict = "pass"
            break
        print("  ✗ 判读命中文字（或禁人时命中人物）（has_text=%s has_person=%s）：%s" % (
            obs.get("has_text"), obs.get("has_person"), obs.get("notes", "")), file=sys.stderr)
        verdict = "fail"

    if verdict in ("pass", "skipped"):
        cand.replace(final)
        print("插画已就位：%s" % final)
    ill.update({
        "file": final.name if verdict in ("pass", "skipped") else cand.name,
        "provider": client.name, "model": getattr(client, "model", ""),
        "prompt_used": prompt_file.name,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "style_used": ({"number": style["number"], "name": style["name"],
                        "reference_image": Path(style["ref_path"]).name} if style else None),
        "judge": {"verdict": verdict, "obs": obs if isinstance(obs, dict) else None},
    })
    C.dump_json(data_path, data)
    print("用量：%s" % json.dumps(client.usage, ensure_ascii=False))
    return {"pass": 0, "skipped": 0, "unknown": 0, "fail": 3}[verdict]


def main():
    ap = argparse.ArgumentParser(description="单元海报插画：生图 + 判读 + 落盘")
    ap.add_argument("data", help="<课次>-习作海报.json")
    ap.add_argument("--provider", default=None, choices=["gemini", "doubao"])
    ap.add_argument("--ratio", default=None, choices=["4:3", "1:1", "3:4", "16:9"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="已有正式图也重生")
    ap.add_argument("--no-judge", action="store_true", help="跳过机器判读，候选直接转正（人工验收路径）")
    ap.add_argument("--style", default=None, help="手绘风格编号 001–274（默认 None ⇒ 取 json.illustration.style；都没有走通用前缀）")
    a = ap.parse_args()
    return run(a.data, a.provider, a.ratio, a.seed, a.force, a.no_judge, a.style)


if __name__ == "__main__":
    sys.exit(main())
