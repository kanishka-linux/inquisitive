from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from backend.config import settings
from backend.core.logging import get_logger

logger = get_logger()

# Initialize embeddings
embeddings = OllamaEmbeddings(model=settings.EMBEDDINGS_MODEL)
persist_directory = settings.VECTOR_STORE_PERSISTS_DIRECTORY

# Initialize Chroma vector store
vector_store = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=512,
    chunk_overlap=50,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)


def add_link_content_to_vector_store(
        text_content, source, title, link_id, username):

    texts = text_splitter.split_text(text_content)

    documents = [
        Document(
            page_content=f"{title}\n\n{text}",
            metadata={
                "source": source,
                "page": f"{i}",
                "title": title,
                "belongs_to": username,
                "link_id": f"{link_id}"
            }
        ) for i, text in enumerate(texts)
    ]

    Chroma.from_documents(
        embedding=embeddings,
        documents=documents,
        persist_directory=persist_directory
    )

    logger.info(f"processed: {source} with {title}")
