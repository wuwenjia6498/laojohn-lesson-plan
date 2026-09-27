from PIL import Image, ImageDraw
import sys
D="写作课教材插图/五上-第五单元-介绍一种事物/"
out=sys.argv[1]
GRAY=(222,226,232)
def mask(im, L, R, lines, keep):
    """lines: 行中心 y；keep: {行下标: 可见到的 x（None=整行可见）}"""
    d=ImageDraw.Draw(im)
    for k,c in enumerate(lines):
        if k in keep and keep[k] is None: continue
        x0 = keep.get(k, L)
        d.rectangle((x0, c-29, R+10, c+26), fill="white")
        if x0 < R-40:
            d.rounded_rectangle((x0+(6 if x0>L else 0), c-15, R, c+15), radius=8, fill=GRAY)
    return im
a=Image.open(D+"五上第五单元_习作例文《鲸》_P72.jpg").convert("RGB")
L72=[400+52.3*k for k in range(23)]
L72=[int(round(v)) for v in L72]
keep72={0:None,1:751,6:None,7:825,12:984,14:902}
# 段落分组：0-5 / 6-11 / 12-13 / 14-22
a=mask(a,344,1125,L72,keep72)
a=a.crop((330,235,1145,1590))
b=Image.open(D+"五上第五单元_习作例文《鲸》_P73.jpg").convert("RGB")
L73=[int(round(143+52.4*k)) for k in range(16)]
keep73={0:None,8:None,12:None,13:431}
b=mask(b,176,955,L73,keep73)
b=b.crop((165,80,980,965))
W=a.width+b.width+60; H=a.height
c=Image.new("RGB",(W,H),"white")
c.paste(a,(0,0)); c.paste(b,(a.width+60,a.height-b.height- (a.height-b.height)))
c.paste(b,(a.width+60,0))
d=ImageDraw.Draw(c); d.line((a.width+30,40,a.width+30,H-40),fill=(210,210,210),width=3)
c.save(out)
print(c.size)
