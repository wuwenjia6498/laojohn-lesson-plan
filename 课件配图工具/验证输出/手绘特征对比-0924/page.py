# 生成「参考图｜旧特征｜新特征」三栏对比页（图缩到 640 宽内嵌，单文件可直接打开）
import base64, io, json, os, pathlib, subprocess
from PIL import Image
OUT = pathlib.Path(__file__).resolve().parent; ROOT = pathlib.Path(r"E:/laojohn-lesson-plan")
pkg = pathlib.Path(os.environ["USERPROFILE"])/".claude/skills/handdraw-style-prompter"
new = {r["number"]: r for r in json.loads(subprocess.run(["git","-C",str(ROOT),"show","8b3d45f:课件配图工具/手绘风格库/styles.json"],capture_output=True).stdout.decode("utf-8"))}
cur = {r["number"]: r for r in json.loads((ROOT/"课件配图工具/手绘风格库/styles.json").read_text(encoding="utf-8"))}
old = {r["number"]: r for r in json.loads(subprocess.run(["git","-C",str(ROOT),"show","HEAD:课件配图工具/手绘风格库/styles.json"],capture_output=True).stdout.decode("utf-8"))}
fit = {n: v["写作课招生"] for n, v in json.loads((ROOT/"课件配图工具/手绘风格库/style_tags.json").read_text(encoding="utf-8")).items()}
def b64(p, w=640):
    if not pathlib.Path(p).exists(): return ""
    im = Image.open(p).convert("RGB"); im.thumbnail((w, w)); buf = io.BytesIO(); im.save(buf, "JPEG", quality=82)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
def ref(n):
    base = pkg/"images/individual"/("001-200" if int(n) <= 200 else "201-400")
    return next(p for p in (base/f"{n}_grid.webp", base/f"{n}.webp") if p.exists())
rows = []
for n in ["001","036","061","084","150","185","201","222","274"]:
    cells = [(f"参考图", b64(ref(n)), ""), ("旧特征出图", b64(OUT/f"{n}-old.jpg"), old[n]["traits"] or "（原库为空，只靠参考图）"),
             ("新特征出图", b64(OUT/f"{n}-new.jpg"), new[n]["traits"])]
    if (OUT/f"{n}-new2.jpg").exists():
        cells.append(("修正后出图（睁眼／补喜剧感）", b64(OUT/f"{n}-new2.jpg"), cur[n]["traits"]))
    tds = "".join(f'<figure><figcaption>{t}</figcaption>' + (f'<img src="{s}">' if s else '<div class="miss">未生成</div>') +
                  (f'<p>{txt}</p>' if txt else '') + '</figure>' for t, s, txt in cells)
    rows.append(f'<section><h2>#{n} · {new[n]["generation_name"]} <span>{fit[n]["档"]}｜{fit[n]["理由"]}</span></h2><div class="row" style="grid-template-columns:repeat({len(cells)},1fr)">{tds}</div></section>')
html = f"""<!doctype html><meta charset="utf-8"><title>手绘特征新旧对比</title>
<style>body{{font:14px/1.6 "Microsoft YaHei",sans-serif;background:#f6f3ec;color:#2b2620;margin:24px}}
h1{{font-size:20px}}h2{{font-size:16px;margin:28px 0 8px}}h2 span{{font-weight:400;color:#7a6f60;font-size:13px}}
.row{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}}figure{{margin:0;background:#fff;padding:10px;border-radius:8px}}
figcaption{{font-weight:600;margin-bottom:6px}}img{{width:100%;border-radius:4px}}p{{font-size:12px;color:#5a5044;margin:8px 0 0}}
.miss{{height:200px;display:grid;place-items:center;color:#b0a595;border:1px dashed #d8cfbf}}</style>
<h1>手绘风格特征 · 新旧对比（同一画面、同一参考图，gpt-image）</h1>
<p>画面统一为：十岁左右的小学生在教室窗边读书，桌上一盆绿植。看新特征那一栏是不是比旧特征更贴左边的参考图。150、036、001 三行多一栏「修正后」：按用户看图意见改了表情（睁眼）与 001 的喜剧感、发型后重出。</p>
{''.join(rows)}"""
(OUT/"对比.html").write_text(html, encoding="utf-8"); print(OUT/"对比.html")
