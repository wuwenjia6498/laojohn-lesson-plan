"""writing_deck_kit.py - 写作课仓内直出：按母版 framework.md 写 dc.html 的版式积木（2026-09-26，六上五试点沉淀）。

每课一份构建脚本（放 `写作课件中间稿输出/<课次>/<课次>-课件构建.py`，入库），逐页调用本模块拼页面：

    import importlib.util, pathlib
    _k = pathlib.Path(__file__).resolve().parents[2] / ".claude/skills/laojohn-ppt/tools/writing_deck_kit.py"
    _s = importlib.util.spec_from_file_location("kit", _k); kit = importlib.util.module_from_spec(_s); _s.loader.exec_module(kit)
    from kit import *            # 或 kit.page(...) 逐个调用
    configure("六上-第五单元-围绕中心意思写", theme="#FDEBD9")
    S = [cover(...), section_page(...), page(...), ..., worksheet_page(25), end_page(...)]
    write(S)

页序：详案有〖PPT第N页〗照页标；新详案没有页标时按 laojohn-ppt-draft/references/writing-mode.md 的写作课节拍自行切页，出件后回注页标。
规则（配色、骨架、配图、动画、稿纸页、讲评不进 PPT……）的唯一源是 framework.md 的正文与「本仓增补」各节；
本模块只把其中固定的像素值收成函数，改规则先改 framework.md 再改这里。
文字里写「」，write() 统一换成中文弯引号。点击分组用各函数的 a／a0／fa 参数（写成 data-anim）。
"""
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[4]

F = "font-family:'Microsoft YaHei','微软雅黑',sans-serif;"
RED, NAVY, GREEN_ARROW = "#C0392B", "#3D4A63", "#7FA33C"
# 示范文标色 × 旁批表分类色（须一一对应）
C_CENTER, C_DETAIL, C_BRIEF, C_CLOSE = "#8E5AA8", "#C0392B", "#2F72B8", "#4E9A57"
# 底带三色（v8 定稿，页与页交替）：暖黄／浅绿／浅桃
BY, BG, BP = "#FFF6E5", "#EEF5E6", "#FDEFE6"
THEMES = {"粉": "#FCE7EA", "浅绿": "#E6F2E1", "浅蓝灰": "#E3E9F2", "浅桃": "#FDEBD9", "浅黄": "#FFF3D6"}

# configure() 填
UNIT = OUT = None
IMG = LOGO = HAND = MASCOT = ""
THEME = THEMES["粉"]


def configure(unit, theme="#FCE7EA", img_dir=None):
    """unit＝课次标识（如 六上-第五单元-围绕中心意思写）。theme＝标题胶囊主题色（THEMES 五选一，全课统一）。
    img_dir＝放图目录（相对项目根），缺省 课件配图工具/课件产出/<课次>/gpt-image/ppt配图缓存/直出/，
    该目录下约定：吉祥物.png、稿纸.png（grab_worksheet 现截）、各页人物图。"""
    global UNIT, OUT, IMG, LOGO, HAND, MASCOT, THEME
    UNIT = unit
    OUT = ROOT / "写作课件中间稿输出" / unit / f"{unit}-课件.dc.html"
    img_dir = img_dir or f"课件配图工具/课件产出/{unit}/gpt-image/ppt配图缓存/直出/"
    IMG = "../../" + img_dir.rstrip("/") + "/"
    LOGO = "../../品牌资产/logo.png"
    HAND = "../../品牌资产/图标/手指点击.png"
    MASCOT = IMG + "吉祥物.png"
    THEME = THEMES.get(theme, theme)


def A(n):
    return f' data-anim="{n}"' if n is not None else ""


def R(t, c=RED):
    return f'<span style="color:{c};font-weight:700;">{t}</span>'


def fig(name, h, right=None, left=None, bottom=0, top=None):
    pos = f"right:{right}px;" if right is not None else f"left:{left}px;"
    pos += f"top:{top}px;" if top is not None else f"bottom:{bottom}px;"
    return f'<img src="{IMG}{name}" style="position:absolute;{pos}height:{h}px;width:auto;">'


