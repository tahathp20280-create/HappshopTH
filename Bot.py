import os

TOKEN = os.getenv("BOT_TOKEN")
URL = f"https://api.telegram.org/bot{TOKEN}/"

offset = 0

print("HappshopTH is running!")

while True:
    try:
        response = requests.get(
            URL + "getUpdates",
            params={"offset": offset, "timeout": 30}
        )
        updates = response.json()["result"]

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            text = message.get("text", "")

            if chat_id and text == "/start":
                requests.post(URL + "sendMessage", data={
                    "chat_id": chat_id,
                    "text": "سلام! 🌸 به فروشگاه HappshopTH خوش آمدید."
                })

    except Exception as e:
        print(e)
        time.sleep(3)
