"""六上五《围绕中心意思写》课件构建脚本（仓内直出，2026-09-26 试点定稿）。

按母版 framework.md 逐页写 dc.html；版式积木在 laojohn-ppt/tools/writing_deck_kit.py。
页序＝详案〖PPT第N页〗页标；点击分组写在各元素的 a／a0／fa 参数里（按详案师话顺序）。
出件跑 laojohn-ppt/tools/direct_build.py（截稿纸 → 本脚本 → 转 PPT → 审查闸门 → 动画）。
"""
import importlib.util
import pathlib
import sys

_K = pathlib.Path(__file__).resolve().parents[2] / ".claude/skills/laojohn-ppt/tools/writing_deck_kit.py"
_spec = importlib.util.spec_from_file_location("writing_deck_kit", _K)
_kit = importlib.util.module_from_spec(_spec)
sys.modules["writing_deck_kit"] = _kit
_spec.loader.exec_module(_kit)
from writing_deck_kit import *  # noqa: E402,F401,F403

configure("六上-第五单元-围绕中心意思写", theme="浅桃")   # 主题色：情感记事，偏暖

S = []

# P01 封面
S.append(cover("围绕中心意思写", "六年级上册 · 第五单元 · 校内同步写作（记事）", "六年级上册 · 第五单元", figure="P01.png"))

# P02 课时分隔
S.append(section_page("课时分隔·01", "01", "写作指导课", "创设情境 · 观察体验 · 学写法 · 中心选材表 · 教师示范文"))

# P03
S.append(page("创设情境·藏字", "创设情境", f"先听老师读一段话：{R('这段话里藏着哪个字')}",
    f'''<div style="position:absolute;top:290px;left:110px;width:1080px;background:#F7F5F2;border-radius:18px;padding:34px 44px;font-size:32px;line-height:1.75;text-indent:2em;"><div>那只杯子是外婆从老家带来的，杯口有一圈细细的金边。我拿它接水的时候手一滑，它在地上碎成了四瓣。我把碎片扫进簸箕，倒进垃圾桶，又拿一张报纸盖在上面。晚上外婆问杯子哪儿去了，我说不知道。那天夜里我翻来覆去，一闭上眼睛，就是那四瓣碎片和那张报纸。</div></div>
   {steps(["这段话里藏着的是哪个字？", "你是从哪一句听出来的？"], 650, width=1080, gap=26, a0=1)}
   {fig("P03.png", 420, right=90, top=330)}''',
    "这段话是老师围绕一个字写的，写的时候把这个字藏了起来，从头到尾一次也没有说。"))

# P04
S.append(page("创设情境·怕还是悔", "创设情境", f"再看最后一句：这是「怕」，还是{R('「悔」')}？",
    f'''{band(730, color=BY)}
   <div style="position:absolute;top:292px;left:110px;width:1060px;background:#EAF1FB;border:2px solid #C3D6F0;border-radius:18px;padding:26px 40px;font-size:34px;line-height:1.6;font-weight:700;"><div>那天夜里我翻来覆去，一闭上眼睛，就是{R('那四瓣碎片和那张报纸')}。</div></div>
   {bullets([f"说「怕」有道理：打碎杯子的时候，{R('他确实是怕的')}。",
             f"可这时候杯子已经扫掉了，外婆也没有发现，{R('他还是睡不着')}。",
             f"已经没有人知道了，他还是睡不着：这是{R('「悔」')}，他不该说不知道。"], 470, width=1060, fs=32, gap=22, a0=1)}
   {fig("P04.png", 500, right=60)}''',
    f"老师从头到尾没有写{R('「悔」')}这个字，大家却都读出来了。", foot_right=820, fa=4))

# P05
chars = "甜乐泪暖悔望迷妙变忙寻让"
cells = "".join(
    f'<div style="width:86px;height:86px;background:{NAVY};border-radius:14px;color:#fff;font-size:46px;font-weight:700;'
    f'display:flex;align-items:center;justify-content:center;"><div>{c}</div></div>' for c in chars)
S.append(page("创设情境·任务", "创设情境", f"这次习作：选一个字，{R('围绕它写一篇文章')}",
    f'''<div style="position:absolute;top:286px;left:110px;width:500px;height:614px;border-radius:14px;overflow:hidden;border:1px solid #e4e7ec;">{fig("插-01.jpg", 614, left=0, top=0)}</div>
   <div style="position:absolute;top:286px;left:670px;width:1140px;background:#F7F5F2;border-radius:18px;padding:26px 38px;font-size:32px;line-height:1.6;"><div>课文《盼》围绕「盼」字，写出了「我」的种种表现。选择一个你{R('感受最深的汉字')}写一篇习作。</div></div>
   <div style="position:absolute;top:470px;left:670px;width:640px;display:grid;grid-template-columns:repeat(6,86px);gap:18px 20px;">{cells}</div>
   {bullets(["可以从这十二个字里选，也可以选别的字", "可以写生活中发生过的事，也可以写想象的故事"], 690, left=670, width=860, fs=32, gap=18, a0=1)}
   {fig("P05.png", 400, right=40)}''',
    f"要求只有一件事：选一个你感受最深的字，{R('围绕它写一篇文章')}。", foot_right=380))

