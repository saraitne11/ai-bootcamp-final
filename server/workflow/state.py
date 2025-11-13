from typing import List, TypedDict, Optional
from langchain_core.messages import BaseMessage
from langchain_core.documents import Document


class GraphState(TypedDict):
    """
    LangGraph의 모든 노드가 공유하는 상태 객체입니다.
    """

    # --- 입력 ---
    # DB에서 로드한 전체 채팅 이력
    messages: List[BaseMessage]
    # 사용자의 마지막 원본 질문
    original_query: str

    # --- 그래프 실행 중 채워지는 값 ---
    # 쿼리 변환 노드에서 생성
    transformed_query: Optional[str] = None
    # 의도 분류 노드에서 생성 ('admission_question' 또는 'general_chat')
    intent: Optional[str] = None
    # 문서 검색 노드에서 생성
    documents: Optional[List[Document]] = None
    # 최종 답변 (스트리밍 청크가 누적됨)
    answer: str = ""
