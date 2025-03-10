from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from backend.config import settings
from backend.core.logging import get_logger
from backend.core.utils import extract_text_from_pdf, is_file_pdf, read_text_file_content

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

    vector_store.add_documents(documents=documents)
    logger.info(f"processed: {source} with {title}")


def add_uploaded_document_content_to_vector_store(
        file_path, file_name, file_url, file_id, username):

    if is_file_pdf(file_path):
        text_content = extract_text_from_pdf(file_path)
    else:
        text_content = read_text_file_content(file_path)

    texts = text_splitter.split_text(text_content)

    documents = [
        Document(
            page_content=text,
            metadata={
                "source": file_url,
                "page": f"{i}",
                "filename": file_name,
                "belongs_to": username,
                "file_id": f"{file_id}"
            }
        ) for i, text in enumerate(texts)
    ]

    vector_store.add_documents(documents=documents)
    logger.info(f"processed: {file_name} with id={file_id}")


def fetch_documents(include_selected, exclude_selected, window_size, username, prompt):

    filter_dict = {}
    if exclude_selected and include_selected:
        filter_dict = {
            "$and": [
                # Exclude these sources
                {"source": {"$nin": exclude_selected}},
                # Include these sources
                {"source": {"$in": include_selected}},
                # Include souces belonging to current users only
                {"belongs_to": {"$in": [username]}}

            ]
        }
    elif exclude_selected:
        filter_dict = {
            "$and": [
                {"source": {"$nin": exclude_selected}},
                {"belongs_to": {"$in": [username]}}

            ]
        }
    elif include_selected:
        filter_dict = {
            "$and": [
                {"source": {"$in": include_selected}},
                {"belongs_to": {"$in": [username]}}

            ]
        }
    else:
        filter_dict = {
            "belongs_to": {"$in": [username]}
        }

    docs = vector_store.similarity_search_with_relevance_scores(
        prompt,
        filter=filter_dict,
        k=window_size  # Retrieve more relevant chunks
    )

    return docs
