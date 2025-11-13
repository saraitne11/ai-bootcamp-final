import streamlit as st
import requests
import os
from dotenv import load_dotenv

# API 엔드포인트 기본 URL
load_dotenv()
API_BASE_URL = os.environ.get("API_BASE_URL")


def init_session_state():
    """
    Streamlit 세션 상태를 챗봇 앱에 맞게 초기화합니다.
    """
    if "app_mode" not in st.session_state:
        st.session_state.app_mode = "chat"  # 기본 모드를 'chat'으로 설정
    if "messages" not in st.session_state:
        st.session_state.messages = []  # 채팅 메시지 기록
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = None  # 현재 채팅 세션 ID
    if "viewing_history" not in st.session_state:
        st.session_state.viewing_history = False  # 채팅 이력 조회 모드 여부


def reset_chat_session():
    """
    '새 채팅 시작' 시 호출됩니다.
    백엔드에 새 채팅 세션을 생성하고 ID를 받아와 세션 상태를 초기화합니다.
    """
    st.session_state.messages = []
    st.session_state.viewing_history = False

    try:
        # 백엔드에 새 세션 생성을 요청 (기본 주제)
        response = requests.post(
            f"{API_BASE_URL}/chats/",
            json={"topic": "새 채팅"}  # 첫 질문을 topic으로 하려했으나, 새 채팅 시점엔 알 수 없음
        )
        if response.status_code == 200 or response.status_code == 201:
            new_session = response.json()
            st.session_state.current_chat_id = new_session["id"]
            # 새 세션이 생성되면 topic을 업데이트 (첫 질문 때 업데이트되도록 B/E 수정 필요)
            # st.session_state.topic = new_session["topic"]
        else:
            st.error(f"새 채팅 세션 생성 실패: {response.text}")
            st.session_state.current_chat_id = None
    except requests.RequestException as e:
        st.error(f"API 연결 실패: {e}")
        st.session_state.current_chat_id = None

    st.session_state.app_mode = "chat"


def load_chat_session(session_id: int, topic: str, messages: list):
    """
    채팅 이력에서 '보기'를 눌렀을 때 호출됩니다.
    선택한 세션의 정보를 현재 세션 상태로 로드합니다.
    """
    st.session_state.app_mode = "chat"
    st.session_state.messages = messages
    st.session_state.viewing_history = True
    st.session_state.current_chat_id = session_id
    # st.session_state.topic = topic # 필요시 토픽(첫 질문)도 로드