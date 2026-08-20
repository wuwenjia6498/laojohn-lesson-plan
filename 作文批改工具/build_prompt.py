# -*- coding: utf-8 -*-
"""把「课次批改标准包 JSON」渲染成可直接粘进任意 AI 的批改助手提示词。

用法：
    PYTHONUTF8=1 python 作文批改工具/build_prompt.py 标准包/三上-第一单元-猜猜他是谁.json

产出：Phase0试用包/<课次>-批改助手.md

设计要点：
- 标准包在提示词里渲染成**中文条目而非 JSON**——通用 AI 读中文段落比读 JSON 稳，
  老师打开看见的也是人话、不是代码。
- 模板与标准包分离：改措辞只动 _批改提示词模板.md，改判据只动标准包 JSON。
- 逐字段来自详案，禁止在本脚本里新增判据（判据的唯一源是详案）。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "Phase0试用包" / "_批改提示词模板.md"
OUTDIR = ROOT / "Phase0试用包"


def render_pack(d):
    """把标准包渲染成中文条目。顺序＝老师批改时的思考顺序。"""
    L = []
    m = d["meta"]
    L.append(f'**题目**：{m["grade_volume"]}·{m["unit"]}《{m["topic"]}》（{m["genre"]}）')
    L.append(f'**教材要求**：{m["textbook_requirement"]}')
    L.append(f'**这次课教的核心技法**：{d["core_technique"]}')
    L.append(f'**学生要达成的**：{d["learning_goal"]}')

    L.append("\n### 三条判据（老师上课时已经念给学生听过，学生知道这三条）\n")
    for c in d["three_checks"]:
        dep = f'（**须第 {c["depends_on"]} 条先成立**；不成立则本条记「不适用」）' if c.get("depends_on") else ""
        L.append(f'{c["no"]}. **{c["text"]}**{dep} —— {c["judge_by"]}')

    L.append("\n### 三档标准（内部参考，不给家长看）\n")
    for band, text in d["bands"].items():
        L.append(f'- **{band}**：{text}')

    moves = d.get("technique_moves") or []
    if moves:
        L.append("\n### 「写具体」具体指什么（课上讲的几种写法，判断时对照着看）\n")
        for mv in moves:
            L.append(f'- {mv["move"]}　例：{mv["model_example"]}')

    ap = d.get("anti_patterns") or {}
    if ap:
        L.append("\n### 这次最容易出的问题\n")
        if ap.get("empty_words"):
            L.append("- **空话**（放在谁身上都成立）：" + "、".join("“" + w + "”" for w in ap["empty_words"]))
        for key in ("rule", "scatter", "secondary_trait_allowance"):
            if ap.get(key):
                L.append(f'- {ap[key]}')

    anchors = d.get("model_essay_anchor_sentences") or []
    if anchors:
        L.append("\n### 课上示范文里的样子（学生听过这几句，可作为「写到位了」的参照）\n")
        for s in anchors:
            L.append(f'- {s}')

    nis = d.get("not_in_scope") or {}
    if nis.get("items"):
        L.append("\n### 明确不判的\n")
        L.append("- " + "、".join(nis["items"]))
        if nis.get("why"):
            L.append(f'  原因：{nis["why"]}')
        for exc in nis.get("exceptions") or []:
            L.append(f'- **但这一项要判**：{exc}')

    return "\n".join(L)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    pack_path = Path(sys.argv[1])
    if not pack_path.is_absolute():
        pack_path = ROOT / pack_path
    d = json.loads(pack_path.read_text(encoding="utf-8"))

    if not d.get("source", {}).get("verified_by_human"):
        print("⚠ 提醒：该标准包 verified_by_human=false，人工过一遍再发给加盟商。")

    md = TEMPLATE.read_text(encoding="utf-8")
    md = md.replace("{{TOPIC}}", d["meta"]["topic"])
    md = md.replace("{{STANDARD_PACK}}", render_pack(d))
    md = md.replace("{{JUDGING_RULES}}", judging_rules(d))
    md = md.replace("{{PARENT_CARD_RULES}}", parent_card_rules())

    out = OUTDIR / f'{pack_path.stem}-批改助手.md'
    out.write_text(md, encoding="utf-8")
    print(f"已生成：{out}")
    return 0


# ---------------------------------------------------------------------------
# 「怎么判」的共用规则（Phase 0 提示词与 Phase 3 服务端共用同一份）
#
# 为什么抽出来：判断规则原本在两处各写一份措辞——Phase0试用包/_批改提示词模板.md
# 与 web/server/main.py 的 GRADE_RULES。改一处不改另一处，两条线立刻分叉，
# 而分叉了不会报错，只会让加盟商手上那份和线上那份判得不一样。
#
# 边界：这里只放**跨课次通用**的判断规则。课次特有的判据、档位、空话表一律
# 走标准包 JSON（见 render_pack）。往这里塞任何一课的具体内容，就是重蹈
# 「模板写死《猜猜他是谁》三条判据」那次的覆辙。
# ---------------------------------------------------------------------------

def judging_rules(d):
    g = d["meta"].get("grade_volume", "本年级")
    return f"""### 〇、引用铁律（最容易犯，先说）

