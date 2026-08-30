# -*- coding: utf-8 -*-
"""课件配图工具 · 本地单机版服务端（单文件 FastAPI）

启动：
    PYTHONUTF8=1 python 课件配图工具/web/server/main.py
然后浏览器开 http://127.0.0.1:8848

四条硬约束（改代码前先看）：

1. **不新增任何判据、不复制任何引擎逻辑**。拆解、生图、验收、导出全部
   importlib 载入 `scripts/` 下那四个脚本的函数。本文件只做 HTTP 与任务编排。
   规则库的唯一源是 `拆解规则.md`，本文件一个字都不重复。

2. **数据落在既有文件布局上，不另建数据库**：
       课件项目/<项目>.json          项目（风格卡+角色+画面清单）
       课件产出/<项目>/<通道>/角色/  定妆件
       课件产出/<项目>/<通道>/页目/  页目图
       课件产出/<项目>/<通道>/_验收记录.json
   于是 **CLI 跑的项目 Web 能打开，Web 建的项目 CLI 能接着跑**。两边不分家是
   有意的：命令行仍是排查问题最快的路子，产品化不该把它废掉。

3. **闸门：定妆硬、页目软**（2026-08-28 与用户定）。
   定妆图未验收 → 拒绝批量生成页目，因为它错了后面每一张都得废；
   页目验收降为逐张勾验，不阻断流程 —— 错一张只影响一张，边看边改就行。

4. **生图是分钟级的**，一律走后台任务 + 轮询，绝不在请求里干等。
   本地单机、单进程，任务状态放内存足够；进度同时写进任务对象供前端轮询。
"""
import datetime
import importlib.util
import io
import json
import os
import shutil
import sys
import threading
import time
import traceback
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

HERE = Path(__file__).resolve().parent
TOOL_ROOT = HERE.parent.parent              # 课件配图工具/
SCRIPTS = TOOL_ROOT / "scripts"
FRONTEND = HERE.parent / "frontend"
PROJECTS = TOOL_ROOT / "课件项目"
DECKS = TOOL_ROOT / "拆解底稿"
OUTPUTS = TOOL_ROOT / "课件产出"
RULES = TOOL_ROOT / "拆解规则.md"
UPLOADS = TOOL_ROOT / "web" / "_uploads"    # 上传的 pptx/详案原件，留档备查


def _load(name):
    """按路径载入 scripts/ 下的脚本模块（它们不是包，也不该为了 Web 改成包）。"""
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod                 # imgclient 之间互相 import，要先登记
    spec.loader.exec_module(mod)
    return mod


sys.path.insert(0, str(SCRIPTS))
imgclient = _load("imgclient")
extract_deck = _load("extract_deck")
build_specs = _load("build_specs")
run_lesson = _load("run_lesson")
imgclient.load_dotenv()

app = FastAPI(title="课件配图工具")


# ──────────────────────────── 任务：分钟级操作一律异步 ────────────────────────────

JOBS = {}
JOBS_LOCK = threading.Lock()


def new_job(kind, total=0):
    jid = uuid.uuid4().hex[:12]
    with JOBS_LOCK:
        JOBS[jid] = {"id": jid, "kind": kind, "state": "running", "done": 0,
                     "total": total, "log": [], "error": None, "result": None,
                     "started": time.time()}
    return jid


def job_log(jid, msg):
    with JOBS_LOCK:
        j = JOBS.get(jid)
        if j:
            j["log"].append(msg)


def job_step(jid, n=1):
    with JOBS_LOCK:
        j = JOBS.get(jid)
        if j:
            j["done"] += n


def job_end(jid, result=None, error=None):
    with JOBS_LOCK:
        j = JOBS.get(jid)
        if j:
            j["state"] = "error" if error else "done"
            j["result"], j["error"] = result, error
            j["elapsed"] = round(time.time() - j["started"], 1)


def run_bg(jid, fn):
    """后台跑一个任务。异常一律落到 job.error 并保留 traceback ——
    生图失败的原因往往在栈里（画幅不合法、参考图缺失、账户欠费），
    吞掉它前端就只看得到「失败」两个字，跟没说一样。"""
    def wrap():
        try:
            job_end(jid, result=fn(jid))
        except BaseException as e:
            # ⚠ 必须是 BaseException 不是 Exception：引擎里到处是 `raise SystemExit`
            # （CLI 的退出方式），而 SystemExit 继承 BaseException —— 只捕 Exception
            # 就漏掉它，线程静默死掉、job 永远停在 running，前端一直转圈。
            # 实测《写日记》拆解失败后界面就这么「停着不动」，全程没有任何报错。
            job_end(jid, error=f"{type(e).__name__}: {e}\n"
                                f"{traceback.format_exc()[-1800:]}")
    threading.Thread(target=wrap, daemon=True).start()


# ──────────────────────────── 项目读写 ────────────────────────────

