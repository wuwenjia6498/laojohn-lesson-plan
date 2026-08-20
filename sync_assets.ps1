<#
.SYNOPSIS
  大件资产双向同步：项目目录 <-> 网盘同步目录。

.DESCRIPTION
  三类资产 git 管不了——两类是版权扫描件（不能进仓库）、一类是外部平台生成的
  PPT（本仓渲不出来）。它们走网盘共享，本脚本负责把项目目录与网盘目录对齐。

  ⚠ 为什么不用目录联接（mklink /J）：
     项目常放在 exFAT 移动硬盘上，而**联接只能建在 NTFS 卷上**，在 exFAT 上
     建会报 "Local NTFS volumes are required"。项目记忆那条联接之所以能成，
     是因为它建在 C 盘（NTFS）、只是指向 E 盘——方向反过来就不行。
     若你的项目在 NTFS 盘上，可以改用联接，那样是实时的、不必跑本脚本。

  同步策略：**两个方向都只覆盖更旧的（robocopy /XO），不做删除同步**。
     结果是两边取并集、每个文件取较新的那版。这对「只增不改」的资产目录是安全的；
     同一文件两边都改过时较新的赢——插图与外部 PPT 极少出现这种情况。
     **绝不使用 /MIR**：那会按单侧内容删除另一侧，一次手滑就是删掉对方的图。

.PARAMETER CloudRoot
  网盘上的共享根目录。缺省是本机 OneDrive 的位置；换机器/换网盘时传这个参数。

.PARAMETER WhatIf
  只列出会同步什么，不真的动文件。

.EXAMPLE
  .\sync_assets.ps1
  .\sync_assets.ps1 -CloudRoot "D:\Nutstore\laojohn-共享大件"
  .\sync_assets.ps1 -WhatIf
#>
param(
  [string]$CloudRoot = "$env:USERPROFILE\OneDrive\laojohn-共享大件",
  [switch]$WhatIf
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

# 三个目录名即两侧的子目录名，两边必须同名
$DIRS = @("读书会原书插图", "写作课教材插图", "写作课件PPT输出")

if (-not (Test-Path $CloudRoot)) {
  Write-Host "网盘根目录不存在：$CloudRoot" -ForegroundColor Red
  Write-Host "首次使用请先建好，或用 -CloudRoot 指定实际位置。" -ForegroundColor Yellow
  exit 1
}

Write-Host "项目：$ProjectRoot"
Write-Host "网盘：$CloudRoot"
if ($WhatIf) { Write-Host "（试运行，不动文件）" -ForegroundColor Yellow }
Write-Host ""

$flags = @("/E", "/XO", "/NFL", "/NDL", "/NJH", "/NJS", "/R:2", "/W:2", "/MT:8")
if ($WhatIf) { $flags += "/L" }

$total = 0
foreach ($d in $DIRS) {
  $proj  = Join-Path $ProjectRoot $d
  $cloud = Join-Path $CloudRoot   $d

  if (-not (Test-Path $proj))  { New-Item -ItemType Directory -Force $proj  | Out-Null }
  if (-not (Test-Path $cloud)) { New-Item -ItemType Directory -Force $cloud | Out-Null }

  # 方向一：项目 -> 网盘（把本机新增/更新的推上去）
  robocopy $proj $cloud @flags | Out-Null
  $up = $LASTEXITCODE
  # 方向二：网盘 -> 项目（把对方新增/更新的拉下来）
  robocopy $cloud $proj @flags | Out-Null
  $down = $LASTEXITCODE

  # robocopy 退出码 0-7 皆为成功（1=有文件被复制），>=8 才是真失败
  if ($up -ge 8 -or $down -ge 8) {
    Write-Host ("  [失败] {0}  (上行 {1} / 下行 {2})" -f $d, $up, $down) -ForegroundColor Red
    continue
  }

  $np = (Get-ChildItem $proj  -Recurse -File -ErrorAction SilentlyContinue).Count
  $nc = (Get-ChildItem $cloud -Recurse -File -ErrorAction SilentlyContinue).Count
  $total += $np
  $mark = if ($np -eq $nc) { "OK" } else { "两侧文件数不一致，请人工看一眼" }
  Write-Host ("  {0,-16} 项目 {1,4} 个 / 网盘 {2,4} 个   {3}" -f $d, $np, $nc, $mark)
}

Write-Host ""
if ($WhatIf) {
  Write-Host "试运行结束，没有改动任何文件。" -ForegroundColor Yellow
} else {
  Write-Host ("同步完成，项目侧共 {0} 个资产文件。" -f $total) -ForegroundColor Green
  Write-Host "网盘客户端会在后台把改动传给对方；对方跑一次本脚本即可拿到。"
}
