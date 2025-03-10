# frontend/utils.py
import json
import requests
import streamlit as st
from streamlit_js_eval import streamlit_js_eval
from config import settings


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
        result = response.json()
        st.success(f"{result}")
        return True
    else:
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
        result = response.json()
        st.success(f"{result}")
        return True
    else:
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
        result = response.json()
        st.success(f"{result}")
        return True
    else:
        st.error("failed to submit links")
        return False