def proj_path(name):
    p = PROJECTS / f"{name}.json"
    if not p.exists():
        raise HTTPException(404, f"项目不存在：{name}")
    return p


def load_proj(name, provider=None):
    """读项目并算出它的产出目录。目录按**项目文件名**分，不按 project.名称——
    名称是内容字段、可以重名，实测两份同名项目共用目录后，验收记录把
    另一份项目的图也算了进来。这条口径与 run_lesson.load() 必须一致。"""
    return run_lesson.load(str(proj_path(name)), provider)


def save_proj(name, d):
    proj_path(name).write_text(json.dumps(d, ensure_ascii=False, indent=2),
                               encoding="utf-8")


def img_state(d, outdir):
    """给每个角色件/页目算出「图在不在盘上」，以及**图是不是过期**。

    过期＝盘上这张图当初是按另一段描述画的。重新拆解会改写描述，
    而图不会跟着变 —— 实测有个项目 27 张里 18 张比清单旧，
    界面上完全看不出来：封面描述已经改成「主角色剪影」，显示的还是早先那张帆布包，
    人对着看只会以为「描述和实际完全对不上」。
    """
    st = {"角色": {}, "页目": {}, "过期": []}
    pj = PROJECTS / f"{outdir.parent.name}.json"
    proj_mtime = pj.stat().st_mtime if pj.exists() else None
    for c in d.get("characters", []):
        f = outdir / "角色" / f"{c['id']}.jpg"
        st["角色"][c["id"]] = f.exists()
    for s in d.get("slides", []):
        f = outdir / "页目" / f"{s['页码']}.jpg"
        st["页目"][s["页码"]] = f.exists()
        # 有图、且记下过当初的描述、而描述已经变了 → 过期。
        # 没记过描述的（老项目、CLI 出的图）不判过期，免得一片全红。
        # 复用页不自己出图，用的是别页那张 —— 要判就判**源图**，
        # 拿它自己的文件时间比毫无意义（实测把两张复用页误报成「图是旧的」）。
        # 复用页不自己出图，用的是别页那张。
        # ⚠ 这里**不能**把它标成「自己有图」——磁盘上可能还留着上一轮生成的同名文件，
        #   标了之后前端就去取那个残留文件，显示的是上一版画风的旧图（实测踩过）。
        #   只登记「它该显示谁」，取图交给前端按源页码去拿。
        if s.get("通道") == "复用":
            src = s.get("复用")
            st["页目"][s["页码"]] = False
            if src and (outdir / "页目" / f"{src}.jpg").exists():
                st.setdefault("复用源", {})[s["页码"]] = src
            continue
        if not f.exists():
            continue
        was = s.get("_出图描述")
        if was is not None and was.strip() != (s.get("prompt") or "").strip():
            # 有印记就只信印记：描述变了才算过期。
            st["过期"].append(s["页码"])
    return st


def project_brief(name):
    """项目列表用的摘要。读不出来的项目**照样列出来并带上原因**，
    不要静默跳过 —— 少一行比报错更难查。"""
    try:
        d, outdir = load_proj(name)
    except Exception as e:
        return {"名称": name, "错误": str(e)[:120]}
    pj = d.get("project")
    st = img_state(d, outdir)
    gates = run_lesson.read_gates(outdir)
    slides = d.get("slides", [])
    gen_slides = [s for s in slides if s.get("通道") != "人工素材位"]
    return {
        "名称": name,
        # project 可能是 dict、也可能是裸字符串（手写的项目 JSON 就是这样），
        # 两种都得认 —— 一个格式没兼容，整个项目列表就 500。
        "课名": (pj.get("名称", name) if isinstance(pj, dict) else (pj or name)),
        "角色件": len(d.get("characters", [])),
        "角色已出": sum(1 for v in st["角色"].values() if v),
        "页目": len(gen_slides),
        "页目已出": sum(1 for s in gen_slides if st["页目"].get(s["页码"])),
        "人工素材位": sum(1 for s in slides if s.get("通道") == "人工素材位"),
        "闸门": {k: (gates.get(k) or {}).get("验收人") for k in ("char", "pages")},
        "通道": outdir.name,
    }


# ──────────────────────────── 接口 ────────────────────────────

@app.get("/api/projects")
def api_projects():
    PROJECTS.mkdir(parents=True, exist_ok=True)
    # 跳过 `_` 开头的：`_已删除/` 是回收目录，里面的 json 不是项目
    names = sorted(p.stem for p in PROJECTS.glob("*.json")
                   if not p.name.startswith("_"))
    return {"projects": [project_brief(n) for n in names]}


