graph TD
    subgraph "사용자 영역"
        User(🎓 사용자)
    end

    subgraph "프론트엔드 (Streamlit)"
        FE(Streamlit UI)
    end

    subgraph "백엔드 (FastAPI 서버)"
        BE(FastAPI)
        LG(LangGraph 워크플로우)
        RR(Local Reranker)
        API_Chat(/api/v1/chat/stream)
        API_Docs(/api/v1/documents)
        
        BE --> API_Chat
        BE --> API_Docs
        API_Chat -- "(2) 채팅 요청 전달" --> LG
    end

    subgraph "데이터 스토어"
        DB(SQLite)
        FS(File System)
        VS(FAISS Vector Store)
    end

    subgraph "Azure AI 서비스 (외부)"
        LLM(Azure OpenAI LLM)
        Emb(Azure OpenAI Embeddings)
    end

    %% --- 1. 채팅 흐름 (RAG) ---
    User -- "(1) 질문 입력" --> FE
    FE -- "(1) POST /chat/stream" --> API_Chat
    
    LG -- "(3) 의도 분류" --> LLM
    LG -- "(4) 쿼리 변환" --> LLM
    LG -- "(5) 문서 검색" --> VS
    LG -- "(6) 리랭킹" --> RR
    LG -- "(7) 문서 유효성 검증" --> LLM
    LG -- "(8) RAG 답변 생성" --> LLM
    
    LLM -- "(9) 스트리밍 응답" --> LG
    LG -- "(10) 스트리밍 응답" --> API_Chat
    API_Chat -- "(11) 스트리밍 응답" --> FE
    FE -- "(12) 답변 표시" --> User

    %% --- 2. 채팅 이력 저장 ---
    API_Chat -- "(별도) 채팅 이력 저장" --> DB
    FE -- "(사이드바) 채팅 이력 조회" --> BE
    BE -- "(사이드바) 이력 로드" --> DB

    %% --- 3. 문서 업로드 흐름 ---
    User -- "(A) PDF 업로드" --> FE
    FE -- "(B) POST /documents" --> API_Docs
    API_Docs -- "(C) PDF/MD 파일 저장" --> FS
    API_Docs -- "(D) 임베딩 요청" --> Emb
    Emb -- "(E) 벡터 반환" --> API_Docs
    API_Docs -- "(F) Vector Store 업데이트" --> VS
    API_Docs -- "(G) LangGraph 재컴파일" --> LG
    
    %% --- 스타일링 ---
    classDef external fill:#f9d,stroke:#333,stroke-width:2px;
    class LLM,Emb external;

    classDef db fill:#lightgrey,stroke:#333,stroke-width:2px;
    class DB,FS,VS db;

    classDef fe fill:#def,stroke:#333,stroke-width:2px;
    class FE fe;

    classDef be fill:#ffe,stroke:#333,stroke-width:2px;
    class BE,LG,RR,API_Chat,API_Docs be;