# P06
S.append(page("创设情境·成败标准", "创设情境", f"怎样才算写成：{R('让同学读出你的字')}",
    f'''{band(640, color=BY)}
   {steps([f"写完以后，把写得最具体的那一段读给同学听：{R('不报题目，不说那个字')}",
           f"第二节课的后半段，四人一组轮流读；听的同学把读出的字写在纸上，{R('写完同时亮出来')}",
           f"写的字和你选的一样，或者意思很近，{R('这一篇就写成了')}；写出来的字各不相同，第二节课继续修改"], 290, width=1120, fs=33, gap=28, a0=1)}
   {fig("P06.png", 500, right=40)}''',
    "像老师刚才那样：不说那个字，让听的人自己读出来。", foot_right=760))

# P07
def wordcard(x, ch, items, img, img_h, a=None):
    return f'''<div style="position:absolute;left:{x}px;top:420px;width:830px;height:470px;background:#F7F8FA;border-radius:18px;border:1px solid #e4e7ec;">
     <div style="position:absolute;left:34px;top:30px;width:110px;height:110px;border-radius:50%;background:{RED};color:#fff;font-size:60px;font-weight:700;display:flex;align-items:center;justify-content:center;"><div>{ch}</div></div>
     <div style="position:absolute;left:170px;top:62px;font-size:30px;font-weight:700;color:{NAVY};">同学们写下的</div>
     <div{A(a)} style="position:absolute;left:34px;top:160px;width:520px;">{arrows(items, fs=29, gap=10)}</div>
     {fig(img, img_h, right=18)}
   </div>'''
S.append(page("观察体验·一字唤事", "观察体验", f"先试一试：{R('一个字能让你想起什么事')}",
    f'''{strip(f"老师说一个字，先想一想，再在稿纸角上写下这个字让你想起的第一件事：{R('只写几个关键词')}，其中要有当时看见的一样实物，或者听见的一句话。", 280, fs=31)}
   {wordcard(110, "甜", ["过生日，蛋糕上的草莓", "考了一百分，妈妈说的那句「行啊你」", "外婆的桂花糖，黏牙"], "P07a.png", 330, a=1)}
   {wordcard(980, "寻", ["找猫，它躲在洗衣机后面", "找钥匙，找了半个小时，在书包夹层里", "在操场上找掉了的校牌"], "P07b.png", 290, a=2)}''',
    f"写下来的都是自己经历过的事，每一件都有{R('一样具体的事物')}。", fa=3))

# P08
S.append(page("观察体验·定字", "观察体验", f"定下自己的字，{R('写四五件事的关键词')}",
    f'''{band(600, color=BG)}
   {steps(["定下自己的字：十二个字里的一个，或者别的字",
           f"用三分钟，把这个字让你想起的事一件一件写在稿纸角上，{R('写四五件，多写不限')}，同样只写关键词",
           "想写想象故事的同学，把想到的几个情节写下来"], 290, width=1120, fs=33, gap=26, a0=1)}
   {strip(f"只写了一两件？问一问自己：这个字，{R('在家里、在学校、在路上')}，各让你想起哪一件？", 640, width=1120, color="#FFFFFF", fs=30, border="#C3D6F0", a=4)}
   {fig("P08.png", 520, right=50)}''',
    "例如：我选「变」，弟弟以前一进门就抢电视，现在先写作业。", foot_right=760, fa=5))

# P09
para1 = "星期三我发烧了。早上量体温，三十八度五，妈妈给单位打了电话，说要请一天假。中午她煮了一锅白粥，我喝了两碗。下午没什么事，我靠在床上看了两集动画片，又睡了一觉。傍晚再量，三十七度二，妈妈说明天可以上学了。晚上爸爸下班回来，带回来一盒草莓。"
para2 = "星期三我发烧了。妈妈的手先伸过来，手背贴在我额头上，比体温计还早知道我烧了。中午她端来一碗白粥，勺子搁在碗边，舀了一勺，先吹了两口，再递到我嘴边。下午手机响了一声，是同桌发来的语音：「今天的作业我帮你记好了，放你课桌洞里了。」傍晚再量体温，三十七度二。我把那条语音又听了一遍。"
tp = '<div style="text-indent:2em;">{}</div>'
S.append(page("判断对比·两段话", "判断对比", f"两段话写同一天、同一个字：{R('读完哪一段，你能说出那个字？')}",
    f'''{band(300, color=BY)}
   <div style="position:absolute;top:258px;left:110px;right:110px;font-size:28px;line-height:1.4;color:#5b6470;">两段都是老师写的，那个字同样没有写出来。默读，读完举手：哪一段读完，你能说出那个字？</div>
   {card("第一段", tp.format(para1), 110, 330, 610, h=600, fs=30, head_bg="#C98A2E", bg="#FFFFFF")}
   {card("第二段", tp.format(para2), 750, 330, 610, h=600, fs=30, head_bg="#C98A2E", bg="#FFFFFF")}
   {fig("P09.png", 700, right=20)}'''))

# P10
def row2(a, b):
    return (f'<div style="display:flex;gap:14px;margin-top:18px;font-size:33px;line-height:1.5;"><div style="font-weight:700;">{a}</div>'
            f'<div style="color:{GREEN_ARROW};">➤</div><div>{b}</div></div>')
