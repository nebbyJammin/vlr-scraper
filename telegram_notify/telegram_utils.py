import os
import logging
import threading
import requests
from logging_config import VLR_LOGGER, PG_LOGGER, MAIN_LOGGER, UTIL_LOGGER, PRIVATE_API_LOGGER

USE_TELEGRAM = os.getenv("USE_TELEGRAM", "false").lower() in ("true", "1", "yes")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
chat_id_strings = os.getenv("CHAT_IDS", "")
CHAT_IDS = [int(x.strip()) for x in chat_id_strings.split(',') if x.strip()]
SEND_MESSAGE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
GET_ME_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"

def send_telegram_msg(message: str):
    global CHAT_IDS, SEND_MESSAGE_URL, USE_TELEGRAM, TELEGRAM_TOKEN

    if not USE_TELEGRAM or not TELEGRAM_TOKEN:
        return

    if not CHAT_IDS:
        UTIL_LOGGER.warning("No chat IDs configured, skipping the Telegram message.")
        return 

    for CHAT_ID in CHAT_IDS:
        for attempt in range(3):
            try:
                requests.post(url=SEND_MESSAGE_URL, data={"chat_id": CHAT_ID, "text": message}, timeout=5)
                break
            except Exception as e:
                if attempt == 2:
                    UTIL_LOGGER.warning("Failed to send Telegram message: %s", e)

def send_telegram_msg_threaded(message: str):
    threading.Thread(target=send_telegram_msg, args=(message,), daemon=True).start()

class TelegramHandler(logging.Handler):
    def emit(self, record: logging.LogRecord):
        try:
            if record.levelno >= logging.ERROR:
                msg = self.format(record)
                send_telegram_msg_threaded(msg)
        except Exception:
            pass

def test_telegram_token():
    if not USE_TELEGRAM or not TELEGRAM_TOKEN:
        return False
    try:
        response = requests.get(GET_ME_URL, timeout=5)
        json_resp = response.json()
        if json_resp.get("ok"):
            UTIL_LOGGER.info("Telegram token successfully verified.")
            return True
    except Exception as e:
        UTIL_LOGGER.error(f"Failed to verify Telegram token: {e}")
    return False

if USE_TELEGRAM:
    test_telegram_token()
    telegram_handler = TelegramHandler()
    telegram_handler.setFormatter(logging.Formatter("Error received from Scraper: %(message)s"))
    for logger in (VLR_LOGGER, PG_LOGGER, MAIN_LOGGER, UTIL_LOGGER, PRIVATE_API_LOGGER):
        logger.addHandler(telegram_handler)
