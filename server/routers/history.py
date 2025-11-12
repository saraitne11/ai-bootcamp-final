from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from db.database import get_db
from db.models import Debate as DebateModel
from db.schemas import DebateSchema, DebateCreate

router = APIRouter(prefix="/api/v1", tags=["debates"])


# 토론 목록 조회
@router.get("/debates/", response_model=List[DebateSchema])
def read_debates(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    debates = db.query(DebateModel).offset(skip).limit(limit).all()
    return debates


# 토론 생성
@router.post("/debates/", response_model=DebateSchema)
def create_debate(debate: DebateCreate, db: Session = Depends(get_db)):
    db_debate = DebateModel(**debate.model_dump())
    db.add(db_debate)
    db.commit()
    db.refresh(db_debate)
    return db_debate


# 토론 조회
@router.get("/debates/{debate_id}", response_model=DebateSchema)
def read_debate(debate_id: int, db: Session = Depends(get_db)):
    db_debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if db_debate is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    return db_debate


# 토론 삭제
@router.delete("/debates/{debate_id}")
def delete_debate(debate_id: int, db: Session = Depends(get_db)):
    db_debate = db.query(DebateModel).filter(DebateModel.id == debate_id).first()
    if db_debate is None:
        raise HTTPException(status_code=404, detail="Debate not found")

    db.delete(db_debate)
    db.commit()
    return {"detail": "Debate successfully deleted"}
