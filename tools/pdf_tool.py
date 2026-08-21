from langchain.tools import tool
from rag.retrieve import retrieval_chain
import logging

@tool
def search_documents(question: str) -> str:
    """Search indexed documents using RAG and answer the user's question."""
    logging.info("PDF Tool selected")
    try:
        response = retrieval_chain.invoke({"input": question})
        return response["answer"]
    except Exception:
        return "Sorry, I couldn't access the documents right now."
