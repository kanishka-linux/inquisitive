import streamlit as st
import requests
from frontend.utils import navigate_to, save_token_to_storage, clear_token_from_storage
from frontend.config import settings


def login_user(email, password):
    """Login a user using JWT authentication with email only"""
    try:
        # FastAPI-Users expects email in the "username" field
        login_data = {
            "username": email,  # This is the email field for FastAPI-Users
            "password": password
        }

        response = requests.post(
            f"{settings.API_URL}/auth/jwt/login",
            data=login_data  # Use data, not json for form data
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get("access_token")

            if token:
                # Save token to session state
                st.session_state.token = token
                st.session_state.username = email  # Just use email as the identifier
                st.session_state.authenticated = True

                # Save token to browser storage

                save_token_to_storage(token, email)

                return True, "Login successful"

            return False, "Invalid token received"

        return False, f"Login failed: {response.text}"
    except Exception as e:
        return False, f"Login error: {str(e)}"


def register_user(email, password):
    """Register a new user with just email and password"""
    if not settings.ALLOW_AUTO_USER_REGISTER:
        return False, "Registration not allowed. Please contact the Admin"
    try:
        response = requests.post(
            f"{settings.API_URL}/auth/register",
            json={"email": email, "password": password}  # No username
        )

        if response.status_code == 201:
            return True, "Registration successful"

        return False, f"Registration failed: {response.text}"
    except Exception as e:
        return False, f"Registration error: {str(e)}"


def logout_user():
    """Logout user by clearing the token"""
    # Clear token from browser storage

    # Reset session state
    st.session_state.token = None
    st.session_state.username = None  # This clears the email
    st.session_state.authenticated = False
    st.session_state.current_page = "login"
    st.session_state.messages = []

    clear_token_from_storage()


def show_login_page():
    st.title("Login")

    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            if email and password:
                success, message = login_user(email, password)
                if success:
                    st.success(message)
                    navigate_to("rag")
                else:
                    st.error(message)
            else:
                st.warning("Please enter both email and password")

    st.markdown("---")
    st.write("Don't have an account?")
    if st.button("Register"):
        navigate_to("register")


def show_register_page():
    st.title("Register")

    with st.form("register_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        submit = st.form_submit_button("Register")

        if submit:
            if not (email and password and confirm_password):
                st.warning("Please fill out all fields")
            elif password != confirm_password:
                st.warning("Passwords do not match")
            else:
                success, message = register_user(email, password)
                if success:
                    st.success(message)
                    navigate_to("login")
                else:
                    st.error(message)

    st.markdown("---")
    st.write("Already have an account?")
    if st.button("Login"):
        navigate_to("login")
