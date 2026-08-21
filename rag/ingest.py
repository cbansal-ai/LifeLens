from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from langchain_openai import OpenAIEmbeddings
from openai import chat
from langchain_chroma import Chroma
from dotenv import load_dotenv


# Load environment variables (.env)
load_dotenv()

# -------------------------
# Step 1: Load PDF
# -------------------------
loader = PyPDFLoader("rag/documents/insurance.pdf")
documents = loader.load()

print(f"Loaded {len(documents)} page(s)")

# -------------------------
# Step 2: Split into chunks
# -------------------------
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50,
)

chunks = text_splitter.split_documents(documents)

print(f"Created {len(chunks)} chunks")

# -------------------------
# Step 3: Create embeddings
# -------------------------
embeddings = OpenAIEmbeddings()

# -------------------------
# Step 4: Store in ChromaDB
# -------------------------
vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="rag/chroma_db",
)

print("Documents successfully stored in ChromaDB!")


if __name__ == "__main__":

    
    embeddings = OpenAIEmbeddings()

    vectorstore = Chroma(

        persist_directory="rag/chroma_db",

        embedding_function=embeddings,

        )

data = vectorstore.get()

print(data.keys())

for i, doc in enumerate(data["data"]):
    print(f"\nChunk {i+1}")
    print(doc)
    print("-" * 80)
    break