# frontend/utils.py
import json
import requests
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from config import settings
import streamlit.components.v1 as components
from string import Template


def init_session_state():
    """Initialize session state variables"""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "username" not in st.session_state:
        st.session_state.username = None
    if "token" not in st.session_state:
        st.session_state.token = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "login"


def save_token_to_storage(token, username):
    """Save token to browser local storage"""
    auth_data = json.dumps({"token": token, "username": username})
    js_code = f"localStorage.setItem('auth_data', '{auth_data}');"
    streamlit_js_eval(js_expressions=js_code, key="save_token")


def load_token_from_storage():
    """Load token from browser local storage"""
    js_code = "localStorage.getItem('auth_data');"
    auth_data_json = streamlit_js_eval(js_expressions=js_code, key="get_token")

    if auth_data_json:
        try:
            auth_data = json.loads(auth_data_json)
            token = auth_data.get("token")
            username = auth_data.get("username")

            if token and username:
                # Validate token
                if validate_token(token):
                    st.session_state.token = token
                    st.session_state.username = username
                    st.session_state.authenticated = True
                    return True
        except Exception as e:
            print(f"Error loading token: {e}")

    return False


def clear_token_from_storage():
    """Clear token from browser local storage"""
    js_code = "localStorage.removeItem('auth_data');"
    streamlit_js_eval(js_expressions=js_code, key="clear_token")


def validate_token(token):
    """Validate the JWT token"""
    try:
        response = requests.post(
            f"{settings.API_URL}/auth/validate-token",
            json={"token": token}
        )

        if response.status_code == 200:
            data = response.json()
            print(data)
            return data.get("valid", False)

        return False
    except Exception as e:
        print(f"Error validating token: {e}")
        return False


def navigate_to(page):
    """Navigate to a specific page"""
    st.session_state.current_page = page
    st.rerun()


def upload_file_to_api_server(uploaded_file):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    # Create a files dictionary for the request
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}

    # Send the file to FastAPI
    response = requests.post(
        f"{settings.API_URL}/file/upload",
        headers=headers,
        files=files
    )

    if response.status_code == 202:
        result = response.json()
        st.success("File uploaded successfully!")
        return result["file_url"]
    else:
        st.error(f"Upload failed: {response.text}")
        return uploaded_file.name


def upload_note_to_api_server(content, title):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    data = {
        "content": content,
        "title": title
    }

    # Send the note to FastAPI
    response = requests.post(
        f"{settings.API_URL}/file/note",
        headers=headers,
        json=data
    )

    if response.status_code == 202:
        result = response.json()
        st.success("Note Submitted successfully!")
        return result["url"]
    else:
        st.error(f"Upload failed: {response.text}")
        return title


def update_note_to_api_server(content, file_url):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    data = {
        "content": content
    }

    # Send the note to FastAPI
    response = requests.patch(
        f"{settings.API_URL}{file_url}",
        headers=headers,
        json=data
    )

    if response.status_code == 200:
        return True

    st.error(f"Update failed: {response.text}")
    return False


def submit_link(link, custom_headers):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    data = {
        "url": link,
        "headers": custom_headers,
    }

    response = requests.post(
        f"{settings.API_URL}/links/submit",
        headers=headers,
        json=data
    )

    if response.status_code == 202:
        return True

    st.error("failed to submit link")
    return False


def submit_bulk_links(links, custom_headers):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    data = {
        "urls": links,
        "headers": custom_headers,
    }

    response = requests.post(
        f"{settings.API_URL}/links/bulk",
        headers=headers,
        json=data
    )

    if response.status_code == 202:
        return True

    st.error("failed to submit links")
    return False


def submit_recursive_crawl_link(link, custom_headers):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    data = {
        "url": link,
        "headers": custom_headers,
    }

    response = requests.post(
        f"{settings.API_URL}/links/crawl",
        headers=headers,
        json=data
    )

    if response.status_code == 202:
        return True

    st.error("failed to submit links")
    return False


def fetch_documents(prompt):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    data = {
        "include_sources": st.session_state.include_selected,
        "exclude_sources": st.session_state.exclude_selected,
        "window_size": st.session_state.context_window_size,
        "prompt": prompt,
    }

    if st.session_state.source_type:
        data["source_type"] = st.session_state.source_type

    response = requests.post(
        f"{settings.API_URL}/documents/search",
        headers=headers,
        json=data
    )

    docs = []
    if response.status_code == 200:
        result = response.json()
        docs = result["documents"]

    return docs


