import os
import time
import sqlite3
import requests

# =========================
# تنظیمات اصلی
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_TEXT = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("GitHub Secret با نام BOT_TOKEN تنظیم نشده است.")
if not ADMIN_ID_TEXT:
    raise RuntimeError("GitHub Secret با نام ADMIN_ID تنظیم نشده است.")

ADMIN_ID = int(ADMIN_ID_TEXT)
SUPPORT = "@TAHA_THP"

PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "").strip()
PAYMENT_CARDHOLDER = os.getenv("PAYMENT_CARDHOLDER", "").strip()

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/"

PRODUCTS = {
    "5gb": ("۵ گیگابایت", 30000),
    "10gb": ("۱۰ گیگابایت", 70000),
    "20gb": ("۲۰ گیگابایت", 140000),
    "30gb": ("۳۰ گیگابایت", 180000),
    "unlimited1": ("نامحدود تک‌کاربره", 200000),
    "unlimited2": ("نامحدود دوکاربره", 250000),
    "unlimited3": ("نامحدود سه‌کاربره", 300000),
    "unlimited4": ("نامحدود چهارکاربره", 350000),
}

# =========================
# پایگاه داده
# =========================

db = sqlite3.connect("happshop.db", check_same_thread=False)
db.row_factory = sqlite3.Row

db.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY
)
""")

db.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    product TEXT NOT NULL,
    price INTEGER NOT NULL,
    status TEXT NOT NULL,
    receipt_id TEXT
)
""")

order_columns = [
    row["name"] for row in db.execute("PRAGMA table_info(orders)").fetchall()
]
if "receipt_id" not in order_columns:
    db.execute("ALTER TABLE orders ADD COLUMN receipt_id TEXT")

db.commit()# =========================
# ابزارهای تلگرام
# =========================

def api(method, data=None):
    response = requests.post(
        API_URL + method,
        json=data or {},
        timeout=40
    )
    response.raise_for_status()
    result = response.json()
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "Telegram API error"))
    return result


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup is not None:
        payload["reply_markup"] = reply_markup
    return api("sendMessage", payload)


def main_keyboard():
    return {
        "keyboard": [
            [{"text": "🛒 خرید اشتراک"}],
            [{"text": "👤 حساب کاربری"}],
            [{"text": "☎️ پشتیبانی"}]
        ],
        "resize_keyboard": True
    }


def ensure_user(user_id):
    db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    db.commit()# =========================
# محصولات و حساب کاربری
# =========================

def show_products(chat_id):
    rows = []
    for key, (name, price) in PRODUCTS.items():
        rows.append([{
            "text": f"{name} - {price:,} تومان",
            "callback_data": f"buy_{key}"
        }])

    send_message(
        chat_id,
        "🛒 اشتراک موردنظر را انتخاب کن:\n"
        "پس از انتخاب، اطلاعات پرداخت نمایش داده می‌شود.",
        {"inline_keyboard": rows}
    )


def show_account(chat_id, user_id):
    ensure_user(user_id)
    order_count = db.execute(
        "SELECT COUNT(*) AS total FROM orders WHERE user_id = ?",
        (user_id,)
    ).fetchone()["total"]

    paid_count = db.execute(
        "SELECT COUNT(*) AS total FROM orders "
        "WHERE user_id = ? AND status IN (?, ?)",
        (user_id, "در انتظار تحویل", "تحویل شده")
    ).fetchone()["total"]

    send_message(
        chat_id,
        "🤖 اطلاعات حساب کاربری شما:\n\n"
        f"🛒 تعداد سفارش‌ها: {order_count}\n"
        f"📑 تعداد پرداخت‌های تأییدشده: {paid_count}",
        main_keyboard()
)# =========================
# خرید مستقیم و پرداخت سفارش
# =========================

