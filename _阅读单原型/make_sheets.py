# -*- coding: utf-8 -*-
"""格列佛游记 · 表格类阅读单原型生成器（Tier A）。
用法: PYTHONUTF8=1 python make_sheets.py
依赖: playwright (chromium 已装于 ms-playwright)。"""
import os, json, base64, pathlib

os.environ["PLAYWRIGHT_BROWSERS_PATH"] = str(
    pathlib.Path.home() / "AppData" / "Local" / "ms-playwright"
)

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
TPL = (HERE / "template_table.html").read_text(encoding="utf-8")
LOGO = "data:image/png;base64," + base64.b64encode(
    (pathlib.Path("e:/laojohn-lesson-plan/品牌资产/logo.png")).read_bytes()
).decode()

# ---------------------------------------------------------------- 数据定义
SHEETS = []

# 1. 预测阅读单（导读课）
PRED_COLS = [
    {"name": "我读完前 3 章后，我猜……\n（人物 / 情节 / 结局任选）", "width": 38},
    {"name": "我的依据是……", "width": 32},
    {"name": "读完整本书后回看，我猜对了吗？", "width": 30},
]
SHEETS.append({
    "file": "预测阅读单-空",
    "variant": "空白版",
    "title": "《格列佛游记》阅读单 · 预测阅读单",
    "subtitle": "读完前 3 章，先猜一猜——重点不是猜得准，而是写清你凭哪句话猜的",
    "logo": LOGO, "columns": PRED_COLS, "row_min_h": 160,
    "rows": [["", "", ""], ["", "", ""], ["", "", ""]],
    "note": "写两到三条都可以。两周后读完全书，我们回头一起看今天的预测——验过的预测，才算真的用过这个策略。",
})
SHEETS.append({
    "file": "预测阅读单-示范",
    "variant": "示范版（示意一行，仅供参考）",
    "title": "《格列佛游记》阅读单 · 预测阅读单",
    "subtitle": "读完前 3 章，先猜一猜——重点不是猜得准，而是写清你凭哪句话猜的",
    "logo": LOGO, "columns": PRED_COLS, "row_min_h": 116,
    "rows": [
        ["我猜格列佛最后不会安心留在英国，会更喜欢和动物待在一起。",
         "前三章里他一到小人国就被当成怪物清点、捆绑，对人很失望。",
         "（待读完全书再回看填写）"],
        ["", "", ""], ["", "", ""],
    ],
    "note": "示范只示意「依据要写得具体」——把你猜测背后的那句话写出来。你自己的预测不必和示范一样。",
})

# 2. 阅读计划表（导读课）—— 单一成稿版（派发用）
SHEETS.append({
    "file": "阅读计划表",
    "variant": "派发版",
    "title": "《格列佛游记》7 天阅读计划",
    "subtitle": "全书四卷三十九章、约二十三万字。按卷读，一卷一气读完，每读完一卷停一停想一想。",
    "logo": LOGO, "label_first_col": True, "row_min_h": 58,
    "columns": [
        {"name": "7 天阅读计划", "width": 16},
        {"name": "任务", "width": 50},
        {"name": "圈画提示", "width": 34},
    ],
    "rows": [
        ["第 1 天", "卷一·第一至四章（小人国前半）", "圈出「小人国奇怪的制度」3 处以上"],
        ["第 2 天", "卷一·第五至八章（小人国后半至离开）", "圈出格列佛「立大功」和「获罪」的事件"],
        ["第 3 天", "卷二·第一至四章（大人国前半）", "圈出「格列佛变小、被当成珍玩」的细节"],
        ["第 4 天", "卷二·第五至八章（大人国后半至离开）", "圈出大人国国王对英国的两次评价"],
        ["第 5 天", "卷三 全卷（飞岛诸国）", "圈出 3 条「荒诞的研究」"],
        ["第 6 天", "卷四·第一至六章（慧骃国前半）", "圈出「野胡」与「慧骃」各自的特点"],
        ["第 7 天", "卷四·第七至十二章（慧骃国后半至回国）", "圈出格列佛回到英国后的反应"],
    ],
    "note": "这一周的阅读，是接下来三节课讨论的全部地基。读得仔细，下周你就有的说、能说得深。",
})

# 3. 对比表（交流课1）
CMP_COLS = [
    {"name": "对比维度", "width": 34},
    {"name": "第一卷 · 小人国（利立浦特）", "width": 33},
    {"name": "第二卷 · 大人国（布罗卜丁奈格）", "width": 33},
]
SHEETS.append({
    "file": "对比表-空",
    "variant": "空白版",
    "title": "《格列佛游记》阅读单 · 小人国 ↔ 大人国 对比表",
    "subtitle": "分组用 10 分钟填写：同一个格列佛，换了体型，「看世界的位置」也变了",
    "logo": LOGO, "label_first_col": True, "row_min_h": 150,
    "columns": CMP_COLS,
    "rows": [
        ["体型比例\n（格列佛 ∶ 当地人）", "", ""],
        ["格列佛的视角位置\n（俯视 / 平视 / 仰视）", "", ""],
    ],
    "note": "填完想一想：作者为什么要把「小人国」和「大人国」放在一起写？只写其中一个不行吗？",
})
SHEETS.append({
    "file": "对比表-示范",
    "variant": "示范版（参考填法）",
    "title": "《格列佛游记》阅读单 · 小人国 ↔ 大人国 对比表",
    "subtitle": "分组用 10 分钟填写：同一个格列佛，换了体型，「看世界的位置」也变了",
    "logo": LOGO, "label_first_col": True, "row_min_h": 96,
    "columns": CMP_COLS,
    "rows": [
        ["体型比例\n（格列佛 ∶ 当地人）",
         "12 ∶ 1（他是巨人，当地人不足六英寸）",
         "1 ∶ 12（他成了大人国人眼里「约六英寸的小不点」——和小人国人一样大）"],
        ["格列佛的视角位置\n（俯视 / 平视 / 仰视）",
         "居高临下俯视", "处处仰视、随时可能被踩到"],
    ],
    "note": "参考填法，鼓励多元表达——能从「反差」里读出作者要让我们看见的东西即可。",
})

