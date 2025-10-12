import streamlit as st
import requests
import json
import time
import threading
from datetime import datetime
import queue
import sseclient
from typing import Dict, Any, Optional

# --- 1. 상수 관리 --- (변경 없음)
API_BASE_URL = "http://127.0.0.1:8000"

# --- 2. 관심사 분리: TaskMonitor 클래스 --- (변경 없음)
class TaskMonitor:
    def __init__(self):
        self.task_updates = queue.Queue()

    def start_email_task(self, email_address: str, with_progress: bool = False) -> Optional[Dict[str, Any]]:
        """이메일 작업을 시작하고 작업 정보를 반환합니다."""
        endpoint = "/send-email-with-progress/" if with_progress else "/send-email/"
        payload = {"email_address": email_address}
        try:
            response = requests.post(f"{API_BASE_URL}{endpoint}", json=payload, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API 연결 실패: {e}")
            return None

    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """작업 상태를 조회하여 결과를 반환합니다."""
        try:
            response = requests.get(f"{API_BASE_URL}/status/{task_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"status": "ERROR", "result": f"API 연결 실패: {e}"}

    def monitor_task_sse(self, task_id: str) -> threading.Thread:
        """SSE를 통해 작업을 모니터링하는 스레드를 시작합니다."""
        def _sse_worker():
            try:
                response = requests.get(
                    f"{API_BASE_URL}/stream/{task_id}",
                    stream=True,
                    headers={'Accept': 'text/event-stream'},
                    timeout=30
                )
                response.raise_for_status()
                client = sseclient.SSEClient(response)
                
                for event in client.events():
                    if event.data == '[DONE]':
                        break
                    try:
                        data = json.loads(event.data)
                        self.task_updates.put({'type': 'UPDATE', 'data': data})
                    except json.JSONDecodeError:
                        continue
            except Exception as e:
                self.task_updates.put({'type': 'ERROR', 'error': str(e)})
            finally:
                self.task_updates.put({'type': 'DONE'})

        thread = threading.Thread(target=_sse_worker, daemon=True)
        thread.start()
        return thread

# --- 3. UI 헬퍼 함수 --- (변경 없음)
def get_status_emoji(status: str) -> str:
    """상태에 맞는 이모지를 반환합니다."""
    emoji_map = {
        'PENDING': '⏳', 'STARTED': '🚀', 'PROGRESS': '🔄',
        'SUCCESS': '✅', 'FAILURE': '❌', 'RETRY': '🔄', 'ERROR': '⚠️'
    }
    return emoji_map.get(status, '📄')

def display_task_details(task_data: Dict[str, Any], container):
    """실시간 업데이트 및 히스토리 상세 보기에 사용될 UI 컴포넌트를 렌더링합니다."""
    status = task_data.get('status', 'UNKNOWN')
    result = task_data.get('result')

    with container:
        st.markdown(f"**상태:** {get_status_emoji(status)} {status}")

        if status == 'PROGRESS' and isinstance(result, dict):
            progress = result.get('current', 0)
            total = result.get('total', 100)
            percent_complete = (progress / total * 100) if total > 0 else 0
            
            st.progress(int(percent_complete), text=f"진행률: {progress}/{total}")
            if 'status' in result:
                st.info(f"현재 작업: {result['status']}")
        
        elif status == 'SUCCESS':
            st.success("작업이 성공적으로 완료되었습니다.")
            if result:
                st.json(result)
        elif status in ('FAILURE', 'ERROR'):
            st.error("작업 중 오류가 발생했습니다.")
            if result:
                st.code(str(result))


# --- 4. 메인 애플리케이션 로직 (개선된 버전) ---
def main():
    st.set_page_config(page_title="Celery 작업 모니터링", layout="wide")
    st.title("📧 Celery 백그라운드 작업 모니터링")

    # 세션 상태 초기화
    if 'monitor' not in st.session_state:
        st.session_state.monitor = TaskMonitor()
    if 'task_history' not in st.session_state:
        st.session_state.task_history = {}
    if 'monitoring_task_id' not in st.session_state:
        st.session_state.monitoring_task_id = None

    monitor = st.session_state.monitor

    # --- 사이드바 ---
    with st.sidebar:
        st.title("설정 및 관리")
        if st.button("히스토리 초기화"):
            st.session_state.task_history = {}
            st.session_state.monitoring_task_id = None
            st.success("히스토리가 초기화되었습니다!")
            st.rerun()

        st.markdown("---")
        st.subheader("히스토리 요약")
        if st.session_state.task_history:
            status_counts = {}
            for task in st.session_state.task_history.values():
                status = task.get('status', 'UNKNOWN')
                status_counts[status] = status_counts.get(status, 0) + 1
            
            st.write(f"총 작업 수: {len(st.session_state.task_history)}")
            for status, count in status_counts.items():
                st.write(f"- {get_status_emoji(status)} {status}: {count}개")
        else:
            st.write("작업 기록이 없습니다.")

    # --- 메인 레이아웃 ---
    col1, col2 = st.columns(2)

    # --- 새 작업 생성 ---
    with col1:
        st.header("🚀 새 작업 생성")
        with st.form("email_task_form"):
            email = st.text_input("이메일 주소", value="test@example.com")
            with_progress = st.checkbox("진행률 추적 활성화 (SSE)", value=True)
            submitted = st.form_submit_button("이메일 전송 시작")

            if submitted and email:
                with st.spinner("작업을 생성하는 중..."):
                    task_info = monitor.start_email_task(email, with_progress)
                
                if task_info and "task_id" in task_info:
                    task_id = task_info["task_id"]
                    st.success(f"작업이 시작되었습니다! (ID: {task_id})")
                    
                    new_task = {
                        'task_id': task_id, 'email': email,
                        'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'status': 'PENDING', 'with_progress': with_progress, 'result': None
                    }
                    st.session_state.task_history[task_id] = new_task
                    
                    if with_progress:
                        st.session_state.monitoring_task_id = task_id
                        monitor.monitor_task_sse(task_id)

                    st.rerun() # 폼 제출 후 모니터링 UI를 활성화하기 위해 한 번만 실행
                else:
                    st.error("작업 생성에 실패했습니다.")

    # --- 현재 작업 모니터링 ---
    with col2:
        st.header("🔍 현재 작업 모니터링")
        task_id = st.session_state.monitoring_task_id
        
        if task_id and task_id in st.session_state.task_history:
            st.markdown(f"**모니터링 중인 작업:** `{task_id}`")
            
            # ✨ 개선점 1: UI를 업데이트할 빈 공간(placeholder) 생성
            details_placeholder = st.empty()

            # ✨ 개선점 2: st.rerun() 루프 대신, 큐에 이벤트가 들어올 때까지 대기
            while st.session_state.monitoring_task_id == task_id:
                # 현재 상태를 먼저 표시
                current_task_data = st.session_state.task_history[task_id]
                display_task_details(current_task_data, details_placeholder)
                
                try:
                    # 큐에서 업데이트를 기다림 (blocking)
                    update = monitor.task_updates.get(timeout=1) # 1초 타임아웃
                    
                    if update['type'] == 'UPDATE':
                        st.session_state.task_history[task_id].update(update['data'])
                    elif update['type'] == 'DONE':
                        st.info("실시간 스트리밍이 종료되었습니다.")
                        st.session_state.monitoring_task_id = None
                        break # 루프 종료
                    elif update['type'] == 'ERROR':
                        st.error(f"모니터링 오류: {update['error']}")
                        st.session_state.task_history[task_id]['status'] = 'ERROR'
                        st.session_state.monitoring_task_id = None
                        break # 루프 종료
                except queue.Empty:
                    # 타임아웃 발생 시 루프 계속 진행 (세션 상태 변경 감지)
                    continue

            # 루프가 끝나면 마지막 상태를 한 번 더 렌더링
            final_task_data = st.session_state.task_history[task_id]
            display_task_details(final_task_data, details_placeholder)
            st.info("모니터링이 완료되었습니다. 페이지를 새로고침하거나 다른 작업을 시작하세요.")

        else:
            st.info("현재 실시간으로 모니터링 중인 작업이 없습니다.")

    st.markdown("---")

    # --- 작업 히스토리 --- (변경 없음)
    st.header("📋 작업 히스토리")
    if not st.session_state.task_history:
        st.info("아직 생성된 작업이 없습니다.")
    else:
        sorted_tasks = sorted(st.session_state.task_history.values(), key=lambda x: x['start_time'], reverse=True)
        
        for task in sorted_tasks:
            task_id = task['task_id']
            expander_title = (
                f"{get_status_emoji(task['status'])} {task['email']} "
                f"(`{task_id[:8]}...`) - {task['start_time']}"
            )
            with st.expander(expander_title):
                st.markdown(f"**전체 작업 ID:** `{task_id}`")
                details_container = st.container()
                display_task_details(task, details_container)
                
                btn_cols = st.columns(2)
                with btn_cols[0]:
                    if st.button("상태 다시 조회", key=f"recheck_{task_id}"):
                        with st.spinner("상태를 조회하는 중..."):
                            status_data = monitor.get_task_status(task_id)
                            st.session_state.task_history[task_id].update(status_data)
                        st.rerun()
                
                with btn_cols[1]:
                    if task['with_progress']:
                        if st.button("실시간 모니터링 시작", key=f"monitor_{task_id}"):
                            st.session_state.monitoring_task_id = task_id
                            monitor.monitor_task_sse(task_id)
                            st.rerun()

if __name__ == "__main__":
    main()