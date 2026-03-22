@echo off
echo ============================================
echo   VintedScrap — Installation des dependances
echo ============================================
echo.

REM Vérifie que Python est installé
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo [ERREUR] Python n'est pas installe ou pas dans le PATH.
    echo Telecharge Python sur https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [INFO] Installation des bibliotheques requises...
pip install -r requirements.txt

echo.
echo [OK] Installation terminee !
echo.
echo Pour lancer l'application : python main.py
echo.
pause