S.append(page("学写法·第一段的问题", "学写法", f"第一段件件写清，{R('读的人却说不出这一天要说什么')}",
    f'''<div data-anim="1" style="position:absolute;top:290px;left:110px;width:830px;background:#F7F8FA;border-radius:18px;padding:26px 34px;border:1px solid #e4e7ec;">
     <div style="font-size:33px;font-weight:700;color:{NAVY};">第一段：每一样都写清了，读出来的却各不相同</div>
     {row2("两碗粥", "读出的是吃饱了")}{row2("两集动画片", "读出的是闲")}{row2("一盒草莓", "读出的是甜")}
     <div style="margin-top:22px;font-size:31px;line-height:1.5;color:#5b6470;">三件合在一起，读的人说不出这一天到底要说什么。</div>
   </div>
   <div data-anim="2" style="position:absolute;top:290px;left:980px;width:830px;background:#F7F8FA;border-radius:18px;padding:26px 34px;border:1px solid #e4e7ec;">
     <div style="font-size:33px;font-weight:700;color:{NAVY};">第二段：大家说出的字，大多是「暖」</div>
     {row2("手背贴在我额头上", R("暖"))}{row2("舀了一勺，先吹了两口", R("暖"))}{row2("同桌的语音：作业放在课桌洞里", R("暖"))}
     <div style="margin-top:22px;font-size:31px;line-height:1.5;color:#5b6470;">老师写的正是「暖」字。</div>
   </div>
   {strip(f"这次习作要学的，就是{R('围绕一个字选材料')}：先定下这个字代表的中心意思，再看手里的每一件事、每一个方面，能不能让读的人从中读出这个字；能的留下，不能的去掉。", 740, color="#FCF3EE", border="#F0CBB4", fs=31, a=3)}''',
    f"课文《盼》就是这样写的：整篇紧扣一个{R('「盼」')}字，没有一处偏离中心。", fa=4))

# P11
mats = ["跑了几十里地去看戏", "常给我们讲故事", "在爷爷的倡导下，街道组织了业余戏班子", "干活时会哼上两句流行歌曲",
        "边炒菜边做戏曲里的动作，把菜炒煳了", "到文化馆拜师学戏", "每天看书到深夜"]
circ = "①②③④⑤⑥⑦"
matrows = "".join(
    f'<div style="display:flex;gap:16px;align-items:center;background:{"#F7F8FA" if i % 2 == 0 else "#FFFFFF"};'
    f'padding:13px 24px;font-size:32px;line-height:1.45;"><div style="color:{NAVY};font-weight:700;flex:none;">{circ[i]}</div><div>{m}</div></div>'
    for i, m in enumerate(mats))
S.append(page("学写法·戏迷爷爷", "学写法", f"用教材上的一道题来练：哪些材料能表现{R('「戏迷爷爷」')}",
    f'''{band(700, color=BG)}
   {strip(f"先各自判断，能用的在心里记下序号。判断时只问一句：{R('读的人从这一条里，能不能读出「戏迷」两个字')}。", 272, fs=30)}
   <div style="position:absolute;top:400px;left:110px;width:900px;border-radius:14px;overflow:hidden;border:1px solid #e4e7ec;">{matrows}</div>
   <div style="position:absolute;top:400px;left:1050px;width:760px;height:371px;border-radius:14px;overflow:hidden;border:1px solid #e4e7ec;">{fig("插-02.jpg", 371, left=0, top=0)}</div>'''))

# P12
def keeprow(t):
    return f'<div style="font-size:29px;line-height:1.5;margin-top:10px;font-weight:700;">{t}</div>'
def droprow(t, why):
    return (f'<div style="margin-top:10px;"><div style="font-size:29px;line-height:1.45;font-weight:700;">{t}</div>'
            f'<div style="font-size:27px;line-height:1.45;color:#5b6470;">{why}</div></div>')
S.append(page("学写法·判断结果", "学写法", f"判断结果：{R('留下四条，去掉三条')}，其中一条可以改",
    f'''{card("能读出「戏迷」，留下", keeprow("① 跑了几十里地去看戏") + keeprow("③ 组织了业余戏班子") + keeprow("⑤ 边炒菜边做戏曲里的动作，把菜炒煳了") + keeprow("⑥ 到文化馆拜师学戏"), 110, 286, 640, head_bg="#4E9A57", a=1)}
   {card("读不出「戏迷」，去掉", droprow("⑦ 每天看书到深夜", "写的是爱看书，与戏无关") + droprow("④ 干活时会哼上两句流行歌曲", "哼的是戏曲才算") + droprow("② 常给我们讲故事", "读的人读不出讲的是戏"), 780, 286, 620, head_bg="#9aa6b6", a=2)}
   {strip(f"材料不合适，有时不必去掉，{R('改一改就能贴近中心')}：「常给我们讲故事」改成「常给我们讲戏里的故事」，这一条就可以用了。", 700, width=1290, color="#FCF3EE", border="#F0CBB4", fs=30, a=3)}
   {fig("P11.png", 600, right=30)}''',
    "教材说：「要选择合适的材料，突出中心意思。」课文《灯光》写了两件事，合在一起，才让人读出先烈的献身精神。", foot_right=520, fa=4))

# P13
chips = "".join(
    f'<div style="background:{"#FCE7EA" if hi else "#DCE6F5"};border-radius:40px;padding:12px 30px;font-size:30px;font-weight:700;'
    f'color:{"#C0392B" if hi else "#2c3a54"};"><div>{t}</div></div>'
    for t, hi in (("跑几十里看戏", 0), ("组织戏班子", 0), ("炒菜做戏曲动作，把菜炒煳了", 1), ("拜师学戏", 0)))
