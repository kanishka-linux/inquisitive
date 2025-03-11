import PyPDF2
import mimetypes
import uuid
import os
from backend.config import settings
from datetime import datetime


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
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Replace spaces with hyphen and remove special characters
    safe_title = ''.join(c if c.isalnum() else '-' for c in title)
    filename = f"{safe_title}-{timestamp}.md"

    file_path = os.path.join(settings.UPLOAD_DIR, filename)

    # Write content to file
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return doc_id, file_path, filename


def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        return None
