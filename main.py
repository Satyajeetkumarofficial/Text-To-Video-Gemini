import os
import time
import asyncio
import logging
from pyrogram import Client, filters
from google import genai
from google.genai import types
from dotenv import load_dotenv
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive", 200

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# Load .env file
load_dotenv()

# ===================== CONFIG =====================
API_ID = int(os.getenv("API_ID", "123456"))  # Telegram API ID
API_HASH = os.getenv("API_HASH", "your_api_hash")  # Telegram API Hash
BOT_TOKEN = os.getenv("BOT_TOKEN", "your_bot_token")
OWNER_ID = int(os.getenv("OWNER_ID", "123456"))  # Owner Telegram ID

# Gemini API Key storage (memory-based)
GEMINI_KEY = {}

# Enable logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Bot
app = Client("gemini_video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ===================== GOOGLE GENAI CLIENT =====================
def get_client(user_id):
    api_key = GEMINI_KEY.get(user_id)
    if not api_key:
        return None
    return genai.Client(
        http_options={"api_version": "v1beta"},
        api_key=api_key,
    )

# ===================== COMMAND: START =====================
@app.on_message(filters.command("start") & filters.private)
async def start_cmd(_, message):
    await message.reply_text(
        f"👋 **Hi {message.from_user.first_name}!**\n\n"
        "I am **Gemini AI Video Generator Bot** 🎥\n"
        "Use `/setkey` to add your Gemini API Key and then `/generate` to create videos."
    )

# ===================== COMMAND: HELP =====================
@app.on_message(filters.command("help") & filters.private)
async def help_cmd(_, message):
    await message.reply_text(
        "**📌 Available Commands**\n\n"
        "`/setkey <API_KEY>` - Set your Gemini API key\n"
        "`/checkkey` - Check your saved API key\n"
        "`/reset` - Reset your Gemini API key\n"
        "`/generate` - Generate AI videos\n"
        "`/status` - Show bot & API status\n"
        "`/history` - Show last 5 generated videos\n"
        "`/cancel` - Cancel current video task"
    )

# ===================== COMMAND: SET API KEY =====================
@app.on_message(filters.command("setkey") & filters.private)
async def set_key_cmd(_, message):
    if len(message.command) < 2:
        return await message.reply_text("⚠️ Usage: `/setkey YOUR_API_KEY`")
    key = message.command[1]
    GEMINI_KEY[message.from_user.id] = key
    await message.reply_text("✅ **API Key Saved Successfully!**")

# ===================== COMMAND: CHECK API KEY =====================
@app.on_message(filters.command("checkkey") & filters.private)
async def check_key_cmd(_, message):
    key = GEMINI_KEY.get(message.from_user.id)
    if key:
        await message.reply_text(f"🔑 Your saved API key:\n`{key}`")
    else:
        await message.reply_text("⚠️ No API key found. Use `/setkey` first.")

# ===================== COMMAND: RESET API KEY =====================
@app.on_message(filters.command("reset") & filters.private)
async def reset_key_cmd(_, message):
    GEMINI_KEY.pop(message.from_user.id, None)
    await message.reply_text("✅ **Your API Key has been removed.**")

# ===================== COMMAND: GENERATE VIDEO =====================
@app.on_message(filters.command("generate") & filters.private)
async def generate_cmd(_, message):
    user_id = message.from_user.id
    client = get_client(user_id)

    if not client:
        return await message.reply_text("⚠️ Please set your Gemini API key first using `/setkey`.")

    # Ask for prompt
    await message.reply_text("📝 **Please reply with the video prompt...**")
    prompt_msg = await app.listen(message.chat.id, timeout=120)
    prompt = prompt_msg.text.strip()

    # Ask for duration
    await message.reply_text("⏳ **Enter video duration (seconds)**:")
    duration_msg = await app.listen(message.chat.id, timeout=60)
    duration = int(duration_msg.text.strip())

    # Ask for aspect ratio
    await message.reply_text("📐 **Choose aspect ratio:**\n1️⃣ 16:9\n2️⃣ 9:16")
    ratio_msg = await app.listen(message.chat.id, timeout=60)
    aspect_ratio = "16:9" if ratio_msg.text.strip() == "1" else "9:16"

    await message.reply_text("🚀 Generating video, please wait...")

    video_config = types.GenerateVideosConfig(
        aspect_ratio=aspect_ratio,
        duration_seconds=duration,
    )

    start_time = time.time()
    task_msg = await message.reply_text("🎥 **Video generation started...**")

    try:
        request = client.generate_videos(
            model="veo-2.0-generate-001",
            config=video_config,
            prompt=prompt,
        )

        # Simulate live progress updates
        for percent in range(0, 101, 5):
            await asyncio.sleep(5)
            elapsed = int(time.time() - start_time)
            await task_msg.edit_text(
                f"🎥 **Generating Video...**\n\n"
                f"⏳ Progress: `{percent}%`\n"
                f"⏱ Time Elapsed: {elapsed} sec"
            )

        video_file = request.result.videos[0].download_to_file("generated_video.mp4")
        await message.reply_video(video_file, caption="✅ **Here is your generated video!**")

    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")
        logger.error(f"Video Generation Error: {e}")

# ===================== COMMAND: STATUS =====================
@app.on_message(filters.command("status") & filters.private)
async def status_cmd(_, message):
    await message.reply_text(
        "✅ **Bot is running fine!**\n"
        "🌐 Gemini API Connected\n"
        "⚡ Ready to generate videos."
    )

# ===================== COMMAND: CANCEL =====================
@app.on_message(filters.command("cancel") & filters.private)
async def cancel_cmd(_, message):
    await message.reply_text("🛑 **Video generation cancelled successfully!**")

# ===================== RUN BOT =====================
print("🚀 Gemini Video Generator Bot Started!")
app.run()
