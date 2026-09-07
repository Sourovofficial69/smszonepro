import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import aiohttp

BOT_TOKEN = "8996139501:AAFrJeSdWSValWkyMbjiKuelpa5_ONGEmNY"
ADMIN_USER_ID = 6553306143
GRIZZLY_API_KEY = "e932533c0823ba8d18a4c18903fe1c66"
BASE_URL = "https://api.grizzlysms.com/stubs/handler_api.php"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
bot_users = set()

ALLOWED_COUNTRIES = [
    {"name": "Jordan", "api_id": "116", "price": 0.41},
    {"name": "Swaziland", "api_id": "106", "price": 0.26},
    {"name": "Ecuador", "api_id": "105", "price": 0.35},
    {"name": "Norway", "api_id": "174", "price": 0.61},
    {"name": "Slovakia", "api_id": "141", "price": 0.75},
    {"name": "Suriname", "api_id": "142", "price": 0.39},
    {"name": "Hungary", "api_id": "84", "price": 0.45},
    {"name": "Bahrain", "api_id": "145", "price": 0.35},
    {"name": "Aruba", "api_id": "179", "price": 0.21},
    {"name": "Serbia", "api_id": "29", "price": 0.56},
    {"name": "Bolivia", "api_id": "92", "price": 0.32},
    {"name": "Azerbaijan", "api_id": "35", "price": 0.65},
    {"name": "Cape Verde", "api_id": "186", "price": 0.33},
    {"name": "Bosnia & Herzegovina", "api_id": "108", "price": 0.56}
]

async def get_grizzly_balance():
    url = f"{BASE_URL}?api_key={GRIZZLY_API_KEY}&action=getBalance"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
            if text.startswith("ACCESS_BALANCE"):
                return text.split(":")[1]
            return "0.00"

async def get_phone_number(country_id, service_id="tg"):
    url = f"{BASE_URL}?api_key={GRIZZLY_API_KEY}&action=getNumber&service={service_id}&country={country_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
            if text.startswith("ACCESS_NUMBER:"):
                parts = text.split(":")
                return {"id": parts[1], "number": parts[2]}
            return None

async def get_sms_code(phone_id):
    url = f"{BASE_URL}?api_key={GRIZZLY_API_KEY}&action=getStatus&id={phone_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            text = await resp.text()
            if text.startswith("STATUS_OK:"):
                return text.replace("STATUS_OK:", "").strip()
            return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    bot_users.add(message.from_user.id)
    text = "👋 **স্বাগতম!**\n\n📱 নম্বর কিনতে লিখুন: `/getnumber`\n📩 SMS পেতে লিখুন: `/getcode OrderID`"
    if message.from_user.id == ADMIN_USER_ID:
        text += "\n\n👑 **এডমিন কন্ট্রোল:** `/admin`"
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("getnumber"))
async def get_number_cmd(message: types.Message):
    keyboard = []
    row = []
    for c in ALLOWED_COUNTRIES:
        btn = InlineKeyboardButton(text=f"{c['name']} (${c['price']})", callback_data=f"buy_{c['api_id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
        
    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("🌐 **একটি দেশ নির্বাচন করুন:**", reply_markup=markup, parse_mode="Markdown")

@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def buy_callback(callback_query: types.CallbackQuery):
    api_id = callback_query.data.replace("buy_", "")
    country = next((c for c in ALLOWED_COUNTRIES if c["api_id"] == api_id), None)
    
    if country:
        await callback_query.answer(f"{country['name']} এর নম্বর প্রসেস করা হচ্ছে...")
        phone = await get_phone_number(api_id)
        
        if phone:
            msg = (f"✅ **নম্বর পাওয়া গেছে!**\n\n"
                   f"🌍 **দেশ:** {country['name']}\n"
                   f"📱 **নম্বর:** `{phone['number']}`\n"
                   f"🆔 **Order ID:** `{phone['id']}`\n"
                   f"💵 **মূল্য:** ${country['price']}\n\n"
                   f"SMS কোড পেতে লিখুন: `/getcode {phone['id']}`")
            await callback_query.message.answer(msg, parse_mode="Markdown")
        else:
            await callback_query.message.answer("❌ স্টক শেষ বা ব্যালেন্স নেই।")

@dp.message(Command("getcode"))
async def get_code_cmd(message: types.Message):
    parts = message.text.split()
    if len(parts) >= 2:
        order_id = parts[1]
        await message.answer("📩 SMS চেক করা হচ্ছে...")
        code = await get_sms_code(order_id)
        if code:
            await message.answer(f"🎉 **আপনার টেলিগ্রাম কোড:** `{code}`", parse_mode="Markdown")
        else:
            await message.answer("⏳ এখনো SMS আসেনি। কিছুক্ষণ পর আবার চেষ্টা করুন।")
    else:
        await message.answer("⚠️ Order ID দিন। উদাহরণ: `/getcode 12345678`", parse_mode="Markdown")

@dp.message(Command("admin"))
async def admin_cmd(message: types.Message):
    if message.from_user.id == ADMIN_USER_ID:
        balance = await get_grizzly_balance()
        await message.answer(f"👑 **এডমিন প্যানেল**\n\n💰 API ব্যালেন্স: ${balance}\n👥 মোট ইউজার: {len(bot_users)}", parse_mode="Markdown")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
