# -*- coding: utf-8 -*-
"""按课件项目 JSON 跑完一整课的配图（PRD §3 主线的命令行版）。

这不是验证脚本，是「把打样清单整份跑一遍」的生产跑批：产出一套真能插进 PPT 的图，
同时用真实数据检验清单结构够不够用——不够用的地方直接改 JSON，那份 JSON 就是
未来 MVP 的表结构。

分三阶段，**两道人工闸门是真闸门**：
    char    出角色件（定妆 A / 定妆 A 全身 / 定妆 B / 两张剪影）
    ——闸门 1：人工看图，`--approve char` 才写入验收记录
    pages   出各页目（未过闸门 1 直接拒绝执行）
    ——闸门 2：人工看图，`--approve pages`
    export  按 `课名-P页码-用途-序号.png` 导出成包 + 清单 csv（未过闸门 2 拒绝）

用法：
    python scripts/run_lesson.py 课件项目/猜猜他是谁.json --stage char
    python scripts/run_lesson.py 课件项目/猜猜他是谁.json --approve char --by 文佳
    python scripts/run_lesson.py 课件项目/猜猜他是谁.json --stage pages
    python scripts/run_lesson.py 课件项目/猜猜他是谁.json --approve pages --by 文佳
    python scripts/run_lesson.py 课件项目/猜猜他是谁.json --stage export
    python scripts/run_lesson.py 课件项目/猜猜他是谁.json --status
"""
import argparse
import csv
import re
import shutil
import datetime
import json
import pathlib
import sys

from imgclient import make_client

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parents[1]
GATES = {"char": "闸门1·定妆验收", "pages": "闸门2·页目验收"}


def load(project_path, provider=None):
    """产出目录：课件产出/<项目文件名>/<通道>/。

    **按通道分**不是为了整齐，是为了让「换通道 ⇒ 旧验收作废」这件事显式化。
    验收记录跟着目录走；若两条通道共用一个目录，新图会悄悄覆盖已验收的旧图，
    而 `_验收记录.json` 还写着「已通过」——验收记录就成了假的。

    **按项目文件名分（不是按 project.名称）**：名称是内容字段，两份项目可以重名。
    实测手抄版与自动拆解版都叫「猜猜他是谁」，于是共用一个目录、两套角色件混在一起，
    验收记录把另一份项目的 5 张也算了进来——声称验了 8 张，实际只看过 3 张。
    文件名在同一目录里天然唯一，拿它做目录名就不会撞。
    """
    import os
    path = pathlib.Path(project_path)
    d = json.loads(path.read_text(encoding="utf-8"))
    prov = provider or os.environ.get("IMAGE_PROVIDER") or "gemini"
    outdir = ROOT / "课件产出" / path.stem / prov
    outdir.mkdir(parents=True, exist_ok=True)
    return d, outdir


def gate_file(outdir):
    return outdir / "_验收记录.json"


def read_gates(outdir):
    f = gate_file(outdir)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def gate_applies(d, name):
    """这道闸门对本项目适不适用。

    **不是每个课件都有跨页角色。**《写日记》六个图位的人物各不相同
    （小蚯蚓 / 女老师 / 三个不同场合的学生），按规则一个定妆图都不该出，
    于是 characters 为空 —— 这时闸门1 就成了死结：
    要出页目被拦着说「先验收定妆」，去验收又被拦着说「一张图都没有」。
    闸门1 防的是「定妆错了连累后面每一张」，没有定妆图就没有这个风险，
    这道门自然不适用。
    """
    if name == "char":
        return bool(d.get("characters"))
    return True


def require_gate(outdir, name, d=None):
    """查这道闸门的验收记录。**不阻断**（2026-08-28 用户决定）。

    原设计是硬闸门：不可逆节点必须有人判断、不设逃生口，理由是定妆图错了
    后面每一张都得重来。取消阻断是用户的决定；**验收记录功能保留** ——
    `--approve` 照常可用，那是「谁在何时验过哪几张」的凭据。
    要恢复阻断，把下面的 print 换回 raise SystemExit 即可。
    """
    if d is not None and not gate_applies(d, name):
        return None
    g = read_gates(outdir).get(name)
    if not g:
        print(f"提示：{GATES[name]}尚未验收（不阻断）。要留凭据就跑 --approve {name} --by <验收人>")
    return g


