from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


# --- ChatMessage 스키마 ---

# 메시지 생성을 위한 스키마 (API 입력용)
class ChatMessageCreate(BaseModel):
    role: str
    content: str
    session_id: int


# 메시지 읽기를 위한 스키마 (API 출력용)
class ChatMessageSchema(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True  # SQLAlchemy 모델 객체를 Pydantic 스키마로 변환


# --- ChatSession 스키마 ---

# 세션 생성을 위한 스키마 (API 입력용)
class ChatSessionCreate(BaseModel):
    topic: str  # 세션의 시작 질문 또는 주제


# 세션 읽기를 위한 스키마 (API 출력용)
class ChatSessionSchema(BaseModel):
    id: int
    topic: str
    created_at: datetime
    messages: List[ChatMessageSchema] = []  # 관련된 메시지 목록 포함

    class Config:
        from_attributes = True