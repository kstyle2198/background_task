# app/processes/bg_process.py
import time
import logging
from app.utils.setlogger import setup_logger
logger = setup_logger(f"{__name__}", level=logging.INFO)

import random

def send_email(email_address:str):
    logger.debug(f"Start Sending email to {email_address}")
    # Simulate email delay
    time.sleep(10)
    return f"Email sent to {email_address}"