S.append(page("学写法·详写哪一条", "学写法", f"留下的四条：只能把一条写得最详细，{R('选哪一条？')}",
    f'''<div style="position:absolute;top:290px;left:110px;right:110px;display:flex;gap:20px;flex-wrap:wrap;">{chips}</div>
   <div data-anim="1" style="position:absolute;top:392px;left:110px;right:110px;font-size:32px;line-height:1.55;"><div>不管选哪一条，都看同一点：{R('这一条有没有动作、有没有结果')}，能不能让人看见一个戏迷。炒菜那一条，菜煳了，有动作也有结果，最适合写具体。</div></div>
   {strip(f"选材料的第二步：{R('最能表现中心的那一条写具体，其余的一两句带过')}。教材说：「重要的部分要写得详细、具体一些。」", 520, color="#FCF3EE", border="#F0CBB4", fs=31, a=2)}
   {card("《爸爸的计划》：写几件事", "先罗列爸爸给家里每个人订的计划，再写两个典型的事例，最后把订暑假计划这件事写得最具体。", 110, 668, 835, fs=29, a=3)}
   {card("《小站》：写几个方面", "红榜、喷水池、杏树、月台上的人，一处一处写过去，最后落到给旅客带来温暖的春意上。", 975, 668, 835, fs=29, a=4)}''',
    f"写几件事可以，写几个方面也可以，{R('都是为了表现那一个字')}。", fa=5))

# P14
S.append(page("学写法·三件事", "学写法", f"围绕一个字选材料，{R('做三件事')}",
    f'''{band(290, 170, color=BY)}
   {fig("P14.png", 540, left=110, bottom=170)}
   {steps([f"先用一句话{R('定下这个字代表的中心意思')}",
           f"把想到的材料一条一条问一遍：{R('读的人能不能从中读出这个字')}；读不出的去掉，改一改能贴近中心的就改",
           f"留下的两三条里，{R('最能表现这个字的那一条写具体')}，其余一两句带过"], 340, left=760, width=1050, fs=34, gap=34, a0=1)}''',
    "教材第二题的六个题目，如「闲不住的奶奶」「弟弟变了」，课后可以用同样的方法想一想。", fa=4))

# P15
tbl_rows = [
    ("我选的字", R("忙"), ""),
    ("中心意思（一句话）", "我们家的忙，全挤在早上七点到七点二十这二十分钟里", ""),
    ("材料一", "妈妈 · 肩膀夹着手机接电话 · 锅铲翻煎蛋 · 扎头发", R("能 · 详")),
    ("材料二", "爸爸 · 找车钥匙 · 每天在一个新地方", "能 · 略"),
    ("材料三", "我 · 一边刷牙一边背古诗 · 牙膏沫溅到书上", "能 · 略"),
    ("材料四", "妈妈煎的蛋很好吃", '<span style="color:#8a929e;">不能，读出的是好吃 · 去掉</span>'),
    ("材料五", "周六全家睡到九点", '<span style="color:#8a929e;">不能，读出的是不忙 · 去掉</span>'),
]
cols = "grid-template-columns:330px 1fr 470px;"
trs = "".join(
    f'<div data-anim="{i + 1}" style="display:grid;{cols}background:{"#eef1f5" if i % 2 == 0 else "#fff"};font-size:29px;line-height:1.45;">'
    f'<div style="padding:17px 30px;font-weight:700;">{a}</div><div style="padding:17px 30px;border-left:1px solid #dfe3e9;">{b}</div>'
    f'<div style="padding:17px 30px;border-left:1px solid #dfe3e9;">{c}</div></div>' for i, (a, b, c) in enumerate(tbl_rows))
S.append(page("中心选材表·示范", "中心选材表", f"中心选材表：老师选的字是{R('「忙」')}",
    f'''<div style="position:absolute;top:258px;left:110px;right:110px;font-size:28px;line-height:1.4;color:#5b6470;">这张表就是刚才说的三件事。「初试身手」第二题的六个题目里，正好有一个「忙碌的早晨」。</div>
   <div style="position:absolute;top:318px;left:110px;right:110px;border-radius:14px;overflow:hidden;border:1px solid #dfe3e9;">
     <div style="display:grid;{cols}background:{NAVY};color:#fff;font-size:30px;font-weight:700;"><div style="padding:16px 30px;"><div>项目</div></div><div style="padding:16px 30px;border-left:1px solid rgba(255,255,255,0.25);"><div>关键词</div></div><div style="padding:16px 30px;border-left:1px solid rgba(255,255,255,0.25);"><div>能不能读出这个字 · 详或略</div></div></div>
     {trs}
   </div>''',
    f"第二行那一句是关键：字后面要有一句话，{R('说清楚谁的忙，忙在哪里')}。", fa=8))

