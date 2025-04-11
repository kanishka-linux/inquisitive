from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document
from pymilvus import MilvusClient, DataType
import json
import uuid
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
embeddings = OllamaEmbeddings(model=settings.EMBEDDINGS_MODEL)

db_path = settings.MILVUS_VECTOR_STORE_URL

# Initialize Milvus client
milvus_client = MilvusClient("./milvus_data.db")

# Define collection name
COLLECTION_NAME = settings.VECTOR_STORE_COLLECTION_NAME


# Create collection if it doesn't exist
def initialize_collection():
    if not milvus_client.has_collection(COLLECTION_NAME):
        # Create schema
        schema = MilvusClient.create_schema(
            auto_id=False,
            enable_dynamic_field=False,
        )

        # Add fields to schema
        schema.add_field(field_name="id", datatype=DataType.VARCHAR,
                         is_primary=True, max_length=100)
        schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR,
                         dim=settings.EMBEDDINGS_DIMENSION)
        schema.add_field(field_name="page_content",
                         datatype=DataType.VARCHAR, max_length=10000)
        schema.add_field(field_name="source",
                         datatype=DataType.VARCHAR, max_length=500)
        schema.add_field(field_name="page",
                         datatype=DataType.VARCHAR, max_length=50)
        schema.add_field(field_name="title",
                         datatype=DataType.VARCHAR, max_length=500,
                         nullable=True)
        schema.add_field(field_name="filename",
                         datatype=DataType.VARCHAR, max_length=500,
                         nullable=True)
        schema.add_field(field_name="belongs_to",
                         datatype=DataType.VARCHAR, max_length=100)
        schema.add_field(field_name="link_id",
                         datatype=DataType.VARCHAR, max_length=100,
                         nullable=True)
        schema.add_field(field_name="file_id",
                         datatype=DataType.VARCHAR, max_length=100,
                         nullable=True)
        schema.add_field(field_name="source_type",
                         datatype=DataType.VARCHAR, max_length=50)

        # Create collection
        milvus_client.create_collection(
            collection_name=COLLECTION_NAME,
            schema=schema
        )

        # Create vector index separately with proper dictionary format
        milvus_client.create_index(
            collection_name=COLLECTION_NAME,
            field_name="vector",
            index_params={}
        )

        # Create index on metadata fields for efficient filtering
        milvus_client.create_index(
            collection_name=COLLECTION_NAME,
            field_name="belongs_to",
            index_name="idx_belongs_to",
            index_params={}
        )
        milvus_client.create_index(
            collection_name=COLLECTION_NAME,
            field_name="source_type",
            index_name="idx_source_type",
            index_params={}
        )
        milvus_client.create_index(
            collection_name=COLLECTION_NAME,
            field_name="source",
            index_name="idx_source",
            index_params={}
        )
        milvus_client.create_index(
            collection_name=COLLECTION_NAME,
            field_name="filename",
            index_name="idx_filename",
            index_params={}
        )

        logger.info(f"Created new Milvus collection: {COLLECTION_NAME}")
    else:
        logger.info(f"Using existing Milvus collection: {COLLECTION_NAME}")


# Initialize collection
initialize_collection()


def add_documents(documents):
    """Add documents to the Milvus vector store"""
    if not documents:
        return

    # Generate embeddings for documents
    texts = [doc.page_content for doc in documents]
    embeddings_list = embeddings.embed_documents(texts)

    # Prepare data for Milvus
    data = []
    for i, (doc, embedding) in enumerate(zip(documents, embeddings_list)):
        # Generate a unique UUID for each document
        doc_id = str(uuid.uuid4())

        # Create entity with all fields
        entity = {
            "id": doc_id,
            "vector": embedding,
            "page_content": doc.page_content
        }

        # Add all metadata fields
        for key, value in doc.metadata.items():
            entity[key] = str(value)

        data.append(entity)

    # Insert data into Milvus
    milvus_client.insert(collection_name=COLLECTION_NAME, data=data)
    logger.info(f"Added {len(documents)} documents to Milvus collection")


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

    add_documents(documents)
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

    add_documents(documents)
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

    # Build filter expression for Milvus
    filter_expr = f"belongs_to == '{username}'"

    # Handle exclude_selected sources
    if exclude_selected and len(exclude_selected) > 0:
        exclude_conditions = []
        for source in exclude_selected:
            exclude_conditions.append(f"source != '{source}'")

        if exclude_conditions:
            exclude_expr = " && ".join(exclude_conditions)
            filter_expr = f"{filter_expr} && ({exclude_expr})"

    # Handle include_selected sources
    if include_selected and len(include_selected) > 0:
        include_conditions = []
        for source in include_selected:
            include_conditions.append(f"source == '{source}'")

        if include_conditions:
            include_expr = " || ".join(include_conditions)
            filter_expr = f"{filter_expr} && ({include_expr})"

    # Handle source_type filter
    if source_type is not None:
        filter_expr = f"{filter_expr} && source_type == '{source_type}'"

    logger.info(f"Milvus filter expression: {filter_expr}")

    # Generate embedding for the query
    query_embedding = embeddings.embed_query(prompt)

    print(query_embedding,  "qb")
    # Perform similarity search
    search_results = milvus_client.search(
        collection_name=COLLECTION_NAME,
        data=[query_embedding],
        filter=filter_expr,
        limit=window_size_modified,
        output_fields=["page_content", "source", "page", "title", "filename",
                       "belongs_to", "link_id", "file_id", "source_type"]
    )

    print(search_results, "sr..")
    # Process search results
    docs_with_scores = []
    if search_results and 'data' in search_results and len(search_results['data']) > 0:
        results = json.loads(search_results['data'][0])
        for result in results:
            entity = result['entity']

            # Create metadata dictionary
            metadata = {k: v for k, v in entity.items(
            ) if k not in ['page_content', 'vector', 'id']}

            # Create Document object
            doc = Document(
                page_content=entity['page_content'],
                metadata=metadata
            )

            # Add to results with score (1 - distance for cosine similarity)
            docs_with_scores.append((doc, 1 - result['distance']))

    logger.info(f"Found {len(docs_with_scores)} relevant documents")
    return docs_with_scores


def remove_documents(filename, username):
    try:
        # Build explicit filter expression for Milvus
        filter_expr = f"filename == '{filename}' && belongs_to == '{username}'"

        # Delete documents matching the filter
        result = milvus_client.delete(
            collection_name=COLLECTION_NAME,
            filter=filter_expr
        )

        if result and result.get('delete_count', 0) > 0:
            logger.info(
                f"Removed {result.get('delete_count', 0)} documents with filename={filename} belonging to user={username}")
            return True
        else:
            logger.warning(
                f"No documents found with filename={filename} belonging to user={username}")
            return False

    except Exception as err:
        logger.error(
            f"Error removing documents with filename={filename}: {str(err)}")
        return False
