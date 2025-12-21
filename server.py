from flask import Flask, request, jsonify  # type: ignore
from flask_cors import CORS  # type: ignore
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
from rag_pipeline import generate_answer, reload_qa_chain
import multiprocessing
import os
import time
import secrets
import threading

import config
import wiki_loader
import clean_data
import build_index

API_KEY = config.API_KEY
app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)
CORS(app)


issued_tokens = {}

TOKEN_TTL = 600


def is_valid_api_key():
    if config.is_local_mode():
        return True
    client_key = request.headers.get("X-API-Key")
    return client_key == API_KEY


def is_valid_temp_token(token):
    if config.is_local_mode():
        return True
    now = time.time()
    # purge expired
    expired = [t for t, exp in issued_tokens.items() if exp < now]
    for t in expired:
        issued_tokens.pop(t, None)
    # check current token
    return token in issued_tokens and issued_tokens[token] > now


@app.route("/get_token", methods=["POST"])
def get_token():
    """Client (the mod) calls this with the real API key once to get a temp token."""
    # Extra security: Only allow requests from the Auth Server
    internal_secret = request.headers.get("X-Internal-Secret")
    if not config.is_local_mode() and internal_secret != config.INTERNAL_SECRET:
         return jsonify({"error": "Unauthorized – invalid internal secret"}), 401

    if not is_valid_api_key():
        return jsonify({"error": "Unauthorized – invalid or missing API key"}), 401

    temp_token = secrets.token_urlsafe(32)
    issued_tokens[temp_token] = time.time() + TOKEN_TTL
    return jsonify({"token": temp_token, "expires_in": TOKEN_TTL})


@app.route("/ask", methods=["POST"])
def ask_question():
    # Auth check
    if not config.is_local_mode():
        auth = request.headers.get("Authorization", "")
        token = auth.removeprefix("Bearer ").strip()

        if not token or not is_valid_temp_token(token):
            return jsonify({"error": "Unauthorized – invalid or expired token"}), 401

    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field"}), 400

    try:
        answer = generate_answer(data["question"])
        return jsonify({"answer": answer})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


def background_wiki_processing(api_url, categories):
    print(f"🚀 Starting background wiki processing for {api_url}...")
    try:
        wiki_loader.fetch_wiki(api_url, set(categories))
        clean_data.walk_and_clean()
        build_index.build_index(force_rebuild=True) # Force rebuild to include new docs
        reload_qa_chain()
        print("✅ Background wiki processing complete!")
    except Exception as e:
        print(f"❌ Background wiki processing failed: {e}")
        import traceback
        traceback.print_exc()


@app.route("/admin/add-wiki", methods=["POST"])
def add_wiki():
    if not config.is_local_mode():
         # In production, you might want deeper auth for this
         if request.headers.get("X-Internal-Secret") != config.INTERNAL_SECRET:
             return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    if not data or "categories" not in data:
        return jsonify({"error": "Missing 'categories' list"}), 400
    
    api_url = data.get("api_url", config.WIKI_API_URL_DEFAULT)
    categories = data["categories"]

    # Start background thread
    thread = threading.Thread(target=background_wiki_processing, args=(api_url, categories))
    thread.start()

    return jsonify({"status": "processing_started", "message": "Wiki download and indexing started in background."})


@app.route("/admin/detect-mods", methods=["POST"])
def detect_mods():
    if not config.is_local_mode():
         if request.headers.get("X-Internal-Secret") != config.INTERNAL_SECRET:
             return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    if not data or "mods" not in data:
        return jsonify({"error": "Missing 'mods' list"}), 400
        
    raw_mods = data["mods"]
    import mod_discovery
    
    filtered_mods = mod_discovery.filter_mods(raw_mods)
    found_wikis = []
    
    for mod in filtered_mods:
        wiki_url = mod_discovery.find_wiki_for_mod(mod)
        if wiki_url:
            found_wikis.append({"mod": mod, "url": wiki_url})
            # Trigger background processing for each found wiki
            # We use a default set of categories for auto-detected wikis
            # to avoid fetching the whole thing if it's huge, or just fetch 'Crafting', 'Items'
            default_cats = ["Crafting", "Items", "Blocks", "Mobs"]
            threading.Thread(target=background_wiki_processing, args=(wiki_url, default_cats)).start()
            
    return jsonify({
        "status": "success", 
        "processed_mods": len(found_wikis), 
        "details": found_wikis
    })


@app.route("/admin/reload-index", methods=["POST"])
def reload_index():
    if not config.is_local_mode():
         if request.headers.get("X-Internal-Secret") != config.INTERNAL_SECRET:
             return jsonify({"error": "Unauthorized"}), 401
             
    try:
        reload_qa_chain()
        return jsonify({"status": "success", "message": "QA Chain reloaded."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    # If local, debug=True is usually fine, but sticking to False to match orig
    app.run(host="0.0.0.0", port=8000, debug=False)
