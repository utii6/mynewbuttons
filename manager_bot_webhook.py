import os, json, asyncio, random
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError
from fastapi import FastAPI, Request
import uvicorn

# -------- CONFIG ----------
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456:ABC-DEF")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5581457665"))
SESSIONS_FILE = "sessions.json"

WEBHOOK_URL = os.getenv("https://mynewbuttons.onrender.com")  # الرابط الكامل للويبهوك: https://your-app.onrender.com/توكين
PORT = int(os.environ.get("PORT", 10000))

if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, "w") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)

with open(SESSIONS_FILE, "r") as f:
    SESSIONS = json.load(f)

LOGIN_STATE = {}
USE_COUNT = None

# -------- BOT & Dispatcher ----------
bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

# --------- FastAPI Server ----------
app = FastAPI()

# ---------- Helper functions ----------
def save_sessions():
    with open(SESSIONS_FILE, "w") as f:
        json.dump(SESSIONS, f, ensure_ascii=False, indent=2)

def main_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ إضافة حساب", callback_data="btn_add"),
        InlineKeyboardButton("🔌 تسجيل خروج الكل", callback_data="btn_logout_all"),
        InlineKeyboardButton("📋 عرض الحسابات", callback_data="btn_list"),
        InlineKeyboardButton("❌ حذف حساب", callback_data="btn_remove"),
        InlineKeyboardButton("🔢 اختر عدد الحسابات", callback_data="btn_choose_count"),
        InlineKeyboardButton("▶️ انضمام لقناة", callback_data="btn_join"),
        InlineKeyboardButton("◀️ مغادرة قناة", callback_data="btn_leave"),
        InlineKeyboardButton("✉️ تفاعل (أرسل رسالة)", callback_data="btn_interact"),
    )
    return kb

# ---------- Aiogram Webhook Handlers ----------
@app.post(f"/{BOT_TOKEN}")
async def telegram_webhook(req: Request):
    data = await req.json()
    update = types.Update(**data)
    await dp.process_update(update)
    return {"ok": True}

@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)

# ---------- Aiogram Handlers ----------
@dp.message_handler(commands=["start","help"])
async def cmd_start(m: types.Message):
    if m.from_user.id != ADMIN_ID:
        return await m.reply("ما عدك صلاحية.")
    await m.reply("هلو سيدي — لوحة التحكم:", reply_markup=main_kb())

# تقدر تضيف باقي Callback Handlers والـ Login Flow من نسخة polling السابقة
# تذكر فقط استبدال أي polling بـ webhook handlers

# ---------- Run FastAPI ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
