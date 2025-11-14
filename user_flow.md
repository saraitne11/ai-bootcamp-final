graph TD
    User(👤 사용자)
    
    subgraph "Frontend (Streamlit App)"
        User --> App[🎓 AI 입시 어시스턴트]
        App --> Sidebar
        App --> MainChat[메인 채팅 UI]

        subgraph "사이드바"
            direction TB
            NewChat[➕ 새 채팅 시작]
            tab1[🗂️ 문서 관리]
            tab2[📜 채팅 이력]
            
            tab1 --> Upload("1. PDF 업로드")
            tab1 --> FileList("처리된 파일 목록 조회")
            
            tab2 --> HistoryList("채팅 이력 목록 조회")
            HistoryList --> ViewHistory("이전 채팅 보기")
        end
        
        MainChat --> ChatInput("2. 질문 입력")
        MainChat --> ChatDisplay("답변 표시")
    end

    subgraph "Backend Logic"
        %% F/E에서 B/E Logic으로 바로 연결
        Upload --> Logic_Parse["1a. PDF 파싱 (MD 변환)"]
        ChatInput --> Logic_SaveUserMsg("2a. 사용자 메시지 DB 저장")

        %% 기존 로직 흐름
        Logic_Parse --> Logic_VectorStore["1b. Vector Store 재구축"]
        Logic_VectorStore --> Logic_Recompile["1c. Graph 재컴파일"]

        Logic_SaveUserMsg --> Logic_GetHistory("2b. 채팅 이력 조회")
        Logic_GetHistory --> RAG_Workflow["2c. RAG Workflow 실행"]
        RAG_Workflow --> Logic_Stream("2d. 답변 스트리밍")
        
        %% 로직에서 F/E UI로 다시 연결
        Logic_Stream --> ChatDisplay
        Logic_Stream --> Logic_SaveAIMsg("2e. AI 답변 DB 저장")
        
        subgraph "RAG Workflow (LangGraph)"
            direction TB
            RAG_Start(Start) --> NodeIntent("A. 의도 분류")
            NodeIntent -- "일반 대화" --> NodeGeneral("B. 일반 답변 생성")
            NodeIntent -- "입시 질문" --> NodeTransform("C. 쿼리 변환")
            NodeTransform --> NodeRetrieve("D. 문서 검색")
            NodeRetrieve --> NodeRerank("E. 문서 재정렬")
            NodeRerank --> NodeGrade("F. 문서 검증")
            NodeGrade -- "관련 문서 없음" --> NodeGeneral
            NodeGrade -- "관련 문서 있음" --> NodeRAGAnswer("G. RAG 답변 생성")
            NodeGeneral --> RAG_End(End)
            NodeRAGAnswer --> RAG_End(End)
        end
    end
    
    %% 스타일 정의
    classDef frontend fill:#E0F7FA,stroke:#00796B,stroke-width:2px
    class App,Sidebar,MainChat,NewChat,tab1,tab2,Upload,FileList,HistoryList,ViewHistory,ChatInput,ChatDisplay frontend
    
    classDef backendlogic fill:#F3E5F5,stroke:#7B1FA2,stroke-width:2px
    class Logic_Parse,Logic_VectorStore,Logic_Recompile,Logic_SaveUserMsg,Logic_GetHistory,Logic_Stream,Logic_SaveAIMsg,RAG_Workflow backendlogic

    classDef rag fill:#E8F5E9,stroke:#388E3C,stroke-width:2px
    class RAG_Start,NodeIntent,NodeGeneral,NodeTransform,NodeRetrieve,NodeRerank,NodeGrade,NodeRAGAnswer,RAG_End rag