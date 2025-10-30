import os
import time
import faiss  # type: ignore
import requests
from tqdm import tqdm  # type: ignore

from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
from langchain_community.vectorstores import FAISS  # type: ignore
from langchain_community.document_loaders import TextLoader  # type: ignore
from langchain_community.embeddings import OllamaEmbeddings  # type: ignore

# ===========================
# Configuration
# ===========================

DATA_DIR = "data/wiki_pages_cleaned"
INDEX_PATH = "faiss_index"

# Use all CPU cores
NUM_CORES = os.cpu_count() or 8
os.environ["OLLAMA_NUM_THREADS"] = str(NUM_CORES)
faiss.omp_set_num_threads(NUM_CORES)

# --- CONFIGURATION FOR STABILITY ---
BATCH_SIZE = 16  # Small and stable
SAVE_EVERY_N_BATCHES = 20

# ===========================
# Helper Functions
# ===========================


def check_ollama():
    try:
        r = requests.get("http://localhost:11434")
        if r.status_code == 200:
            print("🟢 Ollama server is running.")
            return True
        else:
            raise RuntimeError("Ollama server responded, but not OK.")
    except Exception as e:
        print("❌ Ollama is not running. Please start it with `ollama serve`.")
        raise e


def load_documents():
    docs = []
    print(f"📚 Loading documents from {DATA_DIR}...")
    for root, _, files in os.walk(DATA_DIR):
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                loader = TextLoader(full_path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    relative_path = os.path.relpath(full_path, DATA_DIR)
                    doc.metadata["source"] = relative_path
                docs.extend(loaded)
    print(f"✅ Loaded {len(docs)} raw documents.")
    return docs


def add_batch_with_retry(db, batch, max_retries=5):
    for attempt in range(max_retries):
        try:
            db.add_documents(batch)
            return True  # Success
        except ValueError as e:
            if ("EOF" in str(e) or "500" in str(e)) and attempt < max_retries - 1:
                wait_time = (2**attempt) * 5  # 5s, 10s, 20s, 40s
                print(
                    f"\n⚠️ Ollama connection error. Retrying in {wait_time}s... (Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(wait_time)
                check_ollama()  # Check if server is back
            else:
                raise e
    print(f"\n❌ Failed to embed batch after {max_retries} attempts. Stopping.")
    return False  # Failed


def main():
    check_ollama()

    all_docs = load_documents()
    if not all_docs:
        raise ValueError("❌ No documents loaded from summaries!")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024, chunk_overlap=150, separators=["\n\n", "\n", ".", " "]
    )
    split_docs = splitter.split_documents(all_docs)
    print(f"✅ Split documents into {len(split_docs)} chunks.")

    # Use the new model and new import class
    embedding_model = OllamaEmbeddings(model="mxbai-embed-large")

    num_processed = 0

    # We deleted the index, so this 'if' will be FALSE
    if os.path.exists(INDEX_PATH):
        print("🔁 Found existing FAISS index. Loading to resume...")
        db = FAISS.load_local(
            INDEX_PATH, embedding_model, allow_dangerous_deserialization=True
        )
        num_processed = len(db.index_to_docstore_id)
        print(f"✅ Resuming from document chunk {num_processed} / {len(split_docs)}")
    else:
        print("✨ No index found. Creating a new one...")
        if not split_docs:
            print("No documents to index.")
            return

        # Create index from the first batch
        first_batch = split_docs[:BATCH_SIZE]
        db = FAISS.from_documents(first_batch, embedding_model)
        num_processed = len(first_batch)
        print("✅ Created index with first batch.")
        db.save_local(INDEX_PATH)  # Initial save
        print(f"📦 Saved initial index to {INDEX_PATH}")

    remaining_docs = split_docs[num_processed:]

    if not remaining_docs:
        print("🎉 Index is already up to date! Nothing to do.")
        return

    print(
        f"🧠 Embedding {len(remaining_docs)} remaining documents in batches of {BATCH_SIZE}..."
    )

    progress_bar = tqdm(
        range(0, len(remaining_docs), BATCH_SIZE),
        desc="🧠 Embedding Batches",
        unit="batch",
    )

    for i, batch_start in enumerate(progress_bar):
        batch_end = batch_start + BATCH_SIZE
        batch = remaining_docs[batch_start:batch_end]

        if not batch:
            continue

        success = add_batch_with_retry(db, batch)

        if not success:
            print("Stopping script due to persistent embedding failure.")
            print(
                f"Progress so far has been saved. Re-run script to resume from chunk {num_processed}."
            )
            break

        num_processed += len(batch)

        if (i + 1) % SAVE_EVERY_N_BATCHES == 0:
            progress_bar.set_description(f"📦 Saving progress to {INDEX_PATH}...")
            db.save_local(INDEX_PATH)
            progress_bar.set_description("🧠 Embedding Batches")

    print("\n✅ Embedding complete. Saving final index...")
    db.save_local(INDEX_PATH)
    print(f"🎉 Successfully built and saved index to {INDEX_PATH}.")


if __name__ == "__main__":
    main()
