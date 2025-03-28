import streamlit as st
import ollama
import asyncio
from typing import AsyncGenerator
import time
import PyPDF2
import json
import re
import base64
import aiohttp
import math
from datetime import datetime
from utils import (
    save_token_to_storage,
    navigate_to,
    upload_file_to_api_server,
    submit_link,
    submit_bulk_links,
    submit_recursive_crawl_link,
    fetch_documents,
    upload_note_to_api_server,
    fetch_notes,
    fetch_file,
    update_note_to_api_server,
    create_markdown_editor
)

from config import settings

SVG_ICON = """
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
   <rect x="10" y="75" width="75" height="15"
                  stroke="#666"
                  stroke-width="2"
                  fill="#f5f5f5"/>

   <!-- Left-side books -->
   <rect x="15" y="30" width="10" height="45"
         stroke="#666"
         stroke-width="2"
         fill="#e6e6fa"/>
   <rect x="30" y="35" width="10" height="40"
         stroke="#666"
         stroke-width="2"
         fill="#e6ffe6"/>

   <!-- Boy character -->
   <circle cx="58" cy="55" r="8"
           stroke="#333"
           stroke-width="2"
           fill="#ffcccb"/>

   <!-- Body and arm reaching toward books -->
   <line x1="58" y1="63" x2="58" y2="75"
         stroke="#333"
         stroke-width="2"/>
   <path d="M58,68 Q48,65 43,70"
         stroke="#333"
         stroke-width="2"
         fill="none"/>

</svg>
"""


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
        if "view_mode" not in st.session_state:
            st.session_state.view_mode = None
        if 'list_page_number' not in st.session_state:
            st.session_state.list_page_number = 1
        if 'list_page_number_modified' not in st.session_state:
            st.session_state.list_page_number_modified = False
        if 'edit_note_url' not in st.session_state:
            st.session_state.edit_note_url = None
        if 'prompt_with_docs' not in st.session_state:
            st.session_state.prompt_with_docs = {}
        if 'right_sidebar_rendered' not in st.session_state:
            st.session_state.right_sidebar_rendered = False
        if 'discussion_mode' not in st.session_state:
            st.session_state.discussion_mode = "context-aware"

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
        st.session_state.right_sidebar_rendered = False
        if value == "Include":
            st.session_state.include_selected.append(source)
        else:
            st.session_state.exclude_selected.append(source)

    def display_references(self, index=0):
        docs = st.session_state.prompt_with_docs.get("docs", [])

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
                    "source_type": metadata.get("source_type", "")
                }
                references.append(reference)

            # index field is used for controlling
            # where to display the references
            if index == 2:
                ref = self.main_content
            else:
                ref = self.right_sidebar
            with ref:
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
                    if index == 2:
                        expand = True
                    elif st.session_state.discussion_mode == "only-links":
                        # It means, discussion mode is show only links
                        # but the references will load on right sidebar
                        # so we don't want to auto expand them
                        expand = False
                    else:
                        expand = (i == 1)
                    with st.expander(
                        f"Reference {i} (Score: {ref['score']:.2f}, Page: {ref['page']})",
                        expanded=expand
                    ):
                        st.session_state.right_sidebar_rendered = True
                        st.radio(
                            src,
                            options=["Include", "Exclude"],
                            key=f"radio_{index}_{i}",
                            horizontal=True,
                            index=None,
                            on_change=self.handle_selection_change,
                            args=(ref['source'], f"radio_{index}_{i}",)
                        )
                        if ref['text']:
                            st.markdown(ref['text'])
                        if ref['filename']:

                            cols = st.columns([5, 3])
                            cols[0].button(
                                "View Document",
                                key=f"btn_{index}_{i}",
                                on_click=self.render_file_sync,
                                args=(ref['source'],)
                            )
                            if ref['source_type'] == "note":
                                cols[1].button(
                                    "Edit",
                                    key=f"edit_note_button_{index}_{i}",
                                    on_click=self.edit_note_btn_clicked,
                                    args=(ref['source'],)
                                )

    def format_resource_list(self, docs):
        formatted_text = ""
        for i, resource in enumerate(docs):
            metadata = resource.get("metadata")
            source_type = metadata.get("source_type")
            title = metadata.get("title", "No Title")
            url = "#"
            if source_type == "link":
                url = metadata.get("source", "#")

            text = resource.get("page_content", "No description available")

            # Format each item with markdown
            formatted_text += f"#### {i+1} [{title}]({url})\n"
            formatted_text += f"{text}\n\n---\n"

        return formatted_text

    async def process_response(self, docs, prompt: str):

        discussion_mode = st.session_state.discussion_mode
        context = None

        if len(st.session_state.messages) > 1:
            msgs = [msg["content"] for msg in st.session_state.messages]
            msgstr = '\n'.join(msgs)
            prompt = msgstr + "\n" + prompt

        if docs:
            context = "\n\n".join(
                [doc["page_content"] for doc in docs])

        with self.main_content.chat_message("assistant"):
            message_placeholder = st.empty()
            self.qna_tab.container().empty()
            full_response = ""

            if discussion_mode == "context-aware" and not context:
                full_response = "I couldn't find relevant information in the uploaded document to answer your question."
                message_placeholder.markdown(full_response)
            elif discussion_mode == "only-links":
                message_placeholder.markdown(
                    f"Total references found: {len(docs)}")
                self.display_references(2)
            else:
                context_aware = True if discussion_mode == "context-aware" else False
                async for response_chunk in self.get_llm_response(prompt, context, context_aware):
                    full_response += response_chunk
                    message_placeholder.markdown(full_response + "▌")
                    time.sleep(0.01)

                message_placeholder.markdown(full_response)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response})

    def render_file_sync(self, file_url):
        # when this even is fired, somehow
        # right sidebar content vanishes.
        # To prevent this setting this variable to False
        # meaning right sidebar has vanished.
        # In run() we use this variable to render sidebar again
        # if it has vanished
        st.session_state.right_sidebar_rendered = False
        with self.main_content:
            with st.spinner("Loading document..."):
                st.session_state.is_generating = False

                asyncio.run(self.render_file_async(file_url))

    def render_note_sync(self, file_url, note_id, note_filename):
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

    def set_source_type_radio_button(self, key):
        value = st.session_state.get(key, "")
        if value.startswith("/links"):
            st.session_state.source_type = "link"
        elif value.startswith("/notes"):
            st.session_state.source_type = "note"
        elif value.startswith("/files"):
            st.session_state.source_type = "file"
        else:
            st.session_state.source_type = None

        return value

    def format_timestamp(self, timestamp_str):
        # Parse the ISO format timestamp
        dt = datetime.fromisoformat(timestamp_str)

        # Get the day and add the appropriate ordinal suffix
        day = dt.day
        if 4 <= day <= 20 or 24 <= day <= 30:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")

        # Format the datetime with the day suffix
        formatted_date = dt.strftime(f"%-d{suffix} %B %Y %-I:%M %p")

        return formatted_date

    def display_notes(self):

        page_size = settings.LIST_PAGE_SIZE

        # Initialize session state for page number if not exists
        current_page = st.session_state.list_page_number

        # Calculate offset for API call
        offset = (current_page - 1) * page_size

        # Fetch only the notes for the current page
        response = fetch_notes(offset, page_size)
        records = response["notes"]
        total_notes = response["total"]

        total_pages = math.ceil(total_notes / page_size)

        # Edge case where notes are still not created
        # but we are trying to list notes
        if total_pages == 0:
            total_pages = 1

        col1, col2 = self.main_content.columns([5, 2])

        with col1:
            # Show current range of notes being displayed
            start_idx = offset + 1
            end_idx = min(offset + page_size, total_notes)
            st.write(f"Showing notes {start_idx}-{end_idx} of {total_notes}")

        with col2:
            # Simple page input
            page_input = st.number_input(
                "Go to page",
                min_value=1,
                max_value=total_pages,
                value=current_page,
                step=1,
                key="page_input"
            )

        # Update page number when input changes
        if page_input != current_page:
            st.session_state.list_page_number = page_input
            st.session_state.list_page_number_modified = True
            st.rerun()

        header_cols = self.main_content.columns([1, 5, 5, 2, 2])
        header_cols[0].write("**ID**")
        header_cols[1].write("**Title**")
        header_cols[2].write("**Updated At**")
        header_cols[3].write("**Action**")

        # Add a separator
        self.main_content.markdown("---")

        # Display each note
        for i, note in enumerate(records):
            cols = self.main_content.columns([1, 5, 5, 2, 2])

            # Display ID
            cols[0].write(f"{i+offset+1}")

            # Display Title
            title = note["title"]
            cols[1].write(title)

            # filename = note["filename"].replace("-", " ")
            # cols[2].write(filename)

            url = note["url"]
            # View button

            updated_at = self.format_timestamp(note["updated_at"])
            cols[2].write(updated_at)

            cols[3].button(
                "View",
                key=f"view_note_{note['id']}",
                on_click=self.render_note_sync,
                args=(url, note["id"], note["filename"]))

            cols[4].button(
                "Edit",
                key=f"edit_note_button_{note['id']}",
                on_click=self.edit_note_btn_clicked,
                args=(url,)
            )

    def edit_note_btn_clicked(self, file_url):
        st.session_state.view_mode = "edit-note"
        st.session_state.edit_note_url = file_url
        st.session_state.right_sidebar_rendered = False

    def edit_notes(self, file_url):
        filename = file_url.rsplit("/")[-1]
        content = fetch_file(file_url)
        with self.main_content:
            updated_content = self.main_content.text_area(
                f"Edit {filename} in markdown format:",
                value=content,
                height=600
            )
            cols = self.main_content.columns([1, 1, 2, 2])
            if cols[0].button(
                    "← Notes",
                    key="back_to_list_button"
            ):
                st.session_state.view_mode = "notes-list"
                st.rerun()
            if cols[1].button(
                    "Save",
                    key="note_save_button"
            ):
                if updated_content:
                    st.session_state.right_sidebar_rendered = False
                    updated = update_note_to_api_server(
                        updated_content, file_url)
                    if updated:
                        st.success("file updated successfully")
                    else:
                        st.error("error occurred when updating file")

                    st.rerun()

    def run(self):
        models = self.get_ollama_models()
        with st.sidebar:
            container = st.container()
            with container:
                col1, col2 = st.columns([10, 10])
                with col1:
                    st.title("Inquisitive")
                with col2:
                    st.image(SVG_ICON, width=60)
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
            discussion_mode = st.radio(
                "Choose discussion mode:",
                ["context aware", "non-context aware",
                    "no discussion (only links)"]
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
                            st.success("✅ Submitted for Processing!.")
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
                            st.success("✅ Submitted for Processing!")
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

        if discussion_mode == "context aware":
            st.session_state.discussion_mode = "context-aware"
        elif discussion_mode == "non-context aware":
            st.session_state.discussion_mode = "non-context-aware"
        else:
            st.session_state.discussion_mode = "only-links"

        if prompt := st.chat_input("Ask a question about the uploaded document"):
            st.session_state.messages.append(
                {"role": "user", "content": prompt})
            with self.main_content.chat_message("user"):
                st.markdown(prompt)

            if prompt.startswith("/notes-list"):
                st.session_state.view_mode = "notes-list"
            else:
                st.session_state.view_mode = "ollama-chat"
                prompt = self.set_source_type(prompt)

                st.session_state.context_window_size = input_context_window_size
                docs = fetch_documents(prompt)

                st.session_state.prompt_with_docs['docs'] = docs
                st.session_state.prompt_with_docs['prompt'] = prompt

                self.display_references()
                st.session_state.is_generating = True
                asyncio.run(self.process_response(docs, prompt))
                st.session_state.is_generating = False

        if st.session_state.prompt_with_docs and not st.session_state.right_sidebar_rendered:
            self.display_references(1)

        if (st.session_state.view_mode == "notes-list"
            or st.session_state.list_page_number_modified
            ):
            st.session_state.list_page_number_modified = False
            self.display_notes()

        if st.session_state.view_mode == "edit-note":
            self.edit_notes(st.session_state.edit_note_url)

        if st.session_state.is_generating:
            if st.button("Stop Generating"):
                st.session_state.is_generating = False
                st.rerun()

        with st.sidebar:
            st.sidebar.divider()
        if st.sidebar.button("Clear Chat"):
            st.session_state.messages = []
            self.main_content.empty()
            self.right_sidebar.empty()
            st.session_state.source_type = None
            st.empty()
            st.session_state.prompt_with_docs.clear()
            st.rerun()

        with st.sidebar:
            if st.sidebar.button("Tips"):
                st.markdown(
                    "Shortcuts\n\n`/notes`\n\n`/files`\n\n`/links`\n\n`/notes-list`\n\nStart prompt with above shortcuts for focussed search")

        if st.sidebar.button(f"Logout ({st.session_state.username}) ⬅️"):
            navigate_to("logout")

        if st.session_state.authenticated:
            save_token_to_storage(st.session_state.token,
                                  st.session_state.username)
