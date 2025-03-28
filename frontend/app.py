import streamlit as st
from utils import init_session_state, load_token_from_storage
from auth_page import show_login_page, show_register_page, logout_user
from streamlit_ui import OllamaChatApp, SVG_ICON

st.set_page_config(
    page_title="Inquisitive",
    page_icon=SVG_ICON,
    layout="wide")

# Initialize session state
init_session_state()

app = OllamaChatApp()

# Main app routing


def main():
    # current-page is set to rag only after
    # successful authentication is done
    if st.session_state.current_page == "rag":
        app.run()
    elif st.session_state.current_page == "login":
        load_token_from_storage()
        if st.session_state.authenticated:
            app.run()
        else:
            show_login_page()
    elif st.session_state.current_page == "register":
        show_register_page()
    elif st.session_state.current_page == "logout":
        logout_user()
        st.success("You have been logged out successfully!")
        if st.button("Click here to Login again"):
            show_login_page()
    else:
        show_login_page()


if __name__ == "__main__":
    main()
