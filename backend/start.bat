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
    echo Instalando dependencias...
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Iniciando servidor em http://localhost:8000
echo Pressione Ctrl+C para parar.
echo.

python server.py