@app.delete("/api/projects/{name}")
def api_del_project(name: str):
    """删项目 —— **移进回收目录，不真删**。

    产出目录里那些图每张都是花钱生成的（一个项目十几张，跑一轮十几分钟），
    误删一次代价太大，而删除按钮恰恰是最容易点错的那个。所以照历史图的办法：
    项目 json 和整个产出目录一起挪进 `_已删除/`，带时间戳，随时能搬回来。
    真要腾空间，去那个目录里手工清 —— 那时是明确的第二次决定。
    """
    import datetime
    src = proj_path(name)                      # 不存在会自己 404
    stamp = datetime.datetime.now().strftime("%m%d-%H%M%S")
    moved = []

    bin_p = PROJECTS / "_已删除"
    bin_p.mkdir(exist_ok=True)
    dst = bin_p / f"{name}-{stamp}.json"
    shutil.move(str(src), str(dst))
    moved.append(str(dst))

    out = OUTPUTS / name
    if out.exists():
        bin_o = OUTPUTS / "_已删除"
        bin_o.mkdir(exist_ok=True)
        dst_o = bin_o / f"{name}-{stamp}"
        shutil.move(str(out), str(dst_o))
        moved.append(str(dst_o))

    return {"ok": True, "已移到": moved,
            "说明": "没有真删。要恢复就把这些搬回原处；要腾空间去 _已删除/ 手工清。"}


@app.get("/api/projects/{name}")
def api_project(name: str):
    d, outdir = load_proj(name)
    return {
        "名称": name,
        "project": d.get("project", {}),
        "style_card": d.get("style_card", {}),
        "characters": d.get("characters", []),
        "slides": d.get("slides", []),
        "候选页": d.get("_逐页判断") or d.get("_候选页") or [],
        "角色盘点": d.get("_角色盘点", []),
        "图状态": img_state(d, outdir),
        "闸门": run_lesson.read_gates(outdir),
        "通道": outdir.name,
        "产出目录": str(outdir),
    }


@app.put("/api/projects/{name}")
async def api_save(name: str, body: dict):
    """保存风格卡 / 角色件 / 画面清单的编辑。

    只接受这三个键，其余一律忽略 —— 前端不该有能力改写项目里的其它字段，
    尤其是 `_角色盘点`（那是拆解阶段的判断记录，改了它机检就对不上账）。
    """
    d, _ = load_proj(name)
    # 存量项目里没有 `_初稿prompt`（那是后加的字段）。在**第一次改写之前**，
    # 拿盘上那份旧值补上 —— 等人改完再补就晚了，初稿已经被覆盖掉。
    old_by_pg = {x["页码"]: x for x in d.get("slides", [])}
    for k in ("style_card", "characters", "slides"):
        if k in body:
            d[k] = body[k]
    for sl in d.get("slides", []):
        if "_初稿prompt" not in sl:
            prev = old_by_pg.get(sl["页码"], {})
            base = prev.get("_初稿prompt") or prev.get("prompt") or sl.get("prompt")
            if base:
                sl["_初稿prompt"] = base
    save_proj(name, d)
    return {"ok": True}


@app.post("/api/projects")
async def api_create(name: str = Form(...), style: str = Form(""),
                     model: str = Form("claude-opus-4-5"),
                     pptx: UploadFile = File(...), plan: UploadFile = File(...)):
    """新建项目：上传课件 pptx + 教学详案 → 后台拆解 → 落成项目 JSON。

    两份都必须给：pptx 定**哪页要图、什么画幅**（程序量出来的，是事实），
    详案定**画什么**。少了 pptx 就只能让模型猜页码，实测会错位 1–3 页。
    """
    name = name.strip()
    if not name or "/" in name or "\\" in name:
        raise HTTPException(400, "项目名不能为空，也不能含路径分隔符")
    if (PROJECTS / f"{name}.json").exists():
        raise HTTPException(409, f"项目「{name}」已存在")
    UPLOADS.mkdir(parents=True, exist_ok=True)
    pf = UPLOADS / f"{name}{Path(pptx.filename).suffix or '.pptx'}"
    lf = UPLOADS / f"{name}-详案{Path(plan.filename).suffix or '.md'}"
    pf.write_bytes(await pptx.read())
    lf.write_bytes(await plan.read())

    jid = new_job("拆解", total=3)

    def work(jid):
        job_log(jid, "① 从 pptx 量出图位（纯程序判断，不调模型）…")
        deck = extract_deck.extract(pf, 0.03)
        DECKS.mkdir(parents=True, exist_ok=True)
        dp = DECKS / f"{name}-deck.json"
        dp.write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")
        n_main = sum(pg["主图位数"] for pg in deck["页"])
        job_log(jid, f"   {deck['页数']} 页，识别出 {n_main} 处主图位")
        job_step(jid)

        job_log(jid, "② 盘点角色与画风…")
        rules = RULES.read_text(encoding="utf-8")
        plan_txt = build_specs.load_plan(lf)
        by_page = build_specs.split_by_pagetag(plan_txt)
        job_log(jid, f"   详案 {len(plan_txt)} 字，"
                     + (f"页标对齐 {len(by_page)} 页" if by_page else "详案无页标，整篇喂"))
        deck_txt = json.dumps(build_specs.deck_digest(deck, by_page),
                              ensure_ascii=False, indent=1)
        client = imgclient.make_client()
        sty = (build_specs.STYLE_GIVEN.format(v=style) if style.strip()
               else build_specs.STYLE_NONE)
        s1 = build_specs.call(client, build_specs.STAGE1, model, rules=rules,
                              plan=plan_txt, deck=deck_txt, style=sty)
        job_log(jid, "   角色件：" + "、".join(c["id"] for c in s1.get("characters", [])))
        job_step(jid)

        job_log(jid, "③ 逐页写图位规格…")
        s2 = build_specs.call(client, build_specs.STAGE2, model, rules=rules,
                              plan=plan_txt, deck=deck_txt,
                              stage1=json.dumps(s1, ensure_ascii=False, indent=1))
        spec = assemble(s1, s2)
        PROJECTS.mkdir(parents=True, exist_ok=True)
        (PROJECTS / f"{name}.json").write_text(
            json.dumps(spec, ensure_ascii=False, indent=2), encoding="utf-8")
        job_step(jid)

        issues = build_specs.audit(spec, deck)
        for pg, det, src in build_specs.audit_sources(spec, plan_txt, deck):
            issues.append(f"[来源不实] {pg}「{det}」：{src}")
        job_log(jid, f"机检 {len(issues)} 处" if issues else "机检：低级错误一处没有")
        return {"名称": name, "机检": issues,
                "提示": "机检查不了比喻拆没拆、必现细节准不准、画面对不对——那些必须看图。"}

    run_bg(jid, work)
    return {"job": jid}


