# app/main.py
import asyncio
import json
import time
from fastapi import FastAPI, HTTPException
from celery.result import AsyncResult
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from app.tasks import process
from app.worker import celery_app

import logging
from .utils.setlogger import setup_logger
logger = setup_logger(f"{__name__}", level=logging.INFO)



# 요청 모델 정의
class EmailRequest(BaseModel):
    email_address: str

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


# @app.post("/send-email/")
# async def trigger_email(email_address: str):
#     result = process.delay(email_address)  # .delay() offloads the task to Celery
#     return {
#         "message": f"Email to {email_address} has been queued.",
#         "task_id": result.id,
#         "status": "queued"
#         }


@app.post("/send-email/")
async def trigger_email(request: EmailRequest):
    result = process.delay(request.email_address)
    return {
        "message": f"Email to {request.email_address} has been queued.",
        "task_id": result.id,
        "status": "queued"
    }

# SSE 스트리밍을 위한 엔드포인트
@app.get("/stream/{task_id}")
async def stream_task_progress(task_id: str):
    """
    SSE 스트리밍으로 태스크 진행상태 실시간 전송
    """
    async def event_generator():
        result: AsyncResult = celery_app.AsyncResult(task_id)
        
        # 초기 상태 전송
        yield f"data: {json.dumps({'task_id': task_id, 'status': result.state, 'progress': 0})}\n\n"
        
        # 상태 추적
        last_state = result.state
        max_retries = 60  # 최대 5분 대기 (5초 * 60)
        retry_count = 0
        
        while not result.ready() and retry_count < max_retries:
            # 상태 변경 감지
            if result.state != last_state:
                last_state = result.state
                progress = calculate_progress(result.state)
                
                yield f"data: {json.dumps({'task_id': task_id, 'status': result.state, 'progress': progress})}\n\n"
            
            # 결과가 준비되었는지 확인
            if result.ready():
                break
                
            # 5초 대기
            await asyncio.sleep(5)
            retry_count += 1
        
        # 최종 결과 전송
        if result.ready():
            if result.successful():
                final_result = result.get()
                yield f"data: {json.dumps({'task_id': task_id, 'status': 'SUCCESS', 'progress': 100, 'result': final_result})}\n\n"
            else:
                yield f"data: {json.dumps({'task_id': task_id, 'status': 'FAILURE', 'progress': 100, 'error': str(result.result)})}\n\n"
        else:
            yield f"data: {json.dumps({'task_id': task_id, 'status': 'TIMEOUT', 'progress': 0, 'error': 'Task processing timeout'})}\n\n"
        
        # 스트림 종료
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )

def calculate_progress(state: str) -> int:
    """
    상태에 따른 진행률 계산
    """
    progress_map = {
        'PENDING': 0,
        'STARTED': 25,
        'RETRY': 50,
        'PROGRESS': 75,  # 사용자 정의 진행 상태
        'SUCCESS': 100,
        'FAILURE': 100
    }
    return progress_map.get(state, 0)

# 진행률 업데이트이 가능한 태스크 예제
# @app.post("/send-email-with-progress/")
# async def trigger_email_with_progress(email_address: str):
#     """
#     진행률 업데이트가 가능한 이메일 전송 태스크
#     """
#     result = process.apply_async(args=[email_address], kwargs={'with_progress': True})
#     return {
#         "message": f"Email to {email_address} has been queued with progress tracking.",
#         "task_id": result.id,
#         "status": "queued",
#         "stream_url": f"/stream/{result.id}"
#     }

@app.post("/send-email-with-progress/")
async def trigger_email_with_progress(request: EmailRequest):
    """
    진행률 업데이트가 가능한 이메일 전송 태스크
    """
    result = process.apply_async(args=[request.email_address], kwargs={'with_progress': True})
    return {
        "message": f"Email to {request.email_address} has been queued with progress tracking.",
        "task_id": result.id,
        "status": "queued",
        "stream_url": f"/stream/{result.id}"
    }