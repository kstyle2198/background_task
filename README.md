
# Easy Async Backgroud Task Code Set (Redis, Celery, FastAPI and Docker)

📖 프로젝트 소개

이 프로젝트는 FastAPI를 웹 프레임워크로, Celery를 비동기 태스크 큐로 활용하여 안정적이고 확장 가능한 백엔드 시스템을 구축한 예제입니다. Redis를 메시지 브로커 및 결과 백엔드로 사용하여 서비스 간의 효율적인 통신을 지원합니다.

모든 서비스는 Docker Compose를 통해 컨테이너 환경에서 실행되어, 개발 및 배포 과정을 단순화하고 일관된 환경을 제공합니다.

🚀 시작하기

- git clone [repo url] + .env_example ---> .env.prod
- dev command : docker-compose up -d
- prod command : docker-compose -f docker-compose.prod.yml up --build -d
- All you need to do is just changing "app/utils/bg_process.py" with your own background process"
  (current bg process is a simple mail sending process with intended time sleep)


🏗️ 시스템 아키텍처

본 프로젝트는 Docker Compose를 통해 4개의 주요 서비스 컨테이너를 관리합니다.

📦 서비스 구성

서비스	컨테이너 이름	포트	역할
FastAPI	my_fastapi	8000:8000	웹 API 서버, 비동기 작업을 Celery 워커에게 전달
Celery Worker	my_worker	-	FastAPI로부터 전달받은 작업을 비동기적으로 처리
Redis	my_redis	6379:6379	Celery의 메시지 브로커 및 결과 저장소 역할
Redis Commander	redis_monitor	8081:8081	웹 UI를 통해 Redis 데이터를 시각적으로 모니터링

<br/>

1. fastapi

    설명: Uvicorn을 통해 실행되는 메인 애플리케이션 서버입니다. API 엔드포인트를 제공하며, 시간이 오래 걸리는 작업은 Celery 워커에게 위임합니다.

    Dockerfile: Dockerfile.fastapi

    의존성: redis, worker

2. worker

    설명: Celery 워커 프로세스를 실행합니다. Redis 큐를 주시하고 있다가 새로운 작업이 들어오면 즉시 가져와 비동기적으로 처리합니다.

    Dockerfile: Dockerfile.worker

    의존성: redis

3. redis

    설명: 인-메모리 데이터 저장소로, FastAPI와 Celery 워커 간의 메시지 브로커 역할을 합니다. 또한, Celery 작업의 결과 상태를 저장하는 백엔드로도 사용됩니다.

    Dockerfile: Dockerfile.redis

4. redis-commander

    설명: Redis 데이터를 웹 인터페이스에서 쉽게 조회하고 관리할 수 있도록 도와주는 모니터링 도구입니다. 개발 및 디버깅 시 유용합니다.

🔧 환경 변수

각 서비스의 동작은 docker-compose.yml 파일 내의 environment 섹션에서 설정된 환경 변수를 통해 제어됩니다.

    CELERY_BROKER_URL: Celery가 메시지 큐로 사용할 Redis 주소

    CELERY_RESULT_BACKEND: Celery가 작업 결과를 저장할 Redis 주소

    REDIS_HOSTS: Redis Commander가 연결할 Redis 인스턴스 정보

