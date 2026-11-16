
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
    "p8": ("نامحدود چهارکاربره - یک‌ماهه", 350000),
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



        
def show_topup_options(chat_id):
    keyboard = {
        "inline_keyboard": [
            [{"text": "۵۰ هزار تومان", "callback_data": "topup_50000"}],
            [{"text": "۱۰۰ هزار تومان", "callback_data": "topup_100000"}],
            [{"text": "۱۵۰ هزار تومان", "callback_data": "topup_150000"}],
            [{"text": "۲۰۰ هزار تومان", "callback_data": "topup_200000"}],
            [{"text": "۲۵۰ هزار تومان", "callback_data": "topup_250000"}],
            [{"text": "۳۰۰ هزار تومان", "callback_data": "topup_300000"}],
            [{"text": "۳۵۰ هزار تومان", "callback_data": "topup_350000"}]
        ]
    }

    send_message(
        chat_id,
        "💰 مبلغ شارژ کیف پول را انتخاب کن:",
        keyboard
    )


    


def create_topup(chat_id, user_id, amount):
    fee = amount * 2 // 100
    total = amount + fee

    cursor = db.execute(
        "INSERT INTO topups "
        "(user_id, amount, fee, total, status) "
        "VALUES (?, ?, ?, ?, ?)",
        (user_id, amount, fee, total, "در انتظار رسید")
    )

    topup_id = cursor.lastrowid
    db.commit()

    send_message(
        chat_id,
        "💳 اطلاعات پرداخت کارت‌به‌کارت\n\n"
        "نام صاحب کارت: محمد طاها حسین پور\n"
        "شماره کارت:\n"
        "6037991768691648\n\n"
        f"مبلغ شارژ: {amount:,} تومان\n"
        f"کارمزد ۳٪: {fee:,} تومان\n"
        f"مبلغ قابل پرداخت: {total:,} تومان\n\n"
        "پس از پرداخت، عکس رسید را همین‌جا ارسال کن.\n"
        f"شماره درخواست: {topup_id}"
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
        show_topup_options(chat_id)

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


def handle_photo(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]

    photos = message.get("photo", [])

    if not photos:
        return

    file_id = photos[-1]["file_id"]

    cursor = db.execute(
        "SELECT id, amount, fee, total FROM topups "
        "WHERE user_id = ? AND status = ? "
        "ORDER BY id DESC LIMIT 1",
        (user_id, "در انتظار رسید")
    )

    topup = cursor.fetchone()

    if not topup:
        send_message(
            chat_id,
            "❌ ابتدا از بخش شارژ کیف پول، مبلغ را انتخاب کن."
        )
        return

    topup_id, amount, fee, total = topup

    db.execute(
        "UPDATE topups SET receipt_id = ?, status = ? WHERE id = ?",
        (file_id, "در انتظار بررسی", topup_id)
    )
    db.commit()

    keyboard = {
        "inline_keyboard": [
            [
                {
                    "text": "✅ تأیید پرداخت",
                    "callback_data": f"approve_topup_{topup_id}"
                },
                {
                    "text": "❌ رد پرداخت",
                    "callback_data": f"reject_topup_{topup_id}"
                }
            ]
        ]
    }

    api("sendPhoto", {
        "chat_id": ADMIN_ID,
        "photo": file_id,
        "caption": (
            f"رسید شارژ شماره {topup_id}\n"
            f"شناسه کاربر: {user_id}\n"
            f"مبلغ شارژ: {amount:,} تومان\n"
            f"کارمزد: {fee:,} تومان\n"
            f"مبلغ پرداختی: {total:,} تومان"
        ),
        "reply_markup": keyboard
    })

    send_message(
        chat_id,
        "✅ رسیدت برای مدیر ارسال شد.\n"
        "بعد از بررسی، نتیجه به تو اطلاع داده می‌شود."
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

    elif data.startswith("topup_"):
        amount = int(data.replace("topup_", "", 1))
        if amount in (100000, 200000, 300000):
            create_topup(chat_id, user_id, amount)

    elif data.startswith("approve_topup_") or data.startswith("reject_topup_"):
        if user_id != ADMIN_ID:
            send_message(user_id, "⛔ اجازه انجام این کار را نداری.")
            return

        approve = data.startswith("approve_topup_")
        topup_id = int(data.split("_")[-1])

        cursor = db.execute(
            "SELECT user_id, amount, status FROM topups WHERE id = ?",
            (topup_id,)
        )
        topup = cursor.fetchone()

        if not topup or topup[2] != "در انتظار بررسی":
            send_message(user_id, "این درخواست قبلاً بررسی شده یا وجود ندارد.")
            return

        customer_id, amount, status = topup

        if approve:
            db.execute(
                "UPDATE topups SET status = ? WHERE id = ?",
                ("تأیید شده", topup_id)
            )
            db.execute(
                "UPDATE users SET balance = balance + ? WHERE user_id = ?",
                (amount, customer_id)
            )
            db.commit()
            send_message(customer_id, f"✅ مبلغ {amount:,} تومان به کیف پولت اضافه شد.")
            send_message(user_id, "✅ پرداخت تأیید شد.")
        else:
            db.execute(
                "UPDATE topups SET status = ? WHERE id = ?",
                ("رد شده", topup_id)
            )
            db.commit()
            send_message(customer_id, "❌ رسید پرداخت تأیید نشد.")
            send_message(user_id, "درخواست رد شد.")

        api("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": message["message_id"],
            "reply_markup": {"inline_keyboard": []}
        })
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


run_bot()
