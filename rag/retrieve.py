from pathlib import Path

from dotenv import load_dotenv
from langchain.tools import tool
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_classic.chains import create_retrieval_chain

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"

# -------------------------
# Embeddings + ChromaDB
# -------------------------
embeddings = OpenAIEmbeddings()

vectorstore = Chroma(
    persist_directory=str(CHROMA_DIR),
    embedding_function=embeddings,
)

# -------------------------
# LLM
# -------------------------
llm = ChatOpenAI(model="gpt-4.1-mini")

# -------------------------
# Prompt
# -------------------------
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

# -------------------------
# Document Chain
# -------------------------
document_chain = create_stuff_documents_chain(
    llm=llm,
    prompt=prompt,
)


# -------------------------
# PDF RAG Tool
# -------------------------
@tool
def search_documents(question: str, user_id: str) -> str:
    """Search only the uploaded PDFs belonging to the specified LifeLens user."""
    user_id = user_id.strip().lower()

    if not user_id:
        return "An active LifeLens user is required to search documents."

    # Build a user-scoped retriever for every request.
    retriever = vectorstore.as_retriever(
        search_kwargs={
            "k": 3,
            "filter": {"user_id": user_id},
        }
    )

    retrieval_chain = create_retrieval_chain(
        retriever,
        document_chain,
    )

    response = retrieval_chain.invoke(
        {"input": question}
    )

    answer = response.get("answer")
    if not answer:
        return "I couldn't find an answer in the uploaded documents."

    return answer


if __name__ == "__main__":
    print(
        search_documents.invoke(
            {
                "question": "What hotel was booked in Paris?",
                "user_id": "example@gmail.com",
            }
        )
    )
