import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

_db = None

def get_db():
    global _db
    if _db is not None:
        return _db

    if not firebase_admin._apps:
        key = json.loads(st.secrets["FIREBASE_JSON"])
        key["private_key"] = key["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(key)
        firebase_admin.initialize_app(cred)

    _db = firestore.client()
    return _db
