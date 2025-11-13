import json
from typing import List, Literal

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from pydantic import BaseModel, Field

# --- 기존 코드에서 Import ---
from utils.config import get_llm, get_reranker
from retrieval.vector_store import search_vector_store
from workflow.state import GraphState


# --- 1. 의도 분류 노드 ---

class IntentClassifier(BaseModel):
    """사용자 질문의 의도를 'admission_question' 또는 'general_chat'로 분류합니다."""
    intent: Literal["admission_question", "general_chat"] = Field(
        description="사용자 질문이 입시 요강과 관련된 질문인지, 아니면 단순 잡담/인사인지 분류합니다."
    )


def node_classify_intent(state: GraphState):
    """사용자의 최신 질문을 분석하여 의도를 분류합니다."""
    print("--- 1. 의도 분류 노드 ---")

    llm = get_llm()
    # Pydantic 모델을 JSON 스키마로 변환하여 LLM에 주입 (JSON 모드)
    structured_llm = llm.with_structured_output(IntentClassifier, method="json_mode")

    prompt = ChatPromptTemplate.from_messages([
        ("system",
         "당신은 사용자 의도 분류기입니다. "
         "사용자의 마지막 질문을 분석하여 'admission_question'(입시 요강 질문) 또는 'general_chat'(단순 잡담/인사)으로 분류합니다. "
         "응답은 반드시 'intent'라는 JSON 키(key)를 사용해야 합니다."),
        ("human", "{question}")
    ])

    chain = prompt | structured_llm

    try:
        result = chain.invoke({"question": state["original_query"]})
        print(f"의도 분류 결과: {result.intent}")
        return {"intent": result.intent}
    except Exception as e:
        print(f"의도 분류 실패 (기본값 'admission_question'): {e}")
        # 실패 시 기본적으로 RAG 경로를 타도록 설정
        return {"intent": "admission_question"}


# --- 2. 쿼리 변환 노드 ---

def node_transform_query(state: GraphState):
    """채팅 이력을 바탕으로 사용자의 마지막 질문을 RAG 검색에 적합한 독립적인 질문으로 재작성합니다."""
    print("--- 2. 쿼리 변환 노드 ---")

    system_prompt = """당신은 쿼리 재작성 전문 AI입니다. 
    채팅 이력을 바탕으로, 사용자의 마지막 질문을 VectorDB 검색에 적합하도록 명확하고 독립적인 단일 질문으로 재작성하세요.
    채팅 이력이 없다면 마지막 질문을 그대로 반환하세요.
    """

    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("system", "<채팅 이력>\n{chat_history}"),
        ("human", "마지막 질문: {question}")
    ])

    llm = get_llm()
    chain = (
            RunnablePassthrough.assign(
                chat_history=lambda x: "\n".join(
                    [f"{msg.type}: {msg.content}" for msg in x["history"]])
            )
            | prompt
            | llm
            | StrOutputParser()
    )

    # 'messages'에서 마지막 질문(Human)과 그 이전 이력(History)을 분리
    human_query = state["original_query"]
    history = state["messages"][:-1]  # 마지막 질문 제외

    transformed_query = chain.invoke({
        "question": human_query,
        "history": history
    })

    print(f"쿼리 변환:\n  - 원본: {human_query}\n  - 변환: {transformed_query}")
    return {"transformed_query": transformed_query}


# --- 3. 문서 검색 노드 ---

def node_retrieve_documents(state: GraphState, vector_store: any):
    """변환된 쿼리를 사용하여 Vector Store에서 문서를 검색합니다."""
    print("--- 3. 문서 검색 노드 ---")

    query = state.get("transformed_query")
    if not query:
        print("오류: 변환된 쿼리가 없습니다.")
        return {"documents": []}

    if not vector_store:
        print("경고: Vector Store가 준비되지 않았습니다.")
        return {"documents": []}

    try:
        # 기존 retrieval/vector_store.py의 함수 사용
        documents = search_vector_store(query=query, vector_store=vector_store, k=10)
        print(f"문서 {len(documents)}개 검색됨")
        return {"documents": documents}
    except Exception as e:
        print(f"문서 검색 실패: {e}")
        return {"documents": []}


# --- 4. [신규] Rerank 노드 ---
def node_rerank_documents(state: GraphState):
    """
    검색된(Retrieve) 문서들을 Reranker(Cross-Encoder)를 사용해
    쿼리와의 관련성 점수를 다시 매기고, 관련성 높은 순으로 정렬합니다.
    """
    print("--- 4. Rerank 노드 ---")

    reranker = get_reranker()
    query = state.get("transformed_query")
    documents = state.get("documents")

    if not documents:
        print("Rerank: 문서 없음. 단계를 건너뜁니다.")
        return {"documents": []}

    try:
        # Reranker는 (query, document_text) 쌍의 리스트를 입력으로 받습니다.
        pairs = [(query, doc.page_content) for doc in documents]

        # Reranker 모델로 점수 계산
        scores = reranker.predict(pairs)

        # (점수, 문서) 쌍으로 묶은 뒤, 점수가 높은 순(내림차순)으로 정렬
        reranked_docs_with_scores = sorted(
            zip(scores, documents),
            key=lambda x: x[0],
            reverse=True
        )

        # 일정 점수(Threshold) 이상의 문서만 필터링합니다. (예: 0.5)
        # (이 Threshold는 Reranker 모델과 태스크에 따라 조정이 필요합니다.)
        threshold = 0.5
        final_documents = [
            doc for score, doc in reranked_docs_with_scores if score > threshold
        ]

        print(f"Rerank 완료: {len(documents)}개 -> {len(final_documents)}개 필터링됨 (Threshold: {threshold})")

        return {"documents": final_documents}

    except Exception as e:
        print(f"Rerank 중 오류 발생: {e}")
        return {"documents": []}  # 오류 시 빈 리스트 반환

