#!/usr/bin/env python3 """ Final: Owner-only Gemini Video Telegram Bot (Koyeb-ready) Features:

/setkey, /checkkey, /reset

/generate (or /video) flow: prompt -> aspect (16:9/9:16) -> duration -> /generate to start

Progress updates every ~5s during generation

Upload progress while sending video to Telegram

/history shows last 5 generated videos

/cancel cancels ongoing generation

/status and /help


Dependencies (requirements.txt): pyrogram tgcrypto google-genai requests python-dotenv

Set env vars: BOT_TOKEN, API_ID, API_HASH, OWNER_ID """

import os import time import asyncio import tempfile from datetime import datetime from typing import Optional, Dict, Any

import requests from pyrogram import Client, filters from pyrogram.types import Message

from google import genai from google.genai import types

-------------------- CONFIG --------------------

API_ID = int(os.getenv("API_ID", "0")) API_HASH = os.getenv("API_HASH", "") BOT_TOKEN = os.getenv("BOT_TOKEN", "") OWNER_ID = int(os.getenv("OWNER_ID", "0"))

if not (API_ID and API_HASH and BOT_TOKEN and OWNER_ID): print("[!] Please set API_ID, API_HASH, BOT_TOKEN, OWNER_ID environment variables.")

app = Client("gemini_video_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

-------------------- STATE --------------------

STATE: Dict[str, Any] = { "api_key": None, "prompt": None, "aspect_ratio": None, "duration": None, "task": None, "cancel_requested": False }

history per owner

user_history: Dict[int, list] = {}

-------------------- HELPERS --------------------

def is_owner(msg: Message) -> bool: return msg.from_user and msg.from_user.id == OWNER_ID

def record_history(user_id: int, entry: str): hist = user_history.setdefault(user_id, []) hist.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {entry}") if len(hist) > 5: hist.pop(0)

async def safe_edit(msg: Message, text: str): try: await msg.edit_text(text) except Exception: try: await msg.reply_text(text) except Exception: pass

-------------------- API KEY UTIL --------------------

def make_client_for_key(key: str) -> genai.Client: return genai.Client(api_key=key, http_options={"api_version": "v1beta"})

async def validate_api_key(key: str) -> bool: try: client = make_client_for_key(key) # call list models in thread to avoid blocking await asyncio.to_thread(client.models.list) return True except Exception: return False

-------------------- COMMANDS --------------------

@app.on_message(filters.command("help") & filters.private) async def cmd_help(_, msg: Message): text = ( "📌 Gemini Video Bot Commands: " "/setkey <API_KEY> - Set or update Gemini API key (owner only) " "/checkkey - Validate saved API key " "/reset - Remove saved API key " "/generate or /video - Start the interactive generate flow " "/status - Show current saved settings " "/history - Show last 5 generated videos " "/cancel - Cancel running generation " "/help - This message " ) await msg.reply_text(text)

@app.on_message(filters.command("setkey") & filters.private) async def cmd_setkey(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") parts = msg.text.split(maxsplit=1) if len(parts) != 2: return await msg.reply_text("Usage: /setkey <YOUR_GEMINI_API_KEY>") key = parts[1].strip() await msg.reply_text("🔎 Validating API key...") ok = await validate_api_key(key) if not ok: return await msg.reply_text("❌ Invalid API key or network error. Please check and try again.") STATE["api_key"] = key await msg.reply_text("✅ API key saved. Use /generate to start.")

@app.on_message(filters.command("checkkey") & filters.private) async def cmd_checkkey(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") key = STATE.get("api_key") if not key: return await msg.reply_text("⚠️ No API key saved. Use /setkey first.") await msg.reply_text("🔎 Checking API key...") ok = await validate_api_key(key) await msg.reply_text("✅ API key is valid.") if ok else await msg.reply_text("❌ API key invalid or quota exhausted.")

@app.on_message(filters.command("reset") & filters.private) async def cmd_reset(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") STATE.update({"api_key": None, "prompt": None, "aspect_ratio": None, "duration": None}) await msg.reply_text("✅ All settings cleared.")

@app.on_message(filters.command(["status"]) & filters.private) async def cmd_status(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") ak = "Set" if STATE.get("api_key") else "Not set" prompt = STATE.get("prompt") or "Not set" ar = STATE.get("aspect_ratio") or "Not set" dur = f"{STATE.get('duration')}s" if STATE.get("duration") else "Not set" running = "Yes" if STATE.get("task") and not STATE.get("task").done() else "No" await msg.reply_text(f"📌 Status: API Key: {ak} Prompt: {prompt} Aspect Ratio: {ar} Duration: {dur} Generation running: {running}")

@app.on_message(filters.command("history") & filters.private) async def cmd_history(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") hist = user_history.get(OWNER_ID, []) if not hist: return await msg.reply_text("⚠️ History empty.") text = " ".join([f"{i+1}. {h}" for i, h in enumerate(hist)]) await msg.reply_text(f"📜 Last {len(hist)} generated videos: {text}")

@app.on_message(filters.command("cancel") & filters.private) async def cmd_cancel(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") task: Optional[asyncio.Task] = STATE.get("task") if not task or task.done(): return await msg.reply_text("ℹ️ No active generation to cancel.") STATE["cancel_requested"] = True task.cancel() await msg.reply_text("🛑 Cancel requested. Attempting to stop the job...")

-------------------- INTERACTIVE GENERATE FLOW --------------------

@app.on_message(filters.command(["generate", "video"]) & filters.private) async def cmd_generate_flow(_, msg: Message): if not is_owner(msg): return await msg.reply_text("❌ Not authorized.") if not STATE.get("api_key"): return await msg.reply_text("⚠️ Please set your Gemini API key first with /setkey <API_KEY>")

await msg.reply_text("✍️ Please send your video prompt (short description):")
prompt_msg = await app.listen(msg.chat.id)
prompt = (prompt_msg.text or "").strip()
if not prompt:
    return await msg.reply_text("❌ Prompt cannot be empty.")
STATE["prompt"] = prompt

await msg.reply_text("📐 Choose aspect ratio: reply with 1 for 16:9 or 2 for 9:16")
ar_msg = await app.listen(msg.chat.id)
ar_choice = (ar_msg.text or "").strip()
if ar_choice in ("1", "16:9"):
    STATE["aspect_ratio"] = "16:9"
else:
    STATE["aspect_ratio"] = "9:16"

await msg.reply_text("⏱️ Enter duration in seconds (1-60):")
dur_msg = await app.listen(msg.chat.id)
try:
    dur = int((dur_msg.text or "").strip())
    if dur <= 0 or dur > 60:
        raise ValueError
except Exception:
    return await msg.reply_text("❌ Invalid duration. Please run /generate again and provide a number between 1 and 60.")
STATE["duration"] = dur

# Start background generation task
if STATE.get("task") and not STATE.get("task").done():
    return await msg.reply_text("⚠️ A generation task is already running. Use /cancel to stop it.")

task = asyncio.create_task(generate_and_send(msg.chat.id))
STATE["task"] = task
await msg.reply_text("🚀 Generation started — you'll get progress updates here.")

-------------------- CORE: generate_and_send --------------------

async def generate_and_send(chat_id: int): status_message = None start_time = time.time() try: key = STATE.get("api_key") prompt = STATE.get("prompt") aspect = STATE.get("aspect_ratio") duration = STATE.get("duration")

client = make_client_for_key(key)

    # Send initial status message
    status_message = await app.send_message(chat_id, "🎥 Sending generation request to Gemini...")

    # Start generation in thread (blocking SDK calls)
    def start_request():
        return client.models.generate_videos(model="veo-2.0-generate-001", config=types.GenerateVideosConfig(
            prompt=prompt, aspect_ratio=aspect, duration_seconds=duration
        ))

    try:
        resp = await asyncio.to_thread(start_request)
    except Exception as e:
        txt = str(e)
        if any(x in txt for x in ["401", "UNAUTHENTICATED", "Invalid API key"]):
            await safe_edit(status_message, "❌ Invalid API Key. Please /setkey again.")
            return
        if any(x in txt.lower() for x in ["quota", "exceeded", "429", "resource_exhausted"]):
            await safe_edit(status_message, "⛔ API limit reached. Try later or enable billing.")
            return
        await safe_edit(status_message, f"❌ Error starting generation: {e}")
        return

    # If operation name present, poll
    op_name = getattr(resp, "name", None) or (resp.get("name") if isinstance(resp, dict) else None)
    done_flag = getattr(resp, "done", None)

    # Poll loop with ~5 second updates
    last_pct = 0
    if op_name and (done_flag is False or done_flag is None):
        while True:
            # cancellation check
            if STATE.get("cancel_requested"):
                await safe_edit(status_message, "🛑 Generation canceled by user.")
                STATE["cancel_requested"] = False
                return
            # get op
            try:
                op = await asyncio.to_thread(client.operations.get_operation, op_name)
            except Exception:
                await asyncio.sleep(5)
                continue

            # determine done/progress
            if isinstance(op, dict):
                done = op.get("done", False)
                metadata = op.get("metadata", {})
            else:
                done = getattr(op, "done", False)
                metadata = getattr(op, "metadata", None) or {}

            pct = None
            for k in ("progress", "progress_percent", "progressPercent"):
                if isinstance(metadata, dict) and k in metadata:
                    try:
                        pct = int(metadata[k])
                    except Exception:
                        pct = None
            if pct is None:
                elapsed = int(time.time() - start_time)
                pct = min(95, int((elapsed / 120.0) * 100))

            if pct != last_pct:
                await safe_edit(status_message, f"🎥 Generating...

⏳ Elapsed: {int(time.time() - start_time)}s 🔄 Progress: {pct}%") last_pct = pct

if done:
                await safe_edit(status_message, "✅ Generation finished. Preparing download...")
                # try to get response
                if isinstance(op, dict) and op.get("response"):
                    final = op["response"]
                else:
                    final = op
                break

            await asyncio.sleep(5)
    else:
        final = resp

    # Extract video url
    video_url = None
    for fld in ("uri", "video_uri", "videoUrl", "video_url"):
        if isinstance(final, dict):
            video_url = video_url or final.get(fld)
        else:
            video_url = video_url or getattr(final, fld, None)
    if not video_url:
        s = str(final)
        for token in ("http://", "https://"):
            if token in s:
                start = s.find(token)
                end = s.find(" ", start)
                video_url = s[start:end if end != -1 else None]
                break

    if not video_url:
        await safe_edit(status_message, "❌ Could not find video URL in the generation response.")
        return

    # Record history (store URL)
    record_history(OWNER_ID, video_url)

    # Download the video (simple blocking download in thread)
    await safe_edit(status_message, "⬇️ Downloading video...")
    def download():
        try:
            r = requests.get(video_url, stream=True, timeout=120)
            r.raise_for_status()
            total = int(r.headers.get("Content-Length") or 0)
            tmpf = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
            downloaded = 0
            chunk_size = 1 << 20
            for chunk in r.iter_content(chunk_size=chunk_size):
                if STATE.get("cancel_requested"):
                    r.close()
                    return None
                if chunk:
                    tmpf.write(chunk)
                    downloaded += len(chunk)
            tmpf.flush()
            tmpf.close()
            return tmpf.name
        except Exception as e:
            return None
    tmp_path = await asyncio.to_thread(download)
    if not tmp_path:
        await safe_edit(status_message, "⚠️ Failed to download video.")
        return

    # Send video with upload progress
    await safe_edit(status_message, "📤 Uploading video to Telegram...")
    upload_start = time.time()

    async def _progress(current, total):
        try:
            pct = int(current * 100 / total) if total else 0
            elapsed = int(time.time() - upload_start)
            # update every ~2 seconds
            await status_message.edit_text(f"📤 Uploading to Telegram... {pct}%

Elapsed: {elapsed}s") except Exception: pass

try:
        await app.send_video(chat_id=chat_id, video=tmp_path, caption=f"✅ Your Video (prompt: {STATE.get('prompt')})", progress=_progress)
        await safe_edit(status_message, "✅ Video sent successfully!")
    except Exception as e:
        await safe_edit(status_message, f"❌ Failed to upload video: {e}")
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass

except asyncio.CancelledError:
    await safe_edit(status_message, "🛑 Generation task cancelled.")
    STATE["cancel_requested"] = False
    return
except Exception as e:
    await safe_edit(status_message, f"❌ Unexpected error: {e}")
finally:
    STATE["task"] = None
    STATE["cancel_requested"] = False

-------------------- RUN --------------------

if name == "main": print("✅ Gemini Video Bot Starting...") app.run()

