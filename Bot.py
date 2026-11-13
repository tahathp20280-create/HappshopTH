
import os
import time
import sqlite3
import requests

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8911720331

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing")

URL = "https://api.telegram.org/bot" + TOKEN + "/"

DB = sqlite3.connect("happshop.db")
DB.row_factory = sqlite3.Row


PRODUCTS = [
    ("۵ گیگابایت - یک ماهه", 30000),
    ("۱۰ گیگابایت - یک ماهه", 70000),
    ("۲۰ گیگابایت - یک ماهه", 140000),
    ("۳۰ گیگابایت - یک ماهه", 180000),
    ("نامحدود تک کاربره - یک ماهه", 200000),
    ("نامحدود دو کاربره - یک ماهه", 250000),
    ("نامحدود سه کاربره - یک ماهه", 300000),
]

DB.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product TEXT,
    price INTEGER,
    status TEXT,
    receipt_id TEXT,
    config TEXT
)
""")
DB.commit()

DB.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    first_name TEXT,
    username TEXT,
    blocked INTEGER DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
DB.commit()


def send(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        data["reply_markup"] = keyboard

    response = requests.post(
        URL + "sendMessage",
        json=data,
        timeout=20
    )
    response.raise_for_status()


def main_keyboard(is_admin=False):
    buttons = [
        ["🛍️ خرید اشتراک"],
        ["📦 سفارش‌های من"],
        ["📞 پشتیبانی", "ℹ️ درباره فروشگاه"]
    ]

    if is_admin:

buttons.append(["👑 پنل مدیریت"])
buttons.append(["👥 مدیریت مشتریان"])
buttons.append(["📋 همه سفارش‌ها"])
buttons.append(["⏳ سفارش‌های در انتظار"])
    return {
        "keyboard": buttons,
        "resize_keyboard": True
    }


def products_keyboard():
    return {
        "inline_keyboard": [
            [{
                "text": f"{name} | {price:,} تومان",
                "callback_data": f"buy:{i}"
            }]
            for i, (name, price) in enumerate(PRODUCTS)
        ]
    }


def admin_keyboard(order_id):
    return {
        "inline_keyboard": [[
            {
                "text": "✅ تأیید پرداخت",
                "callback_data": f"approve:{order_id}"
            },
            {
                "text": "❌ رد پرداخت",
                "callback_data": f"reject:{order_id}"
            }
        ]]
    }

def handle_message(message):
    user = message.get("from", {})
    user_id = user.get("id")
    chat_id = message.get("chat", {}).get("id")
    msg = message.get("text", "")

    if not user_id or not chat_id:
        return

    is_admin = user_id == ADMIN_ID

DB.execute("""
INSERT INTO users (user_id, first_name, username)
VALUES (?, ?, ?)
ON CONFLICT(user_id) DO UPDATE SET
first_name=excluded.first_name,
username=excluded.username
""", (
    user_id,
    user.get("first_name", ""),
    user.get("username", "")
))
DB.commit()

blocked = DB.execute(
    "SELECT blocked FROM users WHERE user_id=?",
    (user_id,)
).fetchone()

if blocked and blocked["blocked"]:
    send(chat_id, "⛔ دسترسی شما به ربات مسدود شده است.")
    return

    if msg == "/start":
        send(
            chat_id,
            "🌸 به فروشگاه HappshopTH خوش آمدید!",
            main_keyboard(is_admin)
        )

    elif msg == "🛍️ خرید اشتراک":
        send(
            chat_id,
            "🌸 پلن موردنظر خود را انتخاب کنید:",
            products_keyboard()
        )

    elif msg == "📦 سفارش‌های من":
        orders = DB.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC",
            (user_id,)
        ).fetchall()

        if not orders:
            send(chat_id, "شما هنوز سفارشی ندارید.")
            return

        text = "📦 سفارش‌های شما:\n\n"

        for order in orders:
            text += (
                f"شماره سفارش: {order['id']}\n"
                f"محصول: {order['product']}\n"
                f"مبلغ: {order['price']:,} تومان\n"
                f"وضعیت: {order['status']}\n\n"
            )

        send(chat_id, text)

    elif msg == "📞 پشتیبانی":
        send(chat_id, "📞 پشتیبانی:\n@TAHA_THP")

    elif msg == "ℹ️ درباره فروشگاه":
        send(
            chat_id,
            "🌸 HappshopTH\nفروشگاه اشتراک‌های دیجیتال"
        )

    elif msg == "👑 پنل مدیریت":
        if is_admin:
            send(
                chat_id,
                "👑 پنل مدیریت\n\n"
                "برای ارسال کانفیگ:\n"
                "/config شماره سفارش\n"
                "سپس کانفیگ را در خط بعد بنویس.",
                main_keyboard(True)
            )
        else:
            send(chat_id, "⛔ دسترسی غیرمجاز است.")
    elif msg == "👥 مدیریت مشتریان" and is_admin:
        users = DB.execute(
            "SELECT * FROM users ORDER BY created_at DESC"
        ).fetchall()

        if not users:
            send(chat_id, "هنوز مشتری ثبت نشده است.")
        else:
            text = "👥 فهرست مشتریان:\n\n"
            for u in users:
                text += (
                    f"شناسه: {u['user_id']}\n"
                    f"نام: {u['first_name']}\n"
                    f"آیدی: @{u['username'] or 'ندارد'}\n\n"
                )
            send(chat_id, text)
        elif msg == "📋 همه سفارش‌ها" and is_admin:
        orders = DB.execute(
            "SELECT * FROM orders ORDER BY id DESC"
        ).fetchall()

        if not orders:
            send(chat_id, "هنوز سفارشی ثبت نشده است.")
        else:
            text = "📋 همه سفارش‌ها:\n\n"
            for o in orders:
                text += (
                    f"شماره: {o['id']}\n"
                    f"مشتری: {o['user_id']}\n"
                    f"محصول: {o['product']}\n"
                    f"مبلغ: {o['price']:,} تومان\n"
                    f"وضعیت: {o['status']}\n\n"
                )
            send(chat_id, text)
      elif msg == "⏳ سفارش‌های در انتظار" and is_admin:
        orders = DB.execute(
            "SELECT * FROM orders WHERE status='reviewing' ORDER BY id DESC"
        ).fetchall()

        if not orders:
            send(chat_id, "سفارش در انتظاری وجود ندارد.")
        else:
            for o in orders:
                send(
                    chat_id,
                    f"🧾 سفارش شماره {o['id']}\n"
                    f"مشتری: {o['user_id']}\n"
                    f"محصول: {o['product']}\n"
                    f"مبلغ: {o['price']:,} تومان"
                )
else:
        send(chat_id, "لطفاً از دکمه‌های منو استفاده کنید.")

def handle_callback(callback):
    user_id = callback.get("from", {}).get("id")
    data = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")

    api_answer = requests.post(
        URL + "answerCallbackQuery",
        json={"callback_query_id": callback["id"]},
        timeout=15
    )

    if data.startswith("buy:"):
        try:
            index = int(data.split(":")[1])
            product, price = PRODUCTS[index]
        except (ValueError, IndexError):
            return

        DB.execute(
            """
            INSERT INTO orders
            (user_id, product, price, status)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, product, price, "waiting_receipt")
        )
        DB.commit()

        order_id = DB.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        send(
            chat_id,
            "🛍️ سفارش شما ثبت شد!\n\n"
            f"شماره سفارش: {order_id}\n"
            f"محصول: {product}\n"
            f"مبلغ: {price:,} تومان\n\n"
            "💳 اطلاعات پرداخت:\n"
            "شماره کارت:\n"
            "6037991768691648\n\n"
            "به نام: محمد طاها حسین پور\n\n"
            "پس از پرداخت، تصویر رسید را ارسال کنید."
        )

