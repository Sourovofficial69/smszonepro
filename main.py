
import json
import aiohttp
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# --- কনফিগারেশন ---
BOT_TOKEN = "8882709787:AAEOvT7BcwPCFQ1t-0RelzA-W2A_loEgJmg"
API_KEY = "0ba1caaddfed5777bd40d16af6d18944"
BASE_URL = "https://api.grizzlysms.com/stubs/handler_api.php"

MY_TELEGRAM_ID = 6553306143
SERVICE_CODE = "tg"
USDT_BEP20_ADDRESS = "naiiiiii"

FIXED_COUNTRIES = [
{"id": "1", "flag": "🇺🇦", "name": "Ukraine"},
{"id": "11", "flag": "🇸🇻", "name": "El Salvador"},
{"id": "27", "flag": "🇯🇲", "name": "Jamaica"},
{"id": "12", "flag": "🇰🇷", "name": "South Korea"},
{"id": "187", "flag": "🇺🇸", "name": "USA"},
{"id": "10", "flag": "🇭🇰", "name": "Hong Kong"},
{"id": "31", "flag": "🇧🇭", "name": "Bahrain"},
{"id": "17", "flag": "🇻🇳", "name": "Vietnam"},
{"id": "67", "flag": "🇬🇭", "name": "Ghana"},
{"id": "184", "flag": "🇲🇪", "name": "Montenegro"},
{"id": "19", "flag": "🇳🇴", "name": "Norway"},
{"id": "2", "flag": "🇰🇿", "name": "Kazakhstan"},
{"id": "6", "flag": "🇮🇩", "name": "Indonesia"},
{"id": "39", "flag": "🇦🇷", "name": "Argentina"},
{"id": "15", "flag": "🇵🇱", "name": "Poland"},
{"id": "4", "flag": "🇮🇶", "name": "Iraq"},
{"id": "5", "flag": "🇵🇰", "name": "Pakistan"},
{"id": "22", "flag": "🇮🇳", "name": "India"},
{"id": "16", "flag": "🇬🇧", "name": "United Kingdom"},
{"id": "28", "flag": "🇧🇷", "name": "Brazil"},
{"id": "82", "flag": "🇧🇪", "name": "Belgium"},
{"id": "122", "flag": "🇲🇩", "name": "Moldova"},
{"id": "60", "flag": "🇧🇩", "name": "Bangladesh"},
{"id": "92", "flag": "🇧🇴", "name": "Bolivia"}
]

COUNTRY_DICT = {c["id"]: f"{c['flag']} {c['name']}" for c in FIXED_COUNTRIES}

target_running = False
request_count = 0
target_country_id = None
target_country_name = None
current_max_price = "0.0000"
stored_otps = {}
waiting_for_custom_price = False

async def is_authorized(update: Update) -> bool:
return update.effective_user and update.effective_user.id == MY_TELEGRAM_ID

async def get_grizzly_balance():
url = f"{BASE_URL}?api_key={API_KEY}&action=getBalance"
try:
async with aiohttp.ClientSession() as session:
async with session.get(url, timeout=7) as response:
if response.status == 200:
res_text = await response.text()
if "ACCESS_BALANCE" in res_text:
return res_text.split(':')[1].strip()
except Exception:
pass
return "0.00"

# --- ডকুমেন্টেশন অনুযায়ী সঠিক পার্সিং লজিক ---
async def get_country_price_streams(country_id):
url = f"{BASE_URL}?api_key={API_KEY}&action=getPrices&service={SERVICE_CODE}&country={country_id}"

try:
async with aiohttp.ClientSession() as session:
async with session.get(url, timeout=10) as response:
if response.status == 200:
text_data = await response.text()
data = json.loads(text_data)
[9/7/2026 9:43 AM] メ RaFi (Ø,G): # {"Country": {"Service": {"cost": X, "count": Y}}} ফরম্যাট চেক
c_id = str(country_id)

if c_id in data and SERVICE_CODE in data[c_id]:
service_data = data[c_id][SERVICE_CODE]
cost = float(service_data.get("cost", 0))
count = int(service_data.get("count", 0))
if cost > 0:
return [{"price": cost, "count": count}]

# বিকল্প লেআউট হ্যান্ডলিং (যদি কোনো কারণে সরাসরি সার্ভিস দিয়ে রেসপন্স আসে)
if SERVICE_CODE in data:
service_data = data[SERVICE_CODE]
cost = float(service_data.get("cost", 0))
count = int(service_data.get("count", 0))
if cost > 0:
return [{"price": cost, "count": count}]

