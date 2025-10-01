# manager_bot_buttons.py
import os, json, asyncio, random
from typing import Dict, Any
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, FloodWaitError

# -------- CONFIG (عدّل إذا لازم) ----------
API_ID = int(os.getenv("API_ID", "123456"))
API_HASH = os.getenv("API_HASH", "your_api_hash")
BOT_TOKEN = os.getenv("BOT_TOKEN", "123456:ABC")
ADMIN_ID = int(os.getenv("ADMIN_ID", "5581457665"))  # معرفك محفوظ
SESSIONS_FILE = "sessions.json"   # يخزّن {"name":{"string": "...", "phone": "..."}}
if not os.path.exists(SESSIONS_FILE):
    with open(SESSIONS_FILE, "w") as f:
        json.dump({}, f, ensure_ascii=False, indent=2)
with open(SESSIONS_FILE, "r") as f:
    SESSIONS: Dict[str, Dict[str, Any]] = json.load(f)

# in-memory
LOGIN_STATE: Dict[int, Dict[str, Any]] = {}
USE_COUNT = None   # None = كل الحسابات

bot = Bot(BOT_TOKEN)
dp = Dispatcher(bot)

def save_sessions():
    with open(SESSIONS_FILE, "w") as f:
        json.dump(SESSIONS, f, ensure_ascii=False, indent=2)

# ---------- helper client management ----------
async def start_client_from_string(s: str):
    c = TelegramClient(StringSession(s), API_ID, API_HASH)
    await c.connect()
    return c

async def start_all_clients():
    clients = {}
    for name, info in SESSIONS.items():
        try:
            c = TelegramClient(StringSession(info["string"]), API_ID, API_HASH)
            await c.start()
            clients[name] = c
        except Exception as e:
            print("Failed start", name, e)
    return clients

async def pick_clients(clients: Dict[str, TelegramClient]):
    names = list(clients.keys())
    if not names:
        return {}
    global USE_COUNT
    if USE_COUNT is None:
        return clients
    pick = random.sample(names, min(USE_COUNT, len(names)))
    return {n: clients[n] for n in pick}

# ---------- UI helpers ----------
def main_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("➕ إضافة حساب", callback_data="btn_add"),
        InlineKeyboardButton("🔌 تسجيل خروج الكل", callback_data="btn_logout_all"),
        InlineKeyboardButton("📋 عرض الحسابات", callback_data="btn_list"),
        InlineKeyboardButton("❌ حذف حساب", callback_data="btn_remove"),
    )
    kb.add(
        InlineKeyboardButton("🔢 اختر عدد الحسابات", callback_data="btn_choose_count"),
        InlineKeyboardButton("▶️ انضمام لقناة", callback_data="btn_join"),
        InlineKeyboardButton("◀️ مغادرة قناة", callback_data="btn_leave"),
    )
    kb.add(
        InlineKeyboardButton("✉️ تفاعل (أرسل رسالة)", callback_data="btn_interact"),
        InlineKeyboardButton("🔁 إعادة تشغيل الجلسات", callback_data="btn_restart"),
    )
    return kb

def count_kb():
    kb = InlineKeyboardMarkup(row_width=5)
    for i in [1,2,3,4,5,10,0]:
        label = "الكل" if i==0 else str(i)
        kb.insert(InlineKeyboardButton(label, callback_data=f"set_count:{i}"))
    return kb

# ---------- decorators ----------
def admin_only_cb(func):
    async def wrapper(callback: types.CallbackQuery):
        if callback.from_user.id != ADMIN_ID:
            await callback.answer("ما عدك صلاحية.", show_alert=True)
            return
        await func(callback)
    return wrapper

def admin_only_msg(func):
    async def wrapper(m: types.Message):
        if m.from_user.id != ADMIN_ID:
            return await m.reply("ما عدك صلاحية.")
        return await func(m)
    return wrapper

# ---------- handlers ----------
@dp.message_handler(commands=["start","help"])
@admin_only_msg
async def cmd_start(m: types.Message):
    await m.reply("هلو سيدي — لوحة التحكم:", reply_markup=main_kb())