def band(top, bottom=0, color=BY, left=0, right=0):
    return f'<div style="position:absolute;left:{left}px;right:{right}px;top:{top}px;bottom:{bottom}px;background:{color};"></div>'


def footer(t, right=110, a=None):
    return (f'<div{A(a)} style="position:absolute;bottom:52px;left:110px;right:{right}px;display:flex;gap:14px;align-items:flex-start;">'
            f'<img src="{HAND}" style="height:52px;width:auto;flex:none;margin-top:-2px;">'
            f'<div style="font-size:34.7px;line-height:1.4;color:{NAVY};">{t}</div></div>')


def num(n, size=53, fs=28):
    return (f'<div style="width:{size}px;height:{size}px;flex:none;background:{NAVY};color:#fff;font-size:{fs}px;'
            f'font-weight:700;border-radius:14px;display:flex;align-items:center;justify-content:center;"><div>{n}</div></div>')


def steps(items, top, left=110, width=1040, fs=34, gap=34, a0=None):
    rows = "".join(
        f'<div{A(None if a0 is None else a0 + i)} style="display:flex;gap:26px;align-items:flex-start;">{num(i + 1)}'
        f'<div style="font-size:{fs}px;font-weight:700;line-height:1.5;padding-top:2px;">{t}</div></div>'
        for i, t in enumerate(items))
    return (f'<div style="position:absolute;top:{top}px;left:{left}px;width:{width}px;display:flex;'
            f'flex-direction:column;gap:{gap}px;">{rows}</div>')


def bullets(items, top, left=110, width=1040, fs=34, gap=24, bold=True, a0=None):
    w = "font-weight:700;" if bold else ""
    rows = "".join(
        f'<div{A(None if a0 is None else a0 + i)} style="display:flex;gap:22px;align-items:flex-start;"><div style="width:14px;height:14px;'
        f'border-radius:50%;background:{NAVY};flex:none;margin-top:{int(fs * 0.75 - 7)}px;"></div>'
        f'<div style="font-size:{fs}px;{w}line-height:1.5;">{t}</div></div>' for i, t in enumerate(items))
    return (f'<div style="position:absolute;top:{top}px;left:{left}px;width:{width}px;display:flex;'
            f'flex-direction:column;gap:{gap}px;">{rows}</div>')


def arrows(items, fs=30, gap=12, color="#2A2E37", a0=None):
    return "".join(
        f'<div{A(None if a0 is None else a0 + i)} style="display:flex;gap:14px;align-items:flex-start;margin-top:{gap}px;"><div style="color:{GREEN_ARROW};'
        f'font-size:{fs}px;line-height:1.5;flex:none;">➤</div><div style="font-size:{fs}px;line-height:1.5;color:{color};">{t}</div></div>'
        for i, t in enumerate(items))


def strip(t, top, left=110, width=None, right=110, color="#DCE6F5", fs=32, border=None, a=None):
    geo = f"left:{left}px;" + (f"width:{width}px;" if width else f"right:{right}px;")
    bd = f"border:2px solid {border};" if border else ""
    return (f'<div{A(a)} style="position:absolute;top:{top}px;{geo}background:{color};{bd}border-radius:16px;'
            f'padding:20px 36px;font-size:{fs}px;line-height:1.5;color:#2c3a54;"><div>{t}</div></div>')


def card(head, body, x, y, w, h=None, head_bg=NAVY, fs=30, bg="#F7F8FA", body_pad="22px 30px", a=None):
    hh = f"height:{h}px;" if h else ""
    return (f'<div{A(a)} style="position:absolute;left:{x}px;top:{y}px;width:{w}px;{hh}background:{bg};border-radius:16px;'
            f'overflow:hidden;border:1px solid #e4e7ec;">'
            f'<div style="background:{head_bg};color:#fff;font-size:30px;font-weight:700;padding:14px 30px;"><div>{head}</div></div>'
            f'<div style="padding:{body_pad};font-size:{fs}px;line-height:1.55;">{body}</div></div>')


