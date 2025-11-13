import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Dict, Any

from db.database import get_db
from db.models import ChatMessage, ChatSession
from utils.config import get_llm
from retrieval.vector_store import search_vector_store
from langchain.schema import SystemMessage, HumanMessage, AIMessage

# /api/v1/chat 경로로 라우터 설정
router = APIRouter(
    prefix="/api/v1/chat",
    tags=["chat_workflow"],
    responses={404: {"description": "Not found"}},
)

# 시스템 프롬프트 정의
SYSTEM_PROMPT = """
당신은 대학 입시 요강 전문 어시스턴트입니다.
당신은 업로드된 모집 요강 문서를 기반으로만 답변해야 합니다.
사용자의 질문에 대해 모집 요강의 내용을 근거로 명확하고 친절하게 답변해주세요.

제공된 '참고 문서'에 질문과 관련된 내용이 있다면, 해당 내용을 반드시 참조하여 답변을 구성해야 합니다.
만약 '참고 문서'에 질문에 대한 답변을 찾을 수 없다면, "업로드된 모집 요강 문서에서 관련 정보를 찾을 수 없습니다."라고 솔직하게 답변해야 합니다.
절대로 당신의 기존 지식이나 문맥에 없는 정보를 지어내서 답변하면 안 됩니다.
"""


class ChatRequest(BaseModel):
    session_id: int
    topic: str  # 사용자의 새 질문 (프롬프트)


def format_rag_context(docs: List[Any]) -> str:
    """RAG 검색 결과를 LLM에 주입할 컨텍스트 문자열로 포맷합니다."""
    if not docs:
        return "참고 문서 없음."

    context = "--- 참고 문서 시작 ---\n"
    for i, doc in enumerate(docs):
        source = doc.metadata.get("source", "알 수 없음")
        content = doc.page_content
        context += f"[문서 {i + 1} (출처: {source})]\n"
        context += f"{content}\n\n"
    context += "--- 참고 문서 끝 ---"
    return context


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


async def chat_stream_generator(
        request: Request,
        session_id: int,
        user_prompt: str,
        db: Session
):
    """
    RAG 검색, LLM 스트리밍 호출, DB 저장을 비동기적으로 처리하는 제너레이터
    """

    # 1. 사용자 질문 DB에 저장
    try:
        user_message = ChatMessage(session_id=session_id, role="user", content=user_prompt)
        db.add(user_message)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving user message: {e}")
        # 스트리밍으로 에러 전송
        error_data = {"type": "error", "data": f"사용자 메시지 저장 실패: {e}"}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return

    # 2. RAG 검색
    vector_store = request.app.state.vector_store
    if vector_store:
        rag_docs = search_vector_store(query=user_prompt, vector_store=vector_store, k=3)
        rag_context = format_rag_context(rag_docs)
    else:
        rag_context = "참고 문서 없음. (Vector Store가 초기화되지 않았습니다)"

    # 3. 채팅 이력 조회 및 LLM 프롬프트 구성
    chat_history_dicts = get_chat_history_messages(session_id, db)

    # LangChain 메시지 객체 리스트 생성
    messages = [SystemMessage(content=SYSTEM_PROMPT)]
    messages.append(HumanMessage(content=f"다음은 관련된 참고 문서입니다:\n{rag_context}"))

    for msg in chat_history_dicts:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # 현재 사용자 질문은 DB 저장 후 이력에 포함되었으므로 따로 추가할 필요 없음

    # 4. LLM 스트리밍 호출
    llm = get_llm()
    full_response = ""
    try:
        async for chunk in llm.astream(messages):
            chunk_content = chunk.content
            if chunk_content:
                full_response += chunk_content
                event_data = {"type": "update", "data": {"content": chunk_content}}
                yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.01)  # 이벤트 전송 간 약간의 텀

    except Exception as e:
        print(f"LLM 스트리밍 중 오류 발생: {e}")
        error_data = {"type": "error", "data": f"LLM 호출 실패: {e}"}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
        return

    # 5. LLM 응답 DB에 저장
    try:
        if full_response:
            assistant_message = ChatMessage(session_id=session_id, role="assistant", content=full_response)
            db.add(assistant_message)
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving assistant message: {e}")
        error_data = {"type": "error", "data": f"AI 응답 저장 실패: {e}"}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"

    # 6. 스트림 종료
    event_data = {"type": "end", "data": {"full_response": full_response}}
    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"


@router.post("/stream", summary="채팅 스트림 (RAG + LLM)")
async def stream_chat(
        chat_request: ChatRequest,
        request: Request,
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

    generator = chat_stream_generator(
        request=request,
        session_id=chat_request.session_id,
        user_prompt=chat_request.topic,
        db=db
    )

    return StreamingResponse(generator, media_type="text/event-stream")