import os
import asyncio
from fastapi import FastAPI
import httpx
import motor.motor_asyncio
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv
from contextlib import asynccontextmanager

load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

app = FastAPI()

class MentalHealthBot:
    def __init__(self, bot_token: str, gemini_api_key: str, mongodb_uri: str):
        self.bot_token = bot_token
        self.gemini_api_key = gemini_api_key
        self.mongodb_uri = mongodb_uri
        self.base_url = f"https://api.telegram.org/bot{self.bot_token}"
        self.client = httpx.AsyncClient(base_url=self.base_url)

        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        self.mongo_client = motor.motor_asyncio.AsyncIOMotorClient(self.mongodb_uri)
        self.db = self.mongo_client["mental_health_bot"]
        self.conversations = self.db["conversations"]
        self.last_update_id = 0

    async def get_updates(self):
        """Fetch updates from Telegram API."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(f"{self.base_url}/getUpdates?offset={self.last_update_id + 1}")
                return response.json()
            except Exception as e:
                print(f"Error fetching updates: {e}")
                return {"result": []}

    async def process_update(self, update: dict):
        """Process a single Telegram update."""
        self.last_update_id = update['update_id']
        msg = update['message']['text']
        chat_id = update['message']['chat']['id']
        user = update['message']['from']
        user_id = user.get("id")
        username = user.get("username")
        print(f"User: {msg}")

        await self.send_chat_action(chat_id, "typing")

        response = await self.generate_response(
            msg=msg,
            username=username,
            user_id=user_id
        )

        await self.send_message(chat_id, response)
        print(f"Response: {response}")

        await self.store_conversation(user_id, username, msg, response, update)

    async def generate_response(self, msg: str, username, user_id: int) -> str:
        """Generate a response using Gemini API with user history context."""
        summary = await self.get_user_summary(user_id)
        prompt = f"""
        You are a multilingual AI mental health companion designed to support users with empathy, clarity, and psychological guidance.
        Your role:
        - Act as a friendly, supportive, non-judgmental therapist trained in CBT (Cognitive Behavioral Therapy) and culturally sensitive care.
        - The conversation should feel like a continuous dialogue, not like a fresh message each time.
        - Always respond in a warm, calm, and professional manner, using simple language.
        - Use simple, compassionate language to help users understand and manage emotional challenges.
        - If the user messages in their language, reply in their language with English words. For example, if the user says 'naaku health baaledu' (Telugu), reply in Telugu with English text like 'ayyo avuna jaagratha'.
        - Respond based on both the current message and the user's emotional history (if memory summary is available).
        - Offer gentle nudges toward mental well-being through interactive suggestions like mood-check-ins, self-reflection questions, breathing exercises, games, or helpful resources.
        - If the user appears in distress or mentions suicidal thoughts, record the conversation and escalate internally. Do not panic the user — instead, offer comforting words and subtly suggest talking to a human therapist.
        - When the user requests their progress report or mood history, summarize their emotional trajectory based on past conversations (if available), and offer insights or encouragement.

        Constraints:
        - Never break character. You are always warm, calm, and professionally supportive.
        - If memory, reports, or data from previous sessions are missing (e.g., database or summary not available), acknowledge it politely and continue the conversation without interruption.
        - Always prioritize clarity, emotional safety, and helpfulness. Never guess or assume medical facts. Avoid technical jargon.
        -username : {username}
        User's recent conversation summary: {summary}
        Note : carefully analyse the summary and use it to inform your response. talk to the user as if you are continuing a conversation, not starting fresh.
        Respond to the following message with this mindset: {msg}
        """
        try:
            response = await asyncio.to_thread(self.model.generate_content, prompt)
            return response.text
        except Exception as e:
            print(f"Gemini Error: {e}")
            return "Sorry, I'm having trouble responding right now. Please try again later."

# Add the new send_chat_action method
    async def send_chat_action(self, chat_id: int, action: str):
        try:
            await self.client.post("/sendChatAction", json={
                "chat_id": chat_id,
                "action": action
            })
        except Exception as e:
            print(f"Error sending chat action: {e}")

    async def send_message(self, chat_id: int, text: str):
        """Send a message to the Telegram chat."""
        async with httpx.AsyncClient() as client:
            try:
                await client.post(f"{self.base_url}/sendMessage", json={
                    "chat_id": chat_id,
                    "text": text
                })
            except Exception as e:
                print(f"Error sending message: {e}")

    async def store_conversation(self, user_id: int, username: str, msg: str, response: str, update: dict):
        """Store the conversation in MongoDB."""
        try:
            await self.conversations.insert_one({
                "user_id": user_id,
                "username": username,
                "message": msg,
                "response": response,
                "timestamp": datetime.now(),
                "language": update['message'].get('language_code', 'unknown')
            })
        except Exception as e:
            print(f"Failed to store conversation: {e}")

    async def get_user_summary(self, user_id: int) -> str:
        """Retrieve a summary of the user's recent conversations."""
        try:
            recent_convos = await self.conversations.find({"user_id": user_id}).sort("timestamp", -1).limit(10).to_list(length=10)
            if recent_convos:
                return "Recent conversation topics: " + ", ".join([convo['message'] for convo in recent_convos])
            return "No past conversations found."
        except Exception as e:
            print(f"Failed to retrieve user summary: {e}")
            return "Unable to retrieve past conversations."

    async def poll_updates(self):
        """Continuously poll for Telegram updates."""
        while True:
            updates = await self.get_updates()
            if 'result' in updates:
                for update in updates['result']:
                    await self.process_update(update)
            await asyncio.sleep(0.5)

# Initialize bot instance
bot = MentalHealthBot(
    bot_token=BOT_TOKEN,
    gemini_api_key=GEMINI_API_KEY,
    mongodb_uri=MONGODB_URI
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler to start the polling loop."""
    task = asyncio.create_task(bot.poll_updates())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "Bot is running"}
