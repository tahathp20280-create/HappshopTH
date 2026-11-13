import os
import time
import sqlite3
import requests

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8911720331
CARD = "6037991768691648"
CARD_NAME = "محمد طاها حسین پور"

if not TOKEN:
    raise ValueError("BOT_TOKEN is missing!")

URL = f"https://api.telegram.org/bot{TOKEN}/"
DB = sqlite3.connect("happshop.db", check_same_thread=False)
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
    config TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
""")
DB.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")
DB.commit()


def get_offset():
    row = DB.execute(
        "SELECT value FROM settings WHERE key='offset'"
    ).fetchone()
    return int(row["value"]) if row else 0


def save_offset(value):
    DB.execute(
        "INSERT OR REPLACE INTO settings VALUES ('offset', ?)",
        (str(value),)
    )
    DB.commit()


def api(method, data=None):
    response = requests.post(
        URL + method,
        json=data or {},
        timeout=25
    )
    response.raise_for_status()
    return response.json()


def send(chat_id, text, keyboard=None):
    data = {
        "chat_id": chat_id,
        "text": text
    }
    if keyboard:
        data["reply_markup"] = keyboard
    api("sendMessage", data)


def main_keyboard(is_admin=False):
    buttons = [
        ["🛍️ خرید اشتراک"],
        ["📦 سفارش‌های من"],
        ["📞 پشتیبانی", "ℹ️ درباره فروشگاه"]
    ]

    if is_admin:
        buttons.append(["👑 پنل مدیریت"])

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

    if msg == "/start":
        send(
            chat_id,
            "🌸 به فروشگاه HappshopTH خوش آمدید!\n"
            "برای خرید اشتراک از منوی زیر استفاده کنید.",
            main_keyboard(is_admin)
        )
        return

    if msg == "👑 پنل مدیریت":
        if is_admin:
            send(
                chat_id,
                "👑 پنل مدیریت HappshopTH\n\n"
                "برای ارسال کانفیگ سفارش تأییدشده:\n"
                "/config شماره_سفارش\n"
                "سپس در خط بعد کانفیگ را قرار دهید.",
                main_keyboard(True)
            )
        else:
            send(chat_id, "⛔ دسترسی غیرمجاز است.")
        return

    if msg == "🛍️ خرید اشتراک":
        send(
            chat_id,
            "🌸 پلن موردنظر خود را انتخاب کنید:",
            products_keyboard()
        )
        return

    if msg == "📦 سفارش‌های من":
        orders = DB.execute(
            "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10",
            (user_id,)
        ).fetchall()

        if not orders:
            send(chat_id, "شما هنوز سفارشی ثبت نکرده‌اید.")
            returntext = "📦 سفارش‌های شما:\n\n"        for order in orders:
            text += (
                f"شماره سفارش: {order['id']}\n"
                f"محصول: {order['product']}\n"
                f"مبلغ: {order['price']:,} تومان\n"
                f"وضعیت: {order['status']}\n\n"
            )

        send(chat_id, text)
        return

    if msg == "📞 پشتیبانی":
        send(chat_id, "📞 پشتیبانی:\n@TAHA_THP")
        return

    if msg == "ℹ️ درباره فروشگاه":
        send(
            chat_id,
            "🌸 HappshopTH\nفروشگاه اشتراک‌های دیجیتال"
        )
        return

    # ارسال کانفیگ توسط مدیر
    if msg.startswith("/config"):
        if not is_admin:
            send(chat_id, "⛔ دسترسی غیرمجاز است.")
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

        config = lines[1].strip() if len(lines) > 1 else ""

        if not config:
            send(
                chat_id,
                "لطفاً کانفیگ را در خط بعد دستور قرار بده."
            )
            return

        order = DB.execute(
            "SELECT * FROM orders WHERE id=?",
            (order_id,)
        ).fetchone()

        if not order:
            send(chat_id, "❌ سفارش پیدا نشد.")
            return

        if order["status"] != "approved":
            send(
                chat_id,
                "⛔ این سفارش هنوز تأیید نشده است."
            )
            return

        api("sendMessage", {
            "chat_id": order["user_id"],
            "text": (
                "🎉 پرداخت شما تأیید شد!\n\n"
                "🌸 اشتراک شما آماده است:\n\n"
                + config
            ),
            "protect_content": True
        })

        DB.execute(
            "UPDATE orders SET status='delivered', config=? WHERE id=?",
            (config, order_id)
        )
        DB.commit()

        send(chat_id, f"✅ کانفیگ سفارش {order_id} ارسال شد.")
        return

    # دریافت رسید بانکی
    if message.get("photo"):
        order = DB.execute(
            """SELECT * FROM orders
               WHERE user_id=? AND status='waiting_receipt'
               ORDER BY id DESC LIMIT 1""",
            (user_id,)
        ).fetchone()

        if not order:
            send(chat_id, "ابتدا یک محصول انتخاب و سفارش ثبت کنید.")
            return

        receipt_id = message["photo"][-1]["file_id"]

        DB.execute(
            """UPDATE orders SET status='reviewing', receipt_id=?
               WHERE id=?""",
            (receipt_id, order["id"])
        )
        DB.commit()

        api("sendPhoto", {
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
        })

        send(
            chat_id,
            "✅ رسید شما برای مدیر ارسال شد.\n"
            "پس از بررسی پرداخت، نتیجه اعلام می‌شود."
        )
        return

    send(chat_id, "برای شروع از منوی اصلی استفاده کنید.")


def handle_callback(callback):
    user_id = callback.get("from", {}).get("id")
    data = callback.get("data", "")
    chat_id = callback.get("message", {}).get("chat", {}).get("id")

    api("answerCallbackQuery", {
        "callback_query_id": callback["id"]
    })

    if data.startswith("buy:"):
        try:
            index = int(data.split(":")[1])
            product, price = PRODUCTS[index]
        except (ValueError, IndexError):
            returnDB.execute(            """INSERT INTO orders
               (user_id, product, price, status)
               VALUES (?, ?, ?, 'waiting_receipt')""",
            (user_id, product, price)
        )
        DB.commit()

        order_id = DB.execute(
            "SELECT last_insert_rowid()"
        ).fetchone()[0]

        send(
            chat_id,
            "🛍️ سفارش شما ثبت شد.\n\n"
            f"شماره سفارش: {order_id}\n"
            f"محصول: {product}\n"
            f"مبلغ: {price:,} تومان\n\n"
            "💳 اطلاعات پرداخت:\n"
            f"شماره کارت:\n{CARD}\n"
            f"به نام: {CARD_NAME}\n\n"
            "پس از پرداخت، تصویر رسید را همین‌جا ارسال کنید."
        )
        return

    if data.startswith(("approve:", "reject:")):
        if user_id != ADMIN_ID:
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
                "✅ پرداخت شما توسط مدیر تأیید شد.\n"
                "کانفیگ اشتراک پس از آماده‌سازی ارسال می‌شود."
            )

            send(
                chat_id,
                f"✅ سفارش {order_id} تأیید شد.\n\n"
                f"برای ارسال کانفیگ بنویس:\n"
                f"/config {order_id}\n"
                "در خط بعد کانفیگ را قرار بده."
            )

        else:
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


print("🌸 HappshopTH is running!")

while True:
    try:
        response = requests.get(
            URL + "getUpdates",
            params={
                "offset": get_offset(),
                "timeout": 30
            },
            timeout=35
        )
        response.raise_for_status()

        result = response.json()

        if not result.get("ok"):
            time.sleep(3)
            continue

        for update in result["result"]:
            save_offset(update["update_id"] + 1)

            if "message" in update:
                handle_message(update["message"])

            elif "callback_query" in update:
                handle_callback(update["callback_query"])

    except Exception as error:
        print("Error:", error)
        time.sleep(3)
