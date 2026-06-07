import sys, re, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

path = sys.argv[1]
with open(path, encoding='utf-8') as f:
    xml = f.read()

SLIDE_W, SLIDE_H = 12192000, 6858000

def pct(x, total):
    return f"{100*int(x)/total:.1f}%"

for m in re.finditer(r'<p:(sp|pic)>(.*?)</p:\1>', xml, re.DOTALL):
    kind = m.group(1)
    block = m.group(2)
    name_m = re.search(r'name="([^"]+)"', block)
    off_m = re.search(r'<a:off x="(-?\d+)" y="(-?\d+)"/><a:ext cx="(\d+)" cy="(\d+)"', block)
    text_m = re.findall(r'<a:t>([^<]*)</a:t>', block)
    sz_m = re.findall(r'sz="(\d+)"', block)
    color_m = re.findall(r'srgbClr val="([0-9A-Fa-f]+)"', block)
    font_m = re.findall(r'typeface="([^"]+)"', block)
    if name_m and off_m:
        x, y, w, h = off_m.groups()
        text = ' / '.join(t for t in text_m if t.strip())
        print(f"[{kind}] {name_m.group(1)}")
        print(f"   pos=({pct(x,SLIDE_W)},{pct(y,SLIDE_H)})  size=({pct(w,SLIDE_W)}x{pct(h,SLIDE_H)})")
        if text:
            print(f"   text: {text[:160]}")
        if sz_m:
            print(f"   sizes: {sorted(set(sz_m))}")
        if color_m:
            print(f"   colors: {sorted(set(color_m))}")
        if font_m:
            ff = sorted(set(font_m))
            print(f"   fonts: {ff}")
    print()
