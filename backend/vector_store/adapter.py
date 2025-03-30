from backend.config import settings
from backend.vector_store.models import StoreEngine

if settings.DEFAULT_VECTOR_DB == StoreEngine.LANCE:
    import backend.vector_store.lance_db as vector_store
elif settings.DEFAULT_VECTOR_DB == StoreEngine.CHROMA:
    import backend.vector_store.chroma_db as vector_store
elif settings.DEFAULT_VECTOR_DB == StoreEngine.MILVUS_LITE:
    import backend.vector_store.milvus_db as vector_store


def vector_db():
    return vector_store
