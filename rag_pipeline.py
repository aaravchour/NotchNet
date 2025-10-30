import os
import faiss  # type: ignore
import requests  # type: ignore

from langchain_community.vectorstores import FAISS  # type: ignore
from langchain.chains import create_retrieval_chain  # type: ignore
from langchain.chains.combine_documents import create_stuff_documents_chain  # type: ignore
from langchain_core.prompts import PromptTemplate  # type: ignore
from langchain_community.embeddings import OllamaEmbeddings  # type: ignore
from langchain_community.chat_models import ChatOllama  # type: ignore

# ===========================
# Configuration
# ===========================

INDEX_PATH = "faiss_index"
qa_chain = None

NUM_CORES = os.cpu_count()
os.environ["OLLAMA_NUM_THREADS"] = str(NUM_CORES)
faiss.omp_set_num_threads(NUM_CORES)


QA_PROMPT = PromptTemplate(
    input_variables=["context", "input"],
    template="""
- Do not guess or provide information not explicitly present in the context.
- Do not ask the user for more information, clarification, or questions.
- If the answer is not found in the context, respond exactly: "I don't know."
- Answer as if speaking to a fellow Minecraft player, with a friendly and informative tone.
- If the question is about crafting or making items, respond only with: "Please use /notchnet recipe <item_name> to see the recipe."
- Avoid mentioning mods, plugins, or any content outside vanilla Minecraft.
- Do not include real-world references or personal opinions.
- Answer concisely and directly, without restating the question or adding unnecessary introductions.
- Use the context strictly and exclusively for the answer.
- If the questions requires multiple steps or complex reasoning, break it down into simple, clear steps.
- Don't reply with just one sentence; provide a complete answer based on the context.

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
        r = requests.get("http://localhost:11434")
        if r.status_code == 200:
            print("🟢 Ollama server is running.")
        else:
            print("🔴 Ollama server responded, but not OK.")
    except Exception as e:
        raise RuntimeError(
            "❌ Ollama is not running. Please start it with `ollama serve` or `ollama run <model>`."
        ) from e


def build_retriever():
    """
    Builds a retriever by loading the pre-built FAISS index from disk.
    """
    check_ollama()

    embedding_model = OllamaEmbeddings(model="mxbai-embed-large")

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

    print("🔧 Loading local LLM...")
    llm_model = ChatOllama(model="deepseek-v3.1:671b-cloud")
    print("✅ LLM loaded.")

    print("🔧 Building new LCEL retrieval chain...")
    document_chain = create_stuff_documents_chain(llm_model, QA_PROMPT)
    qa_chain = create_retrieval_chain(retriever, document_chain)

    print("✅ QA chain built successfully.")
    return qa_chain


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
