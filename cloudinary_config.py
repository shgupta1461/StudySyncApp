import streamlit as st
import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv
import os

# Load variables from .env file
load_dotenv()

cloudinary.config(
    cloud_name=st.secrets["CLOUDINARY_CLOUD_NAME"],
    api_key=st.secrets["CLOUDINARY_API_KEY"],
    api_secret=st.secrets["CLOUDINARY_API_SECRET"],
    secure=True
)
