# NotchNet Backend

NotchNet is an AI-powered Minecraft knowledge companion that uses RAG (Retrieval Augmented Generation) to answer questions about Minecraft and its mods.

## 🌟 Features

- **Local RAG Pipeline**: Runs entirely on your machine using Ollama.
- **Dynamic Wiki Fetching**: Can fetch and index any MediaWiki-based wiki (e.g., RLCraft, Feed The Beast).
- **Auto Mod Detection**: Automatically finds and learns about installed mods when the game launches.
- **Cloud Mode**: Support for offloading AI inference to a remote server for low-end machines.
- **Mod Awareness**: Context-aware answers based on the loaded wikis.

## 🚀 Getting Started (Local)

### Prerequisites

1.  **Python 3.10+**
2.  **[Ollama](https://ollama.com/)** installed and running (for Local Mode).

### Quick Start

1.  **Clone the repository**.
2.  **Run the startup script**:

    **Windows:**
    ```cmd
    start_local.bat
    ```

    **Mac/Linux:**
    ```bash
    chmod +x start_local.sh
    ./start_local.sh
    ```
    This script will:
    - Create a virtual environment and automatically install dependencies.
    - Ask if you want to run **Locally** or use **Cloud/Remote AI**.
    - **Local**: Pulls the necessary Ollama model (default: `llama3:8b`).
    - **Cloud**: Configures connection to your remote Ollama instance.
    - Start the API server.

3.  **Interact with the API**:
    The server runs at `http://localhost:8000`.

    **Ask a Question:**
    ```bash
    curl -X POST http://localhost:8000/ask \
         -H "Content-Type: application/json" \
         -d '{"question": "How do I make a shield?"}'
    ```

## 📚 Adding Mod Wikis

You can teach NotchNet about new mods by fetching their wikis.

**Endpoint**: `POST /admin/add-wiki`

**Example (Teaching it RLCraft):**
```bash
curl -X POST http://localhost:8000/admin/add-wiki \
     -H "Content-Type: application/json" \
     -d '{
           "api_url": "https://rlcraft.fandom.com/api.php", 
           "categories": ["Crafting", "Items", "Mobs"] 
         }'
```

_Note: This process runs in the background. It will fetch pages, clean them, rebuild the index, and reload the bot's memory._

## 🛠 Configuration

See `config.py` for default settings. You can override them using environment variables or a `.env` file.

| Variable | Description | Default |
| :--- | :--- | :--- |
| `LOCAL_MODE` | Bypass API key checks for local use | `true` (in start script) |
| `LLM_MODEL` | Ollama model to use | `llama3` |
| `OLLAMA_HOST` | URL of Ollama server | `http://127.0.0.1:11434` |

## 📜 License

MIT License. See [LICENSE](LICENSE) for details.
