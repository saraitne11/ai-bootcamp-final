import streamlit as st
from langchain_community.vectorstores import FAISS
from typing import List, Dict, Any
from langchain.schema import Document


def search_vector_store(query: str, vector_store: FAISS, k: int = 5) -> List[Document]:
    """
    메모리에 로드된 FAISS Vector Store에서 Similarity Search를 수행합니다.

    :param query: 사용자 검색어
    :param vector_store: app.state.vector_store에서 전달된 FAISS 인스턴스
    :param k: 반환할 문서 개수
    :return: Document 리스트
    """
    if not vector_store:
        st.warning("Vector Store가 아직 준비되지 않았습니다. 문서를 업로드하세요.")
        return []

    try:
        # FAISS 인스턴스에서 직접 검색 수행
        return vector_store.similarity_search(query, k=k)
    except Exception as e:
        # Streamlit이 아닌 FastAPI B/E이므로 st.error 대신 print/logging 사용
        print(f"Vector store 검색 중 오류 발생: {str(e)}")
        return []