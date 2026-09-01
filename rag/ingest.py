from pathlib import Path
import hashlib

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"
DOCUMENTS_DIR = BASE_DIR / "documents"


def calculate_file_hash(file_path):
    """Create a SHA-256 hash from the entire PDF file."""
    sha256 = hashlib.sha256()

    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(4096), b""):
            sha256.update(block)

    return sha256.hexdigest()


def index_pdf(file_path, user_id):
    """Index a PDF into ChromaDB for one authenticated LifeLens user."""
    path = Path(file_path)
    user_id = user_id.strip().lower()

    if not user_id:
        raise ValueError("user_id is required to index a PDF.")

    # 1. Calculate file-level hash
    file_hash = calculate_file_hash(path)

    # 2. Connect to ChromaDB
    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )

    # 3. Duplicate check is scoped to this user
    existing = vectorstore.get(
        where={
            "$and": [
                {"user_id": user_id},
                {"file_hash": file_hash},
            ]
        }
    )

    if existing["ids"]:
        return {
            "filename": path.name,
            "user_id": user_id,
            "file_hash": file_hash,
            "duplicate": True,
            "message": "Duplicate File, This PDF is already indexed for this user.",
        }

    # 4. Load PDF (typically one LangChain Document per page)
    loader = PyPDFLoader(str(path))
    documents = loader.load()

    # 5. Add document-level metadata
    for document in documents:
        document.metadata["source"] = path.name
        document.metadata["file_hash"] = file_hash
        document.metadata["user_id"] = user_id

    # 6. Split into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = text_splitter.split_documents(documents)

    # 7. Add chunk metadata and stable IDs
    chunk_ids = []

    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_index"] = i

        chunk_id = hashlib.sha256(
            f"{user_id}-{file_hash}-{i}".encode()
        ).hexdigest()

        chunk.metadata["chunk_id"] = chunk_id
        chunk_ids.append(chunk_id)

    # 8. Store text + vectors + metadata in ChromaDB
    vectorstore.add_documents(
        documents=chunks,
        ids=chunk_ids,
    )

    return {
        "pages": len(documents),
        "chunks": len(chunks),
        "filename": path.name,
        "file_hash": file_hash,
        "user_id": user_id,
        "duplicate": False,
        "message": "PDF uploaded and indexed successfully.",
    }


if __name__ == "__main__":
    default_pdf = DOCUMENTS_DIR / "05_Auto_Service_Record.pdf"
    user_id = "example@gmail.com"

    if not default_pdf.exists():
        raise FileNotFoundError(f"PDF not found: {default_pdf}")

    result = index_pdf(default_pdf, user_id=user_id)
    print(result["message"])
