import os
import threading
from functools import lru_cache
from typing import List, Dict

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document


_index_lock = threading.Lock()


def _get_pdf_path() -> str:
    # Expect the PDF to live at the workspace root alongside this repository
    # Name is provided by the user: ecommerce_policy_notice.pdf
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    pdf_path = os.path.join(root_dir, "ecommerce_policy_notice.pdf")
    return pdf_path


def _get_index_dir() -> str:
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
    cache_dir = os.path.join(root_dir, ".rag_cache")
    os.makedirs(cache_dir, exist_ok=True)
    return os.path.join(cache_dir, "policy_pdf_faiss")


def _load_pdf_documents(pdf_path: str) -> List[Document]:
    loader = PyPDFLoader(pdf_path)
    return loader.load()


def _split_documents(documents: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(documents)


def _build_or_load_vectorstore() -> FAISS:
    index_dir = _get_index_dir()
    embeddings = OpenAIEmbeddings()

    # Try load from disk first
    if os.path.isdir(index_dir) and os.listdir(index_dir):
        return FAISS.load_local(index_dir, embeddings, allow_dangerous_deserialization=True)

    pdf_path = _get_pdf_path()
    if not os.path.isfile(pdf_path):
        raise FileNotFoundError(
            f"Policy PDF not found at '{pdf_path}'. Please place the file at this path."
        )

    documents = _load_pdf_documents(pdf_path)
    chunks = _split_documents(documents)
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(index_dir)
    return vectorstore


@lru_cache(maxsize=1)
def _get_vectorstore_cached() -> FAISS:
    # Ensure single build even under concurrency
    with _index_lock:
        return _build_or_load_vectorstore()


def answer_policy_pdf(question: str, k: int = 4) -> Dict:
    """
    Retrieve top-k relevant chunks from the policy PDF and synthesize an answer
    using a simple extractive approach (return snippets + sources). The LLM can
    compose the final answer from these.
    """
    if not question or not isinstance(question, str):
        return {"error": "Please provide a question string."}

    try:
        vectorstore = _get_vectorstore_cached()
        retriever = vectorstore.as_retriever(search_kwargs={"k": max(1, int(k))})
        docs = retriever.get_relevant_documents(question)
        contexts = [d.page_content for d in docs]
        sources = []
        for d in docs:
            meta = d.metadata or {}
            page = meta.get("page")
            source = meta.get("source", "ecommerce_policy_notice.pdf")
            sources.append({"source": source, "page": page})
        # Return contexts; the agent prompt should guide how to compose final answer
        return {"contexts": contexts, "sources": sources}
    except Exception as e:
        return {"error": f"RAG query failed: {str(e)}"}


