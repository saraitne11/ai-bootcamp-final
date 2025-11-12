import uvicorn
from fastapi import FastAPI

import ssl
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context


# 절대 경로 임포트로 수정
from routers import workflow

# 데이터베이스 초기화를 위한 임포트 추가
from db.database import Base, engine
from routers import history

# 데이터베이스 초기화
Base.metadata.create_all(bind=engine)

# FastAPI 인스턴스 생성
app = FastAPI(
    title="Debate Arena API",
    description="AI Debate Arena 서비스를 위한 API",
    version="0.1.0",
)

# router 추가
app.include_router(history.router)
app.include_router(workflow.router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
