import streamlit as st
import ollama
import asyncio
from typing import AsyncGenerator
import time
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import Chroma
from langchain.embeddings import OllamaEmbeddings
from langchain.schema import Document
from langchain_community.document_loaders import WebBaseLoader
import PyPDF2
import os
import json
from bs4 import BeautifulSoup
from utils import save_token_to_storage, clear_token_from_storage, navigate_to
from auth_page import logout_user


class OllamaChatApp:
    def __init__(self):
        self.init_session_state()
        # self.setup_streamlit_page()
        self.embeddings = OllamaEmbeddings(model="chroma/all-minilm-l6-v2-f32")
        self.persist_directory = "./chroma_db"
        self.load_or_create_vector_store()

    def load_or_create_vector_store(self):
        """Load existing vector store or create new one"""
        try:
            if os.path.exists(self.persist_directory):
                self.vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embeddings
                )
                st.session_state.file_uploaded = True
                st.session_state.vector_store = self.vector_store
            else:
                self.vector_store = None
                st.session_state.vector_store = self.vector_store
        except Exception as e:
            st.error(f"Error loading vector store: {str(e)}")
            self.vector_store = None

    def init_session_state(self):
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        if 'is_generating' not in st.session_state:
            st.session_state.is_generating = False
        if 'vector_store' not in st.session_state:
            st.session_state.vector_store = None
        if 'file_uploaded' not in st.session_state:
            st.session_state.file_uploaded = False
        if 'context_window_size' not in st.session_state:
            st.session_state.context_window_size = 10
        if 'selected_sources' not in st.session_state:
            st.session_state.selected_sources = "All"
        if "exclude_selected" not in st.session_state:
            st.session_state.exclude_selected = []
        if "include_selected" not in st.session_state:
            st.session_state.include_selected = []
        if "ollama_model" not in st.session_state:
            st.session_state.ollama_modle = None

    def setup_streamlit_page(self, layout):
        st.set_page_config(
            page_title="Document Q&A",
            page_icon="📚",
            layout=layout
        )
        st.title("Document Q&A System 📚")

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

    def process_uploaded_file(self, uploaded_file):
        """Process uploaded file (PDF or TXT) and store in vector database"""
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

                # Use RecursiveCharacterTextSplitter for better chunking
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=512,
                    chunk_overlap=50,
                    length_function=len,
                    separators=["\n\n", "\n", " ", ""]
                )
                texts = text_splitter.split_text(text_content)
                documents = [
                    Document(
                        page_content=text,
                        metadata={"source": uploaded_file.name, "page": f"{i}"}
                    ) for i, text in enumerate(texts)
                ]

                # Create or update vector store with persistence
                self.vector_store = Chroma.from_documents(
                    documents=documents,
                    embedding=self.embeddings,
                    persist_directory=self.persist_directory
                )
                self.vector_store.persist()  # Explicitly persist the database
                st.session_state.file_uploaded = True
                return True
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                return False
        return False

    def process_input_text(self, text_content, source):
        """Process uploaded file (PDF or TXT) and store in vector database"""
        if text_content is not None:
            try:
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=512,
                    chunk_overlap=50,
                    length_function=len,
                    separators=["\n\n", "\n", " ", ""]
                )
                texts = text_splitter.split_text(text_content)

                if source is None:
                    source = "N/A"
                documents = [
                    Document(
                        page_content=text,
                        metadata={"source": source, "page": f"{i}"}
                    ) for i, text in enumerate(texts)
                ]

                # Create or update vector store with persistence
                self.vector_store = Chroma.from_documents(
                    embedding=self.embeddings,
                    documents=documents,
                    persist_directory=self.persist_directory
                )
                self.vector_store.persist()  # Explicitly persist the database
                return True
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                return False
        return False

    async def process_input_link(self, url, headers):
        loader = WebBaseLoader(
            [url],
            requests_kwargs={"headers": headers}
        )
        loader.requests_per_second = 2
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        # Load documents
        async for doc in loader.alazy_load():
            try:
                soup = BeautifulSoup(doc.page_content, 'html.parser')
                title = soup.title.string if soup.title else "No title"
                description = soup.find('meta', {'name': 'description'})
                description = description['content'] if description else "No description"
                text = soup.get_text()
            except e as err:
                print(err)
                title = "No title"
                description = "No description"
                text = "No Text"

            texts = text_splitter.split_text(text)

            documents = [
                Document(
                    page_content=text,
                    metadata={
                        "source": doc.metadata['source'],
                        "page": f"{i}",
                        "title": title,
                        "description": description
                    }
                ) for i, text in enumerate(texts)
            ]

            self.vector_store = Chroma.from_documents(
                embedding=self.embeddings,
                documents=documents,
                persist_directory=self.persist_directory
            )
            self.vector_store.persist()
        return True

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

    async def get_mistral_response(self, prompt: str, context: str = None, context_aware: bool = True) -> AsyncGenerator[str, None]:
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
                if 'message' in chunk:
                    content = chunk['message'].get('content', '')
                    if content:
                        yield content

        except Exception as e:
            yield f"\nError: {str(e)}"

    def display_chat_history(self):
        """Display chat messages from history"""
        for message in st.session_state.messages:
            with main_content.chat_message(message["role"]):
                st.markdown(message["content"])

    def ollama_model_selected(self):
        st.session_state.ollama_model_selected = st.session_state.select_ollama_model

    def on_selectbox_change(self):
        selection = st.session_state.selectbox_key
        st.session_state.selected_sources = selection

    def handle_selection_change(self, source, key):
        """Callback function to handle selection changes"""
        # Store the selection in session state
        value = st.session_state[key]
        if value == "Include":
            st.session_state.include_selected.append(source)
        else:
            st.session_state.exclude_selected.append(source)

    async def process_response(self, prompt: str, context_aware: bool):
        """Process and display the model's response"""
        if not st.session_state.file_uploaded:
            with main_content.chat_message("assistant"):
                st.markdown(
                    "Please upload a document first before asking questions.")
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "Please upload a document first before asking questions."
                })
            return

        context = None

        if st.session_state.vector_store:
            # Increase k for more context and add search_type
            if len(st.session_state.messages) > 1:
                msgs = [msg["content"] for msg in st.session_state.messages]
                msgstr = '\n'.join(msgs)
                prompt = msgstr + "\n" + prompt
            filter_dict = {}
            if st.session_state.exclude_selected and st.session_state.include_selected:
                filter_dict = {
                    "$and": [
                        # Exclude these sources
                        {"source": {"$nin": st.session_state.exclude_selected}},
                        # Include these sources
                        {"source": {"$in": st.session_state.include_selected}}
                    ]
                }
            elif st.session_state.exclude_selected:
                filter_dict = {
                    "source": {"$nin": st.session_state.exclude_selected}
                }
            elif st.session_state.include_selected:
                filter_dict = {
                    "source": {"$in": st.session_state.include_selected}
                }
            if filter_dict:
                docs = st.session_state.vector_store.similarity_search_with_relevance_scores(
                    prompt,
                    filter=filter_dict,
                    k=st.session_state.context_window_size  # Retrieve more relevant chunks
                )
            elif st.session_state.selected_sources in ["All", None]:
                docs = st.session_state.vector_store.similarity_search_with_relevance_scores(
                    prompt,
                    k=st.session_state.context_window_size  # Retrieve more relevant chunks
                )
            else:
                docs = st.session_state.vector_store.similarity_search_with_relevance_scores(
                    prompt,
                    filter={"source": st.session_state.selected_sources},
                    k=st.session_state.context_window_size  # Retrieve more relevant chunks
                )

            if docs:
                context = "\n\n".join(
                    [doc.page_content for doc, score in docs])
                # Prepare references for sidebar
                references = []

                sources = set()
                for doc, score in docs:
                    source = doc.metadata.get("source", "N/A")
                    reference = {
                        "source": source,
                        "page": doc.metadata.get("page", "N/A"),
                        "score": score,
                        "text": doc.page_content,
                        "title": doc.metadata.get("title", source),
                    }
                    references.append(reference)
                    sources.add(source)

                with right_sidebar:
                    source_list = ["All"] + list(sources)
                    selected_source_index = 0
                    try:
                        selected_source_index = source_list.index(
                            st.session_state.selected_sources)
                    except ValueError:
                        pass
                    # st.selectbox(
                    #    label='Select a reference for more focused conversation',
                    #    options=source_list,
                    #    on_change=self.on_selectbox_change,
                    #    key="selectbox_key",
                    #    index=selected_source_index
                    # )

                    # if st.session_state.selected_sources not in ["All", None]:
                    #    st.info(f"selected reference: {st.session_state.selected_sources}", icon="ℹ️")
                    # else:
                    if st.session_state.include_selected:
                        st.info(
                            f"Included reference: {','.join(st.session_state.include_selected)}", icon="ℹ️")
                    if st.session_state.exclude_selected:
                        st.info(
                            f"Excluded reference: {','.join(st.session_state.exclude_selected)}", icon="ℹ️")

                    for i, ref in enumerate(references, 1):
                        with st.expander(f"Reference {i} (Score: {ref['score']:.2f}, Page: {ref['page']})", expanded=(i == 1)):
                            st.radio(
                                ref['source'],
                                options=["Include", "Exclude"],
                                key=f"radio_{i}",
                                horizontal=True,
                                index=None,
                                on_change=self.handle_selection_change,
                                args=(ref['source'], f"radio_{i}",)
                            )
                            if ref['text']:
                                st.write(ref['text'])

        with main_content.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            if context_aware and not context:
                full_response = "I couldn't find relevant information in the uploaded document to answer your question."
                message_placeholder.markdown(full_response)
            else:
                async for response_chunk in self.get_mistral_response(prompt, context, context_aware):
                    full_response += response_chunk
                    message_placeholder.markdown(full_response + "▌")
                    time.sleep(0.01)

                message_placeholder.markdown(full_response)

            st.session_state.messages.append(
                {"role": "assistant", "content": full_response})

    def get_ollama_models(self):
        try:
            models = [i.model for i in ollama.list().models]
            return models
        except Exception as e:
            st.error(f"Error connecting to Ollama: {str(e)}")
            return []

    def run(self):
        """Main application loop"""

        models = self.get_ollama_models()

        global right_sidebar, main_content, tab1, tab2

        # tab1, tab2 = st.tabs(["Q&A", "Documents"])
        main_content, right_sidebar = st.columns([3, 1])
        with st.sidebar:
            # st.title("Document Q&A System 📚")
            # st.title("Inquisitive 📚")
            if models:
                selected_model = st.selectbox(
                    "Select an Ollama model",
                    options=models,
                    index=None,
                    key='select_ollama_model',
                    placeholder="Choose a model...",
                    on_change=self.ollama_model_selected
                )
            else:
                st.info("Make sure Ollama is running on your machine.")
            input_method = st.radio(
                "Choose document input method:",
                ["File Upload", "Text Input", "Add Link"]
            )
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

            if input_method == "File Upload":
                st.header("Document Upload")
                uploaded_file = st.file_uploader(
                    "Upload a file", type=['txt', 'pdf', "md", "json", "sh"])
                if uploaded_file:
                    if st.button("Process Document"):
                        with st.spinner("Processing document..."):
                            success = self.process_uploaded_file(uploaded_file)
                            if success:
                                st.success(
                                    "Document processed and stored in vector database!")
                            else:
                                st.error("Error processing document")

                # Display upload status
                if st.session_state.file_uploaded:
                    st.success("Document is loaded and ready for questions!")
                else:
                    st.warning("Please upload a document to begin.")
            elif input_method == "Add Link":
                st.subheader("Input Link")
                input_url = st.text_input("Enter Website URL")

                default_headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5"
                }

                input_headers = st.text_area(
                    "Headers (optional):",
                    height=150,
                    value=json.dumps(default_headers, indent=2),
                    placeholder="Paste or type hdrs in json format"
                )

                if input_url and input_headers and st.button("Process URL"):
                    try:
                        headers = json.loads(input_headers)
                    except:
                        st.error("Invalid JSON format for headers")
                        headers = default_headers

                    with st.spinner("Processing..."):
                        success = asyncio.run(
                            self.process_input_link(input_url, input_headers))
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
                st.subheader("Add Source")
                input_source = st.text_area(
                    "Enter Metadata:",
                    height=70,
                    placeholder="Paste source link or type any metadata here.."
                )
                if input_text and input_source and st.button("Process Text"):
                    with st.spinner("Processing text..."):
                        success = self.process_input_text(
                            input_text,  input_source)
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

        if prompt := st.chat_input("Ask a question about the uploaded document",
                                   disabled=not st.session_state.file_uploaded):
            st.session_state.messages.append(
                {"role": "user", "content": prompt})
            with main_content.chat_message("user"):
                st.markdown(prompt)

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

        if st.sidebar.button("Logout  ⬅️"):
            navigate_to("logout")

        if st.session_state.authenticated:
            save_token_to_storage(st.session_state.token,
                                  st.session_state.username)


# if __name__ == "__main__":
#    app = OllamaChatApp()
#    app.run()
