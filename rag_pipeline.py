import os
import faiss  # type: ignore
import requests  # type: ignore

from langchain_community.vectorstores import FAISS  # type: ignore
from langchain_classic.chains import create_retrieval_chain  # type: ignore
from langchain_classic.chains.combine_documents import create_stuff_documents_chain  # type: ignore
from langchain_core.prompts import PromptTemplate  # type: ignore
from langchain_community.embeddings import OllamaEmbeddings  # type: ignore
from langchain_community.chat_models import ChatOllama  # type: ignore

import config

# ===========================
# Configuration
# ===========================

INDEX_PATH = config.INDEX_PATH
qa_chain = None

NUM_CORES = os.cpu_count()
os.environ["OLLAMA_NUM_THREADS"] = str(NUM_CORES)
faiss.omp_set_num_threads(NUM_CORES)


QA_PROMPT = PromptTemplate(
    input_variables=["context", "input"],
    template="""
- You are a Minecraft knowledge companion. Your primary rule is: ABSOLUTELY NO HALLUCINATIONS.
- DO NOT guess or provide information not explicitly present in the provided context.
- If the context contains a section header (like "Crafting") but NO content follow it, DO NOT assume the feature doesn't exist. Instead, say "I couldn't find the crafting recipe in my current records."
- DO NOT say "Shields can't be crafted" unless the context specifically states "Shields cannot be crafted".
- Answer as if speaking to a fellow Minecraft player, with a friendly and informative tone.
- Use the context strictly and exclusively for the answer.
- If you don't know the answer or the context doesn't provide enough information, simply say "I'm sorry, I don't have the specific details for that in my memory right now."
- Avoid mentioning mods, plugins, or real-world references unless they are in the context.
- Do not include introductions like "According to the context" or "Based on my logs".
- If asked who you are, say "I am NotchNet, your Minecraft knowledge companion."

Context:
{context}

Question: {input}
Answer:""",
)


# ===========================
# Helper Functions
# ===========================


def check_ollama():
    try:
        r = requests.get(config.OLLAMA_HOST)
        if r.status_code == 200:
            print("🟢 Ollama server is running.")
        else:
            print("🔴 Ollama server responded, but not OK.")
    except Exception as e:
        raise RuntimeError(
            f"❌ Ollama is not running at {config.OLLAMA_HOST}. Please start it with `ollama serve`."
        ) from e


def build_retriever():
    """
    Builds a retriever by loading the pre-built FAISS index from disk.
    """
    check_ollama()

    embedding_model = OllamaEmbeddings(model="mxbai-embed-large", base_url=config.OLLAMA_HOST)

    if not os.path.exists(INDEX_PATH):
        print(f"❌ FATAL: FAISS index not found at {INDEX_PATH}")
        print("Please run the `build_index.py` script first to create the index.")
        raise FileNotFoundError(f"FAISS index not found. Run `build_index.py` first.")

    try:
        db = FAISS.load_local(
            INDEX_PATH, embedding_model, allow_dangerous_deserialization=True
        )
        print(f"🔁 Loaded cached FAISS index from {INDEX_PATH}.")
        return db.as_retriever()
    except Exception as e:
        print(f"❌ Error loading FAISS index: {e}")
        print(
            "The index might be corrupted. Try deleting the 'faiss_index' directory and re-running `build_index.py`."
        )
        raise e


def build_qa_chain():
    global qa_chain
    if qa_chain is not None:
        return qa_chain

    retriever = build_retriever()

    print(f"🔧 Loading local LLM ({config.LLM_MODEL})...")
    llm_model = ChatOllama(model=config.LLM_MODEL, base_url=config.OLLAMA_HOST)
    print("✅ LLM loaded.")

    print("🔧 Building new LCEL retrieval chain...")
    document_chain = create_stuff_documents_chain(llm_model, QA_PROMPT)
    qa_chain = create_retrieval_chain(retriever, document_chain)

    print("✅ QA chain built successfully.")
    return qa_chain


def reload_qa_chain():
    """Forces a reload of the QA chain, useful after index updates."""
    global qa_chain
    print("🔄 Reloading QA chain...")
    qa_chain = None
    build_qa_chain()
    print("✅ QA chain reloaded.")


def generate_answer(question: str) -> str:
    global qa_chain
    if qa_chain is None:
        print("🔧 Building QA chain for the first time...")
        qa_chain = build_qa_chain()

    try:
        result = qa_chain.invoke({"input": question})
        answer = result.get("answer", "").strip()
        sources = result.get("context", [])

        if not answer:
            return "❌ Sorry, I couldn't find a good answer to your question."

        formatted_sources = []
        for doc in sources:
            source_name = doc.metadata.get("source", "Unknown")
            filename = os.path.basename(source_name)
            formatted_sources.append(f"- {filename}")

        print(f"\n💬 Answer: {answer}\n")
        if formatted_sources:
            print("📚 Sources:")
            for src in formatted_sources:
                print(src)

        return f"{answer}\n"

    except Exception as e:
        print(f"⚠️ Error while generating answer: {e}")
        raise e
