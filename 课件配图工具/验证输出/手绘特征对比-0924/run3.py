import importlib.util, json, os, pathlib, concurrent.futures as cf
ROOT = pathlib.Path(r"E:/laojohn-lesson-plan"); OUT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gi", ROOT/".claude/skills/laojohn-writing-poster/scripts/gen_illustration.py")
gi = importlib.util.module_from_spec(spec); spec.loader.exec_module(gi); hs = gi._hs
pkg = pathlib.Path(os.environ["USERPROFILE"])/".claude/skills/handdraw-style-prompter"
new = {r["number"]: r for r in json.loads((ROOT/"课件配图工具/手绘风格库/styles.json").read_text(encoding="utf-8"))}
SUBJECT = ("一个十岁左右的小学生坐在教室窗边的课桌前读一本书，头和肩膀在画面中部，头顶离上缘约四分之一，"
           "桌上放着一盆小绿植和一支铅笔，书页没有字，身后不画天空，背景整片留空")
def ref(n):
    base = pkg/"images/individual"/("001-200" if int(n) <= 200 else "201-400")
    return str(next(p for p in (base/f"{n}_grid.webp", base/f"{n}.webp") if p.exists()))
client = gi.load_client("gpt-image")
def one(n):
    p = gi.build_prompt(SUBJECT, style={"traits": hs.positive_traits(new[n]["traits"]), "ref_path": ref(n)})
    try:
        client.save(client.generate(p, ratio="4:3", images=[ref(n)]), OUT/f"{n}-new3.jpg"); return f"{n} OK"
    except Exception as e: return f"{n} FAIL {str(e)[:160]}"
with cf.ThreadPoolExecutor(3) as ex:
    for r in ex.map(one, ["150", "036"]): print(r, flush=True)
