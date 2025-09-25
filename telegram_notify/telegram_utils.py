import os
import logging
import threading
import requests

USE_TELEGRAM = os.getenv("USE_TELEGRAM", "false").lower() in ("true", "1", "yes")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
chat_id_strings = os.getenv("CHAT_IDS", "")
CHAT_IDS = [int(x.strip()) for x in chat_id_strings.split(',') if x.strip()]
SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
GET_ME_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"

def send_telegram_msg(message: str):
    global CHAT_IDS, SEND_MESSAGE_URL

    if not USE_TELEGRAM or not TELEGRAM_TOKEN:
        return

    if not CHAT_IDS:
        logging.getLogger("Telegram Utils").warning("No chat IDs configured, skipping the Telegram message.")
        return 

    for CHAT_ID in CHAT_IDS:
        for attempt in range(3):
            try:
                requests.post(url=SEND_MESSAGE_URL, data={"chat_id": CHAT_ID, "text": message}, timeout=5)
                break
            except Exception as e:
                if attempt == 2:
                    logging.getLogger("Telegram Utils").warning("Failed to send Telegram message: %s", e)

def send_telegram_msg_threaded(message: str):
    threading.Thread(target=send_telegram_msg, args=(message,), daemon=True).start()

def test_telegram_token():
    if not USE_TELEGRAM or not TELEGRAM_TOKEN:
        return False
    try:
        response = requests.get(GET_ME_URL, timeout=5)
        json_resp = response.json()
        if json_resp.get("ok"):
            logging.getLogger("Telegram Utils").info("Telegram token successfully verified.")
            return True
    except Exception as e:
        logging.getLogger("Telegram Utils").error(f"Failed to verify Telegram token: {e}")
    return False

if USE_TELEGRAM:
    test_telegram_token()
