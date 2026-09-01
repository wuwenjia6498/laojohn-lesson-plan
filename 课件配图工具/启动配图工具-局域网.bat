@echo off
chcp 936 >nul
rem 课件配图工具 · 局域网启动（给同办公室的同事用）
rem 双击即可。默认命令行启动是只听本机的，这个 bat 带 --lan 才对外开放。
cd /d "%~dp0.."
set PYTHONUTF8=1
python "%~dp0web\server\main.py" --lan
echo.
echo 服务已停止。窗口关掉就等于关掉服务。
pause