# 4. 找重复表（交流课2）
REP_COLS = [
    {"name": "重复出现的事物", "width": 22},
    {"name": "卷一表现", "width": 26},
    {"name": "卷二表现", "width": 26},
    {"name": "卷四表现", "width": 26},
]
SHEETS.append({
    "file": "找重复表-空",
    "variant": "空白版",
    "title": "《格列佛游记》阅读单 · 找重复",
    "subtitle": "作者反复让什么出现？把三处「重复」在各卷的表现找出来",
    "logo": LOGO, "label_first_col": True, "row_min_h": 150,
    "columns": REP_COLS,
    "rows": [
        ["格列佛被「当成奇物观察」", "", "", ""],
        ["航海挫折开篇", "", "", ""],
        ["与「小便」有关的桥段", "", "", ""],
    ],
    "note": "填完推一推：作者为什么要让这些一卷又一卷地出现？——不凭印象猜，要指出文本里的那条线索。",
})
SHEETS.append({
    "file": "找重复表-示范",
    "variant": "示范版（参考填法）",
    "title": "《格列佛游记》阅读单 · 找重复",
    "subtitle": "作者反复让什么出现？把三处「重复」在各卷的表现找出来",
    "logo": LOGO, "label_first_col": True, "row_min_h": 100,
    "columns": REP_COLS,
    "rows": [
        ["格列佛被「当成奇物观察」",
         "小人官员逐件清点其口袋物品（手枪、表、梳子等）",
         "作为「怪兽」被农民展览、被王后和大学者检视",
         "慧骃用前蹄翻看他的帽子、衣服、手"],
        ["航海挫折开篇", "触礁", "被同伴遗弃", "被叛变水手弃岸"],
        ["与「小便」有关的桥段",
         "卷一第二章撒尿放松、卷一第五章以小便灭火（成为弹劾第一条罪状）",
         "——", "——"],
    ],
    "note": "合起来推：作者反复用这些，是把「我们以为很正常的英国人」放到另一个视角里被反看。",
})

# 5. 两难思辨阅读单（思辨课）
DEB_COLS = [
    {"name": "思辨问题", "width": 30},
    {"name": "书中相关片段（卷·章）", "width": 22},
    {"name": "我的判断", "width": 14},
    {"name": "我的理由", "width": 34},
]
DEB_QS = [
    "人类是「滥用理性、比野胡更可鄙的动物」吗？",
    "把「理性」放在马身上、「兽性」放在像人的野胡身上，作者公平吗？",
    "回到家、对自己妻子气味都受不了的格列佛，他自己是不是变得不像人了？",
]
SHEETS.append({
    "file": "两难思辨单-空",
    "variant": "空白版",
    "title": "《格列佛游记》阅读单 · 两难思辨",
    "subtitle": "三道题只挑一道答深——挑中的那道，三栏（片段 / 判断 / 理由）必须填满",
    "logo": LOGO, "label_first_col": True, "row_min_h": 184,
    "columns": DEB_COLS,
    "rows": [[q, "", "", ""] for q in DEB_QS],
    "note": "站得住的回答：① 引书里具体一段；② 判断明确（认同 / 部分认同 / 不认同，不骑墙）；③ 理由扣着证据说。",
})
SHEETS.append({
    "file": "两难思辨单-示范",
    "variant": "示范版（示意第 1 题答深一道）",
    "title": "《格列佛游记》阅读单 · 两难思辨",
    "subtitle": "三道题只挑一道答深——挑中的那道，三栏（片段 / 判断 / 理由）必须填满",
    "logo": LOGO, "label_first_col": True, "row_min_h": 134,
    "columns": DEB_COLS,
    "rows": [
        [DEB_QS[0],
         "卷一·第四章（鸡蛋之争）、卷二·第七章（献火药）、卷四·第五至七章（慧骃主人的判断）",
         "部分认同",
         "作者举出的「人类用理性做的事」，确实多是战争、欺诈、虚荣；但书里也有大人国国王、葡萄牙船长这样有理性的好人，作者只取了人最糟的一面。"],
        [DEB_QS[1], "", "", ""],
        [DEB_QS[2], "", "", ""],
    ],
    "note": "示范只答深一道（其余两道空着），示意「片段要定位到卷·章、判断不骑墙、理由扣证据」。",
})

# ---------------------------------------------------------------- 渲染
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
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 794, "height": 1123},
                                device_scale_factor=2)
        for s in SHEETS:
            payload = json.dumps(s, ensure_ascii=False)
            html = TPL.replace("/*__DATA__*/ null", payload)
            html_path = OUT / (s["file"] + ".html")
            html_path.write_text(html, encoding="utf-8")
            page.goto("file:///" + str(html_path).replace("\\", "/"),
                      wait_until="networkidle")
            page.wait_for_selector("body[data-rendered='1']", timeout=15000)
            ch = page.evaluate("() => document.getElementById('page').scrollHeight")
            ph = max(1123, ch) + 24
            tag = safe_pdf(page, OUT / (s["file"] + ".pdf"), "794px", f"{ph}px")
            page.set_viewport_size({"width": 794, "height": ph})
            page.screenshot(path=str(OUT / (s["file"] + ".png")), full_page=True)
            print("OK:", s["file"], tag)
        browser.close()

if __name__ == "__main__":
    main()
