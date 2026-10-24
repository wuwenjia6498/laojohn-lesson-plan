# -*- coding: utf-8 -*-
r"""换机装机自检：逐项核对本机能不能像旧机器一样跑全仓流水线。只读、不改任何东西。

用法（项目根目录下）：
    PYTHONUTF8=1 python setup_check.py

每项打印 [OK] / [缺] / [提醒]，[缺] 后面直接给补救命令；有任何 [缺] 则退出码 1。
清单与每一步的来由见 docs\换机装机清单.md——本脚本是那份清单的机检面，两处要一起改。
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
HOME = Path.home()
LA = os.environ.get("LOCALAPPDATA", "")
APPDATA = os.environ.get("APPDATA", "")
miss = 0


def ok(msg):
    print(f"  [OK]   {msg}")


def bad(msg, fix=""):
    global miss
    miss += 1
    print(f"  [缺]   {msg}" + (f"\n         → {fix}" if fix else ""))


def warn(msg, fix=""):
    print(f"  [提醒] {msg}" + (f"\n         → {fix}" if fix else ""))


def run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                           errors="ignore", cwd=ROOT, timeout=60)
        return r.returncode, (r.stdout or "").strip()
    except Exception as e:  # 命令不存在等
        return -1, str(e)


# ---------------------------------------------------------------- 1. Python
print("\n1. Python 与依赖包")
v = sys.version_info
ok(f"Python {v.major}.{v.minor}.{v.micro}（{sys.executable}）")
if os.environ.get("PYTHONUTF8") != "1":
    warn("当前没带 PYTHONUTF8=1", "本仓所有 python 命令一律加 PYTHONUTF8=1（CLAUDE.md §1）")

MODULES = {  # 导入名: pip 包名
    "docx": "python-docx", "lxml": "lxml", "pptx": "python-pptx", "PIL": "Pillow",
    "pypdf": "pypdf", "fitz": "PyMuPDF", "openpyxl": "openpyxl", "win32com": "pywin32",
    "playwright": "playwright", "requests": "requests", "openai": "openai",
    "google.genai": "google-genai", "numpy": "numpy", "cv2": "opencv-python",
    "fontTools": "fonttools", "fastapi": "fastapi", "uvicorn": "uvicorn",
    "httpx": "httpx", "multipart": "python-multipart", "defusedxml": "defusedxml",
    "pdfplumber": "pdfplumber",
}
lack = []
for mod, pkg in MODULES.items():
    try:
        found = importlib.util.find_spec(mod) is not None
    except ModuleNotFoundError:
        found = False
    if not found:
        lack.append(pkg)
if importlib.util.find_spec("brotli") is None and importlib.util.find_spec("brotlicffi") is None:
    lack.append("brotlicffi")
if lack:
    bad("缺包：" + " ".join(lack), "python -m pip install -r requirements.txt")
else:
    ok(f"{len(MODULES) + 1} 个依赖包齐全")

# ---------------------------------------------------------------- 2. 外部程序
print("\n2. 外部程序")
pw = Path(os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or Path(LA) / "ms-playwright")
if pw.exists() and any(p.name.startswith("chromium") for p in pw.iterdir()):
    ok(f"Playwright 浏览器（{pw}）")
else:
    bad("Playwright 浏览器没装", "python -m playwright install chromium")

sys.path.insert(0, str(ROOT / ".claude/skills/laojohn-lesson-video/scripts"))
try:
    import ffmpeg_path  # noqa: E402  仓内单一源，认 PATH / WinGet / 工具\ffmpeg
    exe = ffmpeg_path.ffmpeg()
    code, out = run([exe, "-hide_banner", "-encoders"])
    if "libx264" in out:
        ok(f"ffmpeg（含 libx264）：{exe}")
    else:
        bad(f"ffmpeg 没有 libx264：{exe}", "winget install --id Gyan.FFmpeg -e")
except Exception as e:
    bad("ffmpeg 找不到（备课视频、宣传片要用）", "winget install --id Gyan.FFmpeg -e")

code, out = run(["node", "-v"]) if shutil.which("node") else (-1, "")
ok(f"Node {out}") if code == 0 else warn("没有 Node（仅官方 skill 新建路径用，本仓生产不依赖）",
                                         "winget install OpenJS.NodeJS.LTS")
if not shutil.which("gh"):
    warn("没有 gh（本仓脚本不调用；终端里看 PR/issue 才要）",
         "winget install GitHub.cli，装完 gh auth login")

try:
    import winreg
    for prog in ("PowerPoint.Application", "Word.Application"):
        try:
            winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, prog))
            ok(f"Office COM：{prog}")
        except OSError:
            bad(f"Office COM 缺 {prog}（docx/pptx 转 PDF/PNG 只有这一条路）", "装 Microsoft Office")
except ImportError:
    warn("非 Windows，跳过 Office COM 检查")

FONTS = ["msyh.ttc", "msyhbd.ttc", "simkai.ttf", "simhei.ttf", "simsun.ttc"]
fdir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
lackf = [f for f in FONTS if not (fdir / f).exists()]
bad("缺字体：" + " ".join(lackf), "从旧机器 C:\\Windows\\Fonts 拷过来安装") if lackf \
    else ok("雅黑/楷体/黑体/宋体字体齐全")

# ---------------------------------------------------------------- 3. git 本地配置
print("\n3. git 本地配置（per-clone，不随仓库走）")
code, out = run(["git", "config", "--local", "--get", "core.hooksPath"])
ok("core.hooksPath=.githooks（大文件闸门）") if out == ".githooks" else \
    bad("大文件闸门没装", "git config --local core.hooksPath .githooks")
code, out = run(["git", "config", "--local", "--get-all", "remote.origin.fetch"])
ok("已挡备份支 refspec") if "^refs/heads/backup/*" in out else \
    bad("没挡备份支（一次 pull 会把仓库撑大一倍）",
        "git config --local --add remote.origin.fetch '^refs/heads/backup/*'")
code, name = run(["git", "config", "--local", "--get", "user.name"])
code, mail = run(["git", "config", "--local", "--get", "user.email"])
if mail:
    warn(f"提交身份 {name} <{mail}>——确认是你本人的 GitHub 账号（别照抄 git log 里的历史作者）")
else:
    bad("没配本仓提交身份", "git config --local user.name <你的GitHub用户名>；git config --local user.email <你的GitHub邮箱>")

# ---------------------------------------------------------------- 4. Claude Code 侧
print("\n4. Claude Code 侧")
enc = "".join("-" if c in ":\\/" else c for c in str(ROOT))
link = HOME / ".claude" / "projects" / enc / "memory"
target = ROOT / ".claude" / "memory"
if link.exists() and (link / "MEMORY.md").exists() and link.resolve() == target.resolve():
    ok(f"记忆联接 {link} → {target}")
else:
    bad(f"记忆联接没建或指错（{link}）。联接断了不报错，只表现为「什么都不记得」",
        f'cmd /c mklink /J "{link}" "{target}"（原目录先改名留底，见 docs\\协作同步说明.md 第三节）')
warn(f"项目在移动硬盘：盘符一变，上面的联接路径就变（当前编码 {enc}），换盘符后重跑本脚本")

if (ROOT / ".claude/settings.json").exists() and (ROOT / ".claude/memory/check_memory_index.py").exists():
    ok("SessionStart 记忆索引机检 hook 在（随仓库走）")
else:
    bad("记忆索引机检 hook 或脚本缺失", "git pull 后再查 .claude/settings.json")

hd = HOME / ".claude/skills/handdraw-style-prompter"
ok("用户级 skill handdraw-style-prompter") if (hd / "SKILL.md").exists() else \
    bad("用户级 skill handdraw-style-prompter 没装（换新手绘编号时课件配图工具会报错）",
        f'git clone https://github.com/wuwenjia6498/handdraw-style-prompter.git "{hd}"')
for s in ("h3-prompt-writing",):
    if not (HOME / ".claude/skills" / s).exists():
        warn(f"用户级 skill {s} 不在（宣传片写 H3 提示词用）", "从旧机器 ~\\.claude\\skills\\ 拷过来")

# ---------------------------------------------------------------- 5. 密钥与本地专有文件
print("\n5. 密钥与不入库的本地文件（git 带不过来，只能从旧机器拷）")
cfgs = [p for p in ROOT.rglob("imggen.config.json") if "node_modules" not in str(p)]
if os.environ.get("AIHUBMIX_API_KEY") or cfgs:
    ok("AiHubMix 密钥：" + ("环境变量" if os.environ.get("AIHUBMIX_API_KEY") else str(cfgs[0].relative_to(ROOT))))
else:
    bad("没有 AiHubMix 密钥（生图、海报插画、宣传片、读书会配图全断）",
        "从旧机器拷 .claude\\skills\\laojohn-picture-writing\\scripts\\imggen.config.json，或设环境变量 AIHUBMIX_API_KEY")
# 出图尺寸缺省（2026-10-24 统一长边 1280＋medium）在代码里；本地配置写死了尺寸会盖住缺省，悄悄按大图出、多花钱
stale = []
envf = ROOT / "课件配图工具/.env"
if envf.exists():
    for ln in envf.read_text(encoding="utf-8").splitlines():
        if re.match(r"\s*(GEMINI_IMAGE_SIZE|IMAGE_LONG_SIDE|OPENAI_IMAGE_QUALITY)\s*=", ln):
            stale.append(f"课件配图工具/.env：{ln.strip()}")
for p in cfgs:
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        continue
    for k in ("image_size", "size"):
        if k in d:
            stale.append(f"{p.relative_to(ROOT)}：\"{k}\": \"{d[k]}\"")
if stale:
    warn("本地配置里写死了出图尺寸/质量，会盖住全仓缺省（长边 1280＋medium）：" + "；".join(stale),
         "删掉这几行（临时要大图才写，用完删）")
else:
    ok("出图尺寸走代码缺省（长边 1280＋medium，Gemini 1K）")
grader = ROOT / "作文批改工具/web/server/config.json"
ok("作文批改工具 config.json") if grader.exists() else \
    warn("作文批改工具 config.json 不在（只本地起批改服务才要）", "从旧机器拷 作文批改工具\\web\\server\\config.json")
out_dir = ROOT / "课件配图工具/课件产出"
imgs = sum(1 for p in out_dir.rglob("*") if p.suffix.lower() in (".jpg", ".png")) if out_dir.exists() else 0
if imgs:
    ok(f"课件配图工具\\课件产出\\ 有 {imgs} 张 AI 图")
else:
    warn("课件配图工具\\课件产出\\ 没有 AI 图——v9 读书会 PPT 在本机重烘会缺图",
         "从旧机器整目录拷过来；别在本机重烘 v9 书的正式件")

# ---------------------------------------------------------------- 6. 编辑器
print("\n6. 编辑器")
cur = Path(APPDATA) / "Cursor/User/settings.json"
if cur.exists():
    t = cur.read_text(encoding="utf-8", errors="ignore")
    ok("Cursor 自动保存已开") if '"files.autoSave"' in t and "afterDelay" in t else \
        bad("Cursor 自动保存没开（未保存的手改会被脚本读写冲掉）",
            '在 Cursor settings.json 加 "files.autoSave": "afterDelay", "files.autoSaveDelay": 1000')
else:
    warn("没找到 Cursor 设置（不用 Cursor 可忽略；用别的编辑器也要开自动保存）")

print(f"\n{'全部通过' if not miss else f'有 {miss} 项缺失，按上面 → 补完再跑一次'}。")
sys.exit(1 if miss else 0)
