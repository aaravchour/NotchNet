import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
from tqdm import tqdm
import config

def build_index():
    print("🚀 Starting FAISS index build...")
    
    # 1. Setup paths
    source_dir = config.DATA_DIR_CLEANED
    index_path = config.INDEX_PATH
    
    if not os.path.exists(source_dir):
        print(f"❌ Error: Source directory '{source_dir}' does not exist.")
        return

    # 2. Load documents
    print(f"📂 Loading documents from '{source_dir}'...")
    loader = DirectoryLoader(
        source_dir,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    
    # Use tqdm for loading progress
    documents = []
    
    # Count files to show an accurate progress bar
    import glob
    file_list = glob.glob(os.path.join(source_dir, "**/*.txt"), recursive=True)
    total_files = len(file_list)
    
    for doc in tqdm(loader.lazy_load(), total=total_files, desc="Loading"):
        documents.append(doc)
        
    print(f"✅ Loaded {len(documents)} documents.")

    # 3. Split documents
    print("✂️ Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len,
        is_separator_regex=False,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"✅ Created {len(chunks)} chunks.")

    # 4. Initialize embeddings
    print(f"🧠 Initializing embeddings (Ollama: nomic-embed-text)...")
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=config.OLLAMA_HOST
    )

    # 5. Build and save FAISS index
    print("🏗️ Building FAISS index (this may take a while)...")
    
    BATCH_SIZE = 100
    vector_store = None
    
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), desc="Indexing"):
        batch = chunks[i : i + BATCH_SIZE]
        if vector_store is None:
            vector_store = FAISS.from_documents(batch, embeddings)
        else:
            vector_store.add_documents(batch)
    
    print(f"💾 Saving index to '{index_path}'...")
    if os.path.exists(index_path) and vector_store is not None:
        shutil.rmtree(index_path)
    
    if vector_store is not None:
        vector_store.save_local(index_path)
        print("🎉 FAISS index built and saved successfully!")
    else:
        print("⚠️ No documents were indexed.")

if __name__ == "__main__":
    build_index()
