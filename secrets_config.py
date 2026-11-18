"""Read credentials without logging or exporting them."""
import os
from pathlib import Path
from dotenv import dotenv_values

ENV_PATH = Path(__file__).resolve().parent / '.env'


def setting(name, default=''):
    value = os.getenv(name)
    if value:
        return value.strip()
    value = dotenv_values(ENV_PATH).get(name)
    if value:
        return value.strip()
    try:
        import streamlit as st
        return str(st.secrets.get(name, default)).strip()
    except (FileNotFoundError, KeyError):
        return default
