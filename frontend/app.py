import streamlit as st
import requests
import time
import json

# FastAPI 서버 주소
API_BASE = "http://localhost:8008"   # 필요 시 변경


st.set_page_config(page_title="Task Polling Demo", layout="centered")

if "task_ids" not in st.session_state: st.session_state.task_ids = []
if "pending_results" not in st.session_state: st.session_state.pending_results = []
if "success_results" not in st.session_state: st.session_state.success_results = []


st.title("Task Polling Demo")
st.markdown("---")


if st.button("Task ID 초기화"):
    st.session_state.task_ids = []
    st.session_state.pending_results = []
    st.session_state.success_results = []

# ----------------------------
# 1) Email 입력 및 작업 트리거
# ----------------------------
email = st.text_input("이메일 입력", placeholder="example@test.com")

if st.button("Task Queue"):
    if not email:
        st.warning("이메일을 입력하세요.")
        st.stop()

    # FastAPI POST 호출
    try:
        response = requests.post(
            f"{API_BASE}/test_for_five_seconds/",
            json={"email_address": email}
        )
        data = response.json()
        data
        task_id = data.get("task_id")
        if task_id not in st.session_state.task_ids:
            st.session_state.task_ids.append(task_id)

        st.success(f"작업이 큐에 등록되었습니다! task_id: {task_id}")

    except Exception as e:
        st.error(f"API 요청 실패: {e}")

# -----------------------------
# 2) 폴링 
# -----------------------------
if st.button("Polling"):
    st.session_state.pending_results = []
    st.session_state.success_results = []
    for id in st.session_state.task_ids:
        status_response = requests.get(f"{API_BASE}/task_status/{id}")
        status_data = json.loads(status_response.text)
        if status_data not in st.session_state.pending_results and status_data["status"]!="SUCCESS" :
            st.session_state.pending_results.append(status_data)
        if status_data not in st.session_state.success_results and status_data["status"]=="SUCCESS" :
            st.session_state.success_results.append(status_data)

col1, col2 = st.columns(2)
with col1:
    st.info(f"대기중인 작업: {len(st.session_state.pending_results)}")
    with st.container(border=True, height=500):
        for p in st.session_state.pending_results:
            st.warning(p)
with col2:
    st.info(f"성공한 작업: {len(st.session_state.success_results)}")
    with st.container(border=True, height=500):
        for s in st.session_state.success_results:
            st.success(s)

