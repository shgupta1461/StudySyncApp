import streamlit as st
from pymongo import MongoClient
import bcrypt
import os
from dotenv import load_dotenv
from datetime import datetime
from collections import Counter

load_dotenv()
client = MongoClient(os.getenv("MONGO_URI"))
db = client["studysync"]
sessions_collection = db["sessions"]
users = db["users"]

def insert_session(session_data):
    return sessions_collection.insert_one(session_data)

def get_sessions_for_user(user_email):
    return list(sessions_collection.find({"participants": user_email}))

def get_sessions_hosted_by(user_email):
    return list(sessions_collection.find({"host_email": user_email}))


def propose_slots_to_session(session_id, user_email, proposed_slots):
    sessions_collection.update_one(
        {"_id": session_id},
        {"$push": {
            "proposed_slots": {
                "user": user_email,
                "slots": proposed_slots,
                "submitted_at": datetime.utcnow()
            }
        }}
    )

def get_proposed_slots(session_id):
    session = sessions_collection.find_one({"_id": session_id})
    return session.get("proposed_slots", [])

def finalize_slot(session_id, confirmed_slot):
    sessions_collection.update_one(
        {"_id": session_id},
        {"$set": {
            "final_slot": confirmed_slot,
            "finalized_at": datetime.utcnow()
        }}
    )

def get_session_by_id(session_id):
    return sessions_collection.find_one({"_id": session_id})

def add_resource(session_id, uploader, file_url=None, link=None, filename=None):
    resource = {
        "uploader": uploader,
        "timestamp": datetime.utcnow(),
    }
    if file_url and filename:
        resource["file_url"] = file_url
        resource["filename"] = filename
    if link:
        resource["link"] = link

    sessions_collection.update_one(
        {"_id": session_id},
        {"$push": {"resources": resource}}
    )

def get_resources(session_id):
    session = sessions_collection.find_one({"_id": session_id})
    return session.get("resources", [])


def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def create_user(email, password):
    if users.find_one({"email": email}):
        return False
    users.insert_one({
        "email": email,
        "password": hash_password(password)
    })
    return True

def authenticate_user(email, password):
    user = users.find_one({"email": email})
    if user and check_password(password, user["password"]):
        return user
    return None
