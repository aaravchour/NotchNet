import os
import faiss  # type: ignore
import requests

from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore
from langchain_community.embeddings import OllamaEmbeddings  # type: ignore
from langchain_community.document_loaders import TextLoader  # type: ignore

# ===========================
# Configuration
# ===========================

DATA_DIR = "data/wiki_pages_cleaned"

FAILING_BATCH_INDEX = 484
BATCH_SIZE = 16

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
            print("🔴 Ollama server responded, but not OK.")
            return False
    except Exception:
        print("❌ Ollama is not running. Please start it with `ollama serve`.")
        return False


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


def main():
    if not check_ollama():
        return

    print("Re-creating document splits to find the poison pill...")
    all_docs = load_documents()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1024, chunk_overlap=150, separators=["\n\n", "\n", ".", " "]
    )
    split_docs = splitter.split_documents(all_docs)
    print(f"✅ Re-split {len(split_docs)} chunks.")

    batch_start = FAILING_BATCH_INDEX * BATCH_SIZE
    batch_end = batch_start + BATCH_SIZE
    bad_batch_docs = split_docs[batch_start:batch_end]

    print(
        f"\n--- 🔬 Testing the {len(bad_batch_docs)} documents in failing batch #{FAILING_BATCH_INDEX} ---"
    )

    embedding_model = OllamaEmbeddings(model="nomic-embed-text:latest")

    for i, doc in enumerate(bad_batch_docs):
        print(f"\n--- 🧪 Testing Document {i+1} / {len(bad_batch_docs)} ---")
        print(f"Source: {doc.metadata.get('source', 'Unknown')}")
        print(f"Snippet: {doc.page_content[:400].strip()}...")

        try:
            embedding_model.embed_query(doc.page_content)
            print("✅ ... Success. This document is OK.")

        except Exception as e:
            if "EOF" in str(e) or "500" in str(e):
                print(
                    "\n\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
                )
                print(f"🚨 FOUND IT! This is the poison pill document. 🚨")
                print(f"The server crashed while processing this document.")
                print(f"Source File: {doc.metadata.get('source', 'Unknown')}")
                print("\nTo fix this, go to your 'data/wiki_pages_cleaned' folder and")
                print(f"DELETE THE FILE: {doc.metadata.get('source', 'Unknown')}")
                print("After deleting it, you can safely run `build_index.py` again.")
                print(
                    "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n\n"
                )
                return
            else:
                print(f"⚠️ An unexpected error occurred: {e}")

    print("\n--- ✅ All documents in this batch were processed successfully. ---")
    print("This is strange. If you see this, the error might be intermittent.")
    print("Try re-running `build_index.py`.")


if __name__ == "__main__":
    main()