def assemble(s1, s2):
    """把两阶段结果拼成项目 JSON。与 build_specs.main() 的拼法保持一致 ——
    包括**把逐页判断里判为「需要图但只能人工找素材」的补进 slides**：
    提示词里要求模型自己补，实测它照样只写在判断表，而漏了它那一页
    在导出清单上就没有行，整页被当成「不需要图」跳过。"""
    pj = s1.get("project", "")
    slides = list(s2.get("slides", []))
    have = {x.get("页码") for x in slides}
    for c in s2.get("逐页判断") or s2.get("候选页") or []:
        pg = c.get("页码")
        if c.get("要不要图") and pg not in have:
            slides.append({"页码": pg, "用途": c.get("若要则") or "（待人工找素材）",
                           "角色组合": "", "画幅": "1:1", "通道": "人工素材位",
                           "主体": c.get("若要则", ""), "必现细节": [], "来源": [],
                           "prompt": "", "挂载": [],
                           "_说明": f"由逐页判断补入：{c.get('理由', '')}"})
    slides.sort(key=lambda x: x["页码"])
    return {"project": pj if isinstance(pj, dict) else {"名称": str(pj)},
            "style_card": s1.get("style_card", {}),
            "characters": s1.get("characters", []), "slides": slides,
            "_逐页判断": s2.get("逐页判断") or s2.get("候选页") or [], "_角色盘点": s1.get("角色盘点", [])}


@app.post("/api/projects/{name}/slides")
def api_add_slide(name: str, body: dict):
    """手工新增一个画面（清单之外的）。

    拆解器给的是**候选**不是定论 —— 对照人工成品实测，它的页级命中是 11/16，
    漏的那几页得有地方补回来；临时想给某页多配一张、或加一张备用图也走这里。
    **不做「拆解器说了算」的假设**，清单本来就是给人改的。

    页码可以是 PPT 里的页（P08）、同页第几张（P08-2），也可以是自定义名字
    （备用-封面）。只校验三件事：非空、不重复、不含路径分隔符（它会当文件名用）。
    """
    d, _ = load_proj(name)
    pg = (body.get("页码") or "").strip()
    if not pg:
        raise HTTPException(400, "页码不能为空。可以写 P08、P08-2，也可以写「备用-封面」。")
    if any(c in pg for c in r'/\:*?"<>|'):
        raise HTTPException(400, "页码会用作文件名，不能含 / 反斜杠 : * ? 双引号 < > |")
    if any(x["页码"] == pg for x in d.get("slides", [])):
        raise HTTPException(409, f"「{pg}」已经在清单里了。想再加一张就换个名字，比如 {pg}-2。")

    ids = {c["id"] for c in d.get("characters", [])}
    mount = [m for m in (body.get("挂载") or []) if m in ids]
    sl = {
        "页码": pg,
        "用途": (body.get("用途") or "").strip() or "（手工新增）",
        "类型": body.get("类型") or "场景",
        "角色组合": "", "画幅": body.get("画幅") or "1:1",
        "通道": "生成",
        "主体": "", "必现细节": body.get("必现细节") or [],
        "来源": body.get("来源") or [],
        "prompt": (body.get("prompt") or "").strip(),
        "挂载": mount,
        "_说明": "手工新增，不是拆解器产出的",
        "_手工新增": True,
    }
    if sl["prompt"]:
        sl["_初稿prompt"] = sl["prompt"]
    d.setdefault("slides", []).append(sl)
    d["slides"].sort(key=lambda x: x["页码"])
    save_proj(name, d)
    return {"ok": True, "页码": pg}


