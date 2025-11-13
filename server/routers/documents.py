import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request

from typing import List

# Vector DB 및 PDF 처리 함수 import
from processing import parse_pdf_to_markdown, load_md_documents, build_persistent_vector_store, PDF_FOLDER_PATH
from processing import MD_FOLDER_PATH, VECTOR_STORE_PATH

from utils.config import get_embeddings
from workflow.graph import get_compiled_graph

# /api/v1/documents 경로로 라우터 설정
router = APIRouter(
    prefix="/api/v1/documents",
    tags=["documents"],
    responses={404: {"description": "Not found"}},
)


@router.post("/upload", summary="PDF 업로드 및 Vector DB 재구축")
async def upload_document(
        request: Request,
        file: UploadFile = File(...)
):
    """
    PDF 파일을 업로드합니다.
    1. PDF를 'server/pdf/'에 저장합니다.
    2. PDF를 마크다운으로 파싱하여 'server/md/'에 저장합니다.
    3. 'server/md/' 폴더 전체를 다시 읽어 Vector Store를 재구축하고 저장합니다.
    4. 재구축된 Vector Store를 app.state.vector_store에 업데이트합니다.
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    # 1. PDF 파일 저장
    pdf_filename = file.filename
    pdf_path = os.path.join(PDF_FOLDER_PATH, pdf_filename)

    try:
        # 파일을 바이트로 읽기 (processing.py의 parse_pdf_to_markdown이 바이트를 받음)
        pdf_bytes = await file.read()

        # 디스크에도 저장
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # 2. PDF -> 마크다운 파싱 및 저장
        base_filename = os.path.splitext(pdf_filename)[0]
        md_filename = base_filename + ".md"
        md_path = parse_pdf_to_markdown(pdf_path, md_filename)

        if not md_path:
            raise HTTPException(status_code=500, detail="PDF 파싱 중 오류가 발생했습니다.")

        # 3. Vector Store 재구축
        print(f"'{MD_FOLDER_PATH}'에서 모든 문서를 로드하여 Vector Store 재구축 중...")
        embeddings = get_embeddings()
        documents = load_md_documents(MD_FOLDER_PATH)

        if not documents:
            # 유일한 문서가 파싱 실패한 경우
            request.app.state.vector_store = None
            print("재구축할 문서가 없습니다. Vector Store를 비웁니다.")
            return {"filename": file.filename, "detail": "문서 파싱에 성공했으나, Vector Store에 추가할 콘텐츠가 없습니다."}

        # 기존 Vector Store가 있다면 삭제 후 새로 생성
        if os.path.exists(VECTOR_STORE_PATH):
            shutil.rmtree(VECTOR_STORE_PATH)

        new_vector_store = build_persistent_vector_store(documents, VECTOR_STORE_PATH, embeddings)

        # 4. 앱 상태(메모리)의 Vector Store 업데이트
        request.app.state.vector_store = new_vector_store
        print("Vector Store 재구축 및 앱 상태 업데이트 완료.")

        # 5. LangGraph 재컴파일
        try:
            get_compiled_graph(new_vector_store)
            print("LangGraph가 새 Vector Store로 재컴파일되었습니다.")
        except Exception as e:
            print(f"LangGraph 재컴파일 중 오류 발생: {e}")
            # 오류가 발생해도 일단 업로드는 성공으로 처리하되, 로깅
            pass
        return {"filename": file.filename, "md_path": md_path, "detail": "업로드 및 Vector Store 재구축 성공"}

    except Exception as e:
        print(f"파일 업로드 처리 중 오류 발생: {e}")
        raise HTTPException(status_code=500, detail=f"파일 처리 중 오류: {str(e)}")


@router.get("/", summary="처리된 문서 목록 조회", response_model=List[str])
async def get_processed_documents():
    """
    'server/md/' 폴더에 저장된 (파싱 및 처리가 완료된)
    마크다운 파일의 목록을 반환합니다.
    """
    if not os.path.exists(MD_FOLDER_PATH):
        return []

    try:
        md_files = [f for f in os.listdir(MD_FOLDER_PATH) if f.endswith(".md")]
        return md_files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"문서 목록 조회 중 오류: {str(e)}")