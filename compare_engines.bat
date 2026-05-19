@echo off
chcp 65001 >nul
cd /d "%~dp0"
python triple_translate.py --compare --show-steps --copy
pause
