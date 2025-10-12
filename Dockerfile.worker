#path : dockerfile.worker

# 1단계: 빌더 (의존성 설치)
FROM python:3.12-slim as builder

WORKDIR /app

# 시스템 패키지 업데이트 및 빌드에 필요한 도구 설치
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

# 의존성 설치
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt


# 2단계: 최종 이미지 생성
FROM python:3.12-slim

WORKDIR /app

# 빌더에서 설치한 패키지와 소스 코드 복사
COPY . /app

# 복사한 wheel 파일로 의존성 설치
RUN pip install --no-cache -r requirements.txt

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 환경 변수를 통한 유연한 설정
ENV CELERY_WORKER_CONCURRENCY=4
ENV CELERY_WORKER_POOL=prefork
ENV CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
ENV CELERY_WORKER_LOGLEVEL=info


# Celery 워커 실행 (병렬처리 최적화)
CMD ["sh", "-c", "celery -A app.worker.celery_app worker --loglevel=${CELERY_WORKER_LOGLEVEL} --concurrency=${CELERY_WORKER_CONCURRENCY} -P ${CELERY_WORKER_POOL} --max-tasks-per-child=${CELERY_WORKER_MAX_TASKS_PER_CHILD}", "-P", "eventlet"]

# Celery 워커 실행
# CMD ["celery", "-A", "app.worker.celery_app", "worker", "--loglevel=info", "-P", "eventlet"]