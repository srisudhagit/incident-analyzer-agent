import os
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = chromadb.PersistentClient(path="./chroma_db")

embedding_fn = OpenAIEmbeddingFunction(
    api_key=OPENAI_API_KEY,
    model_name="text-embedding-3-small"
)

runbook_collection = client.get_or_create_collection(
    name="runbooks",
    embedding_function=embedding_fn
)

incident_collection = client.get_or_create_collection(
    name="incident_memory",
    embedding_function=embedding_fn
)