def _skeleton(kicker):
    return (f'<div style="position:absolute;top:54px;left:-16px;width:104px;height:74px;background:{NAVY};border-radius:3px;"></div>\n'
            f'   <div style="position:absolute;top:64px;left:128px;font-size:32px;font-weight:700;">{kicker}</div>\n'
            f'   <img src="{LOGO}" alt="老约翰 深度阅读" style="position:absolute;top:52px;right:100px;height:64px;width:auto;">')


def page(label, kicker, title, body, foot=None, foot_right=110, fa=None):
    """内容页：眉标＋logo＋主题色胶囊（拉到 x≈1470）＋右端吉祥物＋正文 body＋带手指图标的页脚。"""
    f = footer(foot, foot_right, fa) if foot else ""
    return f'''<section data-label="{label}">
 <div style="position:absolute;inset:0;{F}color:#2A2E37;overflow:hidden;">
   {body}
   {_skeleton(kicker)}
   <div style="position:absolute;top:150px;left:110px;"><div style="display:inline-block;min-width:1360px;background:{THEME};border-radius:20px;padding:16px 44px;font-size:42.7px;font-weight:700;line-height:1.3;"><div>{title}</div></div></div>
   <img src="{MASCOT}" style="position:absolute;left:1400px;top:52px;height:200px;width:auto;">
   {f}
 </div>
</section>'''


def cover(title, subtitle, grade_line, figure=None, fig_h=560):
    """封面（全原生形状，禁 raster 标题）。figure＝封面人物图文件名，出血到右下。"""
    img = fig(figure, fig_h, right=50) if figure else ""
    return f'''<section data-label="封面">
 <div style="position:absolute;inset:0;{F}overflow:hidden;">
   <img src="{LOGO}" alt="老约翰 深度阅读" style="position:absolute;top:36px;right:110px;height:60px;width:auto;">
   <div style="position:absolute;top:120px;left:90px;width:1740px;height:600px;border-radius:16px;overflow:hidden;background:linear-gradient(105deg,#EE7B2E 0%,#F0A63C 42%,#57B0A6 100%);">
     <div style="position:absolute;top:30px;left:220px;width:360px;height:360px;border-radius:50%;background:rgba(255,255,255,0.10);"></div>
     <div style="position:absolute;top:230px;left:520px;width:360px;height:360px;border-radius:50%;background:rgba(255,255,255,0.08);"></div>
   </div>
   <div style="position:absolute;left:400px;top:280px;width:1120px;font-weight:700;font-style:italic;font-size:118px;line-height:1.25;color:#fff;">{title}</div>
   <div style="position:absolute;left:404px;top:470px;width:1000px;font-size:40px;font-style:italic;line-height:1.4;color:#fff;font-weight:400;">{subtitle}</div>
   <div data-om-raster="true" style="position:absolute;top:300px;left:0;width:0;height:0;border-top:70px solid transparent;border-bottom:70px solid transparent;border-left:112px solid {NAVY};"></div>
   {img}
   <div style="position:absolute;left:110px;bottom:96px;width:800px;font-size:34px;line-height:1.4;color:{NAVY};font-weight:700;">{grade_line}</div>
 </div>
</section>'''


def section_page(label, big, name, flow):
    """课时分隔页（不放图）。"""
    return f'''<section data-label="{label}">
 <div style="position:absolute;inset:0;{F}overflow:hidden;">
   <div style="position:absolute;top:54px;left:-16px;width:104px;height:74px;background:{NAVY};border-radius:3px;"></div>
   <div style="position:absolute;inset:84px;border-radius:16px;overflow:hidden;background:linear-gradient(120deg,#6FB8AD 0%,#4E93A0 60%,#3D6E82 100%);">
     <div style="position:absolute;left:130px;top:250px;width:600px;font-weight:700;font-size:190px;line-height:1.15;color:rgba(255,255,255,0.95);">{big}</div>
     <div style="position:absolute;left:150px;top:512px;width:1400px;font-size:60px;line-height:1.3;color:#fff;font-weight:700;">{name}</div>
     <div style="position:absolute;left:152px;top:606px;width:1500px;font-size:34px;line-height:1.4;color:rgba(255,255,255,0.95);">{flow}</div>
     <div style="position:absolute;left:130px;bottom:84px;background:#fff;border-radius:12px;padding:12px 20px;"><img src="{LOGO}" alt="老约翰 深度阅读" style="height:50px;width:auto;display:block;"></div>
   </div>
 </div>
</section>'''


