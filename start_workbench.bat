@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "dist\PolyglotTranslationWorkbench\PolyglotTranslationWorkbench.exe" (
    start "" "%~dp0dist\PolyglotTranslationWorkbench\PolyglotTranslationWorkbench.exe"
) else (
    start "" pythonw native_tk_app.py
)
