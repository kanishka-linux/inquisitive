import PyPDF2
import mimetypes
import uuid
import os
from langchain.text_splitter import RecursiveCharacterTextSplitter
from backend.config import settings
import shutil
from backend.core.logging import get_logger


logger = get_logger()


text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=settings.TEXT_SPLITTER_CHUNK_SIZE,
    chunk_overlap=settings.TEXT_SPLITTER_CHUNK_OVERLAP,
    length_function=len,
    separators=["\n\n", "\n", " ", ""]
)


def is_file_pdf(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type == 'application/pdf'


def read_text_file_content(file_path):
    text_content = ""
    with open(file_path, 'r', encoding='utf-8') as file:
        text_content = file.read()
    return text_content


def save_file(content, title):
    # Generate a unique ID
    doc_id = str(uuid.uuid4())

    # Create a filename

    saved = False
    # Replace spaces with hyphen and remove special characters
    safe_title = ''.join(c if c.isalnum() else '-' for c in title)
    filename = f"{safe_title}-{doc_id}.md"

    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Write content to file
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        saved = True
    except Exception as err:
        logger.error(f"Error creating note {file_path}: {err}")
        saved = False

    return doc_id, file_path, filename, saved


def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    texts = []
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        for i, page in enumerate(pdf_reader.pages):
            texts.append({
                "text": page.extract_text(),
                "page_number": i+1
            })
        return texts
    except Exception as err:
        logger.error(f"Error processing {pdf_file}: {err}")
        return None


def chunk_pdf_content(text_content_list):
    texts = []
    for content_dict in text_content_list:
        text = content_dict["text"]
        page_number = content_dict["page_number"]
        for splitted_text in text_splitter.split_text(text):
            texts.append({
                "text": splitted_text,
                "page_number": page_number
            })
    return texts


def chunk_non_pdf_content(text_content):
    texts = []
    for i, splitted_text in enumerate(text_splitter.split_text(text_content)):
        texts.append({
            "text":  splitted_text,
            "page_number": i + 1
        })
    return texts


def chunk_link_content(text_content):
    return text_splitter.split_text(text_content)


def update_file_with_backup(content, filename):
    file_path = os.path.join(settings.UPLOAD_DIR, filename)
    backup_path = f"{file_path}.bak"
    # Check if original file exists
    if not os.path.exists(file_path):
        return False

    try:
        # Create backup of the original file
        shutil.copy2(file_path, backup_path)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.remove(backup_path)
            return True
        except Exception as write_err:
            logger.error(f"Error writing to file {filename}: {write_err}")
            try:
                shutil.copy2(backup_path, file_path)
                logger.info(
                    f"Restored {filename} from backup after failed update")
                os.remove(backup_path)
                return False
            except Exception as restore_err:
                logger.error(
                    f"Error restoring from backup - need manual intervention for {filename} with {backup_path}: {restore_err}")
                return False

    except Exception as backup_err:
        logger.error(f"Error creating backup of {filename}: {backup_err}")
        return False

    return False
