from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from db.database import get_db
from db.models import ChatSession, ChatMessage
from db.schemas import ChatSessionSchema, ChatSessionCreate, ChatMessageSchema

# /api/v1/chats 경로로 라우터 설정
router = APIRouter(
    prefix="/api/v1/chats",
    tags=["chats"],
    responses={404: {"description": "Not found"}},
)


@router.post("/", summary="새 채팅 세션 생성", response_model=ChatSessionSchema)
def create_chat_session(
        chat_session: ChatSessionCreate,
        db: Session = Depends(get_db)
):
    """
    새로운 채팅 세션을 생성합니다.
    'topic'은 이 세션의 첫 번째 사용자 질문(또는 주제)입니다.
    """
    try:
        db_session = ChatSession(topic=chat_session.topic)
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        # 새 세션은 메시지가 비어있으므로 바로 반환
        return db_session
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.get("/", summary="모든 채팅 세션 목록 조회", response_model=List[ChatSessionSchema])
def get_all_chat_sessions(db: Session = Depends(get_db)):
    """
    모든 채팅 세션의 목록을 조회합니다.
    성능을 위해 각 세션의 상세 메시지는 제외하고 세션 정보만 반환합니다.
    (ChatSessionSchema의 messages 필드는 빈 리스트가 됩니다)
    """
    try:
        # joinedload()를 사용하지 않아 messages는 로드하지 않음
        sessions = db.query(ChatSession).order_by(ChatSession.created_at.desc()).all()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 목록 조회 실패: {str(e)}")


@router.get("/{chat_id}", summary="특정 채팅 세션 및 메시지 조회", response_model=ChatSessionSchema)
def get_chat_session(chat_id: int, db: Session = Depends(get_db)):
    """
    특정 ID의 채팅 세션과 관련된 모든 메시지를 함께 조회합니다.
    """
    try:
        # joinedload를 사용하여 ChatMessage를 함께 로드 (Eager Loading)
        session = (
            db.query(ChatSession)
            .options(joinedload(ChatSession.messages))
            .filter(ChatSession.id == chat_id)
            .first()
        )

        if session is None:
            raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다.")

        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 조회 실패: {str(e)}")


@router.delete("/{chat_id}", summary="특정 채팅 세션 삭제")
def delete_chat_session(chat_id: int, db: Session = Depends(get_db)):
    """
    특정 ID의 채팅 세션을 삭제합니다.
    DB 모델의 cascade 설정에 따라 관련된 메시지들도 함께 삭제됩니다.
    """
    try:
        session = db.query(ChatSession).filter(ChatSession.id == chat_id).first()

        if session is None:
            raise HTTPException(status_code=404, detail="채팅 세션을 찾을 수 없습니다.")

        db.delete(session)
        db.commit()
        return {"detail": "채팅 세션이 성공적으로 삭제되었습니다."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"세션 삭제 실패: {str(e)}")