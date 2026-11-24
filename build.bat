@echo off
echo ==================================================
echo   Liny Desktop AI - Standalone Windows Builder
echo ==================================================
python build.py
if %ERRORLEVEL% EQU 0 (
    echo.
    echo Build completed! You can find the standalone app in dist\LinyDesktopAI\
) else (
    echo.
    echo Build failed with error code %ERRORLEVEL%.
)
pause