# --- 5. 문서 검증 노드 (조건부 엣지용) ---
def edge_grade_documents(state: GraphState) -> Literal["generate_rag", "generate_normal"]:
    """
    Rerank 노드를 거친 후, 최종적으로 질문에 사용할 문서가 남아있는지 확인합니다.
    """
    print("--- 5. 문서 검증 엣지 (Rerank 후) ---")

    if state.get("documents"):
        print("검증: 관련성 높은 문서 있음 -> RAG 답변")
        return "generate_rag"
    else:
        print("검증: 관련성 높은 문서 없음 -> 일반 답변")
        return "generate_normal"


# --- 6. 답변 생성 노드 (RAG) ---

async def node_generate_rag_answer(state: GraphState):  # 'async def'로 변경
    """문서(Context)와 채팅 이력을 바탕으로 최종 답변을 스트리밍 생성합니다."""
    print("--- 6a. RAG 답변 생성 노드 ---")

    # ... (기존 system_prompt 및 context 포맷팅 코드) ...
    system_prompt = """
    당신은 대학 입시 요강 전문 어시스턴트입니다.
    당신은 오직 제공된 '참고 문서'의 내용을 기반으로만 답변해야 합니다.
    사용자의 질문에 대해 모집 요강의 내용을 근거로 명확하고 친절하게 답변해주세요.

    만약 '참고 문서'에 질문에 대한 답변을 찾을 수 없다면, "업로드된 모집 요강 문서에서 관련 정보를 찾을 수 없습니다."라고 솔직하게 답변해야 합니다.
    절대로 당신의 기존 지식이나 문맥에 없는 정보를 지어내서 답변하면 안 됩니다.
    """

    # RAG Context 포맷팅
    context = "--- 참고 문서 시작 ---\n"
    if state.get("documents"):
        for i, doc in enumerate(state["documents"]):
            source = doc.metadata.get("source", "알 수 없음")
            content = doc.page_content
            context += f"[문서 {i + 1} (출처: {source})]\n{content}\n\n"
    context += "--- 참고 문서 끝 ---"

    # LLM에 전달할 메시지 재구성
    messages = [
        SystemMessage(content=system_prompt),
        SystemMessage(content=context),  # RAG Context 주입
    ]
    # 채팅 이력 추가
    messages.extend(state["messages"])

    llm = get_llm()

    # .astream()을 호출하여 청크 스트림을 생성
    stream = llm.astream(messages)

    # --- 수정된 부분: 스트림을 'return'하는 대신 'yield'합니다 ---
    full_response = ""
    async for chunk in stream:
        if chunk.content:
            full_response += chunk.content
            # 각 청크를 'answer' 키를 가진 dict로 yield하여 스트리밍
            yield {"answer": chunk.content}

    # 마지막으로 전체 응답을 'answer' 키로 yield하여 상태를 최종 업데이트
    # (LangGraph v0.3+ 에서는 마지막 yield가 최종 상태 업데이트로 간주됨)
    yield {"answer": full_response}
    # --- 수정 완료 ---


# --- 6. 답변 생성 노드 (일반) ---

async def node_generate_normal_answer(state: GraphState):  # 'async def'로 변경
    """문서 없이 채팅 이력만으로 일반 답변(잡담 또는 정보 없음)을 스트리밍 생성합니다."""
    print("--- 6b. 일반 답변 생성 노드 ---")

    # ... (기존 system_prompt 코드) ...
    system_prompt = """
    당신은 친절한 AI 어시스턴트입니다. 
    사용자와 자유롭게 대화하세요. 
    만약 사용자가 입시 정보를 물었지만 관련 문서를 찾지 못한 상황이라면, 
    "업로드된 모집 요강 문서에서는 해당 정보를 찾을 수 없었습니다. 다른 질문이 있으신가요?"라고 답변해주세요.
    """

    messages = [SystemMessage(content=system_prompt)]
    messages.extend(state["messages"])  # 채팅 이력만 추가

    llm = get_llm()
    stream = llm.astream(messages)

    # --- 수정된 부분: 스트림을 'return'하는 대신 'yield'합니다 ---
    full_response = ""
    async for chunk in stream:
        if chunk.content:
            full_response += chunk.content
            # 각 청크를 'answer' 키를 가진 dict로 yield하여 스트리밍
            yield {"answer": chunk.content}

    # 마지막으로 전체 응답을 'answer' 키로 yield하여 상태를 최종 업데이트
    yield {"answer": full_response}
    # --- 수정 완료 ---