# Callback main buttons
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("btn_"))
@admin_only_cb
async def on_btn_main(c: types.CallbackQuery):
    key = c.data
    if key == "btn_add":
        LOGIN_STATE[c.from_user.id] = {"step":"ask_name"}
        await c.message.reply("أرسل اسم تعريفي للحساب (مثلاً: ahmed_main)")
    elif key == "btn_list":
        if not SESSIONS:
            await c.message.reply("ماكو حسابات مسجلة.")
        else:
            lines = [f"{i+1}. {n} -> {info.get('phone','?')}" for i,(n,info) in enumerate(SESSIONS.items())]
            await c.message.reply("الحسابات:\n" + "\n".join(lines))
    elif key == "btn_choose_count":
        await c.message.reply("اختر عدد الحسابات المستخدمة:", reply_markup=count_kb())
    elif key == "btn_logout_all":
        clients = await start_all_clients()
        for name, client in clients.items():
            try:
                await client.log_out()
            except Exception:
                pass
            try:
                await client.disconnect()
            except:
                pass
        await c.message.reply("تم تسجيل خروج كل الجلسات.")
    elif key in ("btn_join","btn_leave","btn_interact","btn_restart"):
        await c.message.reply("أرسل الآن الهدف (اسم القناة @example أو invite link) أو نص الرسالة (للتفاعل). متبوعًا بأمر إنشاء/انضمام/مغادرة حسب الزر الذي ضغطته.\nمثال للانضمام: @channelname\nمثال للتفاعل: @channelname | نص الرسالة")
        # store intent
        LOGIN_STATE[c.from_user.id] = {"step":"action_wait", "action": key}
    elif key == "btn_remove":
        await c.message.reply("أرسل اسم الجلسة اللي تريد تشيلها (مثلاً: ahmed_main)")
    await c.answer()

# set count
@dp.callback_query_handler(lambda c: c.data and c.data.startswith("set_count:"))
@admin_only_cb
async def on_set_count(c: types.CallbackQuery):
    global USE_COUNT
    v = int(c.data.split(":",1)[1])
    USE_COUNT = None if v==0 else v
    await c.message.reply(f"تم تعيين عدد الحسابات: {'الكل' if v==0 else v}")
    await c.answer()