def handle_receipt(message):
    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")

    if not user_id or not chat_id:
        return

    order = DB.execute(
        """
        SELECT * FROM orders
        WHERE user_id = ?
        AND status = 'waiting_receipt'
        ORDER BY id DESC LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    if not order:
        send(chat_id, "ابتدا یک اشتراک انتخاب کنید.")
        return

    photos = message.get("photo", [])

    if not photos:
        send(chat_id, "لطفاً تصویر رسید پرداخت را ارسال کنید.")
        return

    receipt_id = photos[-1]["file_id"]

    DB.execute(
        """
        UPDATE orders
        SET status = 'reviewing', receipt_id = ?
        WHERE id = ?
        """,
        (receipt_id, order["id"])
    )
    DB.commit()

    requests.post(
        URL + "sendPhoto",
        json={
            "chat_id": ADMIN_ID,
            "photo": receipt_id,
            "caption": (
                "🧾 رسید پرداخت جدید\n\n"
                f"شماره سفارش: {order['id']}\n"
                f"شناسه مشتری: {user_id}\n"
                f"محصول: {order['product']}\n"
                f"مبلغ: {order['price']:,} تومان"
            ),
            "reply_markup": admin_keyboard(order["id"])
        },
        timeout=20
    )

    send(
        chat_id,
        "✅ رسید شما برای مدیر ارسال شد.\n"
        "پس از بررسی پرداخت، نتیجه اعلام می‌شود."
    )

def handle_admin_callback(callback):
    user_id = callback.get("from", {}).get("id")
    data = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")

    if user_id != ADMIN_ID:
        requests.post(
            URL + "answerCallbackQuery",
            json={
                "callback_query_id": callback["id"],
                "text": "⛔ دسترسی غیرمجاز",
                "show_alert": True
            },
            timeout=15
        )
        return

    action, order_id = data.split(":")
    order_id = int(order_id)

    order = DB.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not order or order["status"] != "reviewing":
        send(chat_id, "این سفارش قبلاً بررسی شده یا معتبر نیست.")
        return

    if action == "approve":
        DB.execute(
            "UPDATE orders SET status='approved' WHERE id=?",
            (order_id,)
        )
        DB.commit()

        send(
            order["user_id"],
            "✅ پرداخت شما تأیید شد!\n"
            "اشتراک شما پس از آماده‌سازی ارسال می‌شود."
        )

        send(
            chat_id,
            f"✅ سفارش {order_id} تأیید شد.\n\n"
            f"برای ارسال کانفیگ بنویس:\n"
            f"/config {order_id}\n"
            "سپس در خط بعد کانفیگ را قرار بده."
        )

    elif action == "reject":
        DB.execute(
            "UPDATE orders SET status='rejected' WHERE id=?",
            (order_id,)
        )
        DB.commit()

        send(
            order["user_id"],
            "❌ پرداخت سفارش شما تأیید نشد.\n"
            "برای پیگیری با پشتیبانی تماس بگیرید."
        )

        send(chat_id, f"❌ سفارش {order_id} رد شد.")

def handle_config(message):
    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    msg = message.get("text", "")

    if user_id != ADMIN_ID:
        return

    lines = msg.split("\n", 1)
    command = lines[0].split()

    if len(command) != 2:
        send(
            chat_id,
            "فرمت صحیح:\n"
            "/config 12\n"
            "کانفیگ در خط بعد"
        )
        return

    try:
        order_id = int(command[1])
    except ValueError:
        send(chat_id, "شماره سفارش معتبر نیست.")
        return

    if len(lines) < 2 or not lines[1].strip():
        send(chat_id, "کانفیگ را در خط بعد وارد کن.")
        return

    config = lines[1].strip()

    order = DB.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not order:
        send(chat_id, "❌ سفارش پیدا نشد.")
        return

    if order["status"] != "approved":
        send(chat_id, "⛔ ابتدا باید پرداخت سفارش تأیید شود.")
        return

    requests.post(
        URL + "sendMessage",
        json={
            "chat_id": order["user_id"],
            "text": (
                "🎉 اشتراک شما آماده است!\n\n"
                "🔐 کانفیگ VPN:\n\n"
                + config
            ),
            "protect_content": True
        },
        timeout=20
    )

    DB.execute(
        """
        UPDATE orders
        SET status='delivered', config=?
        WHERE id=?
        """,
        (config, order_id)
    )
    DB.commit()

    send(chat_id, f"✅ کانفیگ سفارش {order_id} ارسال شد.")

print("HappshopTH Bot is starting...")

offset = 0

while True:
    try:
        response = requests.get(
            URL + "getUpdates",
            params={
                "offset": offset,
                "timeout": 30
            },
            timeout=35
        )

        response.raise_for_status()
        result = response.json()

        if not result.get("ok"):
            print("Telegram API error:", result)
            time.sleep(3)
            continue

        for update in result["result"]:
            offset = update["update_id"] + 1

            if "callback_query" in update:
                callback = update["callback_query"]
                data = callback.get("data", "")

                if data.startswith("buy:"):
                    handle_callback(callback)

                elif data.startswith(("approve:", "reject:")):
                    handle_admin_callback(callback)

            elif "message" in update:
                message = update["message"]

                if message.get("photo"):
                    handle_receipt(message)

                elif message.get("text", "").startswith("/config"):
                    handle_config(message)

                else:
                    handle_message(message)

    except Exception as error:
        print("Bot error:", error)
        time.sleep(5)
