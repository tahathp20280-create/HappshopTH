import os
import time
import sqlite3
import requests

# -----------------------------
# تنظیمات اصلی ربات
# -----------------------------

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

CARD_NUMBER = os.getenv("CARD_NUMBER", "")
CARD_NAME = os.getenv("CARD_NAME", "")

SUPPORT_USERNAME = "@TAHA_THP"

if not TOKEN:
    raise ValueError("BOT_TOKEN تنظیم نشده است!")

if ADMIN_ID == 0:
    raise ValueError("ADMIN_ID تنظیم نشده است!")

URL = f"https://api.telegram.org/bot{TOKEN}/"

# -----------------------------
# محصولات فروشگاه
# -----------------------------

PRODUCTS = [
    ("۵ گیگابایت - یک ماهه", 30000),
    ("۱۰ گیگابایت - یک ماهه", 70000),
    ("۲۰ گیگابایت - یک ماهه", 140000),
    ("۳۰ گیگابایت - یک ماهه", 180000),
    ("نامحدود تک کاربره - یک ماهه", 200000),
    ("نامحدود دو کاربره - یک ماهه", 250000),
    ("نامحدود سه کاربره - یک ماهه", 300000),
]

TOPUP_AMOUNTS = [100000, 200000, 300000]

# -----------------------------
# اتصال به دیتابیس
# -----------------------------

DB = sqlite3.connect("happshop.db")
DB.row_factory = sqlite3.Row

DB.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    balance INTEGER DEFAULT 0,
    purchases INTEGER DEFAULT 0,
    paid_invoices INTEGER DEFAULT 0,
    referrals INTEGER DEFAULT 0,
    blocked INTEGER DEFAULT 0
)
""")

DB.execute("""
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    product TEXT,
    price INTEGER,
    status TEXT,
    receipt_id TEXT,
    config TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