# P16
S.append(page("中心选材表·自己填", "中心选材表", f"轮到你了：{R('填自己的表，再和同桌互说')}",
    f'''{band(660, color=BP)}
   {steps([f"稿纸角上的事抄进材料各行；第二行那一句自己定，一时定不下来的，{R('先写「谁的什么」')}，比如「弟弟的变」「奶奶的闲不住」",
           f"逐条判断：读得出写「能」，读不出写「去掉」；{R('改一改能贴近中心的，把改法写在旁边')}",
           f"在留下的材料里选一条标「详」，其余标「略」。{R('给大家六分钟')}"], 286, width=1140, fs=31, gap=22, a0=1)}
   {strip(f"填好后和同桌互说，三分钟：作者先说自己的字，再把留下的每一条读一遍；同桌每听一条，只答{R('「读得出」或者「读不出」')}。", 692, width=1140, color="#FFFFFF", border="#C3D6F0", fs=29, a=4)}
   {fig("P16.png", 430, right=30)}''',
    "填表或者拟提纲都可以；中心意思那一句和每一条后面的判断，必须写在纸上。", foot_right=720))

# P17
mom = (f"七点刚过，厨房里同时响着三样声音：油锅里鸡蛋的滋啦声，妈妈的手机铃声，还有她冲着卧室喊我起床的声音。妈妈正煎着蛋，手机一响，她{R('把锅铲往锅沿上一搁，腾出手把手机夹在肩膀和耳朵中间，歪着头接起来')}：「对，那份表我改过了。」两只手也没停，{R('把皮筋往头顶上一举，几下扎好了头发')}。话说到一半，锅里的鸡蛋边上有点发黄了，她抽出一只手{R('把锅铲一翻，鸡蛋在锅里转了半圈')}，正好翻了个面。等她把电话挂掉，头发也扎好了，鸡蛋也铲进盘子里，锅铲还搁在灶台上冒着热气。{R('这一整套动作，她早上做惯了，从来没有把鸡蛋煎煳过。', C_CLOSE)}")
kw = "".join(f'<div style="background:#DCE6F5;border-radius:40px;padding:8px 26px;font-size:29px;font-weight:700;color:#2c3a54;"><div>{t}</div></div>'
             for t in ("妈妈", "肩膀夹着手机接电话", "锅铲翻煎蛋", "扎头发"))
S.append(page("教师示范文·详写段", "教师示范文", f"表上的材料一：{R('在文章里写成了什么样')}",
    f'''{band(758, color=BY)}
   <div style="position:absolute;top:278px;left:110px;display:flex;gap:16px;align-items:center;"><div style="font-size:30px;font-weight:700;color:{NAVY};">表上的关键词：</div>{kw}</div>
   <div style="position:absolute;top:362px;left:110px;width:1220px;background:#F7F5F2;border-radius:18px;padding:26px 40px;font-size:29px;line-height:1.7;text-indent:2em;"><div>{mom}</div></div>
   <div style="position:absolute;top:790px;left:110px;width:1220px;">{arrows(["表上只有十几个字，到了文章里，写成了几句？", "文章里有、表上没有的，是什么？"], fs=31, gap=6, a0=1)}</div>
   {fig("P01.png", 440, right=20)}''',
    f"详写，就是把这一条拆开，{R('一个动作一个动作写出来')}。", foot_right=560, fa=3))

# P18
def ep(t, first=False, narrow=False):
    mr = "margin-right:600px;" if narrow else ""
    return f'<div style="text-indent:2em;margin-top:{0 if first else 6}px;{mr}">{t}</div>'
essay = (
    ep(R("我们家的忙，全挤在早上七点到七点二十这二十分钟里。", C_CENTER), True)
    + ep(f"七点刚过，{R('厨房里同时响着三样声音', C_DETAIL)}：油锅里鸡蛋的滋啦声，妈妈的手机铃声，还有她冲着卧室喊我起床的声音。妈妈正煎着蛋，手机一响，她把锅铲往锅沿上一搁，{R('腾出手把手机夹在肩膀和耳朵中间，歪着头接起来', C_DETAIL)}：「对，那份表我改过了。」两只手也没停，把皮筋往头顶上一举，几下扎好了头发。话说到一半，锅里的鸡蛋边上有点发黄了，她抽出一只手把锅铲一翻，鸡蛋在锅里转了半圈，正好翻了个面。等她把电话挂掉，头发也扎好了，鸡蛋也铲进盘子里，锅铲还搁在灶台上冒着热气。这一整套动作，她早上做惯了，{R('从来没有把鸡蛋煎煳过', C_DETAIL)}。")
    + ep(f"{R('爸爸的忙，忙在找车钥匙上', C_BRIEF)}。他的钥匙每天早上都在一个新地方：{R('前天落在沙发缝里，昨天在饭桌的报纸底下，今天又揣在了外套口袋里', C_BRIEF)}。他一边四处翻找，嘴里念叨着「我明明放这儿了」，慌乱间还把外套穿反了。")
    + ep(f"我呢，左手攥着牙刷，右手捧着语文书，一边刷牙，一边背诵《宿建德江》。{R('牙膏沫溅到书页上，我随手用袖子一抹，又接着往下背', C_BRIEF)}。背到一半才猛然想起红领巾还没戴，昨天放学随手塞进书包，此刻从包底摸出来，已经皱成一团，我只好先塞进口袋，打算下楼之后边走边把它捋平整。", narrow=True)
    + ep(f"七点二十，{R('家门「咔嗒」一声关上，方才屋里此起彼伏的喧闹瞬间归于安静', C_CLOSE)}。三个人下楼的脚步声，一个比一个急促。", narrow=True)
    + ep(f"我跟在最后，手插进外套口袋，摸到一个温温的东西。{R('是早上那个没来得及吃的煎鸡蛋，装在小小的保鲜袋里', C_CLOSE)}，我竟完全没留意妈妈是什么时候悄悄塞进来的。", narrow=True))
