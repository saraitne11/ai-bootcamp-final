import uvicorn
import os
import ssl
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# DB 초기화를 위한 import
from db.database import Base, engine
# db.models를 import해야 Base.metadata.create_all이 테이블을 인식합니다.
import db.models

# 새 라우터 import (계획에 따라 이름 변경)
from routers import chat, documents, chat_workflow

# Vector DB 초기화를 위한 import
from processing import (
    load_md_documents,
    build_persistent_vector_store,
    load_persistent_vector_store,
    MD_FOLDER_PATH,
    PDF_FOLDER_PATH,
    VECTOR_STORE_PATH
)
from utils.config import get_embeddings, settings



# FastAPI 인스턴스 생성 (프로젝트명 변경)
app = FastAPI(
    title="AI 대학 입시 어시스턴트 API",
    description="대학 모집요강 PDF 기반 RAG 챗봇 API",
    version="1.0.0",
)

# CORS 미들웨어 설정 (기존 설정 유지)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """
    서버 시작 시 필요한 폴더를 생성하고 Vector Store를 초기화합니다.
    """
    # 1. 필수 폴더 생성
    os.makedirs(PDF_FOLDER_PATH, exist_ok=True)
    os.makedirs(MD_FOLDER_PATH, exist_ok=True)
    os.makedirs(os.path.dirname(VECTOR_STORE_PATH), exist_ok=True)
    print("필수 폴더 생성을 확인했습니다.")

    # 2. Vector Store 초기화
    embeddings = get_embeddings()
    try:
        if os.path.exists(VECTOR_STORE_PATH):
            print("기존 Vector Store 로드 중...")
            app.state.vector_store = load_persistent_vector_store(VECTOR_STORE_PATH, embeddings)
            print("Vector Store 로드 완료.")
        else:
            print(f"'{MD_FOLDER_PATH}'에서 MD 파일 로드하여 Vector Store 구축 중...")
            documents = load_md_documents(MD_FOLDER_PATH)
            if documents:
                app.state.vector_store = build_persistent_vector_store(documents, VECTOR_STORE_PATH, embeddings)
                print("Vector Store 구축 및 저장 완료.")
            else:
                app.state.vector_store = None  # 문서가 없으면 None으로 초기화
                print("MD 파일이 없어 빈 Vector Store로 초기화합니다.")
    except Exception as e:
        print(f"Vector Store 초기화 중 오류 발생: {e}")
        app.state.vector_store = None

# 3. 데이터베이스 테이블 생성
# (ChatSession, ChatMessage 테이블)
print("데이터베이스 테이블 생성 중...")
Base.metadata.create_all(bind=engine)
print("데이터베이스 테이블 생성 완료.")

# 4. 라우터 추가
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(chat_workflow.router)
print("API 라우터 포함 완료.")


@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "AI 입시 어시스턴트 API에 오신 것을 환영합니다."}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)