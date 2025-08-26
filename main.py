import os
import time
import threading
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
import google.generativeai as genai
from google.generativeai import types
from flask import Flask
from dotenv import load_dotenv

# --------------------- Load Environment ---------------------
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
OWNER_ID = int(os.getenv("OWNER_ID", 0))
BOT_NAME = os.getenv("BOT_NAME", "Gemini Video Generator")
PORT = int(os.getenv("PORT", 8080))

# --------------------- Flask App ---------------------
app = Flask(__name__)

@app.route("/")
def index():
    return f"{BOT_NAME} is running! 🚀"

# --------------------- Pyrogram Bot ---------------------
bot = Client(
    "gemini_video_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# Store user API keys & steps
user_api_keys = {}
user_steps = {}

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
    genai.configure(api_key=api_key)
    config = types.GenerateVideosConfig(
        aspect_ratio=resolution,
        duration_seconds=duration
    )
    response = genai.generate_videos(prompt=prompt, video_config=config)
    return response.output[0].uri

# --------------------- Bot Commands ---------------------
@bot.on_message(filters.command("start"))
@check_owner
async def start(client, message: Message):
    await message.reply_text(
        f"👋 Welcome to {BOT_NAME}!\n\n"
        "Commands available:\n"
        "/set_api - Set your Gemini API key\n"
        "/generate - Generate a video\n"
        "/status - Check API key status\n"
        "/ping - Check bot health\n"
        "/help - Show help"
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

# --------------------- Generate Flow ---------------------
@bot.on_message(filters.command("generate"))
@check_owner
async def generate_cmd(client, message: Message):
    if OWNER_ID not in user_api_keys:
        await message.reply_text("❌ Please set your API key first using /set_api")
        return

    user_steps[OWNER_ID] = {"step": "prompt"}
    await message.reply_text("✏️ Please send the prompt for video generation.")

@bot.on_message(filters.text & filters.user(OWNER_ID))
async def text_handler(client, message: Message):
    if OWNER_ID not in user_steps:
        return
    
    step_data = user_steps[OWNER_ID]

    # Step 1: Prompt
    if step_data["step"] == "prompt":
        step_data["prompt"] = message.text
        step_data["step"] = "resolution"
        await message.reply_text(
            "📏 Choose resolution:",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("16:9", callback_data="res_16:9"),
                    InlineKeyboardButton("9:16", callback_data="res_9:16")
                ]]
            )
        )
        return

    # Step 3: Duration
    if step_data["step"] == "duration":
        try:
            duration = int(message.text.strip())
        except ValueError:
            duration = 8
        step_data["duration"] = duration
        await message.reply_text("🎬 Video generation started... Please wait.")

        api_key = user_api_keys.get(OWNER_ID)
        prompt = step_data["prompt"]
        resolution = step_data["resolution"]

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
        del user_steps[OWNER_ID]

# --------------------- Inline Button Handler ----------------
@bot.on_callback_query()
async def callback_handler(client, callback_query):
    data = callback_query.data
    if OWNER_ID not in user_steps:
        return
    
    step_data = user_steps[OWNER_ID]

    # Step 2: Resolution
    if data.startswith("res_") and step_data["step"] == "resolution":
        resolution = data.replace("res_", "")
        step_data["resolution"] = resolution
        step_data["step"] = "duration"
        await callback_query.message.reply_text(
            "⏱️ Select duration:",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton("5 sec", callback_data="dur_5"),
                    InlineKeyboardButton("8 sec", callback_data="dur_8"),
                    InlineKeyboardButton("12 sec", callback_data="dur_12")
                ]]
            )
        )
        await callback_query.answer("Resolution selected ✅")

    # Step 3 (Alternative): Duration via buttons
    elif data.startswith("dur_") and step_data["step"] == "duration":
        duration = int(data.replace("dur_", ""))
        step_data["duration"] = duration
        await callback_query.message.reply_text("🎬 Video generation started... Please wait.")

        api_key = user_api_keys.get(OWNER_ID)
        prompt = step_data["prompt"]
        resolution = step_data["resolution"]

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
        del user_steps[OWNER_ID]

# --------------------- Run Flask & Bot ---------------------
def run_flask():
    app.run(host="0.0.0.0", port=PORT)

threading.Thread(target=run_flask).start()
bot.run()
        