legend = "".join(f'<div style="font-size:28px;line-height:1.5;font-weight:700;color:{c};">■ {t}</div>' for c, t in
                 ((C_CENTER, "一句点出中心意思"), (C_DETAIL, "详写的一条：一个动作一个动作写"), (C_BRIEF, "略写的两条：一两句带过"), (C_CLOSE, "收住，回到中心")))
S.append(page("教师示范文·全文", "教师示范文", f"老师填的那张表，写成了一篇{R('《忙》')}",
    f'''<div style="position:absolute;top:262px;left:110px;right:110px;background:#F7F5F2;border-radius:18px;padding:18px 44px 16px;font-size:28px;line-height:1.5;"><div>{essay}</div>
     {fig("P18.png", 300, right=50)}
   </div>
   <div style="position:absolute;bottom:14px;left:110px;right:110px;display:flex;gap:40px;">{legend}</div>'''))

# P19
def qcard(head, question, answers, concl, a_ans, a_concl, a_card=None):
    return (f'<div{A(a_card)} style="background:#F7F8FA;border-radius:16px;overflow:hidden;border:1px solid #e4e7ec;">'
            f'<div style="background:{NAVY};color:#fff;font-size:30px;font-weight:700;padding:12px 30px;"><div>{head}</div></div>'
            f'<div style="padding:16px 30px 20px;font-size:29px;line-height:1.5;">'
            f'<div style="font-weight:700;">{question}</div>'
            f'<div{A(a_ans)} style="display:flex;flex-wrap:wrap;gap:0 40px;margin-top:6px;">{arrows(answers, fs=29, gap=0)}</div>'
            f'<div{A(a_concl)} style="margin-top:10px;">{concl}</div></div></div>')
S.append(page("读样稿·两个问题", "读样稿", f"读完整篇，{R('思考两个问题')}",
    f'''<div style="position:absolute;top:280px;left:110px;right:110px;display:flex;flex-direction:column;gap:22px;">
     {qcard("问题①", "爸爸和「我」这两条，老师各只写了三句。如果把其中一条也写成妈妈那一段那么长，读起来会怎么样？", ["那就不知道谁最忙了", "三个人平均了，读的人不知道该看谁", "文章太长，忙反而散了"], f"三条材料都扣着「忙」，{R('只有一条写足、另外两条一两句带过')}，读的人才知道该看谁。", 1, 2)}
     {qcard("问题②", "整篇读下来，哪一句让你像走进了他们家那个早晨？", ["腾出手把手机夹在肩膀和耳朵中间，歪着头接起来", "前天落在沙发缝里，昨天在饭桌的报纸底下，今天又揣在了外套口袋里", "牙膏沫溅到书页上，我随手用袖子一抹，又接着往下背"], f"这几句里找不到「很忙」两个字，写的是{R('肩膀夹着手机的样子、钥匙的三个地方、牙膏沫溅到书上')}。", 4, 5, a_card=3)}
   </div>''',
    "表上去掉的两条，文章里也没有出现；结尾那个煎蛋，写的还是忙，不是好吃。", fa=6))

# P20
side = [
    ("我们家的忙，全挤在早上七点到七点二十这二十分钟里", C_CENTER, "开头一句点出中心意思：字是「忙」，落在谁身上、落在什么时候"),
    ("厨房里同时响着三样声音", C_DETAIL, "三样声音同时响起，忙先从声音里写出来"),
    ("腾出手把手机夹在肩膀和耳朵中间，歪着头接起来", C_DETAIL, "详写的这一条：一个人同时做三件事，一个动作一个动作写"),
    ("从来没有把鸡蛋煎煳过", C_DETAIL, "详写这一条的最后一句：动作写完，用一句话把这一条收住"),
    ("爸爸的忙，忙在找车钥匙上", C_BRIEF, "略写的一条：段首先点明这一段写什么，只写这一件事"),
    ("前天落在沙发缝里，昨天在饭桌的报纸底下，今天又揣在了外套口袋里", C_BRIEF, "略写的一条也要具体：三个地方，一句话写完"),
    ("家门「咔嗒」一声关上，方才屋里此起彼伏的喧闹瞬间归于安静", C_CLOSE, "开头那三样声音到这里一起停下，二十分钟到此结束"),
    ("是早上那个没来得及吃的煎鸡蛋，装在小小的保鲜袋里", C_CLOSE, "结尾回到详写的那一条，再次点明中心意思"),
]
cols2 = "grid-template-columns:900px 1fr;"
srows = "".join(
    f'<div data-anim="{i + 1}" style="display:grid;{cols2}background:{"#eef1f5" if i % 2 == 0 else "#fff"};font-size:28px;line-height:1.4;">'
    f'<div style="padding:11px 28px;color:{c};font-weight:700;">{a}</div><div style="padding:11px 28px;border-left:1px solid #dfe3e9;">{b}</div></div>'
    for i, (a, c, b) in enumerate(side))
