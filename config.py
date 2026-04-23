import os
from dotenv import load_dotenv

# Load local env (works only locally)
load_dotenv()

# Safe secret getter (local + cloud)
def get_secret(key, default=None):
    try:
        import streamlit as st
        return os.getenv(key) or st.secrets.get(key, default)
    except Exception:
        return os.getenv(key, default)

# ===============================
# 🔑 Core LLM
# ===============================
GROQ_API_KEY = get_secret("GROQ_API_KEY")
GROQ_MODEL = get_secret("GROQ_MODEL", "llama-3.3-70b-versatile")

# ===============================
# 🌐 Web Search
# ===============================
TAVILY_API_KEY = get_secret("TAVILY_API_KEY")

# ===============================
# ☁️ Google Drive
# ===============================
GOOGLE_CREDENTIALS_PATH = get_secret(
    "GOOGLE_CREDENTIALS_PATH",
    "./credentials/google_credentials.json"
)

GOOGLE_TOKEN_PATH = get_secret(
    "GOOGLE_TOKEN_PATH",
    "./credentials/google_token.json"
)

# ===============================
# 📂 Local Trial Data
# ===============================
TRIAL_DATA_PATH = get_secret(
    "TRIAL_DATA_PATH",
    "./trial_data"
)

# ===============================
# 📝 Notion (Optional)
# ===============================
NOTION_API_KEY = get_secret("NOTION_API_KEY")