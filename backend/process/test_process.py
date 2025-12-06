# backend/processes/test_process.py
import time
import random
from backend.utils.config import get_config
from backend.utils.setlogger import setup_logger
config = get_config()
logger = setup_logger(f"{__name__}", level=config.LOG_LEVEL)


def test_process_for_five_seconds(email_address:str):
    logger.debug(f"Start Sending email to {email_address}")
    # Simulate email delay
    time.sleep(5)
    return f"Email sent to {email_address}-{random.randint(1,100)}"
