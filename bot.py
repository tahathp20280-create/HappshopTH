
import os
import time
import sqlite3
import requests

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not TOKEN or not ADMIN_ID:
    raise RuntimeError("BOT_TOKEN or ADMIN_ID is missing!")

API = f"https://api.telegram.org/bot{TOKEN}/"

SUPPORT = "@TAHA_THP"

PRODUCTS = {
    "p1": ("۵ گیگابایت - یک ماهه", 30000),
    "p2": ("۱۰ گیگابایت - یک ماهه", 70000),
    "p3": ("۲۰ گیگابایت - یک ماهه", 140000),
    "p4": ("۳۰ گیگابایت - یک ماهه", 180000),
    "p5": ("نامحدود تک‌کاربره - یک ماهه", 200000),
    "p6": ("نامحدود دوکاربره - یک ماهه", 250000),
    "p7": ("نامحدود سه‌کاربره - یک ماهه", 300000),
}

db = sqlite3.connect("shop.db", check_same_thread=False)

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product TEXT,
    price INTEGER,
    status TEXT
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS topups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    fee INTEGER,
    total INTEGER,
    receipt_id TEXT,
    status TEXT
)
""")

db.commit()
def api(method, data=None):
    response = requests.post(
        API + method,
        json=data or {},
        timeout=40
    )
    return response.json()


def send_message(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    api("sendMessage", data)


def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🛒 خرید اشتراک"}],
            [
                {"text": "👤 حساب کاربری"},
                {"text": "💰 شارژ کیف پول"}
            ],
            [{"text": "📞 پشتیبانی"}]
        ],
        "resize_keyboard": True
    }


def ensure_user(user_id):
    db.execute(
        "INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)",
        (user_id,)
    )
    db.commit()

def show_products(chat_id):
    buttons = []

    for key, product in PRODUCTS.items():
        name, price = product

        buttons.append([{
            "text": f"{name} | {price:,} تومان",
            "callback_data": f"buy_{key}"
        }])

    send_message(
        chat_id,
        "🛒 یکی از اشتراک‌های زیر را انتخاب کن:",
        {"inline_keyboard": buttons}
    )


def show_account(chat_id, user_id):
    ensure_user(user_id)

    balance = db.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    count = db.execute(
        "SELECT COUNT(*) FROM orders WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    send_message(
        chat_id,
        "🤖 اطلاعات حساب کاربری شما:\n\n"
        f"💰 موجودی: {balance:,} تومان\n"
        f"🛒 تعداد سفارش‌ها: {count}\n"
        f"📑 تعداد فاکتورها: {count}\n"
        "🤝 تعداد زیرمجموعه‌ها: ۰\n"
        "🔖 گروه کاربری: نماینده",
        main_keyboard()
    )


def buy_product(chat_id, user_id, product_key):
    if product_key not in PRODUCTS:
        return

    ensure_user(user_id)

    name, price = PRODUCTS[product_key]

    balance = db.execute(
        "SELECT balance FROM users WHERE user_id = ?",
        (user_id,)
    ).fetchone()[0]

    if balance < price:
        send_message(
            chat_id,
            "❌ موجودی کیف پول شما کافی نیست.\n"
            f"قیمت اشتراک: {price:,} تومان\n"
            f"موجودی شما: {balance:,} تومان\n\n"
            "برای افزایش موجودی از بخش شارژ کیف پول اقدام کن.",
            main_keyboard()
        )
        return

    db.execute(
        "UPDATE users SET balance = balance - ? WHERE user_id = ?",
        (price, user_id)
    )

    cursor = db.execute(
        "INSERT INTO orders (user_id, product, price, status) "
        "VALUES (?, ?, ?, ?)",
        (user_id, name, price, "در انتظار تحویل")
    )

    order_id = cursor.lastrowid
    db.commit()

    send_message(
        chat_id,
        "✅ سفارش شما ثبت شد.\n\n"
        f"شماره سفارش: {order_id}\n"
        f"اشتراک: {name}\n"
        f"مبلغ: {price:,} تومان\n"
        "وضعیت: در انتظار تحویل کانفیگ",
        main_keyboard()
    )

    send_message(
        ADMIN_ID,
        "📦 سفارش جدید ثبت شد.\n\n"
        f"شماره سفارش: {order_id}\n"
        f"شناسه کاربر: {user_id}\n"
        f"محصول: {name}\n"
        f"مبلغ: {price:,} تومان\n\n"
        f"برای تحویل کانفیگ دستور زیر را ارسال کن:\n"
        f"/deliver {order_id} کانفیگ"
)


def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    text = message.get("text", "")

    ensure_user(user_id)

    if text.startswith("/start"):
        send_message(
            chat_id,
            "سلام! 🌸 به فروشگاه HappshopTH خوش آمدید.",
            main_keyboard()
        )

    elif text == "🛒 خرید اشتراک":
        show_products(chat_id)

    elif text == "👤 حساب کاربری":
        show_account(chat_id, user_id)

    elif text == "💰 شارژ کیف پول":
        send_message(
            chat_id,
            "برای شارژ کیف پول با پشتیبانی تماس بگیر:\n"
            f"{SUPPORT}",
            main_keyboard()
        )

    elif text == "📞 پشتیبانی":
        send_message(
            chat_id,
            f"پشتیبانی: {SUPPORT}",
            main_keyboard()
        )

    elif text.startswith("/addbalance") and user_id == ADMIN_ID:
        try:
            parts = text.split()
            target_id = int(parts[1])
            amount = int(parts[2])

            if amount <= 0:
                raise ValueError

            ensure_user(target_id)

            db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, target_id)
            )
            db.commit()

            send_message(chat_id, "✅ موجودی اضافه شد.")
            send_message(
                target_id,
                f"💰 مبلغ {amount:,} تومان به کیف پول شما اضافه شد."
            )

        except (ValueError, IndexError):
            send_message(
                chat_id,
                "فرمت دستور:\n/addbalance شناسه_کاربر مبلغ"
            )

    elif text.startswith("/deliver") and user_id == ADMIN_ID:
        try:
            parts = text.split(maxsplit=2)
            order_id = int(parts[1])
            config = parts[2]

            order = db.execute(
                "SELECT user_id, status FROM orders WHERE id = ?",
                (order_id,)
            ).fetchone()

            if not order:
                send_message(chat_id, "❌ سفارش پیدا نشد.")
                return

            target_id, status = order

            if status == "تحویل شده":
                send_message(chat_id, "این سفارش قبلاً تحویل شده است.")
                return

            db.execute(
                "UPDATE orders SET status = ? WHERE id = ?",
                ("تحویل شده", order_id)
            )
            db.commit()

            send_message(
                target_id,
                "✅ کانفیگ سفارش شما:\n\n" + config
            )
            send_message(chat_id, "✅ کانفیگ ارسال شد.")

        except (ValueError, IndexError):
            send_message(
                chat_id,
                "فرمت دستور:\n/deliver شماره_سفارش کانفیگ"
            )


def handle_callback(callback):
    data = callback.get("data", "")
    message = callback.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    user_id = callback["from"]["id"]

    api("answerCallbackQuery", {
        "callback_query_id": callback["id"]
    })

    if data.startswith("buy_"):
        product_key = data.replace("buy_", "", 1)
        buy_product(chat_id, user_id, product_key)


def run_bot():
    print("HappshopTH is running!")
    offset = None

    while True:
        try:
            result = api("getUpdates", {
                "offset": offset,
                "timeout": 30
            })

            if not result.get("ok"):
                time.sleep(3)
                continue

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    handle_message(update["message"])

                elif "callback_query" in update:
                    handle_callback(update["callback_query"])

        except Exception as error:
            print("Error:", error)
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