def worksheet_page(minutes):
    """稿纸页（自由写作说明页之后固定一页）：稿纸.png 由 grab_worksheet.py 现截；无胶囊、无吉祥物、不加动画。"""
    return f'''<section data-label="自由写作·稿纸">
 <div style="position:absolute;inset:0;{F}color:#2A2E37;overflow:hidden;">
   {_skeleton("自由写作")}
   <div style="position:absolute;top:150px;left:260px;width:1400px;height:753px;border-radius:14px;overflow:hidden;border:1px solid #dfe3e9;">{fig("稿纸.png", 753, left=0, top=0)}</div>
   <div style="position:absolute;right:110px;bottom:50px;background:{RED};color:#fff;border-radius:20px;padding:12px 32px;font-size:38px;font-weight:700;line-height:1.3;"><div>⏱ 写作时间约 {minutes} 分钟</div></div>
 </div>
</section>'''


def timer_badge(minutes, top=296):
    """说明页右上的计时徽标（稿纸页之外，说明页也保留一枚）。"""
    return (f'<div style="position:absolute;top:{top}px;right:110px;background:{RED};color:#fff;border-radius:20px;'
            f'padding:10px 28px;font-size:34px;font-weight:700;"><div>写作时间约 {minutes} 分钟</div></div>')


def end_page(tagline):
    """尾页（不放图）。"""
    return f'''<section data-label="尾页">
 <div style="position:absolute;inset:0;{F}overflow:hidden;">
   <div style="position:absolute;top:54px;left:-16px;width:104px;height:74px;background:{NAVY};border-radius:3px;"></div>
   <div style="position:absolute;inset:84px;border-radius:16px;overflow:hidden;background:linear-gradient(120deg,#6FB8AD 0%,#4E93A0 60%,#3D6E82 100%);">
     <div style="position:absolute;left:120px;top:300px;width:1300px;font-weight:700;font-size:170px;line-height:1.15;color:#fff;">THE END</div>
     <div style="position:absolute;left:132px;top:512px;width:1500px;font-size:38px;line-height:1.4;color:rgba(255,255,255,0.92);">{tagline}</div>
     <div style="position:absolute;right:120px;bottom:96px;display:flex;align-items:center;gap:24px;">
       <div style="font-size:40px;color:#fff;font-weight:700;">下一次再见</div>
       <div data-om-raster="true" style="width:0;height:0;border-top:28px solid transparent;border-bottom:28px solid transparent;border-left:44px solid #fff;"></div>
     </div>
     <div style="position:absolute;left:130px;bottom:84px;background:#fff;border-radius:12px;padding:12px 20px;"><img src="{LOGO}" alt="老约翰 深度阅读" style="height:50px;width:auto;display:block;"></div>
   </div>
 </div>
</section>'''


def write(sections):
    """拼成 dc.html 写到 OUT：补 data-screen-label、「」换弯引号。返回输出路径。"""
    if OUT is None:
        raise SystemExit("先调用 configure(<课次>)")
    S = [s.replace("<section ", f'<section data-screen-label="{i:02d}" ', 1) for i, s in enumerate(sections, 1)]
    body = "\n".join(S)
    html = f'''<!DOCTYPE html>
<html><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<style>
  * {{ box-sizing: border-box; }}
  image-slot {{ --is-bg:#eef1f5; }}
</style>
</helmet>
<x-import component-from-global-scope="deck-stage" from="./deck-stage.js" width="1920" height="1080" hint-size="100%,100%">
{body}
</x-import>
</x-dc>
</body></html>
'''
    html = html.replace("「", "“").replace("」", "”")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print("写出", OUT, len(S), "页")
    return OUT
