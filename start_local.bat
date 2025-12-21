@echo off
setlocal enabledelayedexpansion

echo 🚀 Starting NotchNet Local...

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed. Please install it from https://python.org/
    exit /b 1
)

:: 2. Create virtual environment if it doesn't exist
if not exist venv (
    echo 📦 Creating virtual environment...
    python -m venv venv
)

:: 3. Activate venv
call venv\Scripts\activate

:: 4. Install/Update dependencies
echo ⬇️ Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

:: 5. Configure Environment
set FLASK_APP=server.py
set LOCAL_MODE=true

echo.
echo ---------------------------------------------------
echo ☁️  Mode Selection
echo ---------------------------------------------------
echo 1) Run Fully Local (Standard)
echo 2) Run with Cloud Model (Uses light local proxy + cloud inference)
set /p MODE_OPT="Select option [1]: "
if "%MODE_OPT%"=="" set MODE_OPT=1

if "%MODE_OPT%"=="2" (
    set CLOUD_MODE=true
) else (
    set CLOUD_MODE=false
)

:: 6. Check for Ollama (Required for both modes)
ollama --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Ollama is not installed. Please install it from https://ollama.com/
    exit /b 1
)

:: 7. Prompt for Model
echo.
echo 🤖 Which Ollama model would you like to use?
if "%CLOUD_MODE%"=="true" (
    echo    Default: gemini-3-flash-preview:cloud (Press Enter to use default)
    set /p USER_MODEL="   Model Name: "
    if "!USER_MODEL!"=="" set USER_MODEL=gemini-3-flash-preview:cloud
) else (
    echo    Default: llama3:8b (Press Enter to use default)
    set /p USER_MODEL="   Model Name: "
    if "!USER_MODEL!"=="" set USER_MODEL=llama3:8b
)
set LLM_MODEL=!USER_MODEL!

:: 8. Check if Model is pulled
echo 🔍 Checking if model '%LLM_MODEL%' is available in Ollama...
ollama list | findstr /R /C:"%LLM_MODEL% " >nul
if %errorlevel% neq 0 (
    echo ⬇️ Model '%LLM_MODEL%' not found. Pulling it now... (This might take a while)
    ollama pull "%LLM_MODEL%"
)

:: 9. Check for Index
if not exist faiss_index (
    echo 🧠 No knowledge base found. Building initial index...
    python build_index.py
)

:: 10. Start Server
echo ✅ Setup complete. Starting Server...
echo ---------------------------------------------------
echo 🌐 Server running at http://localhost:8000
echo 📄 API Documentation in README.md
echo ---------------------------------------------------

python server.py
pause
