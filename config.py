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

# 所有課程資料統一存放的資料夾，位置跟著程式碼走，本機、雲端都適用
WATCH_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Haas_Course")
os.makedirs(WATCH_FOLDER, exist_ok=True)