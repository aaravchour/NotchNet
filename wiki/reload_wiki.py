import os
import shutil
import subprocess
import sys
from config import config

def run_script(script_name):
    print(f"\n▶️ Running {script_name}...")
    result = subprocess.run([sys.executable, script_name], capture_output=False)
    if result.returncode != 0:
        print(f"❌ Error: {script_name} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    print(f"✅ {script_name} completed.")

def reload_wiki():
    print("🌊 Starting full Minecraft Wiki reload and index rebuild...")

    # 1. Cleanup old data
    paths_to_clean = [
        config.DATA_DIR_RAW,
        config.DATA_DIR_CLEANED,
        config.INDEX_PATH
    ]

    for path in paths_to_clean:
        if os.path.exists(path):
            print(f"🧹 Deleting {path}...")
            if os.path.isfile(path):
                os.remove(path)
            else:
                shutil.rmtree(path)

    # 2. Run the pipeline
    run_script("wiki/wiki_loader.py")
    run_script("wiki/clean_data.py")
    run_script("config/build_index.py")

    print("\n✨ All steps completed successfully!")
    print("The Minecraft wiki has been reloaded and a new FAISS index has been produced.")

if __name__ == "__main__":
    reload_wiki()
