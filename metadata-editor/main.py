import streamlit as st
import pandas as pd
from utils import load_from_indexeddb, create_pydantic_model
import json

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = []
if 'model' not in st.session_state:
    st.session_state.model = None

# Import page modules
import data_loading
import data_browsing
import data_search

def handle_url_params():
    if 'data' in st.query_params:
        data_str = st.query_params['data']
        st.session_state.data = json.loads(data_str)
        if st.session_state.data and isinstance(st.session_state.data[0], dict):
            create_pydantic_model(st.session_state.data[0])
        st.query_params.clear()
        st.rerun()

st.set_page_config(page_title="JSON Data Editor", layout="wide")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio("", ["Data Loading", "Data Browsing"])

if page == "Data Loading":
    data_loading.load_data_page()
elif page == "Data Browsing":
    data_browsing.browse_data_page()

if __name__ == "__main__":
    load_from_indexeddb()
    handle_url_params()

# Display current data count
st.sidebar.write(f"当前数据条数: {len(st.session_state.data)}")