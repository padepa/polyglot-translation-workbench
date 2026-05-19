@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "dist\TripleTranslateWorkbench\TripleTranslateWorkbench.exe" (
    start "" "%~dp0dist\TripleTranslateWorkbench\TripleTranslateWorkbench.exe"
) else (
    start "" pythonw native_tk_app.py
)
