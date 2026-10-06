import os
import streamlit as st
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(env_path)

def get_secret(key):
    """優先讀取 Streamlit Cloud 的 Secrets，本地開發則 fallback 用 .env"""
    try:
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key)

# Where data lives. Locally: the project folder. On Railway: the permanent volume (set DATA_DIR=/data).
DATA_DIR = os.getenv("DATA_DIR") or os.path.dirname(os.path.abspath(__file__))
os.makedirs(DATA_DIR, exist_ok=True)

# Public demo mode: hides Canvas sync and uses sample data (set DEMO_MODE=1 on Railway)
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

# 所有課程資料統一存放的資料夾
WATCH_FOLDER = os.path.join(DATA_DIR, "Haas_Course")
os.makedirs(WATCH_FOLDER, exist_ok=True)