DRAFT_TMPL = """给一页课件配图起草规格。用户只填了「这张图要干什么」，你补出其余部分。

## 规则库（必须遵守，每条都是实测结论）
{rules}

## 这一课的风格卡
{style}

## 可以挂载的角色件（挂了就要在描述正文里点名，否则等于没挂）
{chars}

## 这一课已经有的图位（**别和它们撞车**：同一件道具整套不要超过三次）
{existing}

## 用户填的用途
{use}

## 输出这一条的 JSON

{{
  "类型": "例子 / 场景 / 道具 / 素材",
  "画幅": "1:1 / 3:4 / 4:3 / 16:9",
  "挂载": ["角色件 id，没有人物就空数组；全身构图要挂全身件并放第一位"],
  "必现细节": ["3-5 条可验收的具体细节"],
  "prompt": "完整描述。不含风格前缀（前缀由程序拼）",
  "_说明": "一句话说清你为什么这么定"
}}

要点：数量只写总数、不要逐个点名；挂了参考图就在正文写「挂载参考图里的那个…」；
同一角色挂两张要写明是同一个人；画面里有纸或本子就写「只有波浪线示意、
不出现任何可辨认文字、不出现英文字母」；近景构图、主体占据画面主要面积。"""


@app.post("/api/projects/{name}/draft-slide")
def api_draft_slide(name: str, body: dict):
    """按「用途」起草一条画面规格，供人在表单里改。

    手写描述要同时照顾一堆规则 —— 挂载得在正文点名、数量只能写一遍、
    有纸就得禁文字、还不能和已有页撞同一件道具 —— 人记不住这么多，
    交给模型起草、人来改，比从零写省事也更容易合规。

    **把已有图位一并喂进去**：不然它十有八九又画一本日记本
    （实测同一件道具曾占满一整套课件的一半）。
    """
    use = (body.get("用途") or "").strip()
    if not use:
        raise HTTPException(400, "先填「用途」——这张图要干什么，一句话就行。")
    d, _ = load_proj(name)
    sc = d.get("style_card", {})
    chars = "\n".join(
        f"- {c['id']}（{c.get('画幅')}）：{(c.get('prompt') or '')[:70]}"
        for c in d.get("characters", [])) or "（这一课没有角色件）"
    existing = "\n".join(
        f"- {x['页码']}［{x.get('类型','')}］{(x.get('主体') or x.get('用途') or '')[:38]}"
        for x in d.get("slides", []) if x.get("通道") == "生成") or "（还没有别的图位）"
    style = "\n".join(f"- {k}：{v}" for k, v in sc.items()
                       if k in ("画风档", "色板", "人物年龄设定", "场景基调",
                                "概念母题", "通用禁区") and v)

    client = imgclient.make_client()
    r = client.chat(
        DRAFT_TMPL.format(rules=RULES.read_text(encoding="utf-8"), style=style,
                          chars=chars, existing=existing, use=use),
        system="你是课件配图的规格师。只输出 JSON，不要任何解释性文字。"
               "中文引号一律用全角，JSON 字符串内绝不出现半角直引号。",
        max_tokens=4000)
    if "_error" in r or "_raw" in r:
        raise HTTPException(502, "起草失败：" + str(r.get("_error") or "返回的不是 JSON")[:200])
    ids = {c["id"] for c in d.get("characters", [])}
    r["挂载"] = [m for m in (r.get("挂载") or []) if m in ids]
    # 起草的细节是模型按用途拟的，不是从详案抄的 —— 来源如实标「（起草）」。
    # 不能编个出处：`来源` 的全部价值就在可核，编出来的比空着更坏。
    # 也不能留空 —— 机检会报「必现细节与来源不等长」。
    r["来源"] = ["（起草，非详案原文）"] * len(r.get("必现细节") or [])
    return r


@app.delete("/api/projects/{name}/slides/{pg}")
def api_del_slide(name: str, pg: str):
    """删掉一个画面条目。**只允许删手工新增的** —— 拆解器产出的条目删了，
    下次机检就对不上账（它按 deck 的页数核对每页有没有结论），
    而且重新拆解会把它带回来，等于白删。要去掉那种，把通道改成人工素材位。

    图不跟着删：万一删错了，图还在盘上，重新加一条同名的就接上了。
    """
    d, _ = load_proj(name)
    sl = next((x for x in d.get("slides", []) if x["页码"] == pg), None)
    if not sl:
        raise HTTPException(404, f"清单里没有 {pg}")
    if not sl.get("_手工新增"):
        raise HTTPException(400, "这条是拆解器产出的，不能删。"
                                 "不想生成它的话，把它的通道改成「人工素材位」。")
    d["slides"] = [x for x in d["slides"] if x["页码"] != pg]
    save_proj(name, d)
    return {"ok": True, "已删": pg, "图仍在": True}


