import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from db.database import get_db
from db.models import ChatMessage, ChatSession

from workflow.graph import get_graph_app # 컴파일된 그래프 인스턴스를 가져옵니다.
from langchain_core.messages import HumanMessage, AIMessage

# /api/v1/chat 경로로 라우터 설정
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat_workflow"],
    responses={404: {"description": "Not found"}},
)


class ChatRequest(BaseModel):
    session_id: int
    topic: str  # 사용자의 새 질문 (프롬프트)


def get_chat_history_messages(session_id: int, db: Session) -> List[Dict[str, str]]:
    """DB에서 특정 세션의 채팅 이력을 가져옵니다."""
    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    # Pydantic 모델이 아닌, LangChain 메시지 객체로 변환하기 쉬운 dict 리스트로 반환
    return [{"role": msg.role, "content": msg.content} for msg in messages]


def format_db_history_to_langchain(history: List[Dict[str, str]]) -> List:
    """DB 딕셔너리 리스트를 LangChain BaseMessage 객체 리스트로 변환"""
    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


async def langgraph_stream_generator(
        session_id: int,
        user_prompt: str,
        db: Session
):
    """
    LangGraph를 비동기 스트리밍으로 실행하고,
    프론트엔드가 이해하는 SSE 형식으로 변환하여 yield합니다.
    """

    # 1. 사용자 질문 DB에 저장 (기존과 동일)
    try:
        user_message = ChatMessage(session_id=session_id, role="user", content=user_prompt)
        db.add(user_message)
        db.commit()
        db.refresh(user_message)  # ID를 받아옴
    except Exception as e:
        db.rollback()
        print(f"Error saving user message: {e}")
        error_data = {"type": "error", "data": f"사용자 메시지 저장 실패: {e}"}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return

    # 2. 그래프 실행 준비
    compiled_graph = get_graph_app()
    if compiled_graph is None:
        print("치명적 오류: LangGraph가 컴파일되지 않았습니다.")
        error_data = {"type": "error", "data": "서버 그래프 엔진이 준비되지 않았습니다."}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return

    # 3. 채팅 이력 조회 및 변환
    history_dicts = get_chat_history_messages(session_id, db)
    # LangChain BaseMessage 객체 리스트로 변환 (DB에 방금 저장한 user_message 포함)
    messages = format_db_history_to_langchain(history_dicts)

    # 4. 그래프 초기 상태 정의
    initial_state = {
        "messages": messages,
        "original_query": user_prompt
    }

    # LangGraph는 상태를 저장/로드하기 위한 'thread_id'가 필요합니다.
    # 여기서는 DB의 session_id를 사용합니다.
    config = {"configurable": {"thread_id": str(session_id)}}

    # 5. LangGraph 스트리밍 실행
    full_response = ""
    last_yielded_answer = ""
    try:
        # app.astream()은 그래프의 각 노드에서 발생하는 이벤트를 스트리밍합니다.
        async for event in compiled_graph.astream(initial_state, config=config):

            # 우리는 '답변 생성 노드' (generate_rag_answer 또는 generate_normal_answer)
            # 에서 나오는 스트리밍 '청크(chunk)'에만 관심이 있습니다.

            event_data_key = None
            if "generate_rag_answer" in event:
                event_data_key = "generate_rag_answer"
            elif "generate_normal_answer" in event:
                event_data_key = "generate_normal_answer"

            if event_data_key:
                # --- 수정된 부분: 'chunk.content' 대신 'chunk_data["answer"]'를 확인 ---
                # event[event_data_key]는 nodes.py에서 yield한 dict입니다: {"answer": "..."}
                chunk_data = event[event_data_key]

                # 'answer' 키가 있고, 내용이 있는지 확인
                if "answer" in chunk_data and chunk_data["answer"]:
                    chunk_content = chunk_data["answer"]

                    # nodes.py에서 마지막 yield는 '전체 응답'입니다.
                    # 스트리밍 청크는 '누적'되고, 마지막 청크는 '전체'입니다.
                    # '전체 응답'이 '누적된 청크'와 다르다면, 이것이 새로운 '청크'입니다.
                    if chunk_content != last_yielded_answer:
                        # 프론트엔드에 보낼 실제 청크 (전체 응답에서 이전 응답을 뺀 값)
                        sse_chunk = chunk_content[len(last_yielded_answer):]
                        last_yielded_answer = chunk_content  # 마지막 응답 업데이트

                        # 프론트엔드가 요구하는 SSE 형식으로 변환하여 yield
                        sse_data = {"type": "update", "data": {"content": sse_chunk}}
                        yield f"data: {json.dumps(sse_data, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.01)  # 이벤트 전송 간 약간의 텀

    except Exception as e:
        print(f"LangGraph 스트리밍 중 오류 발생: {e}")
        error_data = {"type": "error", "data": f"LLM 스트리밍 실패: {e}"}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return

    # 6. LLM 전체 응답 DB에 저장
    try:
        if last_yielded_answer:
            assistant_message = ChatMessage(session_id=session_id, role="assistant", content=last_yielded_answer)
            db.add(assistant_message)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving assistant message: {e}")
        error_data = {"type": "error", "data": f"AI 응답 저장 실패: {e}"}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    # 7. 스트림 종료
    event_data = {"type": "end", "data": {"full_response": full_response}}
    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"


@router.post("/stream", summary="채팅 스트림 (RAG + LLM)")
async def stream_chat(
        chat_request: ChatRequest,
        db: Session = Depends(get_db)
):
    """
    사용자의 질문을 받아 RAG 검색을 수행하고,
    LLM의 답변을 스트리밍으로 반환합니다.
    """

    # 세션 유효성 검사
    session = db.query(ChatSession).filter(ChatSession.id == chat_request.session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="존재하지 않는 채팅 세션입니다.")

    generator = langgraph_stream_generator(
        session_id=chat_request.session_id,
        user_prompt=chat_request.topic,
        db=db
    )

    return StreamingResponse(generator, media_type="text/event-stream")