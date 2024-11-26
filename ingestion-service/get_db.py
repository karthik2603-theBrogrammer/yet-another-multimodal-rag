import time
import sys
from pinecone import Pinecone, ServerlessSpec
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.retrievers.multi_vector import MultiVectorRetriever
from langchain.storage import InMemoryStore


from logger import logger


def get_retriever(pinecone_api_key, index_name="test-medico-rag"):
    """Set up Pinecone index and retriever."""
    pc = Pinecone(api_key=pinecone_api_key)

    existing_indexes = [index_info["name"] for index_info in pc.list_indexes()]
    if index_name not in existing_indexes:
        pc.create_index(
            name=index_name,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    
    # Wait until the index is ready
    while not pc.describe_index(index_name).status["ready"]:
        time.sleep(1)

    index = pc.Index(index_name)
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")

    vector_store = PineconeVectorStore(index=index, embedding=embeddings)
    doc_store = InMemoryStore()

    return MultiVectorRetriever(
        vectorstore=vector_store,
        docstore=doc_store,
        id_key="doc_id",
        search_kwargs={"k": 3},
    )