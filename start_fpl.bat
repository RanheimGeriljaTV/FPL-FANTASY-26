@echo off
title FPL Super Optimizer Dashboard (Manager 117526)
cd /d "%~dp0"

echo ========================================================
echo   FPL Optimizer og Analytics Dashboard
echo   Manager ID: 117526 (Kristoffer Sandvin)
echo   PuLP MILP / SertalpBilal Solver + Streamlit
echo ========================================================
echo.
echo Starter Streamlit-serveren og aapner nettleseren...
echo Trykk Ctrl+C i dette vinduet for aa avslutte.
echo.

python -m streamlit run app.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [FEIL] Kunne ikke starte applikasjonen. Sjekk at Python og Streamlit er installert.
    pause
)
