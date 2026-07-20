# NotchNet Backend

NotchNet is an AI-powered Minecraft knowledge companion that uses **RAG (Retrieval Augmented Generation)** to answer questions about Minecraft and its mods.

🔗 **Frontend Mod**: [notchnet-mod](https://github.com/aaravchour/notchnet-mod)

## Features

- 🏠 **Local RAG Pipeline** — Runs entirely on your machine using Ollama.
- 🌐 **Dynamic Wiki Fetching** — Fetch and index any MediaWiki-based wiki (e.g., RLCraft, Feed The Beast).
- 🎮 **Auto Mod Detection** — Automatically finds and learns about installed mods when the game launches.
- ☁️ **Cloud Mode** — Offload AI inference to a remote server for low-end machines.
- 🧠 **Mod Awareness** — Context-aware answers based on loaded wikis.

## Quick Start

### Prerequisites

- **Python 3.10+**
- **[Ollama](https://ollama.com/)** installed and running
- 8GB VRAM + 16GB RAM for smooth local model inference

### Run It

**Windows:**
```cmd
start_local.bat
```

**Mac/Linux:**
```bash
chmod +x start_local.sh
./start_local.sh
```

The script will:
1. Create a virtual environment and install dependencies.
2. Ask if you want **Local** or **Cloud/Remote AI**.
3. **Local**: Pulls the default Ollama model (`llama3:8b`).
4. **Cloud**: Configures connection to your remote Ollama instance.
5. Start the API server at `http://localhost:8000`.

### Ask a Question

```bash
curl -X POST http://localhost:8000/ask \\
     -H "Content-Type: application/json" \\
     -d '{"question": "How do I make a shield?"}'
```

## Admin Endpoints

### Add a Mod Wiki

```bash
curl -X POST http://localhost:8000/admin/add-wiki \\
     -H "Content-Type: application/json" \\
     -d '{
         "url": "https://rlcraft.fandom.com",
         "name": "RLCraft"
     }'
```

## Project Structure

```
NotchNet/
├── config/           # RAG pipeline and config
├── mod_discovery/    # Auto-detect installed mods
├── server.py         # FastAPI/Flask server
├── start_local.sh    # Mac/Linux startup script
├── start_local.bat   # Windows startup script
├── wiki/             # Wiki loaders and cleaners
└── requirements.txt
```

## License

[MIT](LICENSE)
