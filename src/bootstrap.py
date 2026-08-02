import streamlit as st

from src.db import get_connection
from src.seed_data import ensure_seeded


@st.cache_resource(show_spinner="Initializing governance database...")
def init_app():
    conn, backend = get_connection()
    ensure_seeded(conn)
    return conn, backend
