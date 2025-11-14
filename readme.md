# AI Bootcamp 최종 과제: 나만의 AI Agent

## 📌 프로젝트 개요

  * AI Bootcamp 최종 과제로, "나만의 AI Agent" 개발을 목표로 함
  * RAG, LangChain/LangGraph 등 기술을 활용하여 특정 역할을 수행하는 AI Agent 설계
  * Streamlit 기반 UI를 통해 사용자와 상호작용 가능한 서비스 구현

-----

## 🛠️ 주요 기술 스택

  * `requirements.txt`에 명시된 라이브러리 기반
  * **Frontend:** Streamlit
  * **Backend:** FastAPI
  * **AI/LLM:** LangChain, LangGraph
  * **RAG (VectorDB):** FAISS (faiss-cpu)
  * **Embedding:** sentence-transformers
  * **LLM (OpenAI):** openai

-----

## ⚙️ 설치 및 환경설정

1.  **필요 라이브러리 설치**

      * `requirements.txt` 파일을 이용한 Python 라이브러리 일괄 설치
      * ```bash
          pip install -r requirements.txt
        ```

2.  **환경 변수 설정**

      * 과제 수행에 필요한 AOAI 키 또는 기타 API 키 환경 변수 설정 필요
      * (예: `.env` 파일 생성 및 관리)

-----

## 🚀 앱 실행 방법

  * 애플리케이션은 Backend(FastAPI)와 Frontend(Streamlit)로 구성됨

### 1\. B/E (Backend) 실행

  * FastAPI 서버 실행
    ```bash
    cd ./server
    uvicorn main:app --reload --port 8085
    ```

### 2\. F/E (Frontend) 실행

  * Streamlit 앱 실행
  * (주의: Backend 서버가 실행 중인 상태에서 진행해야 함)
    ```bash
    cd ./app
    streamlit run .\main.py
    ```