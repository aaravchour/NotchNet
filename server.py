from flask import Flask, request, jsonify  # type: ignore
from flask_cors import CORS  # type: ignore
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
from rag_pipeline import generate_answer, reload_qa_chain
import multiprocessing
import threading
import os
import config
import wiki_loader
import clean_data
import build_index

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app)
CORS(app)

# Global state for indexing
indexing_lock = threading.Lock()
in_progress_wikis = set()
PROCESSED_WIKIS_FILE = os.path.join(config.DATA_DIR_CLEANED, "processed_wikis.json")

def load_processed_wikis():
    import json
    if os.path.exists(PROCESSED_WIKIS_FILE):
        try:
            with open(PROCESSED_WIKIS_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_processed_wiki(wiki_url):
    import json
    import time
    data = load_processed_wikis()
    data[wiki_url] = time.time()
    os.makedirs(os.path.dirname(PROCESSED_WIKIS_FILE), exist_ok=True)
    with open(PROCESSED_WIKIS_FILE, "w") as f:
        json.dump(data, f)


@app.route("/ask", methods=["POST"])
def ask_question():
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


def background_wiki_processing(api_url, categories, force=False):
    if api_url in in_progress_wikis:
        print(f"⏩ Wiki {api_url} is already being processed. Skipping.")
        return
    
    # Check cache if not forced
    if not force:
        import time
        processed = load_processed_wikis()
        last_time = processed.get(api_url, 0)
        # Skip if processed in the last 24 hours
        if time.time() - last_time < 86400:
            print(f"✅ Wiki {api_url} was processed recently. Skipping download.")
            return

    in_progress_wikis.add(api_url)
    print(f"🚀 Starting background wiki processing for {api_url}...")
    try:
        wiki_loader.fetch_wiki(api_url, set(categories))
        clean_data.walk_and_clean()
        
        with indexing_lock:
            build_index.build_index()
            reload_qa_chain()
            
        save_processed_wiki(api_url)
        print(f"✅ Background wiki processing complete for {api_url}!")
    except Exception as e:
        print(f"❌ Background wiki processing failed for {api_url}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        in_progress_wikis.remove(api_url)


@app.route("/admin/add-wiki", methods=["POST"])
def add_wiki():
    data = request.get_json()
    if not data or "categories" not in data:
        return jsonify({"error": "Missing 'categories' list"}), 400
    
    api_url = data.get("api_url", config.WIKI_API_URL_DEFAULT)
    categories = data["categories"]

    # Start background thread
    thread = threading.Thread(target=background_wiki_processing, args=(api_url, categories, True))
    thread.start()

    return jsonify({"status": "processing_started", "message": "Wiki download and indexing started in background."})


@app.route("/admin/detect-mods", methods=["POST"])
def detect_mods():
    data = request.get_json()
    if not data or "mods" not in data:
        return jsonify({"error": "Missing 'mods' list"}), 400
        
    raw_mods = data["mods"]
    import mod_discovery
    
    filtered_mods = mod_discovery.filter_mods(raw_mods)
    found_wikis = []
    
    processed = load_processed_wikis()
    import time
    
    for mod in filtered_mods:
        wiki_url = mod_discovery.find_wiki_for_mod(mod)
        if wiki_url:
            # Skip if already in progress or processed recently
            last_time = processed.get(wiki_url, 0)
            if wiki_url not in in_progress_wikis and (time.time() - last_time > 86400):
                found_wikis.append({"mod": mod, "url": wiki_url})
                # Trigger background processing for each found wiki
                default_cats = ["Crafting", "Items", "Blocks", "Mobs"]
                threading.Thread(target=background_wiki_processing, args=(wiki_url, default_cats)).start()
            else:
                reason = "in_progress" if wiki_url in in_progress_wikis else "recently_processed"
                print(f"⏭️ Skipping background processing for {wiki_url} ({reason})")
            
    return jsonify({
        "status": "success", 
        "processed_mods": len(found_wikis), 
        "details": found_wikis
    })


@app.route("/admin/reload-index", methods=["POST"])
def reload_index():
    try:
        reload_qa_chain()
        return jsonify({"status": "success", "message": "QA Chain reloaded."})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    app.run(host="0.0.0.0", port=8000, debug=False)
