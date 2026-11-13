
import os
import time
import requests

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

keyboard = {
    "keyboard": [
        ["🛍️ مشاهده محصولات", "🔍 جستجوی محصول"],
        ["🛒 سبد خرید", "📞 ارتباط با پشتیبانی"],
        ["ℹ️ درباره فروشگاه"]
    ],
    "resize_keyboard": True
}

print("HappshopTH is running!")

while True:
    try:
        response = requests.get(
            URL + "getUpdates",
            params={"offset": offset if 'offset' in globals() else 0,
                    "timeout": 30},
            timeout=35
        )
        updates = response.json()["result"]

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            msg = message.get("text", "")

            if not chat_id:
                continue

            if msg == "/start":
                requests.post(URL + "sendMessage", data={
                    "chat_id": chat_id,
                    "text": "سلام! 🌸 به فروشگاه HappshopTH خوش آمدید.",
                    "reply_markup": __import__("json").dumps(keyboard)
                })

            elif msg == "🛍️ مشاهده محصولات":
                answer = "🛍️ به‌زودی محصولات فروشگاه نمایش داده می‌شوند."

            elif msg == "🔍 جستجوی محصول":
                answer = "🔍 قابلیت جستجوی محصولات به‌زودی فعال می‌شود."

            elif msg == "🛒 سبد خرید":
                answer = "🛒 سبد خرید شما فعلاً خالی است."

            elif msg == "📞 ارتباط با پشتیبانی":
                answer = "📞 برای ارتباط با پشتیبانی پیام خود را ارسال کنید."

            elif msg == "ℹ️ درباره فروشگاه":
                answer = "🌸 به HappshopTH خوش آمدید!"

            else:
                answer = None

            if answer:
                requests.post(URL + "sendMessage", data={
                    "chat_id": chat_id,
                    "text": answer
                })

    except Exception as e:
        print("Error:", e)
        time.sleep(3)
