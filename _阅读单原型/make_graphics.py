# -*- coding: utf-8 -*-
"""格列佛游记 · 图形类阅读单原型（Tier B）。逐张参数化模板。
用法: PYTHONUTF8=1 python make_graphics.py [name]  (name 省略=全部)"""
import os, sys, json, base64, pathlib

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
    pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"
)
HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
LOGO = "data:image/png;base64," + base64.b64encode(
    pathlib.Path("e:/laojohn-lesson-plan/品牌资产/logo.png").read_bytes()
).decode()

def tpl(name): return (HERE / name).read_text(encoding="utf-8")

JOBS = []

# ================================================== 维恩图（慧骃 ↔ 野胡）
venn_common = {
    "logo": LOGO,
    "title": "《格列佛游记》卷四 · 慧骃 ↔ 野胡",
    "subtitle": "对比维度：理性 / 外形 / 与格列佛的关系",
    "left_label": "慧骃", "center_label": "共同", "right_label": "野胡",
}
JOBS.append({"file": "维恩图-空", "template": "template_venn.html",
             "w": 794, "h": 1123, "data": {**venn_common, "variant": "空白版",
             "left": ["", "", ""], "center": ["", ""], "right": ["", "", ""]}})
JOBS.append({"file": "维恩图-示范", "template": "template_venn.html",
             "w": 794, "h": 1123, "data": {**venn_common, "variant": "示范版（参考填法）",
             "left": ["高度理性，无欺诈无敌意", "形貌是马", "格列佛敬爱、模仿其步态腔调"],
             "center": ["同一国度的生物"],
             "right": ["没有理性，丑陋肮脏，向人抛粪", "形貌反而更像人", "格列佛极度厌恶"]}})

# ================================================== 阶梯图（态度四阶变化）
ladder_common = {
    "logo": LOGO,
    "title": "格列佛对「人类 / 自身同类」的态度 · 四阶变化",
    "subtitle": "每阶用书里的事实写一句话",
    "diagonal_note": "态度愈发疏离，离「人」愈来愈远 ↗",
    "footer": "从第一阶到第四阶，台阶逐级升高 —— 格列佛对「人 / 自己」的态度怎样一步步变化？",
}
LADDER_HD = ["第一阶 · 卷一·第二章", "第二阶 · 卷二·第六章",
             "第三阶 · 卷四·第十章", "第四阶 · 卷四·第十一章"]
JOBS.append({"file": "阶梯图-空", "template": "template_ladder.html",
             "w": 794, "h": 1123, "data": {**ladder_common, "variant": "空白版",
             "steps": [{"header": h, "items": ["", "", ""]} for h in LADDER_HD]}})
JOBS.append({"file": "阶梯图-示范", "template": "template_ladder.html",
             "w": 794, "h": 1123, "data": {**ladder_common, "variant": "示范版（参考填法）",
             "steps": [
                {"header": LADDER_HD[0], "items": ["放走被送到手中的小人犯人，被记作「宽宏大量」，对人仍持友善常态。"]},
                {"header": LADDER_HD[1], "items": ["在大人国仍满怀自豪地向国王颂扬英国，为同胞骄傲。"]},
                {"header": LADDER_HD[2], "items": ["照水中倒影觉得自己「丑不忍睹、还不如野胡」，开始模仿慧骃步态，不愿当人。"]},
                {"header": LADDER_HD[3], "items": ["回国后妻子拥抱即晕倒，一年受不了家人气味，每天与买来的两匹马长谈。"]},
             ]}})

# ================================================== 讽刺逻辑图（三层）
logic_common = {
    "logo": LOGO,
    "title": "《格列佛游记》· 讽刺逻辑图",
    "subtitle": "从下往上读：① 表层荒诞事 → ② 联想现实 → ③ 作者真正想批评什么",
    "footer": "这张三层图，读任何一部讽刺作品都用得上——先抓「荒诞事」，再问「在影射什么」，最后得出「作者到底想批评谁」。",
}
JOBS.append({"file": "讽刺逻辑图-空", "template": "template_logic.html",
             "w": 794, "h": 1123, "data": {**logic_common, "variant": "空白版 · 换你来：绳上跳舞当大官（卷一·第三章）",
             "layers": [
                {"label": "③ 内核：作者真正想批评什么", "text": ""},
                {"label": "② 中层：让你联想到现实里什么事", "text": ""},
                {"label": "① 表层：谁在细绳上跳得最高而不跌下来，谁就能当大官（卷一·第三章）",
                 "text": ""},
             ]}})
JOBS.append({"file": "讽刺逻辑图-示范", "template": "template_logic.html",
             "w": 794, "h": 1123, "data": {**logic_common, "variant": "示范版 · 吃鸡蛋打哪一头（卷一·第四章）",
             "layers": [
                {"label": "③ 内核", "text": "把鸡毛蒜皮的小分歧，当成你死我活的大事——讽刺那种「为芝麻小事就上纲上线、大动干戈」。"},
                {"label": "② 中层", "text": "像现实里因为一点立场 / 观念不同，就互相敌对、甚至兵戎相见的人。"},
                {"label": "① 表层", "text": "小人国为「鸡蛋从大头还是小头打开」分成两派，打了好几代仗（卷一·第四章）。"},
             ]}})

