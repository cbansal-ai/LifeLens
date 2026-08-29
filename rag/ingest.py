from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
CHROMA_DIR = BASE_DIR / "chroma_db"
DOCUMENTS_DIR = BASE_DIR / "documents"


def index_pdf(file_path):
    """Load one PDF, split it into chunks, and add it to the LifeLens Chroma index."""
    path = Path(file_path)
    loader = PyPDFLoader(str(path))
    documents = loader.load()

    for document in documents:
        document.metadata["source"] = path.name
        

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = text_splitter.split_documents(documents)

    embeddings = OpenAIEmbeddings()
    vectorstore = Chroma(
        persist_directory=str(CHROMA_DIR),
        embedding_function=embeddings,
    )
    vectorstore.add_documents(chunks)

    return {
        "pages": len(documents),
        "chunks": len(chunks),
        "filename": path.name,
    }


if __name__ == "__main__":
    default_pdf = DOCUMENTS_DIR / "insurance.pdf"
    if not default_pdf.exists():
        raise FileNotFoundError(f"PDF not found: {default_pdf}")

    result = index_pdf(default_pdf)
    print(
        f"Indexed {result['filename']}: "
        f"{result['pages']} page(s), {result['chunks']} chunks"
    )