def approve(outdir, name, by, note="", d=None):
    """记录一道闸门的验收。

    只记**本项目声明过的那几件**，不记目录里碰巧存在的 jpg。两条理由：
    ① 下划线开头的目录是废版/归档，混进去等于记录说了谎；
    ② 目录里可能躺着别的项目留下的图（实测两份同名项目共用目录，
       验收记录把另一份的 5 张也算了进来，声称验了 8 张、实际只看过 3 张）。
    验收记录要能回答的是「那一刻你验的是哪几张」，多一张都不行。
    """
    want = None
    if d:
        want = {"角色/" + c["id"] + ".jpg" for c in d.get("characters", [])}
        want |= {"页目/" + s["页码"] + ".jpg" for s in d.get("slides", [])}
    imgs = sorted(str(f.relative_to(outdir)).replace(chr(92), "/") for f in outdir.rglob("*.jpg")
                  if not any(part.startswith("_") for part in f.relative_to(outdir).parts))
    if want is not None:
        imgs = [x for x in imgs if x in want]
    if not imgs:
        raise SystemExit("⛔ 目录里一张图都没有，没什么可验收的。")
    g = read_gates(outdir)
    g[name] = {"验收人": by, "时间": datetime.datetime.now().isoformat(timespec="seconds"),
               "备注": note, "验收时已在盘的图": imgs}
    gate_file(outdir).write_text(json.dumps(g, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✓ {GATES[name]} 已记录，验收人：{by}（覆盖 {len(imgs)} 张图）")


def prefix_for(style, slide):
    """拼这一页的风格前缀，按 slide 上的两个开关裁掉人物条目 / 文字禁令。

    优先走**分段字段**（`前缀基底` + `人物条目` + `文字禁令`）——三段拼，开关只决定拼不拼。
    ⚠ 旧格式的整句前缀只能靠 replace 字面串来裁，而那串是照着手抄那份前缀写死的：
    换一份措辞（比如自动拆解生成的前缀）replace 就一个字都匹配不上，开关**静默失效**。
    所以回落分支里未命中必须喊出来，绝不假装裁过了。
    """
    base = style.get("前缀基底")
    if base:
        parts = [base]
        if not slide.get("去人物条目") and style.get("人物条目"):
            parts.append(style["人物条目"])
        if not slide.get("允许画面文字") and style.get("文字禁令"):
            parts.append(style["文字禁令"])
        return "，".join(x.strip("，。 ") for x in parts if x) + "。"

    p = style["通用风格前缀"]
    for on, frag in (("去人物条目", "主体人物为8到9岁的中国小学生，"),
                     ("允许画面文字", "，画面中不出现任何文字")):
        if slide.get(on):
            if frag not in p:
                raise SystemExit(
                    f"⛔ {slide.get('页码','?')} 开了「{on}」，但整句前缀里找不到要裁掉的那段"
                    f"（{frag!r}）。这个开关对当前前缀无效——改用分段字段"
                    f"（前缀基底/人物条目/文字禁令），别让它静默失效。")
            p = p.replace(frag, "")
    return p


def resolve_refs(names, outdir, made):
    """把挂载项换成实际图片路径；缺哪张就说清楚缺哪张，不静默跳过。

    挂载项有两种，按这个顺序找：
      1. **角色件 id** —— 在 `角色/` 下（定妆、剪影这些）
      2. **别页的页码** —— 在 `页目/` 下

    第 2 种是 2026-08-30 加的：对比图、同场景的多个变体，光靠文字说
    「和上一张同样构图」没用，模型看不到上一张。把那张真挂上去才管用。
    ⚠ 一页不能挂自己（会拿上一版当参考，越改越偏），调用方负责拦。
    """
    paths = []
    for n in names or []:
        f = made.get(n) or (outdir / "角色" / f"{n}.jpg")
        if not pathlib.Path(f).exists():
            alt = outdir / "页目" / f"{n}.jpg"      # 不是角色件，那就当页码找
            if alt.exists():
                paths.append(alt)
                continue
            raise FileNotFoundError(
                f"挂载的「{n}」还没生成"
                f"（角色件应在 {f}；若挂的是别页，应在 {alt}）。"
                f"命令行下先跑 --stage char；网页里点「生成未出的」会自动先补。")
        paths.append(pathlib.Path(f))
    return paths


def gen(client, outdir, sub, name, prompt, ratio, refs, force=False):
    dest = outdir / sub / f"{name}.jpg"
    if dest.exists() and not force:
        print(f"  [已有] {sub}/{name}")
        return dest
    print(f"  [生成] {sub}/{name} ({ratio}){f' ←挂{len(refs)}张' if refs else ''}")
    return client.save(client.generate(prompt, ratio=ratio, images=refs or None), dest)


def stage_char(d, outdir, client, force, only=None):
    style = d["style_card"]
    made = {}
    for c in d["characters"]:
        if only and c["id"] not in only:
            made[c["id"]] = outdir / "角色" / f"{c['id']}.jpg"
            continue
        refs = resolve_refs(c.get("挂载"), outdir, made)
        # 编辑通道（剪影转制）不拼风格前缀：整句就是编辑指令，拼前缀反而会把它拉回插画
        p = c["prompt"] if c.get("通道") == "编辑" else prefix_for(style, c) + " " + c["prompt"]
        made[c["id"]] = gen(client, outdir, "角色", c["id"], p, c["画幅"], refs, force)

    # 验收提示按实际角色件生成，不写死名字 —— 原先这里硬编码着手抄那份的
    # 「定妆A 三要素（发型/圆框眼镜/浅蓝毛衣）」，换一份项目就全对不上，
    # 而看图的人多半照着念，等于把验收引到不存在的东西上。
    print(f"\n出了 {len(made)} 个角色件。**请人工逐张看图**：")
    for c in d["characters"]:
        pts = []
        if "全身" in c["id"]:
            pts.append("双脚完整入镜（它是后续所有页的比例基准，截断就没有基准了）")
        if "剪影" in c["id"]:
            pts.append("纯单色、无五官，发型轮廓与所挂的定妆图一致")
        if c.get("挂载"):
            pts.append("与所挂的 " + "、".join(c["挂载"]) + " 是同一个人")
        if not pts:
            pts.append("识别特征清晰稳定（对照下面这句规格原话逐项看）")
        print("  · " + c["id"] + "：" + "；".join(pts))
        print("      规格原话：" + c["prompt"][:76] + "…")
    print("确认后：--approve char --by <你的名字>")
    return made


def stage_pages(d, outdir, client, force, only=None, proj_path=None):
    require_gate(outdir, "char", d)
    style = d["style_card"]
    made = {c["id"]: outdir / "角色" / f"{c['id']}.jpg" for c in d["characters"]}
    done, skipped = {}, []
    for s in d["slides"]:
        ch = s["通道"]
        if ch == "人工素材位":
            skipped.append((s["页码"], s.get("_说明", "人工素材位")))
            continue
        if ch == "复用":
            # --only 补跑时源页多半不在本轮 done 里，但盘上早就有 —— 直接拿盘上那张。
            # 实测 0903 补跑 4 页，走到 P15 复用 P14 就 SystemExit，后面的页全没跑。
            src = (made.get(s["复用"]) or done.get(s["复用"])
                   or outdir / "页目" / f"{s['复用']}.jpg")
            if not src or not pathlib.Path(src).exists():
                raise SystemExit(f"⛔ {s['页码']} 要复用「{s['复用']}」，但那张还不存在。")
            done[s["页码"]] = src
            print(f"  [复用] {s['页码']} ← {s['复用']}")
            continue
        if only and s["页码"] not in only:
            continue
        refs = resolve_refs(s.get("挂载"), outdir, made)
        p = prefix_for(style, s) + " " + s["prompt"]
        done[s["页码"]] = gen(client, outdir, "页目", s["页码"], p, s["画幅"], refs, force)
        # 记下这张图是按哪段描述画的。重新拆解会改写描述而图不会跟着变，
        # 没有这个印记就只能拿文件时间猜「图是不是旧的」——
        # 实测有个项目 27 张里 17 张对不上描述，界面上完全看不出来。
        s["_出图描述"] = s.get("prompt", "")
    print(f"\n生成/复用 {len(done)} 个页目；人工素材位 {len(skipped)} 个：")
    for pg, why in skipped:
        print(f"  · {pg}：{why}")
    if proj_path is not None:
        pathlib.Path(proj_path).write_text(
            json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n**请人工对照必现细节逐条勾验**（各页清单见项目 JSON 的 必现细节 字段）。")
    print("确认后：--approve pages --by <你的名字>")
    return done


def stage_export(d, outdir):
    """按 PRD FR-7 导出：课名-P页码-用途-序号.png + 清单 csv。"""
    # 闸门改成不阻断后，没验收时 require_gate 返回 None —— 这里必须接住。
    # 漏了它，一个没签过字的项目一点「导出」就是 500，而报错还指向 csv 那一行。
    g = require_gate(outdir, "pages") or {}
    name = d["project"]["名称"]
    pack = outdir / "导出"
    pack.mkdir(exist_ok=True)
    rows = []
    for s in d["slides"]:
        if s["通道"] == "人工素材位":
            rows.append([s["页码"], "（人工素材位·未生成）", s["画幅"], s["用途"], "", ""])
            continue
        src = outdir / ("页目" if s["通道"] == "生成" else "角色") / f"{s['页码']}.jpg"
        if s["通道"] == "复用":
            r = s["复用"]
            src = outdir / ("角色" if any(c["id"] == r for c in d["characters"]) else "页目") / f"{r}.jpg"
        if not src.exists():
            rows.append([s["页码"], "（缺图）", s["画幅"], s["用途"], "", ""])
            continue
        # 用途里的斜杠等字符不能进文件名；更要紧的是**长度**——
        # 原来只按「·」切，而自动拆解写出的用途是一整句自然语言、根本没有「·」，
        # 于是 60 多字连标点全进了文件名。按第一个标点切、再截到 14 字。
        use = re.split(r"[·，。、；：—\-]", s["用途"])[0].strip()[:14]
        use = re.sub(r'[/\:*?"<>|]', "／", use) or "配图"
        # 直接复制，不转 PNG。源图本来就是 JPEG —— 转 PNG 既不提升画质
        # （有损压缩的损失早已发生），还把体积放大 6.3 倍、每张多花 1.3 秒。
        # 实测一课 27 张：转 PNG 是 36 秒 / 124MB，直接复制是 1 秒 / 20MB。
        # PPT 插图用 JPEG 完全够。
        fn = f"{name}-{s['页码']}-{use}-01.jpg"
        shutil.copy2(src, pack / fn)
        rows.append([s["页码"], fn, s["画幅"], s["用途"],
                     g.get("验收人", ""), g.get("时间", "")])
    with open(pack / "导出清单.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["页码", "文件名", "画幅", "用途", "验收人", "验收时间"])
        w.writerows(rows)
    print(f"✓ 导出 {sum(1 for r in rows if r[1].endswith('.jpg'))} 张到 {pack}")
    print(f"  清单：{pack / '导出清单.csv'}")


def status(d, outdir):
    g = read_gates(outdir)
    print(f"项目：{d['project']['名称']}  目录：{outdir}")
    for k, label in GATES.items():
        v = g.get(k)
        print(f"  {label}：{'✓ ' + v['验收人'] + ' @ ' + v['时间'] if v else '✗ 未通过'}")
    have_c = sum(1 for c in d["characters"] if (outdir / "角色" / f"{c['id']}.jpg").exists())
    need = [s for s in d["slides"] if s["通道"] == "生成"]
    have_p = sum(1 for s in need if (outdir / "页目" / f"{s['页码']}.jpg").exists())
    print(f"  角色件 {have_c}/{len(d['characters'])}；需生成页目 {have_p}/{len(need)}"
          f"（另有复用 {sum(1 for s in d['slides'] if s['通道']=='复用')} 条、"
          f"人工素材位 {sum(1 for s in d['slides'] if s['通道']=='人工素材位')} 条）")


def main():
    ap = argparse.ArgumentParser(description="按课件项目 JSON 跑完一整课的配图")
    ap.add_argument("project", help="课件项目 JSON 路径")
    ap.add_argument("--stage", choices=["char", "pages", "export"])
    ap.add_argument("--approve", choices=list(GATES), help="记录人工验收，放行下一阶段")
    ap.add_argument("--by", default="", help="验收人")
    ap.add_argument("--note", default="", help="验收备注")
    ap.add_argument("--force", action="store_true", help="已有图也重新生成")
    ap.add_argument("--only", nargs="*",
                    help="只处理指定的角色 id 或页码（配 --force 重跑单件，不炸掉整批）")
    ap.add_argument("--status", action="store_true", help="只看进度")
    ap.add_argument("--provider", choices=["gemini", "doubao"],
                    help="生图通道（缺省读 .env 的 IMAGE_PROVIDER）。换通道＝换产出目录，旧验收不继承")
    a = ap.parse_args()
    d, outdir = load(a.project, a.provider)

    if a.status:
        return status(d, outdir)
    if a.approve:
        if not a.by:
            raise SystemExit("⛔ 验收必须记名：--by <验收人>。没有名字的验收等于没验收。")
        return approve(outdir, a.approve, a.by, a.note, d)
    if not a.stage:
        return status(d, outdir)
    if a.stage == "export":
        return stage_export(d, outdir)
    client = make_client(a.provider)
    print(f"项目：{d['project']['名称']}｜通道：{client.name}｜模型：{client.model}"
          f"｜输出：{outdir}")
    print()
    # 两个 stage 的签名不同：只有 stage_pages 收 proj_path（它要回写出图印记），
    # 所以别再用三元表达式硬拼成一次调用。
    if a.stage == "char":
        stage_char(d, outdir, client, a.force, a.only)
    else:
        stage_pages(d, outdir, client, a.force, a.only, a.project)
    print(f"\n用量：{client.usage}")


if __name__ == "__main__":
    main()
