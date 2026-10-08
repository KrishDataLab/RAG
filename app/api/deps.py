from fastapi import Depends
from app.db.repositories import DatabaseRepository, get_db
from app.retrieval.vector_store import MemoryVectorStore
from app.retrieval.retriever import ArchitectureRetriever
from app.llm.client import LLMClient

# Shared singletons for fast response
_vector_store_instance = MemoryVectorStore(load_existing=True)
_llm_client_instance = LLMClient()
_retriever_instance = ArchitectureRetriever(_vector_store_instance)

def get_repo(db=Depends(get_db)) -> DatabaseRepository:
    return DatabaseRepository(db)

def get_vector_store() -> MemoryVectorStore:
    return _vector_store_instance

def get_retriever() -> ArchitectureRetriever:
    return _retriever_instance

def get_llm_client() -> LLMClient:
    return _llm_client_instance
