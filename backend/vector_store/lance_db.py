from langchain_ollama import OllamaEmbeddings
from langchain.schema import Document
import lancedb
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
import pyarrow as pa


logger = get_logger()

# Initialize embeddings
embeddings = OllamaEmbeddings(
    model=settings.EMBEDDINGS_MODEL, base_url=settings.OLLAMA_HOST)

# Initialize LanceDB
db = lancedb.connect(settings.LANCE_DB_VECTOR_STORE_PERSISTS_DIRECTOY)

# Define table name
TABLE_NAME = settings.VECTOR_STORE_COLLECTION_NAME


# Create table if it doesn't exist
def initialize_collection():
    if TABLE_NAME not in db.table_names():
        # Create schema and table
        schema = pa.schema([
            pa.field("id", pa.string()),
            pa.field("vector", pa.list_(pa.float32(),
                     settings.EMBEDDINGS_DIMENSION)),
            pa.field("page_content", pa.string()),
            pa.field("source", pa.string()),
            pa.field("page", pa.string()),
            pa.field("title", pa.string()),
            pa.field("filename", pa.string()),
            pa.field("belongs_to", pa.string()),
            pa.field("link_id", pa.string()),
            pa.field("file_id", pa.string()),
            pa.field("source_type", pa.string())
        ])

        # Create empty table with schema
        db.create_table(TABLE_NAME, schema=schema)

        # Create vector index
        table = db.open_table(TABLE_NAME)

        # Create secondary indexes for efficient filtering
        # Index on belongs_to field
        table.create_scalar_index("belongs_to", index_type="BTREE")

        # Index on source_type field
        table.create_scalar_index("source_type", index_type="BTREE")

        # Index on source field
        table.create_scalar_index("source", index_type="BTREE")

        # Index on filename field
        table.create_scalar_index("filename", index_type="BTREE")

        # Index on link_id: only applicable for links
        table.create_scalar_index("link_id", index_type="BTREE")
        logger.info(f"Created new LanceDB table: {TABLE_NAME}")
    else:
        logger.info(f"Using existing LanceDB table: {TABLE_NAME}")


# Initialize table
initialize_collection()


def add_documents(documents):
    """Add documents to the LanceDB vector store"""
    if not documents:
        return

    # Generate embeddings for documents
    texts = [doc.page_content for doc in documents]
    embeddings_list = embeddings.embed_documents(texts)

    # Prepare data for LanceDB
    data = []
    for i, (doc, embedding) in enumerate(zip(documents, embeddings_list)):
        # Generate a unique UUID for each document
        doc_id = str(uuid.uuid4())

        # Create entity with all fields
        entity = {
            "id": doc_id,
            "vector": embedding,
            "page_content": doc.page_content,
        }

        # Add all metadata fields
        for key, value in doc.metadata.items():
            entity[key] = value

        # Ensure all required fields exist
        for field in ["source", "page", "title", "filename", "belongs_to",
                      "link_id", "file_id", "source_type"]:
            if field not in entity:
                entity[field] = None

        data.append(entity)

    # Insert data into LanceDB
    table = db.open_table(TABLE_NAME)
    table.add(data)
    logger.info(f"Added {len(documents)} documents to LanceDB table")


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

    # Open the table
    table = db.open_table(TABLE_NAME)

    # Generate embedding for the query
    query_embedding = embeddings.embed_query(prompt)

    # Build filter expression for LanceDB
    filter_conditions = [f"belongs_to = '{username}'"]

    # Handle exclude_selected sources
    if exclude_selected and len(exclude_selected) > 0:
        exclude_conditions = []
        for source in exclude_selected:
            exclude_conditions.append(f"source != '{source}'")

        if exclude_conditions:
            filter_conditions.append(
                "(" + " AND ".join(exclude_conditions) + ")")

    # Handle include_selected sources
    if include_selected and len(include_selected) > 0:
        include_conditions = []
        for source in include_selected:
            include_conditions.append(f"source = '{source}'")

        if include_conditions:
            filter_conditions.append(
                "(" + " OR ".join(include_conditions) + ")")

    # Handle source_type filter
    if source_type is not None:
        filter_conditions.append(f"source_type = '{source_type}'")

    # Combine all filter conditions
    filter_expr = " AND ".join(filter_conditions)

    logger.info(f"LanceDB filter expression: {filter_expr}")

    # Perform similarity search
    search_results = table.search(
        query_embedding,
        vector_column_name="vector"
    ).where(filter_expr).limit(window_size_modified).to_pandas()

    # Process search results
    docs_with_scores = []
    for _, row in search_results.iterrows():
        # Create metadata dictionary
        metadata = {k: v for k, v in row.items()
                    if k not in ['vector', 'page_content', 'id'] and v is not None}

        # Create Document object
        doc = Document(
            page_content=row['page_content'],
            metadata=metadata
        )

        # Add to results with score (already in cosine similarity format)
        docs_with_scores.append((doc, row['_distance']))

    logger.info(f"Found {len(docs_with_scores)} relevant documents")
    return docs_with_scores


def remove_documents(filename, username):
    try:
        # Open the table
        table = db.open_table(TABLE_NAME)

        # Build filter expression for LanceDB
        filter_expr = f"filename = '{filename}' AND belongs_to = '{username}'"

        # Get count before deletion for reporting
        count_before = table.count_rows(filter_expr)

        # Delete documents matching the filter
        table.delete(filter_expr)

        if count_before > 0:
            logger.info(
                f"Removed {count_before} documents with filename={filename} belonging to user={username}")
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
        # Open the table
        table = db.open_table(TABLE_NAME)

        # Build filter expression for LanceDB
        filter_expr = f"link_id = '{link_id}' AND belongs_to = '{username}'"

        # Get count before deletion for reporting
        count_before = table.count_rows(filter_expr)

        # Delete documents matching the filter
        table.delete(filter_expr)

        if count_before > 0:
            logger.info(
                f"Removed {count_before} documents with filename={link_id} belonging to user={username}")
            return True
        else:
            logger.warning(
                f"No documents found with filename={link_id} belonging to user={username}")
            return False

    except Exception as err:
        logger.error(
            f"Error removing documents with filename={link_id}: {str(err)}")
        return False
