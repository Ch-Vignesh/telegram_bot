# from fastapi import FastAPI, Request, BackgroundTasks
# from pydantic import BaseModel
# from typing import Optional
# import httpx
# import os
# import google.generativeai as genai
# from datetime import datetime
# import pymongo

# # Load from environment or hardcoded for simplicity
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7457191062:AAEch_JWLzoAgXSvJzoEPoa6-mdERkq9uQY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA7HsLE6TZuV_-UZnoE66MZR1ZcRajnEGU")
# MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

# # Gemini Configuration
# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel('gemini-2.5-flash')

# # FastAPI app
# app = FastAPI()

# # MongoDB client setup
# try:
#     mongo_client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
#     mongo_client.server_info()  # Attempt connection
#     db = mongo_client["chat_db"]
#     collection = db["conversations"]
#     db_connected = True
# except Exception as e:
#     print("MongoDB connection failed:", e)
#     db_connected = False

# # Telegram send message URL
# TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

# # Models
# class TelegramMessage(BaseModel):
#     update_id: int
#     message: dict

# # Background function to handle AI reply and DB storage
# async def handle_message(chat_id: int, user_message: str, user_id: int, username: Optional[str] = None):
#     try:
#         gemini_reply = model.generate_content(user_message).text
#     except Exception as e:
#         gemini_reply = "Sorry, I'm having trouble thinking right now. Please try again later."
#         print("Gemini error:", e)

#     # Send reply to Telegram
#     async with httpx.AsyncClient() as client:
#         await client.post(TELEGRAM_API_URL, json={
#             "chat_id": chat_id,
#             "text": gemini_reply
#         })

#     # Store conversation if DB connected
#     if db_connected:
#         try:
#             collection.insert_one({
#                 "user_id": user_id,
#                 "username": username,
#                 "message": user_message,
#                 "response": gemini_reply,
#                 "timestamp": datetime.utcnow()
#             })
#         except Exception as e:
#             print("Failed to save to MongoDB:", e)

# # Telegram webhook endpoint
# @app.post("/webhook/telegram")
# async def telegram_webhook(payload: TelegramMessage, background_tasks: BackgroundTasks):
#     message = payload.message
#     text = message.get("text")
#     chat_id = message["chat"]["id"]
#     user_id = message["from"]["id"]
#     username = message["from"].get("username")

#     if text:
#         background_tasks.add_task(handle_message, chat_id, text, user_id, username)

#     return {"status": "ok"}

# # Root endpoint
# @app.get("/")
# def read_root():
#     return {"message": "Telegram Gemini Therapist Bot is running."}

# import time
# import requests
# import google.generativeai as genai
# import os

# # Setup
# BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7457191062:AAEch_JWLzoAgXSvJzoEPoa6-mdERkq9uQY")
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyA7HsLE6TZuV_-UZnoE66MZR1ZcRajnEGU")
# BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
# genai.configure(api_key=GEMINI_API_KEY)
# model = genai.GenerativeModel('gemini-2.5-flash')

# last_update_id = 0

# def get_updates():
#     global last_update_id
#     response = requests.get(f"{BASE_URL}/getUpdates?offset={last_update_id + 1}")
#     return response.json()

# def send_reply(chat_id, text):
#     requests.post(f"{BASE_URL}/sendMessage", json={
#         "chat_id": chat_id,
#         "text": text
#     })

# while True:
#     updates = get_updates()
#     if 'result' in updates:
#         for update in updates['result']:
#             last_update_id = update['update_id']
#             msg = update['message']['text']
#             chat_id = update['message']['chat']['id']

#             print(f"User: {msg}")
#             try:
#                 response = model.generate_content(msg).text
#             except Exception as e:
#                 response = "Sorry, I couldn’t respond right now."
#                 print("Gemini Error:", e)

#             send_reply(chat_id, response)
#     time.sleep(2)

# version 2

import time
import requests
import google.generativeai as genai
import os
import pymongo
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()


# Setup
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# MongoDB setup
try:
    mongo_client = pymongo.MongoClient(MONGODB_URI, serverSelectionTimeoutMS=2000)
    mongo_client.server_info()  # Test connection
    db = mongo_client["mental_health_bot"]
    conversations = db["conversations"]
    db_connected = True
except Exception as e:
    print("MongoDB connection failed:", e)
    db_connected = False

last_update_id = 0

def get_updates():
    global last_update_id
    response = requests.get(f"{BASE_URL}/getUpdates?offset={last_update_id + 1}")
    return response.json()

def send_reply(chat_id, text):
    requests.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": text
    })

while True:
    updates = get_updates()
    if 'result' in updates:
        for update in updates['result']:
            last_update_id = update['update_id']
            msg = update['message']['text']
            chat_id = update['message']['chat']['id']
            user = update['message']['from']
            user_id = user.get("id")
            username = user.get("username")
            
            print(f"User: {msg}")
            try:
                # prompt = f"You are a multilingual AI mental health companion. Use a friendly, supportive tone. Respond like a CBT therapist helping the user. Message: {msg}"
                prompt = f"""
                You are a multilingual AI mental health companion designed to support users with empathy, clarity, and psychological guidance.
                Your role:
                - Act as a friendly, supportive, non-judgmental therapist trained in CBT (Cognitive Behavioral Therapy) and culturally sensitive care.
                - Use simple, compassionate language to help users understand and manage emotional challenges.
                - if the user messages in their languages you have to reply in their language with english words example : if the user says 'naaku health baaledu' - telugu , you should reply in telugu with english text like 'ayyo avuna jaagratha' .
                - Respond based on both the current message and the user's emotional history (if memory summary is available).
                - Offer gentle nudges toward mental well-being through interactive suggestions like mood-check-ins, self-reflection questions, breathing exercises, games, or helpful resources.
                - If the user appears in distress or mentions suicidal thoughts, record the conversation and escalate internally. Do not panic the user — instead, offer comforting words and subtly suggest talking to a human therapist.
                - When the user requests their progress report or mood history, summarize their emotional trajectory based on past conversations (if available), and offer insights or encouragement.

                Constraints:
                - Never break character. You are always warm, calm, and professionally supportive.
                - If memory, reports, or data from previous sessions are missing (e.g., database or summary not available), acknowledge it politely and continue the conversation without interruption.
                - Always prioritize clarity, emotional safety, and helpfulness. Never guess or assume medical facts. Avoid technical jargon.

                Respond to the following message with this mindset: {msg}
                """

                response = model.generate_content(prompt).text
                print("==========")

            except Exception as e:
                response = "Sorry, I'm having trouble responding right now. Please try again later."
                print("Gemini Error:", e)

            send_reply(chat_id, response)
            print("_________________________")
            print(f"Response: {response}")

            # Save to MongoDB if available
            if db_connected:
                try:
                    conversations.insert_one({
                        "user_id": user_id,
                        "username": username,
                        "message": msg,
                        "response": response,
                        "timestamp": datetime.now(),
                        "language": update['message'].get('language_code', 'unknown')
                    })
                except Exception as e:
                    print("Failed to store conversation:", e)
    time.sleep(2)
