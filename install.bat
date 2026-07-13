@echo off
echo ============================================
echo   ALIOS ONE Chat - Community Edition
echo ============================================
where python >nul 2>nul
if errorlevel 1 (
  echo Python not found. Install it from python.org
  echo IMPORTANT: tick "Add Python to PATH" during install.
  pause & exit /b 1
)
python -m pip install -r requirements.txt
if exist openrouter.key goto done
echo.
echo Get a free API key at: https://openrouter.ai/keys
echo TIP: paste with RIGHT-CLICK (Ctrl+V may not work in this window)
:askkey
set "KEY="
set /p KEY="Paste your OpenRouter API key: "
python -c "k='%KEY%'.strip().strip(chr(34)); import sys; sys.exit(0 if k.startswith('sk-') and len(k)>20 else 1)" 2>nul
if errorlevel 1 (
  echo.
  echo That does not look like a valid key ^(should start with sk-^).
  echo Try again - and use RIGHT-CLICK to paste.
  goto askkey
)
python -c "open('openrouter.key','w').write('%KEY%'.strip().strip(chr(34)))"
echo Key saved.
:done
echo.
echo Done! Start the app anytime with:  run.bat
pause
