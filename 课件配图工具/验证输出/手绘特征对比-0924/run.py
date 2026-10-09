# 18 张对比：同一画面、同一参考图，旧特征（git HEAD）vs 新特征（工作区），gpt-image
import importlib.util, json, os, pathlib, subprocess, concurrent.futures as cf
ROOT = pathlib.Path(r"E:/laojohn-lesson-plan"); OUT = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("gi", ROOT/".claude/skills/laojohn-writing-poster/scripts/gen_illustration.py")
gi = importlib.util.module_from_spec(spec); spec.loader.exec_module(gi); hs = gi._hs
pkg = pathlib.Path(os.environ["USERPROFILE"])/".claude/skills/handdraw-style-prompter"
oldtxt = subprocess.run(["git", "-C", str(ROOT), "show", "HEAD:课件配图工具/手绘风格库/styles.json"], capture_output=True).stdout.decode("utf-8")
old = {r["number"]: r for r in json.loads(oldtxt)}
new = {r["number"]: r for r in json.loads((ROOT/"课件配图工具/手绘风格库/styles.json").read_text(encoding="utf-8"))}
SUBJECT = ("一个十岁左右的小学生坐在教室窗边的课桌前读一本书，头和肩膀在画面中部，头顶离上缘约四分之一，"
           "桌上放着一盆小绿植和一支铅笔，书页没有字，身后不画天空，背景整片留空")
NUMS = ["001","036","061","084","150","185","201","222","274"]
def ref(n):
    base = pkg/"images/individual"/("001-200" if int(n) <= 200 else "201-400")
    return str(next(p for p in (base/f"{n}_grid.webp", base/f"{n}.webp") if p.exists()))
jobs = [(n, tag, gi.build_prompt(SUBJECT, style={"traits": hs.positive_traits(lib[n]["traits"]), "ref_path": ref(n)}))
        for n in NUMS for tag, lib in (("old", old), ("new", new))]
(OUT/"prompts.json").write_text(json.dumps([{"n": n, "tag": t, "prompt": p} for n, t, p in jobs], ensure_ascii=False, indent=1), encoding="utf-8")
client = gi.load_client("gpt-image")
def one(j):
    n, tag, p = j; dest = OUT/f"{n}-{tag}.jpg"
    if dest.exists(): return f"{n}-{tag} 已有"
    try:
        client.save(client.generate(p, ratio="4:3", images=[ref(n)]), dest); return f"{n}-{tag} OK"
    except Exception as e:
        return f"{n}-{tag} FAIL {str(e)[:160]}"
with cf.ThreadPoolExecutor(4) as ex:
    for r in ex.map(one, jobs): print(r, flush=True)
print("用量", client.usage)
