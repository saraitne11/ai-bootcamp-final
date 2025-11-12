from dotenv import load_dotenv
import os

import streamlit as st
import requests
import json
from utils.state_manager import reset_session_state


# API 엔드포인트 기본 URL
load_dotenv()
API_BASE_URL = os.environ.get("API_BASE_URL")


# API로 토론 이력 조회
def fetch_debate_history():
    """API를 통해 토론 이력 가져오기"""
    try:
        response = requests.get(f"{API_BASE_URL}/debates/")
        if response.status_code == 200:
            debates = response.json()
            # API 응답 형식에 맞게 데이터 변환 (id, topic, date, rounds)
            return [
                (debate["id"], debate["topic"], debate["created_at"], debate["rounds"])
                for debate in debates
            ]
        else:
            st.error(f"토론 이력 조회 실패: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"API 호출 오류: {str(e)}")
        return []


# API로 특정 토론 데이터 조회
def fetch_debate_by_id(debate_id):
    """API를 통해 특정 토론 데이터 가져오기"""
    try:
        response = requests.get(f"{API_BASE_URL}/debates/{debate_id}")
        if response.status_code == 200:
            debate = response.json()
            topic = debate["topic"]
            # 실제 API 응답 구조에 맞게 변환 필요
            messages = (
                json.loads(debate["messages"])
                if isinstance(debate["messages"], str)
                else debate["messages"]
            )
            docs = (
                json.loads(debate["docs"])
                if isinstance(debate["docs"], str)
                else debate.get("docs", {})
            )
            return topic, messages, docs
        else:
            st.error(f"토론 데이터 조회 실패: {response.status_code}")
            return None, None, None
    except Exception as e:
        st.error(f"API 호출 오류: {str(e)}")
        return None, None, None


# API로 토론 삭제
def delete_debate_by_id(debate_id):
    """API를 통해 특정 토론 삭제"""
    try:
        response = requests.delete(f"{API_BASE_URL}/debates/{debate_id}")
        if response.status_code == 200:
            st.success("토론이 삭제되었습니다.")
            return True
        else:
            st.error(f"토론 삭제 실패: {response.status_code}")
            return False
    except Exception as e:
        st.error(f"API 호출 오류: {str(e)}")
        return False


# API로 모든 토론 삭제
def delete_all_debates():
    """API를 통해 모든 토론 삭제"""
    try:
        # 모든 토론 목록 조회
        debates = fetch_debate_history()
        if not debates:
            return True

        # 각 토론 항목 삭제
        success = True
        for debate_id, _, _, _ in debates:
            response = requests.delete(f"{API_BASE_URL}/debates/{debate_id}")
            if response.status_code != 200:
                success = False

        if success:
            st.success("모든 토론이 삭제되었습니다.")
        return success
    except Exception as e:
        st.error(f"API 호출 오류: {str(e)}")
        return False


# API로 토론 저장
def save_debate(topic, rounds, messages, docs=None):
    """API를 통해 토론 결과를 데이터베이스에 저장"""
    try:
        # API 요청 데이터 준비
        debate_data = {
            "topic": topic,
            "rounds": rounds,
            "messages": (
                json.dumps(messages) if not isinstance(messages, str) else messages
            ),
            "docs": (
                json.dumps(docs)
                if docs and not isinstance(docs, str)
                else (docs or "{}")
            ),
        }

        response = requests.post(f"{API_BASE_URL}/debates/", json=debate_data)

        if response.status_code == 200 or response.status_code == 201:
            st.success("토론이 성공적으로 저장되었습니다.")
            return response.json().get("id")  # 저장된 토론 ID 반환
        else:
            st.error(f"토론 저장 실패: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"API 호출 오류: {str(e)}")
        return None


# 토론 이력 UI 렌더링
def render_history_ui():

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("이력 새로고침", use_container_width=True):
            st.rerun()

    with col2:
        if st.button("전체 이력 삭제", type="primary", use_container_width=True):
            if delete_all_debates():
                st.rerun()

    # 토론 이력 로드
    debate_history = fetch_debate_history()

    if not debate_history:
        st.info("저장된 토론 이력이 없습니다.")
    else:
        render_history_list(debate_history)


# 토론 이력 목록 렌더링
def render_history_list(debate_history):
    for id, topic, date, rounds in debate_history:
        with st.container(border=True):

            # 토론 주제
            st.write(f"***{topic}***")

            col1, col2, col3 = st.columns([3, 1, 1])
            # 토론 정보
            with col1:
                st.caption(f"날짜: {date} | 라운드: {rounds}")

            # 보기 버튼
            with col2:
                if st.button("보기", key=f"view_{id}", use_container_width=True):
                    topic, messages, docs = fetch_debate_by_id(id)
                    if topic and messages:
                        st.session_state.viewing_history = True
                        st.session_state.messages = messages
                        st.session_state.loaded_topic = topic
                        st.session_state.loaded_debate_id = id
                        st.session_state.docs = docs
                        st.session_state.app_mode = "results"
                        st.rerun()

            # 삭제 버튼
            with col3:
                if st.button("삭제", key=f"del_{id}", use_container_width=True):
                    if delete_debate_by_id(id):
                        reset_session_state()
                        st.rerun()
