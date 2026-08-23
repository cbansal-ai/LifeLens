from langchain.tools import tool
from rag.retrieve import retrieval_chain, vectorstore
import logging


@tool
def search_documents(question: str) -> str:
    """
    Search PDFs that have already been indexed in LifeLens ChromaDB.

    The PDFs are indexed by rag/ingest.py and stored in rag/chroma_db.
    This tool retrieves the most relevant document chunks and then uses
    the existing RAG retrieval chain to generate the answer.
    """
    logging.info("PDF Tool selected")

    try:
        # First verify that indexed document chunks are available.
        matches = vectorstore.similarity_search(question, k=3)

        if not matches:
            logging.info("No indexed PDF chunks found")
            return (
                "I couldn't find any relevant information in the uploaded documents. "
                "Please upload and index a PDF first."
            )

        # Use the existing RAG pipeline in rag/retrieve.py.
        response = retrieval_chain.invoke({"input": question})
        answer = response.get("answer")

        if not answer:
            return "I couldn't find an answer in the uploaded documents."

        # Include source filenames when metadata is available.
        sources = sorted(
            {
                doc.metadata.get("source")
                for doc in matches
                if doc.metadata.get("source")
            }
        )

        if sources:
            return f"{answer}\n\nSource: {', '.join(sources)}"

        return answer

    except Exception as exc:
        logging.exception("PDF document search failed: %s", exc)
        return "Sorry, I couldn't access the uploaded documents right now."
