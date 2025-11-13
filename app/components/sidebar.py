import streamlit as st
import requests
import os
from dotenv import load_dotenv
from components.history import render_history_ui

# API 엔드포인트 기본 URL
load_dotenv()
API_BASE_URL = os.environ.get("API_BASE_URL")


def handle_pdf_upload():
    """
    파일 업로더의 on_change 콜백 함수.
    선택된 PDF 파일을 백엔드 API로 전송합니다.
    """
    if st.session_state.pdf_uploader is not None:
        file = st.session_state.pdf_uploader
        files = {"file": (file.name, file, file.type)}

        with st.spinner(f"'{file.name}' 업로드 및 처리 중... (파일 크기에 따라 시간이 걸릴 수 있습니다)"):
            try:
                response = requests.post(
                    f"{API_BASE_URL}/documents/upload",
                    files=files
                )
                if response.status_code == 200:
                    st.success(f"'{file.name}'이(가) 성공적으로 처리되어 Vector DB에 반영되었습니다.")
                    # st.rerun() # 업로드 후 목록 자동 갱신
                else:
                    st.error(f"파일 처리 실패: {response.json().get('detail', response.text)}")
            except requests.RequestException as e:
                st.error(f"API 연결 실패: {e}")
            finally:
                # 업로더 초기화 (다시 업로드할 수 있도록)
                # st.session_state.pdf_uploader = None
                pass


def display_processed_files():
    """
    백엔드에서 처리 완료된(파싱된) 문서 목록을 가져와 표시합니다.
    """
    st.markdown("---")
    st.subheader("처리된 문서 목록")
    try:
        response = requests.get(f"{API_BASE_URL}/documents/")
        if response.status_code == 200:
            files = response.json()
            if not files:
                st.info("아직 처리된 문서가 없습니다. PDF를 업로드하세요.")
            else:
                st.caption(f"총 {len(files)}개의 문서가 RAG에 사용됩니다:")
                # 스크롤 가능한 영역에 파일 목록 표시
                container = st.container(height=200, border=False)
                for f in files:
                    container.markdown(f"- 📄 `{f}`")
        else:
            st.error("처리된 문서 목록을 불러오는 데 실패했습니다.")
    except requests.RequestException:
        st.error("API 서버에 연결할 수 없습니다.")


def render_sidebar():
    """
    메인 사이드바를 렌더링합니다.
    '문서 관리' 탭과 '채팅 이력' 탭을 포함합니다.
    """
    with st.sidebar:
        st.title("AI 입시 어시스턴트")

        tab1, tab2 = st.tabs(["🗂️ 문서 관리", "📜 채팅 이력"])

        with tab1:
            st.header("모집요강 업로드")
            st.file_uploader(
                "PDF 파일을 업로드하세요",
                type="pdf",
                key="pdf_uploader",
                on_change=handle_pdf_upload,
                label_visibility="collapsed"
            )
            st.caption("PDF를 업로드하면 자동으로 문서를 파싱하고 Vector DB에 반영합니다.")

            # 처리된 파일 목록 표시
            display_processed_files()

        with tab2:
            st.header("채팅 이력")
            render_history_ui()