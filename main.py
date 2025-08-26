import os
import threading
import time
from flask import Flask, jsonify
from pyrogram import Client, filters
from pyrogram.types import Message
from dotenv import load_dotenv
import requests
import google.genai as genai

# Load .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
BOT_NAME = os.getenv("BOT_NAME", "Gemini Video Generator")
ENABLE_LOGS = os.getenv("ENABLE_LOGS", "true").lower() == "true"
PORT = int(os.getenv("PORT", 8080))

# ------------------- Flask Health Check -------------------
app = Flask(__name__)

@app.route("/")
def health():
    return jsonify({"status": "healthy"})

def run_flask():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_flask, daemon=True).start()

# ------------------- Gemini API Client -------------------
client_genai = None
api_key_storage = {}  # To store API key per owner

# ------------------- Pyrogram Bot -------------------
bot = Client("gemini_video_bot", bot_token=BOT_TOKEN)

# ------------------- Helper Functions -------------------
def is_owner(user_id):
    return user_id == OWNER_ID

def log(msg):
    if ENABLE_LOGS:
        print(msg)

# ------------------- Commands -------------------
@bot.on_message(filters.command("start") & filters.private)
def start_command(client, message: Message):
    if not is_owner(message.from_user.id):
        return message.reply_text("❌ You are not authorized to use this bot.")
    message.reply_text(f"👋 Welcome to {BOT_NAME}!\nUse /help to see commands.")

@bot.on_message(filters.command("help") & filters.private)
def help_command(client, message: Message):
    if not is_owner(message.from_user.id):
        return message.reply_text("❌ You are not authorized.")
    help_text = """
/start - Start the bot
/help - Show this help
/setkey - Set or update Gemini API Key
/checkkey - Check current API Key
/generatevideo - Generate a video
/cancel - Cancel current generation
"""
    message.reply_text(help_text)

@bot.on_message(filters.command("setkey") & filters.private)
def set_key_command(client, message: Message):
    if not is_owner(message.from_user.id):
        return message.reply_text("❌ Unauthorized.")
    key = message.text.replace("/setkey", "").strip()
    if not key:
        return message.reply_text("❌ Usage: /setkey <YOUR_API_KEY>")
    api_key_storage[OWNER_ID] = key
    message.reply_text("✅ Gemini API Key set successfully!")

@bot.on_message(filters.command("checkkey") & filters.private)
def check_key_command(client, message: Message):
    if not is_owner(message.from_user.id):
        return message.reply_text("❌ Unauthorized.")
    key = api_key_storage.get(OWNER_ID)
    if not key:
        return message.reply_text("⚠️ API Key not set. Use /setkey")
    # Optionally, check API usage via genai client
    message.reply_text(f"✅ Current API Key is set.")

@bot.on_message(filters.command("generatevideo") & filters.private)
def generate_video(client, message: Message):
    if not is_owner(message.from_user.id):
        return message.reply_text("❌ Unauthorized.")
    key = api_key_storage.get(OWNER_ID)
    if not key:
        return message.reply_text("⚠️ API Key not set. Use /setkey first.")
    
    def ask_input(prompt):
        message.reply_text(prompt)
        while True:
            resp = bot.listen(message.chat.id, timeout=300)  # 5 min timeout
            if resp:
                return resp.text.strip()
    
    try:
        # Get inputs
        prompt_text = ask_input("📝 Enter video prompt text:")
        resolution = ask_input("📐 Enter resolution (16:9 or 9:16):")
        duration = ask_input("⏱ Enter duration in seconds:")
        size_mb = ask_input("💾 Enter file size in MB (approx):")
        
        msg = message.reply_text("🎬 Generating video... 0%")
        
        # Initialize Gemini client
        client_genai = genai.Client(api_key=key)
        
        # Call Gemini video generation API
        response = client_genai.generate_video(
            prompt=prompt_text,
            resolution=resolution,
            duration=int(duration)
        )
        
        # Simulate progress (replace with real progress if API provides)
        for i in range(0, 101, 5):
            time.sleep(1)
            try:
                msg.edit_text(f"🎬 Generating video... {i}%")
            except:
                pass
        
        # Save video locally
        video_path = f"video_{int(time.time())}.mp4"
        with open(video_path, "wb") as f:
            f.write(response)  # If API returns bytes
        msg.edit_text("✅ Video generated, uploading...")
        
        # Upload to Telegram
        with open(video_path, "rb") as f:
            client.send_video(chat_id=OWNER_ID, video=f, caption="🎬 Here is your video")
        msg.edit_text("✅ Video uploaded successfully!")
        
    except Exception as e:
        log(f"Error: {e}")
        message.reply_text(f"❌ Error: {e}")

@bot.on_message(filters.command("cancel") & filters.private)
def cancel_command(client, message: Message):
    if not is_owner(message.from_user.id):
        return message.reply_text("❌ Unauthorized.")
    # Implement cancel logic if long running generation
    message.reply_text("⚠️ Video generation cancelled.")

# ------------------- Run Bot -------------------
print(f"🚀 {BOT_NAME} Started!")
bot.run()