def buy_product(chat_id, user_id, product_key):
    if product_key not in PRODUCTS:
        send_message(chat_id, "این محصول معتبر نیست.")
        return

    ensure_user(user_id)
    name, price = PRODUCTS[product_key]

    cursor = db.execute(
        "INSERT INTO orders (user_id, product, price, status) "
        "VALUES (?, ?, ?, ?)",
        (user_id, name, price, "در انتظار پرداخت")
    )
    order_id = cursor.lastrowid
    db.commit()

    if not PAYMENT_CARD_NUMBER or not PAYMENT_CARDHOLDER:
        send_message(
            chat_id,
            "❌ اطلاعات کارت پرداخت هنوز توسط مدیر تنظیم نشده است.\n"
            f"شماره سفارش: {order_id}\n"
            f"برای راهنمایی با پشتیبانی تماس بگیر: {SUPPORT}",
            main_keyboard()
        )
        send_message(
            ADMIN_ID,
            f"سفارش جدید شماره {order_id} ثبت شد، اما اطلاعات کارت پرداخت "
            "در GitHub Secrets تنظیم نشده است."
        )
        return

    send_message(
        chat_id,
        "✅ سفارش شما ثبت شد.\n\n"
        f"📦 محصول: {name}\n"
        f"💰 مبلغ قابل پرداخت: {price:,} تومان\n"
        f"🔢 شماره سفارش: {order_id}\n\n"
        "💳 اطلاعات پرداخت:\n"
        f"نام صاحب کارت: {PAYMENT_CARDHOLDER}\n"
        f"شماره کارت:\n{PAYMENT_CARD_NUMBER}\n\n"
        "پس از پرداخت، تصویر رسید را همین‌جا ارسال کن.\n"
        "پس از بررسی مدیر، اشتراک برایت ارسال می‌شود.",
        main_keyboard()
                    )
def handle_photo(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    photos = message.get("photo", [])

    if not photos:
        return

    order = db.execute(
        "SELECT id, product, price FROM orders "
        "WHERE user_id = ? AND status = ? "
        "ORDER BY id DESC LIMIT 1",
        (user_id, "در انتظار پرداخت")
    ).fetchone()

    if order is None:
        send_message(
            chat_id,
            "❌ سفارشِ در انتظار پرداخت پیدا نشد. "
            "برای خرید، ابتدا از منوی خرید اشتراک استفاده کن."
        )
        return

    file_id = photos[-1]["file_id"]
    db.execute(
        "UPDATE orders SET receipt_id = ?, status = ? WHERE id = ?",
        (file_id, "در انتظار بررسی پرداخت", order["id"])
    )
    db.commit()

    keyboard = {
        "inline_keyboard": [[
            {
                "text": "✅ تأیید پرداخت",
                "callback_data": f"approve_order_{order['id']}"
            },
            {
                "text": "❌ رد پرداخت",
                "callback_data": f"reject_order_{order['id']}"
            }
        ]]
    }
    api("sendPhoto", {
        "chat_id": ADMIN_ID,
        "photo": file_id,
        "caption": (
            f"🧾 رسید سفارش شماره {order['id']}\n"
            f"شناسه کاربر: {user_id}\n"
            f"محصول: {order['product']}\n"
            f"مبلغ: {order['price']:,} تومان"
        ),
        "reply_markup": keyboard
    })

    send_message(
        chat_id,
        "✅ رسید پرداخت برای مدیر ارسال شد. "
        "پس از بررسی، نتیجه به تو اطلاع داده می‌شود."
    )


def review_order(callback, approve):
    if callback["from"]["id"] != ADMIN_ID:
        api("answerCallbackQuery", {
            "callback_query_id": callback["id"],
            "text": "فقط مدیر می‌تواند پرداخت را بررسی کند.",
            "show_alert": True
        })
        return

    message = callback.get("message", {})
    admin_chat_id = message.get("chat", {}).get("id")
    order_id = int(callback["data"].split("_")[-1])

    order = db.execute(
        "SELECT user_id, status FROM orders WHERE id = ?",
        (order_id,)
    ).fetchone()

    if order is None or order["status"] != "در انتظار بررسی پرداخت":
        api("answerCallbackQuery", {
            "callback_query_id": callback["id"],
            "text": "این سفارش قبلاً بررسی شده یا وجود ندارد.",
            "show_alert": True
        })
        return
    if approve:
        new_status = "در انتظار تحویل"
        customer_text = (
            f"✅ پرداخت سفارش شماره {order_id} تأیید شد.\n"
            "اشتراک پس از آماده‌سازی توسط مدیر برایت ارسال می‌شود."
        )
    else:
        new_status = "پرداخت رد شده"
        customer_text = (
            f"❌ پرداخت سفارش شماره {order_id} تأیید نشد.\n"
            f"برای پیگیری با پشتیبانی تماس بگیر: {SUPPORT}"
        )

    db.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        (new_status, order_id)
    )
    db.commit()

    send_message(order["user_id"], customer_text)
    send_message(
        admin_chat_id,
        f"وضعیت سفارش {order_id}: {new_status}"
    )
    api("editMessageReplyMarkup", {
        "chat_id": admin_chat_id,
        "message_id": message["message_id"],
        "reply_markup": {"inline_keyboard": []}
    })


