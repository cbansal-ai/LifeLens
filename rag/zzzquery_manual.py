from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

# Embeddings
embeddings = OpenAIEmbeddings()

# Open Vector DB
vectorstore = Chroma(
    persist_directory="rag/chroma_db",
    embedding_function=embeddings,
)

# Retriever
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

question = "What does the insurance policy cover?"

docs = retriever.invoke(question)

# Combine retrieved chunks
context = "\n\n".join(doc.page_content for doc in docs)

# Prompt
prompt = f"""
You are an insurance assistant.

Use ONLY the information below to answer.

Context:
{context}

Question:
{question}
"""

# LLM
llm = ChatOpenAI(model="gpt-4.1-mini")

response = llm.invoke(prompt)

print(response.content)