# admin typed messages (login flow + actions)
@dp.message_handler(lambda m: m.from_user.id==ADMIN_ID)
async def admin_messages(m: types.Message):
    uid = m.from_user.id
    text = (m.text or "").strip()
    if uid in LOGIN_STATE:
        state = LOGIN_STATE[uid]
        step = state.get("step")
        # add account flow
        if step == "ask_name":
            if not text:
                return await m.reply("أرسل اسم صالح.")
            if text in SESSIONS:
                return await m.reply("الاسم موجود، اختَر واحد ثاني.")
            state["tmp_name"] = text
            state["step"] = "ask_phone"
            return await m.reply("أرسل رقم الهاتف بصيغة دولية (+96477...)")
        if step == "ask_phone":
            phone = text
            state["phone"] = phone
            tmp_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await tmp_client.connect()
            try:
                sent = await tmp_client.send_code_request(phone)
                state["client"] = tmp_client
                state["sent_hash"] = sent.phone_code_hash
                state["step"] = "ask_code"
                return await m.reply("تم إرسال رمز التحقق. أرسله هنا.")
            except Exception as e:
                await tmp_client.disconnect()
                del LOGIN_STATE[uid]
                return await m.reply(f"خطأ بإرسال الرمز: {e}")
        if step == "ask_code":
            code = text
            client = state.get("client")
            phone = state.get("phone")
            try:
                await client.sign_in(phone=phone, code=code, phone_code_hash=state.get("sent_hash"))
                s = StringSession.save(client.session)
                name = state["tmp_name"]
                SESSIONS[name] = {"string": s, "phone": phone}
                save_sessions()
                await client.disconnect()
                del LOGIN_STATE[uid]
                return await m.reply(f"نجحت تسجيل! حفظت الجلسة باسم: {name}")
            except SessionPasswordNeededError:
                state["step"] = "ask_password"
                return await m.reply("هذا الحساب مفعل بخطوتين. أرسل كلمة المرور الثابتة الآن.")
            except Exception as e:
                await client.disconnect()
                del LOGIN_STATE[uid]
                return await m.reply(f"فشل تسجيل الدخول: {e}")
        if step == "ask_password":
            password = text
            client = state.get("client")
            try:
                await client.sign_in(password=password)
                s = StringSession.save(client.session)
                name = state["tmp_name"]
                SESSIONS[name] = {"string": s, "phone": state.get("phone")}
                save_sessions()
                await client.disconnect()
                del LOGIN_STATE[uid]
                return await m.reply(f"نجحت تسجيل بخطوتين! تم حفظ: {name}")
            except Exception as e:
                await client.disconnect()
                del LOGIN_STATE[uid]
                return await m.reply(f"كلمة المرور خاطئة أو خطأ: {e}")
        # actions: join/leave/interact
        if step == "action_wait":
            action = state.get("action")
            # parse input for interact: format "@channel | الرسالة"
            if action == "btn_interact":
                if "|" not in text:
                    del LOGIN_STATE[uid]
                    return await m.reply("استعمال التفاعل: @channel_or_target | نص الرسالة")
                target, msg = [p.strip() for p in text.split("|",1)]
                await m.reply("أبلّش تنفيذ التفاعل...")
                clients = await start_all_clients()
                pick = await pick_clients(clients)
                sent = 0
                for name, client in pick.items():
                    try:
                        await client.send_message(target, msg)
                        sent += 1
                        await asyncio.sleep(1.2)
                        await m.reply(f"{name} رسل ✅")
                    except FloodWaitError as e:
                        await m.reply(f"{name} FloodWait {e.seconds}s")
                        await asyncio.sleep(e.seconds+1)
                    except Exception as e:
                        await m.reply(f"{name} خطأ: {e}")
                del LOGIN_STATE[uid]
                return await m.reply(f"انتهى. رسائل مرسلة: {sent}")
            # join or leave expect single target
            if action in ("btn_join","btn_leave"):
                target = text.strip()
                clients = await start_all_clients()
                pick = await pick_clients(clients)
                total = 0
                for name, client in pick.items():
                    try:
                        if action=="btn_join":
                            await client(functions=0)  # noop safe placeholder
                            # proper join
                            from telethon.tl.functions.channels import JoinChannelRequest
                            await client(JoinChannelRequest(target))
                            await m.reply(f"{name} انضم ✅")
                        else:
                            from telethon.tl.functions.channels import LeaveChannelRequest
                            await client(LeaveChannelRequest(target))
                            await m.reply(f"{name} غادر ✅")
                        total += 1
                        await asyncio.sleep(1.2)
                    except FloodWaitError as e:
                        await m.reply(f"{name} FloodWait {e.seconds}s")
                        await asyncio.sleep(e.seconds+1)
                    except Exception as e:
                        await m.reply(f"{name} خطأ: {e}")
                del LOGIN_STATE[uid]
                return await m.reply(f"انتهى. انفذ على {total} حساب.")
    # not in LOGIN_STATE → support remove command quick text or /use
    if text.startswith("/remove"):
        parts = text.split(maxsplit=1)
        if len(parts)<2:
            return await m.reply("استعمال: /remove <name>")
        name = parts[1].strip()
        if name in SESSIONS:
            del SESSIONS[name]; save_sessions()
            return await m.reply(f"حذفت: {name}")
        return await m.reply("ماكو جلسة بهذا الاسم.")
    if text.startswith("/use"):
        parts = text.split()
        if len(parts)<2:
            return await m.reply("استعمال: /use <number> (0=الكل)")
        try:
            n = int(parts[1]); global USE_COUNT
            USE_COUNT = None if n==0 else n
            return await m.reply(f"تم تعيين عدد الحسابات: {'الكل' if n==0 else n}")
        except:
            return await m.reply("ادخل رقم صحيح.")
    # other text: fallback
    await m.reply("موفّه — استخدم الأزرار باللوحة أو /help.")

# ---------- start ----------
if __name__ == "__main__":
    print("Manager bot running...")
    executor.start_polling(dp, skip_updates=True)