# =========================
# تحویل اشتراک توسط مدیر
# =========================

def admin_deliver(chat_id, text):
    if chat_id != ADMIN_ID:
        return

    parts = text.split(maxsplit=2)
    if len(parts) < 3:
        send_message(
            chat_id,
            "فرمت دستور:\n/deliver شماره_سفارش متن_کانفیگ"
        )
        return

    try:
        order_id = int(parts[1])
    except ValueError:
        send_message(chat_id, "شماره سفارش معتبر نیست.")
        return

    config_text = parts[2]
    order = db.execute(
        "SELECT user_id, status FROM orders WHERE id = ?",
        (order_id,)
    ).fetchone()    if order is None:
        send_message(chat_id, "سفارش پیدا نشد.")
        return
    if order["status"] != "در انتظار تحویل":
        send_message(
            chat_id,
            "این سفارش هنوز پرداخت تأییدشده و آماده تحویل نیست."
        )
        return

    db.execute(
        "UPDATE orders SET status = ? WHERE id = ?",
        ("تحویل شده", order_id)
    )
    db.commit()

    send_message(
        order["user_id"],
        "🎉 اشتراک شما آماده است:\n\n" + config_text
    )
    send_message(chat_id, f"✅ سفارش {order_id} تحویل شد.")


# =========================
# دریافت پیام‌ها و دکمه‌ها
# =========================

def handle_message(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    message_text = message.get("text", "")

    ensure_user(user_id)

    if message_text.startswith("/start"):
        send_message(
            chat_id,
            "سلام! 🌸 به فروشگاه HappshopTH خوش آمدید.",
            main_keyboard()
        )
    elif message_text.startswith("/deliver"):
        admin_deliver(chat_id, message_text)
    elif message_text == "🛒 خرید اشتراک":
        show_products(chat_id)
    elif message_text == "👤 حساب کاربری":
        show_account(chat_id, user_id)
    elif message_text == "☎️ پشتیبانی":
        send_message(
            chat_id,
            f"برای پشتیبانی به این حساب پیام بده:\n{SUPPORT}",
            main_keyboard()
        )
    else:
        send_message(
            chat_id,
            "یکی از گزینه‌های منو را انتخاب کن.",
            main_keyboard()
        )


def handle_callback(callback):
    data = callback.get("data", "")

    api("answerCallbackQuery", {
        "callback_query_id": callback["id"]
    })

    if data.startswith("buy_"):
        product_key = data.replace("buy_", "", 1)
        chat_id = callback["message"]["chat"]["id"]
        user_id = callback["from"]["id"]
        buy_product(chat_id, user_id, product_key)

    elif data.startswith("approve_order_"):
        review_order(callback, True)

    elif data.startswith("reject_order_"):
        review_order(callback, False)


# =========================
# اجرای ربات
# =========================

def run_bot():
    print("HappshopTH is running!")
    offset = None

    while True:
        try:
            result = api("getUpdates", {
                "offset": offset,
                "timeout": 30
            })

            for update in result.get("result", []):
                offset = update["update_id"] + 1

                if "message" in update:
                    msg = update["message"]
                    if "photo" in msg:
                        handle_photo(msg)
                    else:
                        handle_message(msg)

                elif "callback_query" in update:
                    handle_callback(update["callback_query"])

        except Exception as error:
            print("Error:", error)
            time.sleep(5)


if __name__ == "__main__":
    run_bot()
