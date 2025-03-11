import streamlit as st
import ollama
import asyncio
from typing import AsyncGenerator
import time
from langchain_ollama import OllamaEmbeddings
import PyPDF2
import json
import re
import base64
import aiohttp
from utils import (
    save_token_to_storage,
    navigate_to,
    upload_file_to_api_server,
    submit_link,
    submit_bulk_links,
    submit_recursive_crawl_link,
    fetch_documents,
    upload_note_to_api_server
)

from config import settings


class OllamaChatApp:
    def __init__(self):
        self.init_session_state()
        self.setup_streamlit_page_layout()

    def init_session_state(self):
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'is_generating' not in st.session_state:
            st.session_state.is_generating = False
        if 'file_uploaded' not in st.session_state:
            st.session_state.file_uploaded = False
        if 'context_window_size' not in st.session_state:
            st.session_state.context_window_size = 10
        if "exclude_selected" not in st.session_state:
            st.session_state.exclude_selected = []
        if "include_selected" not in st.session_state:
            st.session_state.include_selected = []
        if "ollama_model" not in st.session_state:
            st.session_state.ollama_model = None
        if "source_type" not in st.session_state:
            st.session_state.source_type = None
        if "ollama_model_selected" not in st.session_state:
            st.session_state.ollama_model_selected = None

    def setup_streamlit_page_layout(self):
        self.qna_tab = st
        self.main_content, self.right_sidebar = self.qna_tab.columns([3, 1])

    def format_chat_history(self):
        """Format the entire chat history for context"""
        formatted_messages = []

        # Add system message first
        formatted_messages.append({
            "role": "system",
            "content": 'You are a document Q&A assistant. Only answer questions based on the provided context. If the answer cannot be found in the context, say so.'
        })

        # Add all previous messages
        formatted_messages.extend(st.session_state.messages)

        return formatted_messages

    def format_chat_history_unfocused(self):
        """Format the entire chat history for context"""
        formatted_messages = []

        # Add system message first
        formatted_messages.append({
            "role": "system",
            "content": 'You are a document Q&A assistant'
        })

        # Add all previous messages
        formatted_messages.extend(st.session_state.messages)

        return formatted_messages

    def process_uploaded_file_with_links(self, uploaded_file):
        """Process uploaded file, extact links, fetch pages and store in vector database"""
        if uploaded_file is not None:
            try:
                # Extract text based on file type
                if uploaded_file.type == "application/pdf":
                    text_content = self.extract_text_from_pdf(uploaded_file)
                else:  # text file
                    text_content = uploaded_file.read().decode('utf-8')

                if not text_content:
                    st.error("No text content could be extracted from the file.")
                    return False

                links = re.findall(
                    r'(https?://[^"\'\s\n]+)(?:["\'\s\n]|$)', text_content)
                filtered_links = list(filter(lambda link: not (
                    link.endswith("svg") or link.endswith("ico") or link.endswith("png")), links))

                chunk_size = 500
                chunked_urls = [
                    filtered_links[i:i + chunk_size]
                    for i in range(0, len(filtered_links), chunk_size)
                ]

                for batch in chunked_urls:
                    submit_bulk_links(batch, settings.DEFAULT_HEADERS)
                return True
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                return False
        return False

    def process_uploaded_file(self, uploaded_file):
        if uploaded_file is not None:
            try:
                upload_file_to_api_server(uploaded_file)
                st.success(
                    f"File Name: {uploaded_file.name}")
                return True
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                return False
        return False

    def extract_text_from_pdf(self, pdf_file):
        """Extract text from PDF file"""
        try:
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return None

    def create_prompt_with_context(self, query: str, context: str) -> str:
        """Create a focused prompt that instructs the model to use only the provided context"""
        return f"""Please answer the question based ONLY on the provided context. If the context doesn't contain the information needed to answer the question, please respond with "I cannot answer this question based on the provided context."

Context: {context}

Question: {query}

Answer: """

    def create_prompt_without_context(self, query: str) -> str:
        """Create a focused prompt that instructs the model to use only the provided context"""
        return f"""Please answer the following question"

Question: {query}

Answer: """

    async def get_llm_response(self, prompt: str, context: str = None, context_aware: bool = True) -> AsyncGenerator[str, None]:
        """Get streaming response from Mistral"""
        try:
            client = ollama.AsyncClient()

            # Create system message to enforce context-based answering
            system_message_focused = {
                'role': 'system',
                'content': 'You are a document Q&A assistant. Only answer questions based on the provided context. If the answer cannot be found in the context, say so.'
            }
            system_message_non_focused = {
                'role': 'system',
                'content': 'You are Q&A assistant'
            }

            # Create the focused prompt
            if context_aware:
                focused_prompt = self.create_prompt_with_context(
                    prompt, context)
            else:
                non_focused_prompt = self.create_prompt_without_context(prompt)

            if len(st.session_state.messages) > 1 and context_aware:
                messages = self.format_chat_history()
                messages.append({'role': 'user', 'content': focused_prompt})
            elif len(st.session_state.messages) > 1 and not context_aware:
                messages = self.format_chat_history_unfocused()
                messages.append(
                    {'role': 'user', 'content': non_focused_prompt})
            elif context_aware:
                messages = [
                    system_message_focused,
                    {'role': 'user', 'content': focused_prompt}
                ]
            else:
                messages = [
                    system_message_non_focused,
                    {'role': 'user', 'content': non_focused_prompt}
                ]

            stream = await client.chat(
                model=st.session_state.ollama_model_selected,
                messages=messages,
                stream=True
            )

            async for chunk in stream:
                if not st.session_state.is_generating:
                    break
                if 'message' in chunk:
                    content = chunk['message'].get('content', '')
                    if content:
                        yield content
                        await asyncio.sleep(0)

        except Exception as e:
            yield f"\nError: {str(e)}"

    def display_chat_history(self):
        """Display chat messages from history"""
        for message in st.session_state.messages:
            with self.main_content.chat_message(message["role"]):
                st.markdown(message["content"])

    def ollama_model_selected(self):
        st.session_state.ollama_model_selected = st.session_state.select_ollama_model

    def handle_selection_change(self, source, key):
        """Callback function to handle selection changes"""
        # Store the selection in session state
        value = st.session_state[key]
        if value == "Include":
            st.session_state.include_selected.append(source)
        else:
            st.session_state.exclude_selected.append(source)

    async def process_response(self, prompt: str, context_aware: bool):

        context = None

        if len(st.session_state.messages) > 1:
            msgs = [msg["content"] for msg in st.session_state.messages]
            msgstr = '\n'.join(msgs)
            prompt = msgstr + "\n" + prompt

        docs = fetch_documents(prompt)

        if docs:
            context = "\n\n".join(
                [doc["page_content"] for doc in docs])
            # Prepare references for sidebar
            references = []

            for doc in docs:
                metadata = doc["metadata"]
                source = metadata.get("source", "N/A")
                reference = {
                    "source": source,
                    "page": metadata.get("page", "N/A"),
                    "score": doc["score"],
                    "text": doc["page_content"],
                    "title": metadata.get("title", source),
                    "filename": metadata.get("filename", ""),
                }
                references.append(reference)

            with self.right_sidebar:
                if st.session_state.include_selected:
                    st.info(
                        f"Included reference: {','.join(st.session_state.include_selected)}", icon="ℹ️")
                if st.session_state.exclude_selected:
                    st.info(
                        f"Excluded reference: {','.join(st.session_state.exclude_selected)}", icon="ℹ️")

                for i, ref in enumerate(references, 1):
                    if ref["filename"]:
                        src = ref['filename']
                    else:
                        src = ref['source']
                    with st.expander(f"Reference {i} (Score: {ref['score']:.2f}, Page: {ref['page']})", expanded=(i == 1)):
                        st.radio(
                            src,
                            options=["Include", "Exclude"],
                            key=f"radio_{i}",
                            horizontal=True,
                            index=None,
                            on_change=self.handle_selection_change,
                            args=(ref['source'], f"radio_{i}",)
                        )
                        if ref['text']:
                            st.markdown(ref['text'])
                        if ref['filename']:
                            st.button("View Document", key=f"btn_{i}", on_click=self.render_file_sync, args=(
                                ref['source'],))

        with self.main_content.chat_message("assistant"):
            message_placeholder = st.empty()
            self.qna_tab.container().empty()
            full_response = ""

            if context_aware and not context:
                full_response = "I couldn't find relevant information in the uploaded document to answer your question."
                message_placeholder.markdown(full_response)
            else:
                async for response_chunk in self.get_llm_response(prompt, context, context_aware):
                    full_response += response_chunk
                    message_placeholder.markdown(full_response + "▌")
                    time.sleep(0.01)

                message_placeholder.markdown(full_response)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response})

    def render_file_sync(self, file_url):
        with self.main_content:
            with st.spinner("Loading document..."):
                st.session_state.is_generating = False
                asyncio.run(self.render_file_async(file_url))

    async def render_file_async(self, file_url):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{settings.API_URL}{file_url}",
                headers={"Authorization": f"Bearer {st.session_state.token}"}
            ) as response:
                if response.status != 200:
                    self.qna_tab.error(
                        f"Failed to fetch file: {response.status}")
                    return

                content_type = response.headers.get("content-type", "")
                content = await response.read()

                if content_type == "application/pdf":
                    base64_pdf = base64.b64encode(content).decode('utf-8')
                    pdf_display = f'<embed src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf">'
                    self.qna_tab.container(border=True).markdown(
                        pdf_display, unsafe_allow_html=True)
                elif content_type.startswith("image/"):
                    self.qna_tab.container(border=True).image(content)

                elif content_type == "text/markdown":
                    try:
                        markdown_text = content.decode(
                            'utf-8', errors='replace')
                        self.qna_tab.container(border=True).markdown(
                            markdown_text, unsafe_allow_html=True)
                    except:
                        self.qna_tab.text_area(
                            "Markdown Content", content, height=300)

                elif content_type == "application/json":
                    try:
                        text = content.decode('utf-8', errors='replace')
                        self.qna_tab.container(border=True).json(text)
                    except:
                        self.qna_tab.text_area(
                            "JSON Content", content, height=300)

                elif content_type.startswith("text/"):
                    try:
                        text = content.decode('utf-8', errors='replace')
                        self.qna_tab.container(border=True).markdown(text)
                    except Exception as e:
                        self.qna_tab.error(f"Failed to render text file: {e}")

                else:
                    self.qna_tab.warning(
                        f"Unsupported file type: {content_type}")

    def get_ollama_models(self):
        try:
            models = [i.model for i in ollama.list().models]
            return models
        except Exception as e:
            st.error(f"Error connecting to Ollama: {str(e)}")
            return []

    def set_source_type(self, prompt):
        if prompt.startswith("/links"):
            st.session_state.source_type = "link"
            prompt = re.sub(r"^/links ", "", prompt)
        elif prompt.startswith("/notes"):
            st.session_state.source_type = "note"
            prompt = re.sub(r"^/notes ", "", prompt)
        elif prompt.startswith("/files"):
            st.session_state.source_type = "file"
            prompt = re.sub(r"^/files ", "", prompt)

        return prompt


    def run(self):
        """Main application loop"""

        models = self.get_ollama_models()
        with st.sidebar:
            st.title("Inquisitive 📚")
            if models:
                if st.session_state.ollama_model_selected is None:
                    st.session_state.ollama_model_selected = models[0]
                selected_model = st.selectbox(
                    "Select an Ollama model",
                    options=models,
                    index=0,
                    key='select_ollama_model',
                    placeholder="Choose a model...",
                    on_change=self.ollama_model_selected
                )
            else:
                st.info("Make sure Ollama is running on your machine.")
            context_aware = st.radio(
                "Choose discussion type:",
                ["context aware", "non-context aware"]
            )

            input_context_window_size = st.number_input(
                label='Enter Reference Window Size',
                min_value=1,
                max_value=100,
                value=3,
                step=1,
                format='%d'
            )

            input_method = st.radio(
                "Choose document input method:",
                ["File Upload", "Add Note", "Add Link",
                    "File with Links", "Recursive Crawl"]
            )

            if input_method == "File Upload":
                uploaded_file = st.file_uploader(
                    "Upload a file", type=settings.UPLOAD_FILE_TYPES)
                if uploaded_file:
                    if st.button("Process Document"):
                        with st.spinner("Processing document..."):
                            success = self.process_uploaded_file(uploaded_file)
                            if success:
                                st.success("Document Accepted for Processing")
                            else:
                                st.error("Error processing document")
            elif input_method == "File with Links":
                uploaded_file = st.file_uploader(
                    "Upload Any file containing links", type=settings.UPLOAD_FILE_TYPES)
                if uploaded_file:
                    if st.button("Process Document"):
                        with st.spinner("Processing document..."):
                            success = self.process_uploaded_file_with_links(
                                uploaded_file)
                            if success:
                                st.success("Document submitted for processing")
                            else:
                                st.error("Error processing document")
            elif input_method == "Recursive Crawl":
                st.subheader("Input Link")
                input_url = st.text_input("Enter Website URL")

                input_headers = st.text_area(
                    "Headers (optional):",
                    height=150,
                    value=json.dumps(settings.DEFAULT_HEADERS, indent=2),
                    placeholder="Paste or type hdrs in json format"
                )

                if input_url and input_headers and st.button("Process URL"):
                    try:
                        headers = json.loads(input_headers)
                    except:
                        st.error("Invalid JSON format for headers")
                        headers = settings.DEFAULT_HEADERS

                    with st.spinner("Processing..."):
                        success = submit_recursive_crawl_link(
                            input_url, headers)
                        if success:
                            st.success("✅ Done! Processed.")
                        else:
                            st.error("Error Processing")
            elif input_method == "Add Link":
                st.subheader("Input Link")
                input_url = st.text_input("Enter Website URL")

                input_headers = st.text_area(
                    "Headers (optional):",
                    height=150,
                    value=json.dumps(settings.DEFAULT_HEADERS, indent=2),
                    placeholder="Paste or type hdrs in json format"
                )

                if input_url and input_headers and st.button("Process URL"):
                    try:
                        headers = json.loads(input_headers)
                    except:
                        st.error("Invalid JSON format for headers")
                        headers = settings.DEFAULT_HEADERS

                    with st.spinner("Processing..."):
                        success = submit_link(input_url, headers)
                        if success:
                            st.success("✅ Done! Processed.")
                        else:
                            st.error("Error Processing")
            else:
                st.subheader("Text Input")
                input_text = st.text_area(
                    "Enter your text here:",
                    height=300,
                    placeholder="Paste or type your text here..."
                )
                st.subheader("Add Title")
                input_title = st.text_area(
                    "Enter Title of the Note:",
                    height=70,
                    placeholder="Enter Title.."
                )
                if input_text and input_title and st.button("Process Text"):
                    with st.spinner("Processing text..."):
                        success = upload_note_to_api_server(
                            input_text,  input_title)
                        if success:
                            st.success(
                                "Text processed and stored in vector database!")
                        else:
                            st.error("Error processing text")

        # Main chat interface
        self.display_chat_history()

        if context_aware == "context aware":
            context_aware_search = True
        else:
            context_aware_search = False

        if prompt := st.chat_input("Ask a question about the uploaded document"):
            st.session_state.messages.append(
                {"role": "user", "content": prompt})
            with self.main_content.chat_message("user"):
                st.markdown(prompt)

            prompt = self.set_source_type(prompt)
            st.session_state.is_generating = True
            st.session_state.context_window_size = input_context_window_size
            asyncio.run(self.process_response(prompt, context_aware_search))
            st.session_state.is_generating = False

        if st.session_state.is_generating:
            if st.button("Stop Generating"):
                st.session_state.is_generating = False
                st.rerun()

        if st.sidebar.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()

        if st.sidebar.button(f"Logout ({st.session_state.username}) ⬅️"):
            navigate_to("logout")

        if st.session_state.authenticated:
            save_token_to_storage(st.session_state.token,
                                  st.session_state.username)