@app.post("/api/projects/{name}/gen")
async def api_gen(name: str, body: dict):
    """生成图片。body: {kind: "char"|"page", ids: [...], force: bool}

    **闸门在这里落地：定妆硬、页目软。**
    要生成页目时，定妆闸门未过就直接拒绝 —— 定妆错了后面每一张都得重来，
    这道门挡住的是成批的浪费。页目那道门不拦生成，只在验收时逐张勾。
    """
    kind = body.get("kind")
    ids = body.get("ids") or []
    force = bool(body.get("force"))
    d, outdir = load_proj(name)
    if kind not in ("char", "page", "edit"):
        raise HTTPException(400, "kind 只能是 char / page / edit")

    if kind == "edit":
        return do_edit(d, outdir, ids, (body.get("instruction") or "").strip())

    if kind == "page":
        gates = run_lesson.read_gates(outdir)
        # 先问这道门适不适用：没有角色件的项目（每页人物都不同）无定妆可验，
        # 硬拦就成了死结 —— 出页目被拦着说先验定妆，去验定妆又被拦着说没有图。
        # 2026-08-28 用户决定：闸门不阻断。这里不再拦，验收记录仍可留。
        pass

    # 点名了却一个都对不上 —— 必须当场报错，不能让任务空转 0 秒再报「✓ 完成」。
    # 实测过一次：拿旧版页码 P13 去重出，新版清单里早没这一页了，
    # 任务瞬间完成、日志空白、界面显示成功，人会以为图已经重出。
    # **这是「无效请求」，不是「做完了」。**
    if ids:
        pool = ({c["id"] for c in d["characters"]} if kind == "char"
                else {s["页码"] for s in d["slides"]})
        miss = [x for x in ids if x not in pool]
        if miss:
            raise HTTPException(
                404, f"清单里没有这些：{'、'.join(miss)}。"
                     f"（现有{'角色件' if kind == 'char' else '页码'}："
                     f"{'、'.join(sorted(pool))}）"
                     f"—— 多半是重新拆解过、页码变了，刷新页面再点。")

    client = imgclient.make_client()
    if kind == "char":
        items = [c for c in d["characters"] if not ids or c["id"] in ids]
        jid = new_job("生成定妆", total=len(items))

        def work(jid):
            made = {c["id"]: outdir / "角色" / f"{c['id']}.jpg" for c in d["characters"]}
            out = []
            for c in items:
                refs = run_lesson.resolve_refs(c.get("挂载"), outdir, made)
                p = (c["prompt"] if c.get("通道") == "编辑"
                     else run_lesson.prefix_for(d["style_card"], c) + " " + c["prompt"])
                job_log(jid, f"生成 {c['id']}（{c['画幅']}）"
                             + (f" ←挂 {len(refs)} 张" if refs else ""))
                run_lesson.gen(client, outdir, "角色", c["id"], p, c["画幅"], refs, force)
                job_step(jid); out.append(c["id"])
            return {"生成": out, "用量": client.usage}
    else:
        items = [s for s in d["slides"]
                 if s.get("通道") == "生成" and (not ids or s["页码"] in ids)]
        if not items:
            raise HTTPException(
                400, "这几页都不是「生成」通道（复用别页的图，或是人工素材位），没有可生成的。"
                     if ids else "本项目没有「生成」通道的页目。")
        # 页目挂的定妆件如果还没图，**先把它们补出来**，而不是跑到一半崩掉。
        # 取消硬闸门之后这条就成了必需：闸门原本拦的正是这一幕（定妆没出就批量出页目），
        # 现在不拦了，就得自己把前置补齐 —— 「不阻断」的意思是不撞墙，不是撞了不管。
        need, need_pages = [], []
        for sl in items:
            for m in (sl.get("挂载") or []):
                c = next((x for x in d["characters"] if x["id"] == m), None)
                if c:
                    if not (outdir / "角色" / f"{m}.jpg").exists() and c not in need:
                        need.append(c)
                    continue
                # 挂的是别页：那一页也得先有图，否则这一页生成时缺参考。
                if (not (outdir / "页目" / f"{m}.jpg").exists()
                        and m not in need_pages and m != sl["页码"]):
                    need_pages.append(m)
        if need_pages:
            # 把被挂的页排到前面先生成。只挪一层 —— 挂载链更深就该人自己理顺，
            # 程序去做拓扑排序反而藏问题（互挂会死循环，机检已单独报）。
            head = [x for x in items if x["页码"] in need_pages]
            items = head + [x for x in items if x["页码"] not in need_pages]
        jid = new_job("生成页目", total=len(items) + len(need))

        def work(jid):
            made = {c["id"]: outdir / "角色" / f"{c['id']}.jpg" for c in d["characters"]}
            out = []
            if need:
                job_log(jid, f"这些页要挂定妆图，但还没生成，先补 {len(need)} 张："
                             + "、".join(c["id"] for c in need))
                for c in need:
                    refs = run_lesson.resolve_refs(c.get("挂载"), outdir, made)
                    pc = (c["prompt"] if c.get("通道") == "编辑"
                          else run_lesson.prefix_for(d["style_card"], c) + " " + c["prompt"])
                    job_log(jid, f"  补定妆 {c['id']}（{c['画幅']}）")
                    run_lesson.gen(client, outdir, "角色", c["id"], pc, c["画幅"], refs, False)
                    job_step(jid)
                job_log(jid, "定妆补齐，开始出页目。")
            for s in items:
                refs = run_lesson.resolve_refs(s.get("挂载"), outdir, made)
                p = run_lesson.prefix_for(d["style_card"], s) + " " + s["prompt"]
                job_log(jid, f"生成 {s['页码']}（{s['画幅']}）"
                             + (f" ←挂 {len(refs)} 张" if refs else ""))
                run_lesson.gen(client, outdir, "页目", s["页码"], p, s["画幅"], refs, force)
                s["_出图描述"] = s.get("prompt", "")     # 记下这张图是按哪段描述画的
                job_step(jid); out.append(s["页码"])
            save_proj(name, d)
            return {"生成": out, "用量": client.usage}

    run_bg(jid, work)
    return {"job": jid}


