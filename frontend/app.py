import streamlit as st
import requests
import sseclient
import time

FASTAPI_URL = "http://localhost:8000"  # FastAPI 서버 주소 (Docker 환경에 맞게 변경)

st.set_page_config(page_title="Email Sender", page_icon="📧", layout="centered")

st.title("📧 Email Sender (Celery + FastAPI + Redis + Streamlit)")
st.write("이메일 전송 작업을 비동기로 실행하고, SSE를 통해 실시간 상태를 수신합니다.")

email = st.text_input("받는 이메일 주소를 입력하세요:")
send_btn = st.button("Send Email")

# 상태 영역
status_placeholder = st.empty()

if send_btn and email:
    # 1️⃣ 작업 요청
    try:
        with st.spinner("작업 요청 중..."):
            resp = requests.post(f"{FASTAPI_URL}/send-email", json={"email_address": email})
            resp.raise_for_status()
            task_info = resp.json()
            task_id = task_info["task_id"]
            st.success(f"작업이 큐에 등록되었습니다. (task_id: {task_id})")
    except Exception as e:
        st.error(f"요청 실패: {e}")
        st.stop()

    # 2️⃣ SSE 구독
    st.write("📡 실시간 결과 수신 중...")
    progress_bar = st.progress(0)
    status_text = st.empty()

    try:
        stream_url = f"{FASTAPI_URL}/stream-results/{task_id}"
        messages = sseclient.SSEClient(stream_url)

        start_time = time.time()
        for i, event in enumerate(messages):
            if event.event == "ping":
                # 주기적 ping
                status_text.info("⏳ 작업 대기 중...")
                progress_bar.progress(min(i * 10 % 100, 99))
            elif event.event == "task_result":
                status_text.success(f"✅ 완료: {event.data}")
                progress_bar.progress(100)
                break
            elif event.event == "task_error":
                status_text.error(f"❌ 에러: {event.data}")
                progress_bar.progress(100)
                break
    except Exception as e:
        status_text.error(f"SSE 연결 실패: {e}")
    finally:
        elapsed = round(time.time() - start_time, 2)
        st.info(f"스트림 종료 (소요시간: {elapsed}초)")

