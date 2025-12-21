#!/bin/bash

# NotchNet Local Startup Script (Mac/Linux)

echo "🚀 Starting NotchNet Local..."

# 1. Check for Python
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python is not installed. Please install it first."
    exit 1
fi

# 2. Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    $PYTHON_CMD -m venv venv
fi

# 3. Activate venv
source venv/bin/activate

# 4. Install/Update dependencies
echo "⬇️ Installing dependencies..."
$PYTHON_CMD -m pip install --upgrade pip
$PYTHON_CMD -m pip install -r requirements.txt

# 5. Configure Environment
export FLASK_APP=server.py
export LOCAL_MODE=true

echo ""
echo "---------------------------------------------------"
echo "☁️  Mode Selection"
echo "---------------------------------------------------"
echo "1) Run Fully Local (Standard)"
echo "2) Run with Cloud Model (Uses light local proxy + cloud inference)"
read -p "Select option [1]: " MODE_OPT
MODE_OPT=${MODE_OPT:-1}

if [ "$MODE_OPT" = "2" ]; then
    export CLOUD_MODE=true
    # For "Ollama Cloud", we presumably still talk to localhost, 
    # but the model name directs it to the cloud.
else
    export CLOUD_MODE=false
fi

# 6. Check for Ollama (Required for both modes now)
if ! command -v ollama &> /dev/null; then
    echo "❌ Ollama is not installed. Please install it from https://ollama.com/"
    exit 1
fi

# 7. Prompt for Model
echo ""
echo "🤖 Which Ollama model would you like to use?"
if [ "$CLOUD_MODE" = "true" ]; then
    echo "   Default: gemini-3-flash-preview:cloud (Press Enter to use default)"
    read -p "   Model Name: " USER_MODEL
    USER_MODEL=${USER_MODEL:-gemini-3-flash-preview:cloud}
else
    echo "   Default: llama3:8b (Press Enter to use default)"
    read -p "   Model Name: " USER_MODEL
    USER_MODEL=${USER_MODEL:-llama3:8b}
fi
export LLM_MODEL=$USER_MODEL

# 8. Check if Models are pulled
echo "🔍 Checking for required models in Ollama..."
for MODEL in "$LLM_MODEL" "mxbai-embed-large"; do
    if ! ollama list | grep -q "$MODEL"; then
        echo "⬇️ Model '$MODEL' not found. Pulling it now... (This might take a while)"
        ollama pull "$MODEL"
    else
        echo "✅ Model '$MODEL' is ready."
    fi
done

# 9. Check for Index
if [ ! -d "faiss_index" ]; then
    echo "🧠 No knowledge base found. Building initial index..."
    $PYTHON_CMD build_index.py
fi

# 10. Start Server
echo "✅ Setup complete. Starting Server..."
echo "---------------------------------------------------"
echo "🌐 Server running at http://localhost:8000"
echo "📄 API Documentation in README.md"
echo "---------------------------------------------------"

$PYTHON_CMD server.py