def fetch_notes(skip=0, limit=100):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}",
        "Content-Type": "application/json"
    }

    params = {"skip": skip, "limit": limit}
    response = requests.get(
        f"{settings.API_URL}/file/note",
        headers=headers,
        params=params
    )

    result = {"notes": [], "total": 0}
    if response.status_code == 200:
        result = response.json()
    else:
        result

    return result


def fetch_file(file_url):
    headers = {
        "Authorization": f"Bearer {st.session_state.token}"
    }

    response = requests.get(
        f"{settings.API_URL}{file_url}",
        headers=headers
    )

    if response.status_code == 200:
        return response.content.decode("utf-8")

    return "failed to fetch  content"


# TODO: WIP markdown editor
def create_markdown_editor(default_content, key, height):
    # Define the HTML and JavaScript for the markdown editor
    default_content_escaped = default_content.replace(
        '"', '\\"').replace('\n', '\\n')
    template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8"/>
        <title>Markdown Editor</title>
        <style>
            body {
                margin: 0;
                padding: 0;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            }
            
            #editor {
                display: flex;
                position: relative;
                width: 100%;
                height: 600px;
            }
            
            #markdown-content,
            #html-preview {
                padding: 20px;
                width: 50%;
                height: 100%;
                box-sizing: border-box;
                overflow-y: auto;
            }
            
            #markdown-content {
                background: #f8f9fa;
                border: none;
                border-radius: 4px 0 0 4px;
                color: #212529;
                outline: none;
                resize: none;
                font-family: monospace;
                font-size: 14px;
                line-height: 1.5;
            }
            
            #html-preview {
                background: #ffffff;
                border-radius: 0 4px 4px 0;
                border-left: 1px solid #dee2e6;
                color: #212529;
            }
            
            #html-preview h1, #html-preview h2, #html-preview h3, 
            #html-preview h4, #html-preview h5, #html-preview h6 {
                margin-top: 0;
                margin-bottom: 0.5rem;
                font-weight: 500;
                line-height: 1.2;
            }
            
            #html-preview h1 { font-size: 2.5rem; }
            #html-preview h2 { font-size: 2rem; }
            #html-preview h3 { font-size: 1.75rem; }
            #html-preview h4 { font-size: 1.5rem; }
            #html-preview h5 { font-size: 1.25rem; }
            #html-preview h6 { font-size: 1rem; }
            
            #html-preview p {
                margin-top: 0;
                margin-bottom: 1rem;
            }
            
            #html-preview a {
                color: #007bff;
                text-decoration: none;
            }
            
            #html-preview a:hover {
                text-decoration: underline;
            }
            
            #html-preview pre {
                background-color: #f8f9fa;
                border-radius: 4px;
                padding: 1rem;
                overflow: auto;
            }
            
            #html-preview code {
                font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                font-size: 87.5%;
                color: #e83e8c;
            }
            
            #html-preview pre code {
                font-size: inherit;
                color: inherit;
            }
            
            #html-preview blockquote {
                padding: 0.5rem 1rem;
                margin-left: 0;
                margin-right: 0;
                border-left: 0.25rem solid #dee2e6;
            }
            
            #html-preview ul, #html-preview ol {
                padding-left: 2rem;
                margin-top: 0;
                margin-bottom: 1rem;
            }
            
            #html-preview img {
                max-width: 100%;
                height: auto;
            }
            
            #html-preview table {
                width: 100%;
                margin-bottom: 1rem;
                color: #212529;
                border-collapse: collapse;
            }
            
            #html-preview table th,
            #html-preview table td {
                padding: 0.75rem;
                vertical-align: top;
                border-top: 1px solid #dee2e6;
            }
            
            #html-preview table thead th {
                vertical-align: bottom;
                border-bottom: 2px solid #dee2e6;
            }
            
            .editor-toolbar {
                display: flex;
                background: #f1f3f5;
                padding: 8px;
                border-radius: 4px 4px 0 0;
            }
            
            .editor-toolbar button {
                background: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #495057;
                cursor: pointer;
                font-size: 14px;
                margin-right: 4px;
                padding: 4px 8px;
            }
            
            .editor-toolbar button:hover {
                background: #e9ecef;
            }
            
            .editor-container {
                display: flex;
                flex-direction: column;
                width: 100%;
            }
        </style>
    </head>
    <body>
        <div class="editor-container">
            <div class="editor-toolbar">
                <button onclick="insertMarkdown('# ')">H1</button>
                <button onclick="insertMarkdown('## ')">H2</button>
                <button onclick="insertMarkdown('### ')">H3</button>
                <button onclick="insertMarkdown('**', '**')">Bold</button>
                <button onclick="insertMarkdown('*', '*')">Italic</button>
                <button onclick="insertMarkdown('[', '](url)')">Link</button>
                <button onclick="insertMarkdown('- ')">List</button>
                <button onclick="insertMarkdown('1. ')">Numbered List</button>
                <button onclick="insertMarkdown('> ')">Quote</button>
                <button onclick="insertMarkdown('```\\n', '\\n```')">Code</button>
                <button onclick="insertMarkdown('---\\n')">Divider</button>
            </div>
            <div id="editor">
                <textarea id="markdown-content" placeholder="Write your markdown here..."></textarea>
                <div id="html-preview"></div>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.5/dist/purify.min.js"></script>
        <script>
            // Initialize with default content
            const defaultContent = "$default_content";
            document.getElementById('markdown-content').value = defaultContent;
            
            // Function to insert markdown syntax
            function insertMarkdown(before, after = '') {
                const textarea = document.getElementById('markdown-content');
                const start = textarea.selectionStart;
                const end = textarea.selectionEnd;
                const selectedText = textarea.value.substring(start, end);
                const newText = before + selectedText + after;
                
                textarea.value = 
                    textarea.value.substring(0, start) + 
                    newText + 
                    textarea.value.substring(end);
                
                // Update preview
                updatePreview();
                
                // Set cursor position
                const newCursorPos = start + before.length + selectedText.length + after.length;
                textarea.focus();
                textarea.setSelectionRange(newCursorPos, newCursorPos);
                
                // Send value to Streamlit
                sendValueToStreamlit();
            }
            
            // Function to update preview
            function updatePreview() {
                const markdownContent = document.getElementById('markdown-content').value;
                const htmlContent = marked.parse(markdownContent);
                const sanitizedHtml = DOMPurify.sanitize(htmlContent, {USE_PROFILES: {html: true}});
                document.getElementById('html-preview').innerHTML = sanitizedHtml;
            }
            
            // Function to send value to Streamlit
            function sendValueToStreamlit() {
                const markdownContent = document.getElementById('markdown-content').value;
                console.log(markdownContent)
                window.parent.postMessage({
                    isStreamlitMessage: true,
                    type: 'streamlit:setComponentValue',
                    value: markdownContent
                }, '*');
            }
            
            function initStreamlit() {
                window.parent.postMessage({
                    isStreamlitMessage: true,
                    type: 'streamlit:componentReady'
                }, '*');
            }
            // Listen for acknowledgment from Streamlit
            window.addEventListener('message', function(event) {
                console.log(event.data.type)
                if (event.data.type === 'streamlit:componentReady') {
                    log('Component ready event received');
                    // Send initial value
                    sendValueToStreamlit();
                } else {
                    log('Received message: ' + JSON.stringify(event.data).substring(0, 50) + '...');
                }
            });


            // Event listener for textarea changes
            document.getElementById('markdown-content').addEventListener('input', function() {
                updatePreview();
                sendValueToStreamlit();
            });
            
            // Initialize the component
            document.addEventListener('DOMContentLoaded', function() {
                updatePreview();
                // Initialize Streamlit component after a short delay
                setTimeout(function() {
                    initStreamlit();
                    sendValueToStreamlit();
                }, 100);
            });

            // Initial preview update
            initStreamlit();
            updatePreview();
            sendValueToStreamlit()
        </script>
    </body>
    </html>
    """)

    html_content = template.substitute(default_content=default_content_escaped)

    # Render the HTML component
    component_value = components.html(html_content, height=500)

    return component_value
