from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from db.database import Base


# 채팅 세션 모델
class ChatSession(Base):
    __tablename__ = "chatsessions"

    id = Column(Integer, primary_key=True, index=True)
    # 첫 번째 사용자 질문을 세션의 '주제'로 저장합니다.
    topic = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ChatSession이 삭제될 때 관련된 ChatMessage도 함께 삭제됩니다.
    messages = relationship(
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )


# 채팅 메시지 모델
class ChatMessage(Base):
    __tablename__ = "chatmessages"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("chatsessions.id"), nullable=False)
    role = Column(String(50), nullable=False)  # "user" 또는 "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")