S.append(page("旁批表", "旁批表", f"让人读出这个字，{R('靠的是这样的句子')}，动笔时可以对照",
    f'''<div style="position:absolute;top:282px;left:110px;right:110px;border-radius:14px;overflow:hidden;border:1px solid #dfe3e9;">
     <div style="display:grid;{cols2}background:{NAVY};color:#fff;font-size:30px;font-weight:700;"><div style="padding:14px 28px;"><div>示范文里的句子</div></div><div style="padding:14px 28px;border-left:1px solid rgba(255,255,255,0.25);"><div>这一句用了什么写法</div></div></div>
     {srows}
   </div>''',
    f"这几句里找不到「很忙」两个字：字是靠{R('动作、声音和地方')}让人读出来的。"))

# P21
ann = [("罗列爸爸给每个人订的计划，突出了爸爸爱订计划的特点。", "先点出中心"),
       ("两个典型的事例，让人印象深刻。", "几条材料都扣着它"),
       ("订暑假计划这个事例，写得很具体。", "最后一条写得最具体")]
annrows = "".join(
    f'<div data-anim="{i + 1}" style="display:flex;gap:22px;align-items:flex-start;">{num(i + 1)}<div style="font-size:29px;line-height:1.5;">'
    f'<div>「{a}」</div><div style="color:{RED};font-weight:700;">➤ {b}</div></div></div>' for i, (a, b) in enumerate(ann))
S.append(page("读样稿·教材旁批", "读样稿", f"教材例文的三条旁批，{R('和中心选材表的三件事一致')}",
    f'''<div style="position:absolute;top:290px;left:110px;width:800px;height:293px;border-radius:14px;overflow:hidden;border:1px solid #e4e7ec;">{fig("插-03.jpg", 293, left=0, top=0)}</div>
   <div style="position:absolute;top:284px;left:960px;width:850px;display:flex;flex-direction:column;gap:22px;">{annrows}</div>
   {strip(f"再看结尾：老师的文章结束在口袋里那个煎蛋上，没有再说一句「我们家真忙」；也可以在这个画面后面再加一句，直接说出自己的感受。{R('两种收法都可以，选哪一种由作者自己决定。')}", 660, width=1250, color="#FCF3EE", border="#F0CBB4", fs=30, a=4)}
   {fig("P21.png", 330, right=30)}''',
    "老师写的是虚构的一家人，大家写的是自己那个字、自己的事，不必照着老师的样子写。", foot_right=520, fa=5))

# P22 课时分隔
S.append(section_page("课时分隔·02", "02", "当堂写作与评改课", "先定两件事 · 自由写作 · 轮读猜字 · 同桌互读 · 修改收束"))

# P23
S.append(page("写作热身·先定两件事", "写作热身", f"拿出中心选材表，{R('动笔之前先定两件事')}",
    f'''{band(740, color=BY)}
   {card("一　整篇从哪一句起笔", arrows(["像老师那样，第一句就把中心意思说出来", "先从详写那一条里选一个画面起笔，中心意思放到结尾再说"], fs=30, gap=4), 110, 284, 1150, fs=30, a=1)}
   {card("二　详写那一条放在什么位置", arrows(["放在最前面，读的人一开始就读出这个字", "放在最后，前面几条先作铺垫，最后一条写足"], fs=30, gap=4), 110, 510, 1150, fs=30, a=2)}
   {strip(f"在表上详写那一条旁边写上{R('「前」或者「后」')}，再在稿纸第一行把起笔的那一句写下来。", 750, width=1150, color="#FFFFFF", border="#C3D6F0", fs=30, a=3)}
   {fig("P23.png", 460, right=30)}''',
    "例如：第一句写「弟弟这个学期变了」，先说出来，后面三件事一件比一件明显。", foot_right=680, fa=4))

# P24
S.append(page("自由写作", "自由写作", f"接着起笔的那一句往下写：{R('一条材料写一段')}",
    f'''{band(600, color=BY)}
   {timer_badge(25)}
   {bullets([f"留下的材料一条写一段；标了「详」的那一条{R('把动作一个一个写出来')}，其余两条一两句带过",
             "开头或者结尾，有一句话把中心意思说出来",
             f"篇幅在五百字到六百字之间；{R('中途遇到错字、病句先不改')}，写完全篇再修改"], 290, width=1150, fs=33, gap=22, a0=1)}
   {strip(f"写不下去？对照自己的表，看还有哪几条没有写到。详写那一段只写了「妈妈很忙」？问一问：{R('这时候这个人在做什么动作，身子朝着哪边')}。", 640, width=1150, color="#FFFFFF", border="#C3D6F0", fs=29, a=4)}
   {fig("P24.png", 440, right=30)}''',
    "写不完的，当堂至少把详写的那一条写完。", foot_right=700, fa=5))

# P25 稿纸页（自由写作说明页之后固定一页）
S.append(worksheet_page(25))

# P26（详案 P26 起）
S.append(page("交流评议·轮读猜字", "交流评议", f"四人一组轮读，{R('让同学读出你的字')}",
    f'''{band(660, color=BG)}
   {steps([f"每人只读标了「详」的那一段：{R('不读题目，不读点出中心意思的那一句，不说那个字')}",
           f"同桌以外的两位同学听完，各自在稿纸角上写下读出的字，{R('写完同时亮出来')}",
           "同桌不猜，只记一件事：哪一句让你听出了这个字，读完告诉作者"], 284, width=1150, fs=31, gap=22, a0=1)}
   {strip(f"写出的字和你选的一样，或者意思很近，比如「忙」和「急」，就算读出来了。都对不上？请两位同学各说从哪一句读出的，作者自己判断：{R('是这一段没有写出这个字，还是写出来的其实是另一个字')}。", 640, width=1150, color="#FCF3EE", border="#F0CBB4", fs=28, a=4)}
   {fig("P25.png", 440, right=30)}''',
    "每人读约一分钟，四人轮流读完后，各自查看结果。", foot_right=700))