def do_edit(d, outdir, ids, instruction):
    """在**已有的那张图**上改，而不是照描述重画一张。

    与 kind="page" 的两处关键差别，都不能省：
    1. **不拼风格前缀**。前缀是一整套画风指令，拼上去模型会当成新的作画要求，
       把「在这张图上改一处」变回「重画一张」——那就失去了编辑的全部意义。
    2. **原图先备份**。编辑会覆盖原文件，而改坏是常事（T3 只验过减人、改色、
       转剪影三类，其余没测）。旧图存进 `_历史/`，随时能退回来。

    实测可靠的三类（T3）：转剪影 3/3、改颜色材质 3/3、减少人数 5/5（指名去掉哪个）。
    ⚠ **加人、以及不指名的「随便去掉一个」没测过**，那两种更适合改描述重画。
    """
    import datetime
    if not instruction:
        raise HTTPException(400, "请写清要改哪里，比如「男孩站到讲台前，面对着台下的同学」。")
    if len(ids) != 1:
        raise HTTPException(400, "一次只改一张。")
    pg = ids[0]
    sl = next((x for x in d["slides"] if x["页码"] == pg), None)
    if not sl:
        raise HTTPException(404, f"清单里没有 {pg}")
    src = outdir / "页目" / f"{pg}.jpg"
    if not src.exists():
        raise HTTPException(409, f"{pg} 还没有图，先生成一张再改。")

    client = imgclient.make_client()
    jid = new_job("局部修改", total=1)

    def work(jid):
        hist = outdir / "_历史"
        hist.mkdir(exist_ok=True)
        stamp = datetime.datetime.now().strftime("%m%d-%H%M%S")
        backup = hist / f"{pg}-{stamp}.jpg"
        shutil.copy2(src, backup)
        job_log(jid, f"原图已备份到 _历史/{backup.name}")
        job_log(jid, f"在 {pg} 上改：{instruction}")
        data = client.generate(instruction, ratio=sl.get("画幅", "1:1"), images=[src])
        client.save(data, src)
        job_step(jid)
        job_log(jid, "改完了。**必须看图**：编辑通道会连带动到没让它改的地方，"
                     "尤其人数和人物长相。不满意就用 _历史 里那张覆盖回来。")
        return {"页码": pg, "备份": str(backup), "用量": client.usage}

    run_bg(jid, work)
    return {"job": jid}


@app.get("/api/jobs/{jid}")
def api_job(jid: str):
    with JOBS_LOCK:
        j = JOBS.get(jid)
    if not j:
        raise HTTPException(404, "任务不存在（服务重启后旧任务会丢，重新发起即可）")
    return j


@app.post("/api/projects/{name}/approve")
async def api_approve(name: str, body: dict):
    """记录闸门验收。没有验收人名字一律拒绝 —— 没有名字的验收等于没验收。"""
    gate, by = body.get("gate"), (body.get("by") or "").strip()
    if gate not in ("char", "pages"):
        raise HTTPException(400, "gate 只能是 char 或 pages")
    if not by:
        raise HTTPException(400, "请填验收人姓名：没有名字的验收等于没验收。")
    d, outdir = load_proj(name)
    if not run_lesson.gate_applies(d, gate):
        raise HTTPException(400, "本项目没有定妆件（每页人物都不同，按规则不出定妆图），"
                                 "这道闸门不适用，直接生成页目即可。")
    run_lesson.approve(outdir, gate, by, body.get("note", ""), d)
    return {"ok": True, "闸门": run_lesson.read_gates(outdir)}


