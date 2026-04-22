import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def get_db():
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        key = dict(st.secrets["firebase"])
        cred = credentials.Certificate(key)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db
