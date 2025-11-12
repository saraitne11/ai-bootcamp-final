import streamlit as st

from typing import Dict, Any

from components.history import render_history_ui


def render_input_form():
    with st.form("debate_form", border=False):
        # 토론 주제 입력
        st.text_input(
            label="토론 주제를 입력하세요:",
            value="인공지능은 인간의 일자리를 대체할 수 있습니다.",
            key="ui_topic",
        )

        max_rounds = st.slider("토론 라운드 수", min_value=1, max_value=5, value=1)
        st.session_state.max_rounds = max_rounds
        st.form_submit_button(
            "토론 시작",
            on_click=lambda: st.session_state.update({"app_mode": "debate"}),
        )
        # RAG 기능 활성화 옵션
        st.checkbox(
            "RAG 활성화",
            value=True,
            help="외부 지식을 검색하여 토론에 활용합니다.",
            key="ui_enable_rag",
        )


def render_sidebar() -> Dict[str, Any]:
    with st.sidebar:

        tab1, tab2 = st.tabs(["새 토론", "토론 이력"])

        with tab1:
            render_input_form()

        with tab2:
            render_history_ui()
