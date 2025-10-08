from datetime import datetime
import os
import pickle
import logging


def dump_failed_payloads(failed_payload: any):
    """Dumps failed payloads into directory failed_payloads/"""

    os.makedirs(os.path.dirname("failed_payloads/"), exist_ok=True)
    if failed_payload and len(failed_payload) > 0:
        filename = f"data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        with open(f"failed_payloads/{filename}", "wb") as f:
            pickle.dump(failed_payload, f)

def double_log(logger: logging.Logger, msg: str):
    print(msg)
    logger.info(msg)
