from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"

embeddings = OpenAIEmbeddings()

vectorstore = Chroma(
    persist_directory=str(CHROMA_DIR),
    embedding_function=embeddings,
)

llm = ChatOpenAI(model="gpt-4.1-mini", temperature=0)

prompt = ChatPromptTemplate.from_template("""
You are a helpful assistant.

Answer the user's question using ONLY the provided context.

If the answer cannot be found in the context, reply:
"I don't have enough information to answer."

Context:
{context}

Question:
{input}
""")

document_chain = create_stuff_documents_chain(llm=llm, prompt=prompt)


def search_documents_with_details(question: str, user_id: str, k: int = 3) -> dict[str, Any]:
    """Run user-scoped RAG and expose contexts/metadata for evaluation."""
    user_id = (user_id or "").strip().lower()
    question = (question or "").strip()

    if not user_id:
        return {
            "answer": "An active LifeLens user is required to search documents.",
            "contexts": [],
            "metadata": [],
        }

    if not question:
        return {"answer": "Question cannot be empty.", "contexts": [], "metadata": []}

    retriever = vectorstore.as_retriever(
        search_kwargs={"k": k, "filter": {"user_id": user_id}}
    )
    docs = retriever.invoke(question)

    if not docs:
        return {
            "answer": "I don't have enough information to answer.",
            "contexts": [],
            "metadata": [],
        }

    answer = document_chain.invoke({"input": question, "context": docs})

    return {
        "answer": answer or "I don't have enough information to answer.",
        "contexts": [doc.page_content for doc in docs],
        "metadata": [doc.metadata for doc in docs],
    }


@tool
def search_documents(question: str, user_id: str) -> str:
    """Search only uploaded PDFs belonging to the specified LifeLens user."""
    return search_documents_with_details(question=question, user_id=user_id)["answer"]