# P26
def mark(sym, t, y, a=None):
    return f'''<div{A(a)} style="position:absolute;left:110px;top:{y}px;width:1130px;background:#F7F8FA;border-radius:18px;border:1px solid #e4e7ec;padding:24px 34px;display:flex;gap:30px;align-items:center;">
     <div style="width:96px;height:96px;flex:none;border-radius:50%;background:{RED};color:#fff;font-size:54px;font-weight:700;display:flex;align-items:center;justify-content:center;"><div>{sym}</div></div>
     <div style="font-size:34px;line-height:1.5;">{t}</div></div>'''
S.append(page("交流评议·两个记号", "交流评议", f"同桌互换稿子默读，{R('做两个记号')}",
    f'''{band(640, color=BY)}
   {mark("～", f"最能让你读出这个字的一句，{R('画一道波浪线')}", 300, a=1)}
   {mark("？", f"和这个字关系不大的一句或者一段，{R('在旁边打一个问号')}；全篇没有这样的句子，就不打问号", 480, a=2)}
   {fig("P26.png", 440, right=30)}''',
    "从头到尾默读一遍，给大家两分钟。", foot_right=700))

# P27  （v8 版式：左三种情况、右三档，逐行对齐；左栏一击、右栏一击，同顶不回跳）
CASES = [("字没猜对，也没有波浪线", f"详写那一段还没有把字写出来：回到这一段，在人物做事的地方{R('补上两句，一句写动作，一句写这个动作的结果')}"),
         ("有问号", "打了问号的那一句或者那一段，先看能不能改一句，让它贴近中心意思，改不了就去掉"),
         ("字猜对了，也没有问号", "看留下的两三条是不是一条详、其余略；三条差不多长的，把略写的压缩到两三句")]
TIERS = [("#9aa6b6", "#F7F8FA", "基础过关", "我选定了一个字，围绕它写出了几件事，句子读得通。"),
         ("#E0A43B", "#FBF3E6", "良好达标", "我留下的每一条材料都扣着那个字，听的人说得出我写的是哪个字。"),
         ("#C0392B", "#FCE7EA", "优秀进阶", "我有一条写足了，动作一个接一个；其余的一两句带过；开头或者结尾有一句把中心意思说出来。")]
cells = (f'<div data-anim="1" style="font-size:30px;font-weight:700;color:{NAVY};">三种情况，各自确定改哪里</div>'
         f'<div data-anim="2" style="font-size:30px;font-weight:700;color:{NAVY};">我写到了哪一档</div>')
for (h, t), (bd, bg, th, tt) in zip(CASES, TIERS):
    cells += (f'<div data-anim="1" style="background:#F7F8FA;border-radius:14px;border:1px solid #e4e7ec;padding:12px 24px;font-size:28px;line-height:1.5;">'
              f'<div><span style="font-weight:700;color:{NAVY};">{h}　</span>{t}</div></div>'
              f'<div data-anim="2" style="background:{bg};border-left:8px solid {bd};border-radius:10px;padding:12px 22px;font-size:28px;line-height:1.5;">'
              f'<div><span style="font-weight:700;">{th}　</span>{tt}</div></div>')
S.append(page("修改收束·改一处", "修改收束", f"对照记号，只改一处：{R('先看自己写到了哪一档')}",
    f'''{band(770, color=BP)}
   <div style="position:absolute;top:282px;left:110px;right:110px;display:grid;grid-template-columns:960px 1fr;gap:14px 30px;">{cells}</div>
   {fig("P27.png", 300, right=60)}''',
    "只改这一处，给大家三分钟；改完再用一分钟通读全文，用修改符号改正多字、漏字、错字。", foot_right=560, fa=3))

# P28
S.append(page("收束·意犹帅也", "收束", f"单元导语里的一句话：{R('意犹帅也')}",
    f'''{band(744, 120, color=BY)}
   <div style="position:absolute;top:320px;left:110px;width:1040px;background:#F7F5F2;border-radius:18px;padding:34px 40px;font-size:38px;line-height:1.5;font-weight:700;text-align:center;"><div>「无论诗歌与长行文字，俱以意为主。{R('意犹帅也')}。」</div></div>
   {bullets(["写文章，中心意思是主帅，材料是兵，兵都要听从主帅",
             f"今天大家做的就是这件事：{R('先定主帅，再选兵')}",
             "请把稿子交上来，中心选材表夹在稿子里一起上交"], 504, width=1040, fs=34, gap=24, a0=1)}
   {fig("P28.png", 653, left=1190, top=297)}''',
    "围绕一个字选材料：一句话定下中心意思，材料一条一条问一遍，最能表现它的那一条写足。", fa=4))

# P30 尾页
S.append(end_page("围绕一个字选材料：先定主帅，再选兵，最能表现它的那一条写足。"))

if __name__ == "__main__":
    write(S)
