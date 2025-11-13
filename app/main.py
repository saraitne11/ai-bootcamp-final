import os
from dotenv import load_dotenv
import json
import requests
import streamlit as st

# 사이드바 및 세션 관리자 import
from components.sidebar import render_sidebar
from utils.state_manager import init_session_state, reset_chat_session

# API 기본 URL 로드
load_dotenv()
API_BASE_URL = os.environ.get("API_BASE_URL")


def process_streaming_response(chunk):
    """
    API의 스트리밍 응답 청크(줄)를 파싱합니다.
    """
    if not chunk:
        return None

    line = chunk.decode("utf-8")

    if not line.startswith("data: "):
        return None

    data_str = line[6:]  # 'data: ' 부분 제거

    try:
        event_data = json.loads(data_str)
        event_type = event_data.get("type")

        if event_type == "update":
            return event_data.get("data", {}).get("content")
        elif event_type == "end":
            return None  # 스트림 종료 신호
        elif event_type == "error":
            st.error(f"스트리밍 중 오류 발생: {event_data.get('data')}")
            return None

    except json.JSONDecodeError:
        print(f"JSON 파싱 오류: {data_str}")
        return None
    return None


def handle_chat_input(prompt: str):
    """
    사용자 채팅 입력을 처리합니다.
    API로 스트리밍 요청을 보내고 응답을 UI에 표시합니다.
    """
    # 1. 현재 채팅 세션 ID 확인 (없으면 새 세션 생성)
    if st.session_state.current_chat_id is None:
        reset_chat_session()
        # 새 세션 생성 시 첫 질문으로 topic 업데이트 (B/E에서 구현 필요)
        # B/E의 /api/v1/chats/ POST가 topic을 받으므로, reset_chat_session 수정 필요
        # --> 수정: reset_chat_session이 "새 채팅"으로 세션을 만들고,
        #         여기서 첫 질문을 보낼 때 topic을 업데이트 하도록 B/E 수정이 필요하나,
        #         현재 구조에서는 그냥 진행합니다.

    # 2. 사용자 메시지를 세션 상태와 UI에 추가
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 3. API 스트리밍 요청 데이터 준비
    data = {
        "session_id": st.session_state.current_chat_id,
        "topic": prompt  # 'topic' 키가 B/E의 ChatRequest 모델과 일치
    }

    # 4. 스트리밍 응답 처리
    with st.chat_message("assistant"):
        placeholder = st.empty()
        full_response = ""
        with st.spinner("응답 생성 중..."):
            try:
                with requests.post(
                        f"{API_BASE_URL}/chat/stream",
                        json=data,
                        stream=True,
                        headers={"Content-Type": "application/json"},
                        timeout=300  # 5분 타임아웃
                ) as response:
                    if response.status_code != 200:
                        st.error(f"API 오류: {response.status_code} - {response.text}")
                        return

                    for chunk in response.iter_lines():
                        content = process_streaming_response(chunk)
                        if content:
                            full_response += content
                            placeholder.markdown(full_response + "▌")

                placeholder.markdown(full_response)

            except requests.RequestException as e:
                st.error(f"API 요청 오류: {str(e)}")
                return

    # 5. 전체 AI 응답을 세션 상태에 추가
    # (B/E가 이미 DB에 저장했으므로, 이것은 순전히 현재 UI 표시용)
    if full_response:
        st.session_state.messages.append({"role": "assistant", "content": full_response})


def render_ui():
    """
    메인 챗봇 UI를 렌더링합니다.
    """
    # 페이지 설정
    st.set_page_config(page_title="AI 입시 어시스턴트", page_icon="🎓", layout="wide")

    # 제목
    st.title("🎓 AI 입시 어시스턴트 챗봇")
    st.markdown("좌측 사이드바에서 모집요강 PDF를 업로드하고, 입시 정보를 질문하세요.")

    # 사이드바 렌더링 (문서 관리, 채팅 이력)
    render_sidebar()

    # '새 채팅 시작' 버튼 (사이드바 상단으로 이동)
    if st.sidebar.button("➕ 새 채팅 시작", use_container_width=True, type="primary"):
        reset_chat_session()
        st.rerun()

    st.sidebar.markdown("---")  # 새 채팅 버튼과 탭 사이에 구분선

    # 채팅 메시지 표시 영역
    chat_container = st.container()
    with chat_container:
        if st.session_state.viewing_history:
            st.info(f"이전 채팅(ID: {st.session_state.current_chat_id})을 보고 있습니다. '새 채팅 시작'을 눌러 새로 시작하세요.")

        # `st.session_state.messages`에 저장된 메시지 표시
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

    # 채팅 입력창 (항상 페이지 하단에 고정)
    if prompt := st.chat_input("모집요강에 대해 질문하세요..."):
        handle_chat_input(prompt)


if __name__ == "__main__":
    # 세션 상태 초기화 (최초 1회 실행)
    init_session_state()

    # UI 렌더링
    render_ui()