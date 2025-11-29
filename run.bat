@echo off
title Sistema Ares - Web App
echo =======================================
echo     🚀 Iniciando o Sistema Ares
echo =======================================

:: 1. Criar ambiente virtual se não existir
if not exist venv (
    echo 📦 Criando ambiente virtual...
    python -m venv venv
)

:: 2. Ativar ambiente virtual
echo 🔧 Ativando ambiente virtual...
call venv\Scripts\activate

:: 3. Instalar dependências
if exist requirements.txt (
    echo 📚 Instalando dependências...
    pip install -r requirements.txt
) else (
    echo ⚠️ Nenhum requirements.txt encontrado. Pulando instalacao.
)

:: 4. Inicializar banco de dados (se existir o arquivo)
if exist init_db.py (
    echo 🗄️ Inicializando banco de dados...
    python init_db.py
)

:: 5. Executar servidor Flask
echo 🌐 Iniciando Web App Ares...
set FLASK_APP=app.py
set FLASK_ENV=development
flask run --host=0.0.0.0 --port=5000

echo =======================================
echo   ✔ Sistema Ares está rodando!
echo   Acesse no navegador: http://localhost:5000
echo =======================================
pause