import os
# import fitz  # PyMuPDF
import pymupdf4llm
from typing import List
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import UnstructuredMarkdownLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain.schema import Document

# MD 파일 저장 경로
MD_FOLDER_PATH = "data/md"
# PDF 파일 저장 경로
PDF_FOLDER_PATH = "data/pdf"
# Vector Store 저장 경로
VECTOR_STORE_PATH = "data/vector_store/faiss_index"


def parse_pdf_to_markdown(pdf_path: str, md_filename: str) -> str:
    """
    PDF 바이트 데이터를 받아 텍스트를 추출하고 마크다운 파일로 저장합니다.
    PyMuPDF를 사용하여 텍스트를 블록 단위로 추출합니다.
    """
    if not os.path.exists(MD_FOLDER_PATH):
        os.makedirs(MD_FOLDER_PATH)

    md_path = os.path.join(MD_FOLDER_PATH, md_filename)

    try:
        # PyMuPDF4LLM을 사용하여 바이트 데이터로부터 직접 마크다운 생성
        # to_markdown()는 표, 제목, 단락 구조를 인식하여 변환합니다.
        md_content = pymupdf4llm.to_markdown(pdf_path)

        # 변환된 마크다운을 파일로 저장
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return md_path

    except Exception as e:
        print(f"Error parsing PDF to MD: {e}")
        return ""


def load_md_documents(md_folder_path: str) -> List[Document]:
    """
    지정된 폴더 내의 모든 마크다운 파일을 로드하고 분할합니다.
    """
    documents = []
    if not os.path.exists(md_folder_path):
        return documents

    for filename in os.listdir(md_folder_path):
        if filename.endswith(".md"):
            file_path = os.path.join(md_folder_path, filename)
            try:
                loader = UnstructuredMarkdownLoader(file_path)
                docs = loader.load()
                # Document에 원본 파일명 메타데이터 추가
                for doc in docs:
                    doc.metadata["source"] = filename
                documents.extend(docs)
            except Exception as e:
                print(f"Error loading MD file {filename}: {e}")

    if not documents:
        return []

    # 텍스트 분할
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=100,
        length_function=len
    )
    return text_splitter.split_documents(documents)


def build_persistent_vector_store(documents: List[Document], store_path: str, embeddings) -> FAISS:
    """
    Document 목록으로부터 FAISS Vector Store를 생성하고 디스크에 저장합니다.
    """
    vector_store = FAISS.from_documents(documents, embeddings)

    store_dir = os.path.dirname(store_path)
    if not os.path.exists(store_dir):
        os.makedirs(store_dir)

    vector_store.save_local(store_path)
    return vector_store


def load_persistent_vector_store(store_path: str, embeddings) -> FAISS:
    """
    디스크에 저장된 FAISS Vector Store를 로드합니다.
    """
    if not os.path.exists(store_path):
        raise FileNotFoundError(f"Vector store not found at {store_path}")

    # allow_dangerous_deserialization=True는 FAISS.load_local에 필요합니다.
    return FAISS.load_local(
        store_path,
        embeddings,
        allow_dangerous_deserialization=True
    )