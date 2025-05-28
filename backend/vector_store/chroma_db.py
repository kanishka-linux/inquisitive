from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document
from backend.config import settings
from backend.core.logging import get_logger
from backend.core.utils import (
    extract_text_from_pdf,
    is_file_pdf,
    read_text_file_content,
    chunk_pdf_content,
    chunk_non_pdf_content,
    chunk_link_content
)
from backend.api.models import SourceType

logger = get_logger()

# Initialize embeddings
embeddings = OllamaEmbeddings(
    model=settings.EMBEDDINGS_MODEL, base_url=settings.OLLAMA_HOST)
persist_directory = settings.CHROMA_VECTOR_STORE_PERSISTS_DIRECTORY

# Initialize Chroma vector store
vector_store = Chroma(
    embedding_function=embeddings,
    persist_directory=persist_directory
)


def add_link_content_to_vector_store(
        text_content, source, title, link_id, username):

    texts = chunk_link_content(text_content)

    documents = [
        Document(
            page_content=f"{title}\n\n{text}",
            metadata={
                "source": source,
                "page": f"{i+1}",
                "title": title,
                "belongs_to": username,
                "link_id": f"{link_id}",
                "source_type": SourceType.LINK
            }
        ) for i, text in enumerate(texts)
    ]

    vector_store.add_documents(documents=documents)
    logger.info(f"processed: {source} with {title}")


def add_uploaded_document_content_to_vector_store(
        file_path, file_name, file_url, file_id, username):

    texts = []
    if is_file_pdf(file_path):
        text_content_list = extract_text_from_pdf(file_path)
        texts = chunk_pdf_content(text_content_list)

    else:
        text_content = read_text_file_content(file_path)
        texts = chunk_non_pdf_content(text_content)

    if file_name.endswith('.md'):
        source_type = SourceType.NOTE
    else:
        source_type = SourceType.FILE

    documents = [
        Document(
            page_content=content_dict['text'],
            metadata={
                "source": file_url,
                "page": f"{content_dict['page_number']}",
                "filename": file_name,
                "belongs_to": username,
                "file_id": f"{file_id}",
                "source_type": source_type
            }
        ) for content_dict in texts
    ]

    vector_store.add_documents(documents=documents)
    logger.info(f"processed: {file_name} with id={file_id}")


def fetch_documents(
        include_selected,
        exclude_selected,
        window_size,
        username,
        prompt,
        source_type=None):

    if source_type == 'link':
        window_size_modified = window_size * settings.WINDOW_SIZE_MULTIPLIER
    else:
        window_size_modified = window_size

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

    if source_type is not None:
        conditions = filter_dict.get("$and")
        if conditions and isinstance(conditions, list):
            # It means there are existing conditions
            # and we need to just append new condition
            # to existing one
            conditions.append({"source_type": {"$in": [source_type]}})
            filter_dict["$and"] = conditions.copy()
        else:
            filter_dict = {
                "$and": [
                    {"source_type": {"$in": [source_type]}},
                    {"belongs_to": {"$in": [username]}}
                ]
            }

    docs = vector_store.similarity_search_with_relevance_scores(
        prompt,
        filter=filter_dict,
        k=window_size_modified  # Retrieve more relevant chunks
    )

    # TODO: Add mmr search later
    # retriever = vector_store.as_retriever(
    #    search_type="mmr",  # Maximum Marginal Relevance
    #    search_kwargs={
    #        "k": window_size,  # Number of documents to return
    #        "fetch_k": 20,  # Fetch more documents initially for diversity
    #        "lambda_mult": 0.5,  # Balance between relevance and diversity
    #        "filter": filter_dict  # Metadata filter
    #    }
    # )
    # docs = retriever.get_relevant_documents(prompt)
    return docs


def remove_documents(filename, username):
    try:
        filter_dict = {
            "$and": [
                {"filename": {"$eq": filename}},
                {"belongs_to": {"$eq": username}}
            ]
        }

        # Access the underlying Chroma collection
        # Use the get method with the where parameter
        matching_docs = vector_store._collection.get(where=filter_dict)
        if matching_docs and len(matching_docs['ids']) > 0:
            # Delete the documents using their IDs
            vector_store.delete(ids=matching_docs['ids'])
            logger.info(
                f"Removed documents with filename={filename} belonging to user={username}")
            return True
        else:
            logger.warning(
                f"No documents found with filename={filename} belonging to user={username}")
            return False

    except Exception as err:
        logger.error(
            f"Error removing documents with filename={filename}: {str(err)}")
        return False


def remove_link_documents(link_id, username):
    try:
        filter_dict = {
            "$and": [
                {"link_id": {"$eq": f"{link_id}"}},
                {"belongs_to": {"$eq": username}}
            ]
        }

        # Access the underlying Chroma collection
        # Use the get method with the where parameter
        matching_docs = vector_store._collection.get(where=filter_dict)
        if matching_docs and len(matching_docs['ids']) > 0:
            # Delete the documents using their IDs
            vector_store.delete(ids=matching_docs['ids'])
            logger.info(
                f"Removed documents with link_id={link_id} belonging to user={username}")
            return True
        else:
            logger.warning(
                f"No documents found with link_id={link_id} belonging to user={username}")
            return False

    except Exception as err:
        logger.error(
            f"Error removing documents with link_id={link_id}: {str(err)}")
        return False
