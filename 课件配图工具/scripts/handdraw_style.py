# -*- coding: utf-8 -*-
"""手绘风格编号 → 画风特征 + 参考图（单一源）。

2026-09-24 从写作课海报 `gen_illustration.py` 抽出，供两家共用：
  · 课件配图工具（`run_lesson.compose()`，风格卡字段 `手绘编号`）
  · laojohn-writing-poster（`gen_illustration.py` importlib 载入，**禁复制**）
改这里的任何一句，两家都要回归：海报跑 build_prompt 快照比对（逐字相等），
课件配图跑 compose 看拼出来的提示词。

资产：`课件配图工具/手绘风格库/`
  · `styles.json`：用户级 skill handdraw-style-prompter 的 274 条风格索引整份拷贝
  · `refs/<编号>.webp`：**只放用过的编号**。首次用某编号自动从用户级包拷一份进来——
    请随项目/海报 json 一并提交，同事机器不装风格库也能重生
用户级包（可能不存在）：`%USERPROFILE%/.claude/skills/handdraw-style-prompter/`，
私有仓库与装法见 docs/协作同步说明.md 五点五节。
"""
import json
import re
import shutil
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "手绘风格库"
USER_PKG = Path.home() / ".claude" / "skills" / "handdraw-style-prompter"

# ⚠ 上色句只在特征里没有「色板」一项（即没说清用什么颜色）时才加，且不指定媒介——
#   原句写死「水彩淡彩」，把 #046 块面平涂、#013 扁平色块都拉成了水彩（2026-09-23）。
# ⚠ 速写／线稿类（#105「上色：极少」）光说「按画风自己的上色方式」等于没说，实测出成近黑白；
#   这类改用 COLOR_SKETCH 写明具体颜色，线条与人物仍照画风。
COLOR_STYLED = "整幅为彩色画面，按上述画风自己的上色方式着色，不要只有黑白线稿或单色。"
COLOR_SKETCH = ("整幅为彩色画面：保留上述线条与速写感，线条之外用暖黄、浅蓝、淡粉、浅绿的透明淡彩轻轻铺色，"
                "人物衣服、皮肤和主要物件都要有颜色，不要只有黑白或灰色线稿。")
_SKETCH_RE = re.compile(r"上色：(?:极少|少量|几乎不)|黑白|单色")

# 参考图说明：短的正向句。否定清单在 Gemini／Seedream 上易反向泄漏，且风格库原文连「构图、布局」都禁，
# 削弱了风格迁移；内容隔离仍保留（2026-09-23）。
REF_ISOLATION = ("所附参考图只用来取画风：线条、上色方式、色彩、质感和人物造型比例都照它画；"
                 "画面内容完全按上面的描述，不沿用参考图里的角色和物件。")
# 同时挂了定妆图／别页图时用这句：风格图排在最后，要把两类参考图分开说，
# 否则模型会拿风格图里的角色去替掉定妆图的人。
REF_ISOLATION_MIXED = ("所附参考图中，最后一张只用来取画风：线条、上色方式、色彩、质感和人物造型比例都照它画，"
                       "不沿用它里面的角色和物件；其余参考图用来保持人物长相与画面一致。")


def needs_color(traits):
    """特征没写色板时返回要补的上色句：速写/线稿类给具体颜色，其余给通用句；写了色板返回空串。"""
    if "色板" in traits:
        return ""
    return COLOR_SKETCH if _SKETCH_RE.search(traits) else COLOR_STYLED


def positive_traits(traits):
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
    num = "%03d" % int(str(number).lstrip("#").strip())
    idx = ASSETS / "styles.json"
    if not idx.exists():
        idx = USER_PKG / "skills" / "handdraw-style-prompter" / "references" / "styles.json"
    if not idx.exists():
        raise FileNotFoundError("风格索引不存在（仓内 课件配图工具/手绘风格库/styles.json 与用户级风格库都没有）")
    rec = next((r for r in json.loads(idx.read_text(encoding="utf-8")) if r.get("number") == num), None)
    if not rec:
        raise ValueError("风格编号 %s 不在索引里（001–274）" % num)
    refs = ASSETS / "refs"
    local = next((p for p in (refs / (num + "_grid.webp"), refs / (num + ".webp")) if p.exists()), None)
    if local is None:
        start = ((int(num) - 1) // 200) * 200 + 1
        bucket = USER_PKG / "images" / "individual" / ("%03d-%03d" % (start, start + 199))
        src = next((p for p in (bucket / (num + "_grid.webp"), bucket / (num + ".webp")) if p.exists()), None)
        if src is None:
            raise FileNotFoundError("编号 %s 的参考图既不在仓内 refs/ 也不在用户级风格库（%s）" % (num, bucket))
        refs.mkdir(parents=True, exist_ok=True)
        local = refs / src.name
        shutil.copyfile(src, local)
        print("  [风格] 参考图首次使用，已拷进仓：%s（请一并提交）" % local.name)
    return {"number": num, "name": rec.get("generation_name", ""), "reference": rec.get("reference", ""),
            "traits": positive_traits(rec.get("traits", "")), "ref_path": str(local)}
