import time

def send_email(email_address:str):
    print(f"Sending email to {email_address}")
    # Simulate email delay
    time.sleep(5)
    return f"Email sent to {email_address}"