except Exception:
pass

return []

async def set_activation_status(order_id, status_code):
url = f"{BASE_URL}?api_key={API_KEY}&action=setStatus&status={status_code}&id={order_id}"
try:
async with aiohttp.ClientSession() as session:
async with session.get(url, timeout=5) as response:
return await response.text()
except Exception:
return "ERROR"
[9/7/2026 10:57 AM] メ RaFi (Ø,G): async def start_number_interface(chat_id, order_id, phone_number, context: ContextTypes.DEFAULT_TYPE):
global stored_otps, target_country_name
status_url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={order_id}"
stored_otps[order_id] = []
formatted_number = f"+{phone_number.lstrip('+')}"

keyboard = [[InlineKeyboardButton("❌ Cancel Order", callback_data=f"cnl_{order_id}")]]
reply_markup = InlineKeyboardMarkup(keyboard)
total_seconds = 1195

num_msg = await context.bot.send_message(
chat_id=chat_id,
text=f"📱 Number Captured**\n🌍 Country: {target_country_name}\n🚀 Number: `{formatted_number}`\n⏱️ Time Left: `19:55`\n🔎 Check: ✅\n\n📬 Status: `Waiting for SMS...`",
reply_markup=reply_markup,
parse_mode="Markdown"
)

async with aiohttp.ClientSession() as session:
for i in range(300):
if order_id not in stored_otps:
return
current_left = total_seconds - (i * 4)
if current_left <= 0:
break
mins, secs = divmod(current_left, 60)
time_string = f"{mins:02d}:{secs:02d}"

try:
async with session.get(status_url, timeout=4) as response:
if response.status == 200:
res_text = await response.text()

if "STATUS_OK" in res_text:
otp_code = res_text.split(":")[1]
if otp_code not in stored_otps[order_id]:
stored_otps[order_id].append(otp_code)
await set_activation_status(order_id, 3)

otp_display = "\n".join([f"🔑 **OTP {idx+1}: {code}" for idx, code in enumerate(stored_otps[order_id])])

active_keyboard = [
[
InlineKeyboardButton("🔄 Another", callback_data=f"ref_{order_id}_{phone_number}"),
InlineKeyboardButton("✅ Complete", callback_data=f"fin_{order_id}_{phone_number}")
]
]

await context.bot.edit_message_text(
chat_id=chat_id, message_id=num_msg.message_id,
[9/7/2026 9:43 AM] メ RaFi (Ø,G): text=f"📱 Number Captured**\n🌍 Country: {target_country_name}\n🚀 Number: `{formatted_number}`\n⏱️ Time Left: `{time_string}`\n🔎 Check: ✅\n\n{otp_display}",
reply_markup=InlineKeyboardMarkup(active_keyboard),
parse_mode="Markdown"
)
elif "STATUS_WAIT_CODE" in res_text:
if stored_otps[order_id]:
otp_display = "\n".join([f"🔑 **OTP {idx+1}: {code}" for idx, code in enumerate(stored_otps[order_id])])
current_markup = InlineKeyboardMarkup([[
InlineKeyboardButton("🔄 Another", callback_data=f"ref_{order_id}_{phone_number}"),
InlineKeyboardButton("✅ Complete", callback_data=f"fin_{order_id}_{phone_number}")
]])
else:
otp_display = "📬 Status: Waiting for SMS..."
current_markup = reply_markup

try:
await context.bot.edit_message_text(
chat_id=chat_id, message_id=num_msg.message_id,
text=f"📱 Number Captured**\n🌍 Country: {target_country_name}\n🚀 Number: {formatted_number}`\n⏱️ Time Left: {time_string}`\n🔎 Check: ✅\n\n{otp_display}",
reply_markup=current_markup,
parse_mode="Markdown"
)
except Exception:
pass
elif "STATUS_CANCEL" in res_text:
if order_id in stored_otps:
del stored_otps[order_id]
try:
await context.bot.delete_message(chat_id=chat_id, message_id=num_msg.message_id)
except Exception:
pass
return
except Exception:
pass
await asyncio.sleep(4)

async def catcher_loop(chat_id, context: ContextTypes.DEFAULT_TYPE):
global target_running, request_count, target_country_id, target_country_name, current_max_price

url = f"{BASE_URL}?api_key={API_KEY}&action=getNumber&service={SERVICE_CODE}&country={target_country_id}&maxPrice={current_max_price}"
stop_markup = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 Stop Loop", callback_data="btn_stop")]])