凡是写进 evidence／quote／quoted_sentence 的句子，必须是**原文里连续的一段，逐字照抄**：

- **不许用省略号跨接**——把相隔很远的两处拼成「他最大的毛病……他又慌了」，那是编造；
- **不许写「从 X 到 Y」**这类范围描述，那不是引用；
- **不许加字、改字、动标点**——原文是「说：」就不要写成「他说：」；原文是全角逗号，
  就不要输出半角逗号；
- **引不全没关系，宁可只引半句**，也不许把几处拼起来凑一句完整的。

老师会拿着点评卡对稿纸看。引错一个字，他就再也不信这个工具了。

### 一、先读这一篇本身，别一上来就套判据

通读一遍，先在心里回答三个问题：这孩子写了什么？哪一处是**他自己的东西**？哪一处卡住了？

一上来就照判据打钩，三十篇会批出三十条一模一样的话，老师和家长一眼就看穿。

### 二、三条判据（主判据，档位只由这三条定）

逐条判断，每条都要引用学生原文里的具体句子作依据，不能只说“做到了／没做到”。
若某条标了「须第 N 条先成立」而第 N 条不成立，该条记「不适用」，改进方向落回第 N 条。
判完对照三档标准给一个内部档位。

### 三、整篇怎么样（三项，给老师看，**不进档位**）

1. **完整性**：写完了没有？开头、经过、结尾齐不齐？半截停住、只开了个头就没下文，要明确说出来。
2. **顺序**：讲得清不清楚？有没有前后跳、有没有自相矛盾的地方？
3. **读不读得通**：句子顺不顺？有没有哪句绕不出来、同一个意思翻来覆去说。

每项一句话说清怎么看出来的。**不要为这三项去引原文**——完整性、顺序是全篇的属性，硬要举一句原文，只会逼出省略号拼接和「从 X 到 Y」这种假引用。

**这三项不改档位**——档位是三条判据的事；它们是给老师判断
「这篇要不要重写、讲评课讲什么」用的，**也不要直接跟家长说“你孩子逻辑乱”**。

按 **{g}** 的水平判断，别拿高年级的标准要求低年级——中年级把一件事写清楚就够了，
不必苛求过渡自然、首尾呼应。

### 四、这孩子自己写得好的地方

找出**他自己的东西**：用得准的词、有意思的句式、一个别人想不到的观察、一句实在的真心话。
逐字引原文，说清好在哪。

- **可以一个都没有。** 这一篇确实没有就说没有，硬找出来夸是假话，家长看得出。
- **不许夸空的**：“语言生动”“感情真挚”“用词优美”这类放在谁身上都成立的话一律不算亮点。
  说不出具体好在哪，就不是亮点。
- **不限于这次课教的技法。** 孩子自己蹦出来的好句子，哪怕跟本课技法无关也值得记下来——
  这往往是点评卡里最打动家长的那一句。

### 五、挑出这一篇最值得说的那一件事

把上面的东西过一遍，挑出**最值得跟家长说的一件**：可能是一个亮点，可能是某条判据做到了，
也可能是“还没写完”这种得先解决的问题。**点评卡就从这一件说起**——每篇都从第一条判据
开头，正是三十篇一个样的根源。"""


def parent_card_rules():
    """给家长的点评卡要求（两条线共用）。150 字的硬约束在这里，不要在别处再写一份。"""
    return """150 字以内，会做成图片发家长群。硬要求：

- **围绕上面挑出的那一件事写，只说这一件**，不要面面俱到——什么都提等于什么都没说；
- **必须引用孩子作文里的一个真实句子**（一字不改）。**优先引「他自己写得好的地方」里的句子**，
  那是家长最想看到的；确实没有亮点的，才从判据的依据句里选；
- 说清这一句好在哪。若这句正对着本课技法，就贴着技法说；若是孩子自己的灵光，就照实夸那一处，
  不必硬往技法上靠。**不要泛泛夸“语言生动”“感情真挚”**；
- 给一条**具体到能做**的下次方向（如“下次试着为他的这个特点再多写一件小事”，不是“继续加油”）；
- **你在跟家长说话，不是跟孩子说话。** 说“他／她”或直接说名字，**不要用“你”称呼孩子**；
  下次方向写成“下次可以请他试着……”，不是“下次你可以试着……”。
- 口气像老师当面跟家长说话，不出现“该生”“本文”“习作水平”这类书面语；
- **别用固定招呼语起头**：不要每篇都是“××同学……”，也不要每篇都是“××家长您好”。
  一个班二三十份发在同一个群里，起手式一样，家长一眼就看出是一个模子印的。
  **从这个孩子写的内容说起**，第一句就落到他的原句或他这一篇的那件事上。
- 不出现档位、分数、排名；不要“首先……其次……最后”这种结构；
- 写得确实弱的**不要硬夸**：找出他写得最像样的那一句照实说，努力方向说具体些；
- 学生若写到家人隐私或不愉快的事，点评卡上不展开，改在给老师的那块里提醒。"""


if __name__ == "__main__":
    sys.exit(main())
