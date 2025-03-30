import enum


class StoreEngine(str, enum.Enum):
    CHROMA = "chroma_db"
    LANCE = "lance_db"
    MILVUS_LITE = "milvus_lite_db"