status_msg = await context.bot.send_message(
chat_id=chat_id,
text=f"🎯 **Grizzly Catcher Running**\n🌍 Country: {target_country_name}\n💵 Target Price: {current_max_price}$\n🔄 Requests: {request_count}",
reply_markup=stop_markup,
parse_mode="Markdown"
)

async with aiohttp.ClientSession() as session:
while target_running:
request_count += 1
try:
async with session.get(url, timeout=4) as response:
if response.status == 200:
res_text = await response.text()
if "ACCESS_NUMBER" in res_text:
parts = res_text.split(":")
order_id = parts[1]
phone_number = parts[2]
[9/7/2026 10:57 AM] メ RaFi (Ø,G): formatted_num = f"+{phone_number.lstrip('+')}"
await context.bot.edit_message_text(
chat_id=chat_id, message_id=status_msg.message_id,
text=f"✅ **Captured!**\n🌍 Country: {target_country_name}\n🚀 Number: `{formatted_num}`\n\n🔄 Searching next...",
reply_markup=stop_markup,
parse_mode="Markdown"
)
asyncio.create_task(start_number_interface(chat_id, order_id, phone_
[9/7/2026 9:43 AM] メ RaFi (Ø,G): number, context))
elif "NO_BALANCE" in res_text:
target_running = False
await context.bot.send_message(chat_id=chat_id, text="⚠️ **Stopped: No Balance.", parse_mode="Markdown")
break
else:
if request_count % 3 == 0:
try:
await context.bot.edit_message_text(
chat_id=chat_id, message_id=status_msg.message_id,
text=f"🎯 Grizzly Catcher Running**\n🌍 Country: {target_country_name}\n💵 Target Price: {current_max_price}$\n🔄 Requests: {request_count}",
reply_markup=stop_markup,
parse_mode="Markdown"
)
except Exception:
pass
except Exception:
pass
await asyncio.sleep(0.35)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not await is_authorized(update):
return
bal = await get_grizzly_balance()

reply_keyboard = [
['💰 Balance', '🎯 Target'],
['💳 TOP UP']
]
markup = ReplyKeyboardMarkup(reply_keyboard, resize_keyboard=True)

await context.bot.send_message(
chat_id=update.effective_chat.id,
text=f"📊 **GrizzlySMS Overview**\n💰 Bal: ${bal} USD",
reply_markup=markup,
parse_mode="Markdown"
)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not await is_authorized(update):
return
global target_running, request_count, stored_otps, waiting_for_custom_price
target_running = False
waiting_for_custom_price = False
request_count = 0
stored_otps.clear()
await update.message.reply_text("🔄 **Bot Reset Successful!", parse_mode="Markdown")
await start(update, context)

def build_fixed_keyboard():
keyboard = []
row = []
for item in FIXED_COUNTRIES:
button_text = f"{item['flag']} {item['name']}"
keyboard_data = f"gsc_{item['id']}"
row.append(InlineKeyboardButton(button_text, callback_data=keyboard_data))
if len(row) == 2:
keyboard.append(row)
row = []
if row:
keyboard.append(row)
return InlineKeyboardMarkup(keyboard)

async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
if not await is_authorized(update):
return
global target_running, waiting_for_custom_price, current_max_price, request_count

text = update.message.text.strip()

if waiting_for_custom_price:
try:
price_val = float(text)
current_max_price = f"{price_val:.4f}"
waiting_for_custom_price = False

target_running = True
request_count = 0
asyncio.create_task(catcher_loop(update.effective_chat.id, context))
except ValueError:
await update.message.reply_text("❌ Invalid input! Please enter a valid number (e.g., 0.25).")
return

if text == '💰 Balance':
await start(update, context)
elif text == '💳 TOP UP':
await context.bot.send_message(
chat_id=update.effective_chat.id,
text=f"📥 Grizzly Deposit**\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n🪙 Network: USDT (BEP20)`\n\n{USDT_BEP20_ADDRESS}`",
parse_mode="Markdown"
)
elif text == '🎯 Target':
target_running = False
markup = build_fixed_keyboard()
await update.message.reply_text("🎯 Select Target Country Region:", reply_markup=markup)

async def inline_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
global target_running, stored_otps, current_max_price, request_count
global target_country_id, target_country_name, waiting_for_custom_price
[9/7/2026 9:43 AM] メ RaFi (Ø,G): query = update.callback_query
if query.from_user.id != MY_TELEGRAM_ID:
return

