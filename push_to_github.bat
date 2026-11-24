@echo off
cd /d "%~dp0"
echo ========================================================
echo   Pushing Liny Desktop AI to GitHub...
echo ========================================================
echo.
git push -u origin main
echo.
if %errorlevel% equ 0 (
    echo [SUCCESS] Code successfully pushed to GitHub!
) else (
    echo [FAILED] Push failed. If authentication was requested, please complete the browser login prompt.
)
echo.
pause
