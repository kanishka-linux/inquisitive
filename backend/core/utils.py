import PyPDF2
import mimetypes


def is_file_pdf(file_path):
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type == 'application/pdf'


def read_text_file_content(file_path):
    text_content = ""
    with open(file_path, 'r', encoding='utf-8') as file:
        text_content = file.read()
    return text_content


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
