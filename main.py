import os
import time
import threading
from pyrogram import Client, filters
from pyrogram.types import Message
import google.generativeai as genai
from google.generativeai import types
from flask import Flask
from dotenv import load_dotenv

# --------------------- Load Environment ---------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
BOT_NAME = os.getenv("BOT_NAME", "Gemini Video Generator")
PORT = int(os.getenv("PORT", 8080))

# --------------------- Flask App ---------------------
app = Flask(__name__)

@app.route("/")
def index():
    return f"{BOT_NAME} is running! 🚀"

# --------------------- Pyrogram Bot ---------------------
bot = Client("gemini_video_bot", bot_token=BOT_TOKEN)

# Store user API keys
user_api_keys = {}

# --------------------- Helper Functions ---------------------
def check_owner(func):
    async def wrapper(client, message: Message):
        if message.from_user.id != OWNER_ID:
            await message.reply_text("❌ You are not authorized to use this bot.")
            return
        await func(client, message)
    return wrapper

def generate_video(api_key, prompt, resolution, duration):
    """
    Gemini video generation function.
    Returns video URL or path.
    """
    client = genai.Client(api_key=api_key)
    config = types.GenerateVideosConfig(
        aspect_ratio=resolution,
        duration_seconds=duration
    )
    response = client.generate_videos(prompt=prompt, video_config=config)
    video_url = response.output[0].uri
    return video_url

# --------------------- Bot Commands ---------------------
@bot.on_message(filters.command("start"))
@check_owner
async def start(client, message: Message):
    await message.reply_text(
        "👋 Welcome to Gemini Video Generator!\n\n"
        "Commands available:\n"
        "/set_api - Set your Gemini API key\n"
        "/generate - Generate a video\n"
        "/status - Check API key status\n"
        "/ping - Check bot health\n"
        "/help - Show this help message"
    )

@bot.on_message(filters.command("help"))
@check_owner
async def help_cmd(client, message: Message):
    await message.reply_text(
        "📚 Help Commands:\n"
        "/set_api YOUR_API_KEY - Set your Gemini API key\n"
        "/generate - Generate video (prompt → resolution → duration)\n"
        "/status - Check if API key is set\n"
        "/ping - Check bot responsiveness"
    )

@bot.on_message(filters.command("ping"))
@check_owner
async def ping_cmd(client, message: Message):
    await message.reply_text("🏓 Pong! Bot is alive.")

@bot.on_message(filters.command("set_api"))
@check_owner
async def set_api(client, message: Message):
    try:
        api_key = message.text.split(" ", 1)[1]
        user_api_keys[OWNER_ID] = api_key
        await message.reply_text("✅ API key saved successfully!")
    except IndexError:
        await message.reply_text("⚠️ Usage: /set_api YOUR_API_KEY")

@bot.on_message(filters.command("status"))
@check_owner
async def status(client, message: Message):
    api_status = "✅ Set" if OWNER_ID in user_api_keys else "❌ Not Set"
    await message.reply_text(f"API key status: {api_status}")

@bot.on_message(filters.command("generate"))
@check_owner
async def generate(client, message: Message):
    if OWNER_ID not in user_api_keys:
        await message.reply_text("❌ Please set your API key first using /set_api")
        return
    
    await message.reply_text("✏️ Please send the prompt for video generation.")
    
    @bot.on_message(filters.text & filters.user(OWNER_ID))
    async def receive_prompt(client, msg: Message):
        prompt = msg.text
        await msg.reply_text("📏 Choose resolution: 16:9 or 9:16. Example: 16:9")
        
        @bot.on_message(filters.text & filters.user(OWNER_ID))
        async def receive_resolution(client, res_msg: Message):
            resolution = res_msg.text.strip()
            if resolution not in ["16:9", "9:16"]:
                resolution = "16:9"
            await res_msg.reply_text("⏱️ Enter duration in seconds (e.g., 8)")
            
            @bot.on_message(filters.text & filters.user(OWNER_ID))
            async def receive_duration(client, dur_msg: Message):
                try:
                    duration = int(dur_msg.text.strip())
                except ValueError:
                    duration = 8
                await dur_msg.reply_text("🎬 Video generation started... Please wait.")
                
                api_key = user_api_keys[OWNER_ID]
                
                def task():
                    for i in range(0, duration, 5):
                        time.sleep(5)
                        try:
                            bot.send_message(OWNER_ID, f"⏳ Generating... {i}/{duration} sec elapsed")
                        except:
                            pass
                    video_url = generate_video(api_key, prompt, resolution, duration)
                    bot.send_message(OWNER_ID, f"✅ Video ready: {video_url}")
                
                threading.Thread(target=task).start()

# --------------------- Run Flask & Bot ---------------------
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_flask).start()
bot.run()
