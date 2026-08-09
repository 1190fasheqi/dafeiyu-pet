@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "×À³è.py"
) else (
    start "" pythonw "×À³è.py"
)
