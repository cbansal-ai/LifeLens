from langchain_chroma import Chroma

from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

# -------------------------
# Load environment variables
# -------------------------
load_dotenv()


embeddings = OpenAIEmbeddings()

vectorstore = Chroma(

    persist_directory="rag/chroma_db",

    embedding_function=embeddings,

)

data = vectorstore.get()


print("ids  \n " + str(data["ids"]))

print(" len(data[documents]): " + str(len(data["documents"])))
for i in range(len(data["documents"])):

    print("ID:", data["ids"][i])

    print("Document:", data["documents"][i])

    print("Metadata:", data["metadatas"][i])

    print("-" * 50)