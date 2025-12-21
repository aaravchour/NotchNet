import os
import shutil
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OllamaEmbeddings
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
    documents = loader.load()
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
    print(f"🧠 Initializing embeddings (Ollama: mxbai-embed-large)...")
    embeddings = OllamaEmbeddings(
        model="mxbai-embed-large",
        base_url=config.OLLAMA_HOST
    )

    # 5. Build and save FAISS index
    print("🏗️ Building FAISS index (this may take a while)...")
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    print(f"💾 Saving index to '{index_path}'...")
    if os.path.exists(index_path):
        shutil.rmtree(index_path)
    
    vector_store.save_local(index_path)
    print("🎉 FAISS index built and saved successfully!")

if __name__ == "__main__":
    build_index()
