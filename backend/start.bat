@echo off
echo ============================================
echo    GateVision API Server
echo ============================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\activate.bat" (
    echo Criando ambiente virtual...
    python -m venv .venv
    call .venv\Scripts\activate.bat
) else (
    call .venv\Scripts\activate.bat
)

python -c "import dotenv" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    python -m pip install -r requirements.txt
)

echo.
echo Iniciando servidor em http://localhost:8000
echo Pressione Ctrl+C para parar.
echo.

python server.py