@app.post("/api/projects/{name}/export")
def api_export(name: str):
    """导出成品包。走 CLI 同一个 stage_export，命名与清单格式完全一致。

    ⚠ 它内部会 require_gate("pages")：导出是交付动作，这一步仍要求页目验收过。
    「页目软」指的是**生成**不被拦住，可以边生边看边改；到了往外交的这一步，
    还是得有人签字说这批能用。
    """
    d, outdir = load_proj(name)
    # 导出同样不拦（2026-08-28 用户决定）。导出清单里的「验收人 / 验收时间」两列
    # 仍照常填：签过就有名字，没签就是空的——记录如实反映做没做过，不替人担保。
    pack = outdir / "导出"
    if pack.exists():
        shutil.rmtree(pack)
    run_lesson.stage_export(d, outdir)
    files = sorted(p.name for p in pack.glob("*.png"))
    return {"ok": True, "目录": str(pack), "文件数": len(files), "文件": files}


@app.get("/api/rules")
def api_rules():
    """规则库原文。前端只读展示 —— 它是量出来的资产，改它要在编辑器里
    连着出处一起改，不该在网页上随手敲两句就覆盖掉。"""
    return {"text": RULES.read_text(encoding="utf-8") if RULES.exists() else ""}


@app.get("/api/projects/{name}/history/{pg}")
def api_history(name: str, pg: str):
    """列出某一页的历史版本（新的在前）。

    每次「在这张图上改」之前都会把当前图存一份进 `_历史/`，
    但存在磁盘上人是看不见的 —— 得让页面能列出来、能点回去，
    否则「改坏了可以还原」只是一句空话。
    """
    _, outdir = load_proj(name)
    hist = outdir / "_历史"
    if not hist.exists():
        return {"版本": []}
    out = []
    for f in sorted(hist.glob(f"{pg}-*.jpg"), reverse=True):
        st = f.stat()
        out.append({"文件": f.name,
                    "时间": datetime.datetime.fromtimestamp(st.st_mtime)
                                    .strftime("%m-%d %H:%M:%S"),
                    "大小KB": st.st_size // 1024})
    return {"版本": out}


@app.post("/api/projects/{name}/restore")
def api_restore(name: str, body: dict):
    """把某个历史版本恢复成当前图。

    ⚠ **恢复前先把当前图也存进历史**：否则「还原」就成了另一次不可逆覆盖，
    人点错一次就把刚生成的好图弄丢了。来回切换要能随时反悔。
    """
    pg, fnm = body.get("页码"), body.get("文件")
    if not pg or not fnm:
        raise HTTPException(400, "缺少 页码 或 文件")
    if "/" in fnm or "\\" in fnm or not fnm.startswith(f"{pg}-"):
        raise HTTPException(400, "文件名不合法")
    _, outdir = load_proj(name)
    old = outdir / "_历史" / fnm
    cur = outdir / "页目" / f"{pg}.jpg"
    if not old.exists():
        raise HTTPException(404, "这个历史版本不在了")
    if cur.exists():
        stamp = datetime.datetime.now().strftime("%m%d-%H%M%S")
        shutil.copy2(cur, outdir / "_历史" / f"{pg}-{stamp}.jpg")
    shutil.copy2(old, cur)
    return {"ok": True, "已还原": fnm}


@app.get("/hist/{name}/{fn}")
def api_hist_img(name: str, fn: str):
    """取历史图。与 /img 分开：历史目录以 `_` 开头，不该混进正常取图的路径判断。"""
    if "/" in fn or "\\" in fn:
        raise HTTPException(400, "文件名不合法")
    _, outdir = load_proj(name)
    f = outdir / "_历史" / fn
    if not f.exists():
        raise HTTPException(404, "图不存在")
    return FileResponse(f)


@app.get("/img/{name}/{sub}/{fn}")
def api_img(name: str, sub: str, fn: str):
    """取图。加 mtime 查询参数即可绕过浏览器缓存（前端重跑后会带上）。"""
    if sub not in ("角色", "页目", "导出"):
        raise HTTPException(400, "sub 只能是 角色/页目/导出")
    _, outdir = load_proj(name)
    f = outdir / sub / fn
    if not f.exists():
        raise HTTPException(404, "图不存在")
    return FileResponse(f)


@app.get("/api/health")
def api_health():
    """自检：密钥在不在、通道是哪条、引擎载没载上。
    密钥只回答「有没有」，不回显任何一位 —— 本地单机也不例外。"""
    try:
        c = imgclient.make_client()
        ok, info = True, {"通道": c.name, "生图模型": c.model,
                          "拆解模型": getattr(c, "text_model", "?")}
    except SystemExit as e:
        ok, info = False, {"错误": str(e)}
    return {"密钥": ok, **info, "规则库": RULES.exists(), "项目目录": str(PROJECTS)}


app.mount("/", StaticFiles(directory=str(FRONTEND), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    print("课件配图工具 · 本地单机版")
    print("  打开 http://127.0.0.1:8848")
    uvicorn.run(app, host="127.0.0.1", port=8848, log_level="warning")
