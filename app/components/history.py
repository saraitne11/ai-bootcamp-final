from dotenv import load_dotenv
import os
import streamlit as st
import requests
import json
from utils.state_manager import reset_chat_session, load_chat_session

# API 엔드포인트 기본 URL
load_dotenv()
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000")


def fetch_chat_sessions():
    """API를 통해 모든 채팅 세션 목록을 가져옵니다."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/chats/")
        if response.status_code == 200:
            sessions = response.json()
            # (id, topic, created_at) 튜플 리스트로 반환
            return [
                (s["id"], s["topic"], s["created_at"])
                for s in sessions
            ]
        else:
            st.error(f"채팅 이력 조회 실패: {response.status_code}")
            return []
    except requests.RequestException as e:
        st.error(f"API 호출 오류: {str(e)}")
        return []


def fetch_chat_session(session_id: int):
    """API를 통해 특정 채팅 세션의 모든 메시지를 가져옵니다."""
    try:
        response = requests.get(f"{API_BASE_URL}/api/v1/chats/{session_id}")
        if response.status_code == 200:
            session_data = response.json()
            topic = session_data["topic"]
            # 메시지 포맷 변환 (role, content만 추출)
            messages = [
                {"role": msg["role"], "content": msg["content"]}
                for msg in session_data.get("messages", [])
            ]
            return topic, messages
        else:
            st.error(f"채팅 데이터 조회 실패: {response.status_code}")
            return None, None
    except requests.RequestException as e:
        st.error(f"API 호출 오류: {str(e)}")
        return None, None


def delete_chat_session(session_id: int):
    """API를 통해 특정 채팅 세션을 삭제합니다."""
    try:
        response = requests.delete(f"{API_BASE_URL}/api/v1/chats/{session_id}")
        if response.status_code == 200:
            st.success("채팅 이력이 삭제되었습니다.")
            return True
        else:
            st.error(f"채팅 삭제 실패: {response.status_code}")
            return False
    except requests.RequestException as e:
        st.error(f"API 호출 오류: {str(e)}")
        return False


def delete_all_chat_sessions():
    """API를 통해 모든 채팅 세션을 삭제합니다."""
    try:
        sessions = fetch_chat_sessions()
        if not sessions:
            st.info("삭제할 채팅 이력이 없습니다.")
            return True

        success = True
        for session_id, _, _ in sessions:
            response = requests.delete(f"{API_BASE_URL}/api/v1/chats/{session_id}")
            if response.status_code != 200:
                success = False

        if success:
            st.success("모든 채팅 이력이 삭제되었습니다.")
        return success
    except requests.RequestException as e:
        st.error(f"API 호출 오류: {str(e)}")
        return False


def render_history_ui():
    """채팅 이력 탭의 UI를 렌더링합니다."""

    col1, col2 = st.columns(2)
    with col1:
        if st.button("새로고침", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("전체 삭제", type="primary", use_container_width=True):
            if delete_all_chat_sessions():
                reset_chat_session()  # 세션 상태도 초기화
                st.rerun()

    st.markdown("---")

    # 채팅 이력 로드
    chat_history = fetch_chat_sessions()

    if not chat_history:
        st.info("저장된 채팅 이력이 없습니다.")
    else:
        # 스크롤 가능한 컨테이너에 이력 표시
        container = st.container(height=400, border=False)
        render_history_list(container, chat_history)


def render_history_list(container, chat_history):
    """채팅 이력 목록을 렌더링합니다."""
    for session_id, topic, date in chat_history:
        with container.container(border=True):
            # 채팅 주제 (첫 질문)
            st.write(f"**{topic[:50]}...**")  # 너무 길면 잘라내기

            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.caption(f"ID: {session_id} | {date.split('T')[0]}")

            with col2:
                if st.button("보기", key=f"view_{session_id}", use_container_width=True):
                    topic, messages = fetch_chat_session(session_id)
                    if topic is not None and messages is not None:
                        # state_manager를 통해 세션 상태 로드
                        load_chat_session(session_id, topic, messages)
                        st.rerun()

            with col3:
                if st.button("삭제", key=f"del_{session_id}", use_container_width=True):
                    if delete_chat_session(session_id):
                        # 만약 현재 보고 있는 채팅을 삭제했다면, 새 채팅으로 리셋
                        if st.session_state.current_chat_id == session_id:
                            reset_chat_session()
                        st.rerun()