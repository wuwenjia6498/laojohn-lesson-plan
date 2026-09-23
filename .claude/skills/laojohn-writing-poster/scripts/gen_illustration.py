# -*- coding: utf-8 -*-
r"""gen_illustration.py —— 单元海报中央插画：json.illustration.subject → 提示词 → 生图 → 判读 → 落盘（两段式第 2b 步）

    PYTHONUTF8=1 python gen_illustration.py <data.json> [--provider gpt-image|gemini|doubao（缺省 gpt-image）] [--ratio 4:3|1:1|3:4]
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
  json.illustration.style 或 --style 给编号（001–274）⇒ 提示词改为「画风特征（最前）+ 画面内容 + 本工具固定约束 +
  参考图说明」，并把该编号的参考图作为 images 传给生图（对 Gemini 该库判定为能力未知 ⇒ 特征+参考图双保险）。
  2026-09-23 起：风格名／作者名不再进提示词（只进回执）；上色句只在特征缺「色板」时加（上色极少的速写类给具体颜色，见 _needs_color）；参考图由风格库重切（去错格、去文字标签）。
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
# ⚠ 人物那一句分两档（2026-09-22 拆）：走编号风格时不能再说「形象简洁、不夸张」——
#   风格库的人物类特征（脸型/头身比例/表情自成一套）正好被这句话压平，出来就是通用写实脸，
#   而特征里那半句「避免回落为统一的标准Q版表情」又被 _positive_traits 按含「避免」滤掉了，
#   两头一夹，编号形同虚设（六上五 #105 快速线稿实测出成精修水彩）。styled 档把这半句补回来。
_BG_CONSTRAINT = "浅奶油色背景（色值 #FFF6E3，画面四周渐淡融入背景、留白干净），主体集中在画面中央。"
# 编号分支的底色句去掉「四周渐淡」——那是水彩语汇，会把平涂／清线类画风拉向水彩（2026-09-23）
_BG_STYLED = "浅奶油色背景（色值 #FFF6E3，留白干净），主体集中在画面中央。"
_PEOPLE_PLAIN = "画面中如有人物，为中国小学生、家长或教师，形象简洁亲切、不夸张。"
_PEOPLE_STYLED = ("画面中如有人物，为中国小学生、家长或教师，形象亲切；"
                  "人物的脸型、头身比例、手脚形状、表情与肢体动作一律服从上述风格特征，"
                  "不要回落成通用写实画法。")
# ⚠ 这一条只在编号分支加：通用分支的「水彩平涂」写在 STYLE_PREFIX 里，编号分支没有任何上色约束——
#   风格特征里凡带「线稿／速写／素描」字样的编号（#105 等），不兜这句就直接出黑白单色，
#   放进暖色卡片的海报里整张发灰（六上五实测）。
# ⚠ 2026-09-23 改：原句写死「柔和水彩淡彩上色」，对所有编号一律生效，把 #046 块面平涂、#013 扁平色块等
#   都拉成了水彩。现只在特征里没有「色板」一项（即没说清用什么颜色）时才加，且不指定媒介。
# ⚠ 同日补：速写／线稿类（#105「上色：极少」）光说「按画风自己的上色方式」等于没说，实测又出成近黑白；
#   这类改用 _COLOR_SKETCH 写明具体颜色，线条与人物仍照画风。判型见 _needs_color()。
_COLOR_STYLED = "整幅为彩色画面，按上述画风自己的上色方式着色，不要只有黑白线稿或单色。"
_COLOR_SKETCH = ("整幅为彩色画面：保留上述线条与速写感，线条之外用暖黄、浅蓝、淡粉、浅绿的透明淡彩轻轻铺色，"
                 "人物衣服、皮肤和主要物件都要有颜色，不要只有黑白或灰色线稿。")
_SKETCH_RE = re.compile(r"上色：(?:极少|少量|几乎不)|黑白|单色")


def _needs_color(traits):
    """特征没写色板时返回要补的上色句：速写/线稿类给具体颜色，其余给通用句；写了色板返回空串。"""
    if "色板" in traits:
        return ""
    return _COLOR_SKETCH if _SKETCH_RE.search(traits) else _COLOR_STYLED


_NO_TEXT_CONSTRAINT = ("没有任何文字、字母、数字、水印、品牌标志；"
                       "黑板、纸张、屏幕、标签一律保持空白，不得出现任何可辨认的文字或符号。")
FIXED_CONSTRAINTS = _BG_CONSTRAINT + _PEOPLE_PLAIN + _NO_TEXT_CONSTRAINT
NO_PEOPLE = "画面里没有人、没有手、没有拟人角色。"
NEG_SUFFIX = "。" + FIXED_CONSTRAINTS
# 参考图说明（2026-09-23 由风格库原文的长串「不要…」改为短的正向句：否定清单在 Gemini／Seedream 上易反向泄漏，
#   且原文连「构图、布局」都禁，削弱了风格迁移；内容隔离仍保留）
REF_ISOLATION = ("所附参考图只用来取画风：线条、上色方式、色彩、质感和人物造型比例都照它画；"
                 "画面内容完全按上面的描述，不沿用参考图里的角色和物件。")
JUDGE_Q = (
    "只看这张插画，只回一个 JSON 对象，键与含义："
    "has_text＝画面里是否出现任何文字/字母/数字（true/false）；"
    "has_person＝是否出现人、手或人形角色（true/false）；"
    "bg_cream＝背景主色是否为浅奶油/米白色（true/false）；"
    "subject_ok＝画面是否包含下列物件——{subject}（true/false）；"
    "notes＝一句话说明。只回 JSON，不要解释文字、不要 markdown 代码块。"
)


# 2026-09-23 起海报默认走 gpt-image（#044 两轮对比最贴示例图）；不读 IMAGE_PROVIDER——那是课件配图工具的 .env 口径
DEFAULT_PROVIDER = "gpt-image"


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
        # 画风段放最前、只用中文可见特征；英文风格名与作者名 Gemini／Seedream 基本不认，只留在回执 style_used 里
        traits = style["traits"]
        p = (("请用这种画风绘制：%s。" % traits if traits else "")
             + "画面内容：" + subj + "。"
             + _BG_STYLED + _needs_color(traits) + _PEOPLE_STYLED + _NO_TEXT_CONSTRAINT
             + extra + REF_ISOLATION)
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

    client = load_client(provider or DEFAULT_PROVIDER)
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
    ap.add_argument("--provider", default=None, choices=["gemini", "doubao", "gpt-image"])
    ap.add_argument("--ratio", default=None, choices=["4:3", "1:1", "3:4", "16:9"])
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--force", action="store_true", help="已有正式图也重生")
    ap.add_argument("--no-judge", action="store_true", help="跳过机器判读，候选直接转正（人工验收路径）")
    ap.add_argument("--style", default=None, help="手绘风格编号 001–274（默认 None ⇒ 取 json.illustration.style；都没有走通用前缀）")
    a = ap.parse_args()
    return run(a.data, a.provider, a.ratio, a.seed, a.force, a.no_judge, a.style)


if __name__ == "__main__":
    sys.exit(main())