DB.execute("""
CREATE TABLE IF NOT EXISTS topups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    fee INTEGER,
    total INTEGER,
    receipt_id TEXT,
    status TEXT DEFAULT 'waiting',
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

DB.execute("""
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    amount INTEGER,
    description TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

DB.commit()

print("Database is ready!")# -----------------------------
# ارسال پیام
# -----------------------------

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
    return response.json()


# -----------------------------
# ثبت کاربر
# -----------------------------

def register_user(user_id):
    DB.execute(
        "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
        (user_id,)
    )
    DB.commit()


# -----------------------------
# منوی اصلی
# -----------------------------

def main_keyboard(is_admin=False):
    buttons = [
        ["🛍️ خرید اشتراک"],
        ["💰 کیف پول و حساب کاربری"],
        ["📦 سفارش‌های من"],
        ["📞 پشتیبانی", "ℹ️ درباره فروشگاه"]
    ]

    if is_admin:
        buttons.append(["👑 پنل مدیریت"])

    return {
        "keyboard": buttons,
        "resize_keyboard": True
    }


# -----------------------------
# منوی محصولات
# -----------------------------

def products_keyboard():
    buttons = []

    for i, (name, price) in enumerate(PRODUCTS):
        buttons.append([{
            "text": f"{name} | {price:,} تومان",
            "callback_data": f"buy:{i}"
        }])

    return {
        "inline_keyboard": buttons
    }


# -----------------------------
# منوی افزایش موجودی
# -----------------------------

def topup_keyboard():
    buttons = []

    for amount in TOPUP_AMOUNTS:
        buttons.append([{
            "text": f"{amount:,} تومان",
            "callback_data": f"topup:{amount}"
        }])

    return {
        "inline_keyboard": buttons
    }


# -----------------------------
# منوی مدیریت سفارش
# -----------------------------

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


# -----------------------------
# منوی مدیریت افزایش موجودی
# -----------------------------

def topup_admin_keyboard(topup_id):
    return {
        "inline_keyboard": [[
            {
                "text": "✅ تأیید شارژ",
                "callback_data": f"topup_approve:{topup_id}"
            },
            {
                "text": "❌ رد شارژ",
                "callback_data": f"topup_reject:{topup_id}"
            }
        ]]
}# -----------------------------
# نمایش اطلاعات کیف پول
# -----------------------------

def show_wallet(chat_id, user_id):
    user = DB.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    send(
        chat_id,
        "🤖 اطلاعات حساب کاربری شما:\n\n"
        f"💰 موجودی: {user['balance']:,} تومان\n"
        f"🛒 تعداد سرویس‌های خریداری‌شده: {user['purchases']}\n"
        f"📑 تعداد فاکتورهای پرداخت‌شده: {user['paid_invoices']}\n"
        f"🤝 تعداد زیرمجموعه‌ها: {user['referrals']}\n"
        "🔖 گروه کاربری: نماینده\n\n"
        "برای افزایش موجودی، مبلغ موردنظر را انتخاب کنید:",
        topup_keyboard()
    )


# -----------------------------
# ثبت سفارش اشتراک
# -----------------------------

def create_order(user_id, product_index):
    if product_index < 0 or product_index >= len(PRODUCTS):
        return None

    product, price = PRODUCTS[product_index]

    DB.execute(
        """
        INSERT INTO orders
        (user_id, product, price, status)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, product, price, "waiting_receipt")
    )

    DB.commit()

    return DB.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]


# -----------------------------
# ثبت درخواست افزایش موجودی
# -----------------------------

def create_topup(user_id, amount):
    if amount not in TOPUP_AMOUNTS:
        return None

    fee = int(amount * 0.03)
    total = amount + fee

    DB.execute(
        """
        INSERT INTO topups
        (user_id, amount, fee, total)
        VALUES (?, ?, ?, ?)
        """,
        (user_id, amount, fee, total)
    )

    DB.commit()

    topup_id = DB.execute(
        "SELECT last_insert_rowid()"
    ).fetchone()[0]

    return topup_id, fee, total


# -----------------------------
# دریافت رسید پرداخت
# -----------------------------

def handle_receipt(message):
    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")

    if not user_id or not chat_id:
        return

    photos = message.get("photo", [])

    if not photos:
        send(chat_id, "لطفاً تصویر رسید را ارسال کنید.")
        return

    receipt_id = photos[-1]["file_id"]

    # ابتدا بررسی درخواست شارژ کیف پول
    topup = DB.execute(
        """
        SELECT * FROM topups
        WHERE user_id=? AND status='waiting_receipt'
        ORDER BY id DESC LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    if topup:
        DB.execute(
            """
            UPDATE topups
            SET receipt_id=?, status='reviewing'
            WHERE id=? AND status='waiting_receipt'
            """,
            (receipt_id, topup["id"])
        )
        DB.commit()

        requests.post(
            URL + "sendPhoto",
            json={
                "chat_id": ADMIN_ID,
                "photo": receipt_id,
                "caption": (
                    "🧾 رسید شارژ کیف پول\n\n"
                    f"شماره درخواست: {topup['id']}\n"
                    f"شناسه مشتری: {user_id}\n"
                    f"مبلغ شارژ: {topup['amount']:,} تومان\n"
                    f"کارمزد: {topup['fee']:,} تومان\n"
                    f"مبلغ نهایی: {topup['total']:,} تومان"
                ),
                "reply_markup": topup_admin_keyboard(topup["id"])
            },
            timeout=20
        ).raise_for_status()

        send(chat_id, "✅ رسید شارژ برای مدیر ارسال شد.")
        return

    # بررسی سفارش اشتراک
    order = DB.execute(
        """
        SELECT * FROM orders
        WHERE user_id=? AND status='waiting_receipt'
        ORDER BY id DESC LIMIT 1
        """,
        (user_id,)
    ).fetchone()

    if not order:
        send(chat_id, "❌ درخواست پرداخت فعالی پیدا نشد.")
        return

    DB.execute(
        """
        UPDATE orders
        SET receipt_id=?, status='reviewing'
        WHERE id=? AND status='waiting_receipt'
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
                "🧾 رسید خرید اشتراک\n\n"
                f"شماره سفارش: {order['id']}\n"
                f"شناسه مشتری: {user_id}\n"
                f"محصول: {order['product']}\n"
                f"مبلغ: {order['price']:,} تومان"
            ),
            "reply_markup": admin_keyboard(order["id"])
        },
        timeout=20
    ).raise_for_status()

    send(
        chat_id,
        "✅ رسید شما برای مدیر ارسال شد.\n"
        "پس از بررسی، نتیجه اعلام می‌شود."
    )# پاسخ به دکمه‌های تلگرام
def answer_callback(callback, text=""):
    requests.post(
        URL + "answerCallbackQuery",
        json={
            "callback_query_id": callback["id"],
            "text": text
        },
        timeout=15
    )


# نمایش اطلاعات پرداخت
def payment_info(chat_id, amount, title):
    card = CARD_NUMBER or "شماره کارت تنظیم نشده"
    name = CARD_NAME or "نام صاحب کارت تنظیم نشده"

    send(
        chat_id,
        f"💳 پرداخت {title}\n\n"
        f"مبلغ: {amount:,} تومان\n"
        f"شماره کارت:\n{card}\n\n"
        f"به نام: {name}\n\n"
        "پس از پرداخت، تصویر رسید را ارسال کنید."
    )


# تأیید یا رد سفارش و شارژ توسط مدیر
def handle_admin_callback(callback):
    user_id = callback.get("from", {}).get("id")
    data = callback.get("data", "")
    chat_id = callback["message"]["chat"]["id"]

    if user_id != ADMIN_ID:
        answer_callback(callback, "دسترسی غیرمجاز")
        return

    try:
        action, item_id = data.split(":")
        item_id = int(item_id)
    except (ValueError, TypeError):
        answer_callback(callback, "درخواست نامعتبر")
        return

    if action in ("approve", "reject"):
        order = DB.execute(
            "SELECT * FROM orders WHERE id=?",
            (item_id,)
        ).fetchone()

        if not order or order["status"] != "reviewing":
            answer_callback(callback, "سفارش قبلاً بررسی شده است.")
            return

        if action == "approve":
            DB.execute(
                "UPDATE orders SET status='approved' "
                "WHERE id=? AND status='reviewing'",
                (item_id,)
            )

            DB.execute(
                """
                UPDATE users
                SET purchases=purchases+1,
                    paid_invoices=paid_invoices+1
                WHERE user_id=?
                """,
                (order["user_id"],)
            )

            DB.commit()

            send(
                order["user_id"],
                "✅ پرداخت شما تأیید شد!\n"
                "اشتراک شما پس از آماده‌سازی ارسال می‌شود."
            )

            send(
                chat_id,
                f"سفارش {item_id} تأیید شد.\n"
                f"برای ارسال کانفیگ بنویس:\n"
                f"/config {item_id}\n"
                "کانفیگ را در خط بعد قرار بده."
            )

        else:
            DB.execute(
                "UPDATE orders SET status='rejected' "
                "WHERE id=? AND status='reviewing'",
                (item_id,)
            )
            DB.commit()

            send(
                order["user_id"],
                "❌ پرداخت شما تأیید نشد.\n"
                "برای پیگیری با پشتیبانی تماس بگیرید."
            )

            send(chat_id, f"سفارش {item_id} رد شد.")

    elif action in ("topup_approve", "topup_reject"):
        topup = DB.execute(
            "SELECT * FROM topups WHERE id=?",
            (item_id,)
        ).fetchone()

        if not topup or topup["status"] != "reviewing":
            answer_callback(callback, "درخواست قبلاً بررسی شده است.")
            return

        if action == "topup_approve":
            DB.execute(
                "UPDATE topups SET status='approved' "
                "WHERE id=? AND status='reviewing'",
                (item_id,)
            )

            DB.execute(
                "UPDATE users SET balance=balance+? WHERE user_id=?",
                (topup["amount"], topup["user_id"])
            )

            DB.execute(
                """
                INSERT INTO transactions
                (user_id, amount, description)
                VALUES (?, ?, ?)
                """,
                (
                    topup["user_id"],
                    topup["amount"],
                    f"شارژ کیف پول شماره {item_id}"
                )
            )

            DB.commit()

            send(
                topup["user_id"],
                "✅ شارژ کیف پول تأیید شد!\n"
                f"مبلغ افزوده‌شده: {topup['amount']:,} تومان"
            )

            send(chat_id, f"شارژ شماره {item_id} تأیید شد.")

        else:
            DB.execute(
                "UPDATE topups SET status='rejected' "
                "WHERE id=? AND status='reviewing'",
                (item_id,)
            )
            DB.commit()

            send(
                topup["user_id"],
                "❌ درخواست شارژ شما رد شد."
            )

            send(chat_id, f"شارژ شماره {item_id} رد شد.")

    answer_callback(callback, "انجام شد")# -----------------------------
# ارسال کانفیگ توسط مدیر
# -----------------------------

def handle_config(message):
    user_id = message.get("from", {}).get("id")
    chat_id = message.get("chat", {}).get("id")
    msg = message.get("text", "")

    if user_id != ADMIN_ID:
        return

    lines = msg.split("\n", 1)
    command = lines[0].split()

    if len(command) != 2:
        send(chat_id, "فرمت صحیح:\n/config 12\nکانفیگ در خط بعد")
        return

    try:
        order_id = int(command[1])
    except ValueError:
        send(chat_id, "شماره سفارش معتبر نیست.")
        return

    if len(lines) < 2 or not lines[1].strip():
        send(chat_id, "کانفیگ را در خط بعد وارد کنید.")
        return

    config = lines[1].strip()

    order = DB.execute(
        "SELECT * FROM orders WHERE id=?",
        (order_id,)
    ).fetchone()

    if not order or order["status"] != "approved":
        send(chat_id, "سفارش پیدا نشد یا هنوز تأیید نشده است.")
        return

    response = requests.post(
        URL + "sendMessage",
        json={
            "chat_id": order["user_id"],
            "text": (
                "🎉 اشتراک شما آماده است!\n\n"
                "اطلاعات سرویس:\n" + config
            ),
            "protect_content": True
        },
        timeout=20
    )

    response.raise_for_status()

    DB.execute(
        "UPDATE orders SET status='delivered', config=? WHERE id=?",
        (config, order_id)
    )
    DB.commit()

    send(chat_id, f"✅ کانفیگ سفارش {order_id} ارسال شد.")


# -----------------------------
# دریافت پیام کاربران
# -----------------------------

def handle_message(message):
    user = message.get("from", {})
    user_id = user.get("id")
    chat_id = message.get("chat", {}).get("id")
    msg = message.get("text", "")

    if not user_id or not chat_id:
        return

    register_user(user_id)

    account = DB.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if account["blocked"]:
        send(chat_id, "⛔ دسترسی شما مسدود شده است.")
        return

    is_admin = user_id == ADMIN_ID

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

    elif msg == "💰 کیف پول و حساب کاربری":
        show_wallet(chat_id, user_id)

    elif msg == "📦 سفارش‌های من":
        orders = DB.execute(
            """
            SELECT * FROM orders
            WHERE user_id=?
            ORDER BY id DESC LIMIT 20
            """,
            (user_id,)
        ).fetchall()

        if not orders:
            send(chat_id, "شما هنوز سفارشی ندارید.")
            return

        text = "📦 سفارش‌های شما:\n\n"

        for order in orders:
            text += (
                f"شماره: {order['id']}\n"
                f"محصول: {order['product']}\n"
                f"مبلغ: {order['price']:,} تومان\n"
                f"وضعیت: {order['status']}\n\n"
            )

        send(chat_id, text)

    elif msg == "📞 پشتیبانی":
        send(chat_id, f"📞 پشتیبانی:\n{SUPPORT_USERNAME}")

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
                "کانفیگ در خط بعد"
            )
        else:
            send(chat_id, "⛔ دسترسی غیرمجاز")

    else:
        send(chat_id, "لطفاً از دکمه‌های منو استفاده کنید.")# -----------------------------
# پردازش دکمه‌های خرید و شارژ
# -----------------------------

def handle_callback(callback):
    user_id = callback.get("from", {}).get("id")
    chat_id = callback["message"]["chat"]["id"]
    data = callback.get("data", "")

    answer_callback(callback)

    if not user_id:
        return

    register_user(user_id)

    account = DB.execute(
        "SELECT * FROM users WHERE user_id=?",
        (user_id,)
    ).fetchone()

    if account["blocked"]:
        send(chat_id, "⛔ دسترسی شما مسدود شده است.")
        return

    if data.startswith("buy:"):
        try:
            index = int(data.split(":")[1])
        except ValueError:
            return

        order_id = create_order(user_id, index)

        if order_id is None:
            send(chat_id, "محصول انتخاب‌شده معتبر نیست.")
            return

        product, price = PRODUCTS[index]

        send(
            chat_id,
            f"🛍️ سفارش ثبت شد!\n"
            f"شماره سفارش: {order_id}\n"
            f"محصول: {product}"
        )

        payment_info(chat_id, price, "خرید اشتراک")

    elif data.startswith("topup:"):
        try:
            amount = int(data.split(":")[1])
        except ValueError:
            return

        result = create_topup(user_id, amount)

        if result is None:
            send(chat_id, "مبلغ انتخابی معتبر نیست.")
            return

        topup_id, fee, total = result

        send(
            chat_id,
            f"🧾 درخواست شارژ شماره {topup_id}\n\n"
            f"مبلغ شارژ: {amount:,} تومان\n"
            f"کارمزد ۳٪: {fee:,} تومان\n"
            f"مبلغ نهایی: {total:,} تومان"
        )

        payment_info(chat_id, total, "افزایش موجودی")


# -----------------------------
# اجرای اصلی ربات
# -----------------------------

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
            time.sleep(3)
            continue

        for update in result["result"]:
            offset = update["update_id"] + 1

            if "callback_query" in update:
                callback = update["callback_query"]
                data = callback.get("data", "")

                if data.startswith((
                    "approve:",
                    "reject:",
                    "topup_approve:",
                    "topup_reject:"
                )):
                    handle_admin_callback(callback)
                else:
                    handle_callback(callback)

            elif "message" in update:
                message = update["message"]
                text_message = message.get("text", "")

                if text_message.startswith("/config"):
                    handle_config(message)

                elif message.get("photo"):
                    handle_receipt(message)

                else:
                    handle_message(message)

    except Exception as error:
        print("Bot error:", error)
        time.sleep(5)
run: python bot.py
