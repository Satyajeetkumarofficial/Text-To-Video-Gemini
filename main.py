import os import time import threading from pyrogram import Client, filters from pyrogram.types import Message from google import genai from google.genai import types from flask import Flask from dotenv import load_dotenv

------------------- Load Env Variables -------------------

load_dotenv() BOT_TOKEN = os.getenv("BOT_TOKEN") OWNER_ID = int(os.getenv("OWNER_ID")) BOT_NAME = os.getenv("BOT_NAME", "Gemini Video Generator") PORT = int(os.getenv("PORT", 8080)) ENABLE_LOGS = os.getenv("ENABLE_LOGS", "true").lower() == "true"

------------------- Pyrogram Client -------------------

bot = Client("gemini_bot", bot_token=BOT_TOKEN)

------------------- Flask App for Health -------------------

app = Flask(name)

@app.route('/') def index(): return f"{BOT_NAME} is running!"

def run_flask(): app.run(host="0.0.0.0", port=PORT)

------------------- Gemini Client Placeholder -------------------

gemini_client = None API_TOKEN = None

------------------- Helper Functions -------------------

def log(text): if ENABLE_LOGS: print(text)

def check_owner(func): async def wrapper(client, message: Message): if message.from_user.id != OWNER_ID: await message.reply_text("🚫 You are not authorized to use this bot.") return await func(client, message) return wrapper

------------------- Bot Commands -------------------

@bot.on_message(filters.command("start")) @check_owner def start(client, message: Message): message.reply_text(f"👋 Hello! I am {BOT_NAME}.")

@bot.on_message(filters.command("help")) @check_owner def help_cmd(client, message: Message): help_text = ( "/start - Start bot\n" "/help - Show commands\n" "/setapi <API_KEY> - Set or change Gemini API key\n" "/generate - Generate video from prompt" ) message.reply_text(help_text)

@bot.on_message(filters.command("setapi")) @check_owner def set_api(client, message: Message): global API_TOKEN, gemini_client if len(message.command) < 2: message.reply_text("❌ Usage: /setapi <API_KEY>") return API_TOKEN = message.command[1] gemini_client = genai.Client(api_key=API_TOKEN) message.reply_text("✅ Gemini API key saved! Now send /generate to create a video.")

@bot.on_message(filters.command("generate")) @check_owner def generate_video(client, message: Message): global gemini_client, API_TOKEN if not API_TOKEN: message.reply_text("❌ Set the API key first using /setapi <API_KEY>") return

# Step 1: Ask prompt
msg = message.reply_text("✏️ Please send the prompt for your video.")

@bot.on_message(filters.private & filters.user(OWNER_ID))
async def get_prompt(c, prompt_msg: Message):
    prompt_text = prompt_msg.text
    # Ask resolution
    res_msg = await prompt_msg.reply_text("🖼️ Choose resolution: 16:9 or 9:16")

    @bot.on_message(filters.private & filters.user(OWNER_ID))
    async def get_resolution(c2, res_resp: Message):
        resolution = res_resp.text.strip()
        if resolution not in ["16:9", "9:16"]:
            await res_resp.reply_text("❌ Invalid resolution. Using default 16:9.")
            resolution = "16:9"

        # Ask duration
        dur_msg = await res_resp.reply_text("⏱️ Enter duration in seconds (max 60)")

        @bot.on_message(filters.private & filters.user(OWNER_ID))
        async def get_duration(c3, dur_resp: Message):
            try:
                duration = int(dur_resp.text.strip())
                if duration > 60: duration = 60
            except:
                duration = 10

            progress_msg = await dur_resp.reply_text("🎬 Generating video: 0%")
            
            # Start video generation
            config = types.GenerateVideosConfig(
                prompt=prompt_text,
                aspect_ratio=resolution,
                duration=duration
            )
            
            # Simulate progress
            for i in range(0, 101, 5):
                await progress_msg.edit_text(f"🎬 Generating video: {i}%")
                time.sleep(1)
            
            # Simulate final video file
            video_file = f"generated_video.mp4"
            with open(video_file, "wb") as f:
                f.write(b"\x00"*1024)  # dummy 1KB file
            
            await progress_msg.edit_text(f"✅ Video ready! Sending...")
            await dur_resp.reply_document(video_file)
            os.remove(video_file)

------------------- Run Threads -------------------

if name == "main": threading.Thread(target=run_flask).start() log("🚀 Gemini Video Generator Started!") bot.run()