# ================================================== 四次远航导图（思维导图）
voyage_common = {
    "logo": LOGO, "title_main": "《格列佛游记》", "title_sub": "四次远航",
    "footer": "读完每一卷，把「去哪里 / 主要事件 / 怎么离开」填到对应横线上。",
}
VOY_HD = ["一 · 利立浦特 / 小人国（卷一）", "二 · 布罗卜丁奈格 / 大人国（卷二）",
          "三 · 勒皮他 / 飞岛诸国（卷三）", "四 · 慧骃国（卷四）"]
def blank_branch(h):
    return {"header": h, "fields": [
        {"label": "去到哪里", "lines": 1},
        {"label": "主要事件", "lines": 3},
        {"label": "怎么离开", "lines": 1}]}
JOBS.append({"file": "四次远航导图-空", "template": "template_voyage.html",
             "w": 794, "h": 1123, "data": {**voyage_common, "variant": "空白版",
             "branches": [blank_branch(h) for h in VOY_HD]}})
VOY_FILL = [
    {"go": "随「羚羊号」出海遇风暴触礁，泅水登陆利立浦特",
     "ev": ["拖走敌国五十艘战舰、被封「那达克」", "皇后寝宫失火，他以小便浇灭、惹皇后愤恨", "群臣联名弹劾，皇帝拟刺瞎其双眼、渐减口粮"],
     "out": "逃往布莱夫斯库，借一只小船离开，被英国船救起"},
    {"go": "第二次出海取水时被同伴遗弃，被农民捉住",
     "ev": ["小保姆格兰黛克利齐带他赶集巡回展览", "王后以千金买下、献给国王", "盛赞英国反被国王斥为「小害虫」，献火药遭拒"],
     "out": "装他的箱子被鹰叼走、落入海中，被英国船救起"},
    {"go": "第三次航海遭海盗劫掠、弃于荒岛，被飞岛勒皮他接入",
     "ev": ["勒皮他人沉迷天文数学、要仆人拍打才听人说话", "拉格多科学院荒诞研究（黄瓜里提取阳光等）", "见永生不死的「斯特鲁德布鲁格」，长生实为不幸"],
     "out": "经日本搭荷兰船返回英国"},
    {"go": "任「冒险号」船长遇水手叛乱，被囚后弃于无名陆地",
     "ev": ["先遇抛粪的「野胡」，再遇有理性的「慧骃」", "向灰马主人叙述英国，被判人类是「滥用理性的兽」", "代表大会劝令逐他，他听后悲痛昏倒"],
     "out": "在栗色小马帮助下造船出海，被葡萄牙船长彼得罗救起回英"},
]
JOBS.append({"file": "四次远航导图-示范", "template": "template_voyage.html",
             "w": 794, "h": 1123, "data": {**voyage_common, "variant": "示范版（参考填法）",
             "branches": [{"header": VOY_HD[i], "fields": [
                {"label": "去到哪里", "value": f["go"]},
                {"label": "主要事件", "value": f["ev"]},
                {"label": "怎么离开", "value": f["out"]}]} for i, f in enumerate(VOY_FILL)]}})


def safe_pdf(page, path, w, h):
    """写 PDF；若目标被占用（预览器锁文件），改写 .new.pdf 旁路，不中断。"""
    try:
        page.pdf(path=str(path), width=w, height=h, print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        return ""
    except Exception:
        alt = path.with_suffix(".new.pdf")
        page.pdf(path=str(alt), width=w, height=h, print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        return "(锁定→" + alt.name + ")"


def main():
    only = sys.argv[1] if len(sys.argv) > 1 else None
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for job in JOBS:
            if only and only not in job["file"]:
                continue
            html = tpl(job["template"]).replace(
                "/*__DATA__*/ null", json.dumps(job["data"], ensure_ascii=False))
            hp = OUT / (job["file"] + ".html")
            hp.write_text(html, encoding="utf-8")
            page = browser.new_page(viewport={"width": job["w"], "height": job["h"]},
                                    device_scale_factor=2)
            page.goto("file:///" + str(hp).replace("\\", "/"), wait_until="networkidle")
            page.wait_for_selector("body[data-rendered='1']", timeout=15000)
            ch = page.evaluate("() => document.getElementById('page').scrollHeight")
            ph = max(job["h"], ch + 16)
            tag = safe_pdf(page, OUT / (job["file"] + ".pdf"), f'{job["w"]}px', f'{ph}px')
            page.screenshot(path=str(OUT / (job["file"] + ".png")), full_page=True)
            page.close()
            print("OK:", job["file"], tag)
        browser.close()

if __name__ == "__main__":
    main()
