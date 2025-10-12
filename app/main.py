# app/main.py
from fastapi import FastAPI, HTTPException
from celery.result import AsyncResult
from app.tasks import process
from app.worker import celery_app

import logging
from .utils.setlogger import setup_logger
logger = setup_logger(f"{__name__}", level=logging.INFO)


app = FastAPI()


@app.get("/status/{task_id}")
async def get_task_status(task_id: str):
    result: AsyncResult = celery_app.AsyncResult(task_id)
    if result.state == "FAILURE":
        raise HTTPException(status_code=500, detail=str(result.result))
    return {
        "task_id": task_id,
        "status": result.state,
        "result": result.get() if result.ready() else None
    }


@app.post("/send-email/")
async def trigger_email(email_address: str):
    result = process.delay(email_address)  # .delay() offloads the task to Celery
    return {
        "message": f"Email to {email_address} has been queued.",
        "task_id": result.id,
        "status": "queued"
        }
		