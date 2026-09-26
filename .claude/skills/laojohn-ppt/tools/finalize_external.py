"""finalize_external.py - 外部件添图后的终稿收尾（2026-09-26，六上五 v9 手工步骤沉淀）。

外部平台出的写作课 PPT，添完图（illustrate_pptx.py）后还差几步才是终稿，本工具一次做完，可任选：

  --worksheet-after N   在第 N 页（自由写作说明页）之后插稿纸页：沿用该页的眉标方块、眉标字、logo、计时徽标，
                        中间放 grab_worksheet.py 从 --student-html 现截的稿纸图（14.63 英寸宽、居中，同三套终稿）。
  --drop-match 文字      删掉含该文字的页（缺省不删；讲评页用 --drop-match 习作讲评）。
  --text-from 参考.pptx  按参考件（同一外部件血缘的文字润色版）逐框换文字：页按「眉标+文本框 id」自动配对，
                        同 shape_id 的文本框整框换 txBody，几何与动画不动。
  --zh-cn               把含中文的 run 由 lang=en-US 改 zh-CN——外部件一律标 en-US，PowerPoint 就按英文断行、
                        标点落行首；页题文字框顺带加宽到放得下，题条同步拉长。

同目录若有 <pptx>-anim.json（仓内动画版），插页／删页后按新页序重排，新插的稿纸页 skip。
每步之后校验：shape id 不重复、各页点击数与改前一致（插删页之外）。

    python finalize_external.py 终稿.pptx --worksheet-after 24 --student-html 写作配套输出/<课次>/<课次>-学生用.html \\
        --drop-match 习作讲评 --text-from 润色稿.pptx --zh-cn [-o 另存.pptx]
"""
import argparse
import copy
import difflib
import importlib.util
import io
import json
import pathlib
import re
import tempfile
from collections import Counter

from PIL import Image
from pptx import Presentation
from pptx.oxml.ns import qn
from pptx.util import Emu

IN = 914400
HERE = pathlib.Path(__file__).resolve().parent
CJK = re.compile(r"[　-〿一-鿿＀-￯]")


def texts(slide):
    return [sh.text_frame.text.strip() for sh in slide.shapes if sh.has_text_frame and sh.text_frame.text.strip()]


def insert_worksheet(prs, after, sheet_png):
    src = prs.slides[after - 1]
    keep = []
    for sh in src.shapes:
        t = sh.text_frame.text.strip() if sh.has_text_frame else ""
        top, left = sh.top / IN, sh.left / IN
        if top < 1.4 and left < 4 and sh.shape_type != 13:           # 眉标方块＋眉标字
            keep.append(sh)
        elif "⏱" in t:                                               # 计时徽标文字
            keep.append(sh)
    timer = [sh for sh in keep if sh.has_text_frame and "⏱" in sh.text_frame.text]
    if not timer:
        raise SystemExit(f"第 {after} 页没有计时徽标（⏱），不像自由写作说明页")
    tb = timer[0]
    for sh in src.shapes:                                             # 徽标底色块：罩住计时文字的无字形状
        if sh in keep or sh.shape_type == 13 or (sh.has_text_frame and sh.text_frame.text.strip()):
            continue
        if sh.left <= tb.left and sh.top <= tb.top and sh.left + sh.width >= tb.left + tb.width - IN * 0.1 \
                and sh.top + sh.height >= tb.top + tb.height - IN * 0.1 and sh.width < IN * 8:
            keep.append(sh)
    new = prs.slides.add_slide(src.slide_layout)
    for ph in list(new.placeholders):
        ph._element.getparent().remove(ph._element)
    tree = new.shapes._spTree
    for sh in sorted(keep, key=lambda s: 0 if "⏱" not in (s.text_frame.text if s.has_text_frame else "") else 1):
        tree.append(copy.deepcopy(sh._element))
    for sh in src.shapes:                                             # logo：页顶右侧的小图
        if sh.shape_type == 13 and sh.top / IN < 1.2 and sh.left / IN > 16:
            new.shapes.add_picture(io.BytesIO(sh.image.blob), sh.left, sh.top, sh.width, sh.height)
    im = Image.open(sheet_png).convert("RGB")
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    w = 14.63
    new.shapes.add_picture(buf, Emu(int((20 - w) / 2 * IN)), Emu(int(1.53 * IN)), Emu(int(w * IN)),
                           Emu(int(w * im.height / im.width * IN)))
    lst = prs.slides._sldIdLst
    el = lst[-1]
    lst.remove(el)
    lst.insert(after, el)


def drop_pages(prs, match):
    lst = prs.slides._sldIdLst
    gone = []
    for i in range(len(prs.slides) - 1, -1, -1):
        if any(match in t for t in texts(prs.slides[i])):
            el = lst[i]
            prs.part.drop_rel(el.rId)
            lst.remove(el)
            gone.append(i + 1)
    return sorted(gone)