if query.data == "back_to_countries":
await query.answer()
markup = build_fixed_keyboard()
await query.edit_message_text("🎯 Select Target Country Region:", reply_markup=markup)
return

if query.data.startswith("gsc_"):
await query.answer()
target_country_id = query.data.split("_")[1]
target_country_name = COUNTRY_DICT.get(target_country_id, "Unknown Country")

await query.edit_message_text(f"⏳ Fetching real-time rates for {target_country_name}...")
streams = await get_country_price_streams(target_country_id)
[9/7/2026 10:57 AM] メ RaFi (Ø,G): price_keyboard = []
if streams:
for stream in streams:
price = stream['price']
count = stream['count']
btn_txt = f"{count}pc - {price:.2f}$"
price_keyboard.append([InlineKeyboardButton(btn_txt, callback_data=f"stp_{price}")])
else:
price_keyboard.append([InlineKeyboardButton("⚠️ No Active Stock on Site (Click to Refresh)", callback_data=f"gsc_{target_country_id}")])

price_keyboard.append([InlineKeyboardButton("✏️ Suggest Custom Price", callback_data="btn_custom_price")])
price_keyboard.append([InlineKeyboardButton("🔙 Back to Countries", callback_data="back_to_countries")])
price_markup = InlineKeyboardMarkup(price_keyboard)

await query.edit_message_text(
text=f"⚙️ Available Supplier Streams for {target_country_name}:",
reply_markup=price_markup
)
return

if query.data == "btn_custom_price":
await query.answer()
waiting_for_custom_price = True
await query.edit_message_text("✍️ Enter your custom suggested price in USD\n(e.g., 0.12):", parse_mode="Markdown")
return

if query.data.startswith("stp_"):
selected_price = query.data.split("_")[1]
current_max_price = f"{float(selected_price):.4f}"
await query.answer(f"Target Price Set: ${current_max_price}")
try:
await query.delete_message()
except Exception:
pass

target_running = True
request_count = 0
asyncio.create_task(catcher_loop(query.message.chat_id, context))
return

if query.data.startswith("cnl_"):
order_id = query.data.split("_")[1]
await set_activation_status(order_id, 8)
if order_id in stored_otps:
del stored_otps[order_id]
await query.answer("❌ Order Canceled successfully!")
try:
await query.delete_message()
except Exception:
pass
return

if query.data == "btn_stop":
await query.answer("Stopped")
target_running = False
try:
await query.edit_message_text("🛑 **Catcher Terminated.", parse_mode="Markdown")
except Exception:
pass

elif query.data.startswith("fin_"):
await query.answer("Finished")
parts = query.data.split("_")
order_id = parts[1]
phone_number = parts[2]
await set_activation_status(order_id, 6)
formatted_number = f"+{phone_number.lstrip('+')}"

otp_display = ""
if order_id in stored_otps and stored_otps[order_id]:
otp_display = "\n".join([f"🔑 OTP {idx+1}: {code}" for idx, code in enumerate(stored_otps[order_id])])
del stored_otps[order_id]
[9/7/2026 9:43 AM] メ RaFi (Ø,G): try:
await query.edit_message_text(
text=f"✅ **Saved Successfully**\n📱 Number: `{formatted_number}`\n┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n{otp_display}",
parse_mode="Markdown"
)
except Exception:
pass

elif query.data.startswith("ref_"):
parts = query.data.split("_")
order_id = parts[1]
status_url = f"{BASE_URL}?api_key={API_KEY}&action=getStatus&id={order_id}"

try:
async with aiohttp.ClientSession() as session:
async with session.get(status_url, timeout=4) as response:
if response.status == 200:
res_text = await response.text()
if "STATUS_OK" in res_text:
otp_code = res_text.split(":")[1]
if order_id not in stored_otps:
stored_otps[order_id] = []
if otp_code not in stored_otps[order_id]:
stored_otps[order_id].append(otp_code)
await set_activation_status(order_id, 3)
await query.answer("🎉 New SMS Received!")
else:
await query.answer("⏳ Waiting for code...")
except Exception:
pass

async def post_init(application: Application) -> None:
commands = [
BotCommand("start", "Start"),
BotCommand("cancel", "Reset your bot")
]
await application.bot.set_my_commands(commands)

def main():
app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("cancel", cancel))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))
app.add_handler(CallbackQueryHandler(inline_buttons))

print("🤖 Grizzly Custom Layout Bot Started...")
app.run_polling(drop_pending_updates=True)

if name == 'main':
main()
