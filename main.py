import os
import time
import logging
from datetime import datetime
from pymongo import MongoClient
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from google.genai import types

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Telegram Bot Token
MONGO_URI = os.getenv("MONGO_URI")  # MongoDB connection
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Only admin can set API

client_mongo = MongoClient(MONGO_URI)
db = client_mongo["video_bot"]
settings_col = db["settings"]

# ---------------- LOGGER ----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---------------- HELP MESSAGE ----------------
HELP_TEXT = """
🎥 *Video Generator Bot*

Commands:
/set_api <KEY> - Set Gemini API Key (Admin only)
/get_api - Show current API Key (Admin only)
/generate <prompt> - Generate video
/help - Show this help
"""

# ---------------- FUNCTIONS ----------------
def get_api_key():
    data = settings_col.find_one({"_id": "gemini_api"})
    return data["key"] if data else None

def set_api_key(new_key: str):
    settings_col.update_one({"_id": "gemini_api"}, {"$set": {"key": new_key}}, upsert=True)

# ---------------- HANDLERS ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use /help to see commands.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_TEXT, parse_mode="Markdown")

async def set_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ You are not authorized.")

    if len(context.args) != 1:
        return await update.message.reply_text("⚠️ Usage: /set_api <KEY>")

    new_key = context.args[0]
    set_api_key(new_key)
    await update.message.reply_text("✅ Gemini API Key updated successfully.")

async def get_api(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return await update.message.reply_text("❌ You are not authorized.")

    key = get_api_key()
    if key:
        await update.message.reply_text(f"🔑 Current API Key: `{key}`", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No API key set.")

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    api_key = get_api_key()
    if not api_key:
        return await update.message.reply_text("⚠️ Gemini API Key not set. Use /set_api <KEY>")

    if not context.args:
        return await update.message.reply_text("⚠️ Usage: /generate <prompt>")

    prompt = " ".join(context.args)

    await update.message.reply_text(f"⏳ Starting video generation...\n📝 Prompt: `{prompt}`", parse_mode="Markdown")

    # Init Gemini client
    client = genai.Client(http_options={"api_version": "v1beta"}, api_key=api_key)

    video_config = types.GenerateVideosConfig(
        aspect_ratio="16:9",
        number_of_videos=1,
        duration_seconds=8,
        person_generation="ALLOW_ALL",
    )

    # Track timing
    start_time = datetime.now()

    try:
        operation = client.models.generate_videos(
            model="veo-2.0-generate-001",
            prompt=prompt,
            config=video_config,
        )

        while not operation.done:
            await update.message.reply_text("⏳ Video is being generated... Checking again in 10s...")
            time.sleep(10)
            operation = client.operations.get(operation)

        end_time = datetime.now()
        total_time = end_time - start_time

        result = operation.result
        if not result or not result.generated_videos:
            return await update.message.reply_text("❌ No video generated.")

        video_uri = result.generated_videos[0].video.uri
        file = client.files.download(file=result.generated_videos[0].video)

        # Save to file
        filename = "generated_video.mp4"
        result.generated_videos[0].video.save(filename)

        await update.message.reply_text(
            f"✅ Video generated!\n\n"
            f"🕒 Start: {start_time.strftime('%H:%M:%S')}\n"
            f"🏁 End: {end_time.strftime('%H:%M:%S')}\n"
            f"⌛ Total: {total_time}",
            parse_mode="Markdown"
        )

        # Send video
        with open(filename, "rb") as f:
            await update.message.reply_video(video=InputFile(f, filename))

    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("set_api", set_api))
    app.add_handler(CommandHandler("get_api", get_api))
    app.add_handler(CommandHandler("generate", generate))

    app.run_polling()

if __name__ == "__main__":
    main()
    
