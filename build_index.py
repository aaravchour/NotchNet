import os
import time
import faiss  # type: ignore
import requests  # type:ignore
from tqdm import tqdm  # type: ignore

from langchain_text_splitters import RecursiveCharacterTextSplitter  # type: ignore
from langchain_community.vectorstores import FAISS  # type: ignore
from langchain_community.document_loaders import TextLoader  # type: ignore
from langchain_community.embeddings import OllamaEmbeddings  # type: ignore

import config

# ===========================
# Configuration
# ===========================

DATA_DIR = config.DATA_DIR_CLEANED
INDEX_PATH = config.INDEX_PATH

NUM_CORES = os.cpu_count() or 8
os.environ["OLLAMA_NUM_THREADS"] = str(NUM_CORES)
faiss.omp_set_num_threads(NUM_CORES)

BATCH_SIZE = 16
SAVE_EVERY_N_BATCHES = 20

# ===========================
# Helper Functions
# ===========================


def check_ollama():
    try:
        r = requests.get(config.OLLAMA_HOST)
        if r.status_code == 200:
            print("🟢 Ollama server is running.")
            return True
        else:
            raise RuntimeError("Ollama server responded, but not OK.")
    except Exception as e:
        print(f"❌ Ollama is not running at {config.OLLAMA_HOST}. Please start it with `ollama serve`.")
        raise e


def load_documents(data_dir=DATA_DIR):
    docs = []
    print(f"📚 Loading documents from {data_dir}...")
    for root, _, files in os.walk(data_dir):
        for file in files:
            if file.endswith(".txt"):
                full_path = os.path.join(root, file)
                loader = TextLoader(full_path, encoding="utf-8")
                loaded = loader.load()
                for doc in loaded:
                    relative_path = os.path.relpath(full_path, data_dir)
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
                check_ollama()
            else:
                raise e
    print(f"\n❌ Failed to embed batch after {max_retries} attempts. Stopping.")
    return False


def build_index(data_dir=DATA_DIR, index_path=INDEX_PATH, force_rebuild=False):
    check_ollama()

    all_docs = load_documents(data_dir)
    if not all_docs:
        print("❌ No documents loaded from summaries!")
        return # return instead of raise for programmatic safety

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024, chunk_overlap=150, separators=["\n\n", "\n", ".", " "]
    )
    split_docs = splitter.split_documents(all_docs)
    print(f"✅ Split documents into {len(split_docs)} chunks.")

    embedding_model = OllamaEmbeddings(model="mxbai-embed-large", base_url=config.OLLAMA_HOST)

    num_processed = 0
    db = None

    if os.path.exists(index_path) and not force_rebuild:
        print("🔁 Found existing FAISS index. Loading to resume...")
        try:
            db = FAISS.load_local(
                index_path, embedding_model, allow_dangerous_deserialization=True
            )
            num_processed = len(db.index_to_docstore_id)
            print(f"✅ Resuming from document chunk {num_processed} / {len(split_docs)}")
        except Exception:
             print("⚠️ Existing index corrupted or incompatible. Rebuilding...")
             force_rebuild = True

    if not db or force_rebuild:
        print("✨ Creating a new index...")
        if not split_docs:
            print("No documents to index.")
            return

        first_batch = split_docs[:BATCH_SIZE]
        db = FAISS.from_documents(first_batch, embedding_model)
        num_processed = len(first_batch)
        print("✅ Created index with first batch.")
        db.save_local(index_path)
        print(f"📦 Saved initial index to {index_path}")

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
            progress_bar.set_description(f"📦 Saving progress to {index_path}...")
            db.save_local(index_path)
            progress_bar.set_description("🧠 Embedding Batches")

    print("\n✅ Embedding complete. Saving final index...")
    db.save_local(index_path)
    print(f"🎉 Successfully built and saved index to {index_path}.")


if __name__ == "__main__":
    build_index()