def sync_text(prs, ref_path):
    ref = Presentation(ref_path)

    def sig(s):
        t = texts(s)
        return (t[0][:10] if t else "") + "|" + ",".join(str(sh.shape_id) for sh in s.shapes if sh.has_text_frame)

    A = [sig(s) for s in prs.slides]
    B = [sig(s) for s in ref.slides]
    pairs = []
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, A, B, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and a2 - a1 == b2 - b1):
            pairs += list(zip(range(a1, a2), range(b1, b2)))
    n = 0
    for ia, ib in pairs:
        X = {sh.shape_id: sh for sh in prs.slides[ia].shapes if sh.has_text_frame}
        Y = {sh.shape_id: sh for sh in ref.slides[ib].shapes if sh.has_text_frame}
        for sid in set(X) & set(Y):
            if X[sid].text_frame.text != Y[sid].text_frame.text:
                old = X[sid]._element.find(qn("p:txBody"))
                old.addprevious(copy.deepcopy(Y[sid]._element.find(qn("p:txBody"))))
                old.getparent().remove(old)
                n += 1
    unpaired = sorted(set(range(len(A))) - {a for a, _ in pairs})
    return n, [i + 1 for i in unpaired]


def zh_cn(prs):
    n = 0
    for s in prs.slides:
        for sh in s.shapes:
            if not sh.has_text_frame:
                continue
            for para in sh.text_frame.paragraphs:
                for r in para.runs:
                    rp = r._r.find(qn("a:rPr"))
                    if rp is not None and rp.get("lang") == "en-US" and CJK.search(r.text):
                        rp.set("lang", "zh-CN")
                        rp.set("altLang", "en-US")
                        n += 1
                e = para._p.find(qn("a:endParaRPr"))
                if e is not None and e.get("lang") == "en-US" and CJK.search(para.text):
                    e.set("lang", "zh-CN")
        # 页题（题条内的文字框）放不下就加宽，题条同步拉长
        tt = [sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.strip()
              and 1.6 <= sh.top / IN <= 1.8 and 1.5 <= sh.left / IN <= 1.7]
        bars = [sh for sh in s.shapes if abs(sh.top / IN - 1.55) < 0.06 and abs(sh.left / IN - 1.15) < 0.06
                and not (sh.has_text_frame and sh.text_frame.text.strip())]
        if tt:
            t = tt[0]
            need = len(t.text_frame.text.strip()) * 0.4445 + 0.35       # 32pt 全角字宽约 0.4445 英寸
            if t.width / IN < need:
                t.width = Emu(int(need * IN))
                if bars and bars[0].left + bars[0].width < t.left + t.width + IN * 0.15:
                    bars[0].width = Emu(int(t.left + t.width + IN * 0.35 - bars[0].left))
    return n


def clicks(prs):
    return [s._element.xml.count('nodeType="clickEffect"') for s in prs.slides]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pptx")
    ap.add_argument("-o", "--out")
    ap.add_argument("--worksheet-after", type=int)
    ap.add_argument("--student-html")
    ap.add_argument("--drop-match")
    ap.add_argument("--text-from")
    ap.add_argument("--zh-cn", action="store_true")
    a = ap.parse_args()
    src = pathlib.Path(a.pptx)
    out = pathlib.Path(a.out) if a.out else src
    prs = Presentation(src)
    order = list(range(1, len(prs.slides) + 1))                      # 新页序里每页对应的原页号（0＝新插）

    if a.text_from:
        before = clicks(prs)
        n, unpaired = sync_text(prs, a.text_from)
        assert clicks(prs) == before
        print(f"文字按 {pathlib.Path(a.text_from).name} 同步：换 {n} 个文本框；未配对页 {unpaired or '无'}")
    if a.worksheet_after:
        if not a.student_html:
            raise SystemExit("--worksheet-after 需要 --student-html")
        spec = importlib.util.spec_from_file_location("grab", HERE / "grab_worksheet.py")
        grab = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(grab)
        png = pathlib.Path(tempfile.mkdtemp()) / "稿纸.png"
        grab.grab(a.student_html, png)
        insert_worksheet(prs, a.worksheet_after, png)
        order.insert(a.worksheet_after, 0)
        print(f"已在第 {a.worksheet_after} 页后插稿纸页")
    if a.drop_match:
        gone = drop_pages(prs, a.drop_match)
        for g in reversed(gone):
            del order[g - 1]
        print(f"删含「{a.drop_match}」的页：{gone or '无'}")
    if a.zh_cn:
        print(f"中文 run 改 zh-CN：{zh_cn(prs)} 个")

    for i, s in enumerate(prs.slides, 1):
        ids = [e.get("id") for e in s._element.iter() if e.tag.endswith("}cNvPr")]
        dup = [k for k, v in Counter(ids).items() if v > 1]
        if dup:
            raise SystemExit(f"第 {i} 页 shape id 重复 {dup}，未保存")
    prs.save(out)

    sheet = src.with_name(src.stem + "-anim.json")
    if sheet.exists() and (a.worksheet_after or a.drop_match) and out == src:
        doc = json.loads(sheet.read_text(encoding="utf-8"))
        old = doc["slides"]
        doc["slides"] = {str(i): (old[str(o)] if o else {"skip": True, "groups": [], "kicker": "自由写作", "title": "写作稿纸"})
                         for i, o in enumerate(order, 1)}
        doc["slide_count"] = len(order)
        sheet.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"已按新页序重排 {sheet.name}（记得重跑 audit_against_plan.py 与页标回注）")
    print(f"完成：{out}（{len(prs.slides)} 页）")


if __name__ == "__main__":
    main()
