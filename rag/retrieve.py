from dotenv import load_dotenv

from langchain.tools import tool

from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from langchain_core.prompts import ChatPromptTemplate

from langchain_classic.chains.combine_documents import (
    create_stuff_documents_chain,
)

from langchain_classic.chains import (
    create_retrieval_chain,
)

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()

# -------------------------
# Embedding model
# -------------------------
embeddings = OpenAIEmbeddings()

# -------------------------
# Load existing ChromaDB
# -------------------------
vectorstore = Chroma(
    persist_directory="rag/chroma_db",
    embedding_function=embeddings,
)

# -------------------------
# Retriever
# -------------------------
retriever = vectorstore.as_retriever(
    search_kwargs={"k": 3}
)

# -------------------------
# LLM
# -------------------------
llm = ChatOpenAI(model="gpt-4.1-mini")

# -------------------------
# Prompt Template
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
# Create Document Chain
# -------------------------
document_chain = create_stuff_documents_chain(
    llm=llm,
    prompt=prompt,
)

# -------------------------
# Create Retrieval Chain
# -------------------------
retrieval_chain = create_retrieval_chain(
    retriever,
    document_chain,
)

# -------------------------
# PDF RAG Tool
# -------------------------
@tool
def     search_documents(question: str) -> str:
    """
    Search uploaded PDFs using RAG and answer the user's question.
    """

    response = retrieval_chain.invoke(
        {
            "input": question
        }
    )

    return response["answer"]


# -------------------------
# Test the Tool
# -------------------------
if __name__ == "__main__":

    answer = search_documents.invoke(
        "What does the insurance policy cover?"
    )

    print("\nAnswer")
    print("-" * 80)
    print(answer)