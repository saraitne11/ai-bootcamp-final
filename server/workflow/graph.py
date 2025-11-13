from functools import partial
from langgraph.graph import StateGraph, END

from workflow.state import GraphState
from workflow.nodes import node_classify_intent, node_transform_query, node_retrieve_documents, edge_grade_documents, node_generate_rag_answer, node_generate_normal_answer


def build_graph(vector_store: any):
    """
    LangGraph 워크플로우를 구축하고 컴파일합니다.
    Vector Store를 인자로 받아 node_retrieve_documents에 바인딩합니다.
    """

    workflow = StateGraph(GraphState)

    # --- 1. 노드 정의 ---
    workflow.add_node("classify_intent", node_classify_intent)
    workflow.add_node("transform_query", node_transform_query)

    # node_retrieve_documents는 vector_store 인자가 필요하므로 partial로 바인딩
    retrieve_partial = partial(node_retrieve_documents, vector_store=vector_store)
    workflow.add_node("retrieve_documents", retrieve_partial)

    # 답변 생성 노드들은 스트리밍을 위해 .astream()을 반환합니다.
    workflow.add_node("generate_rag_answer", node_generate_rag_answer)
    workflow.add_node("generate_normal_answer", node_generate_normal_answer)

    # --- 2. 엣지(흐름) 정의 ---

    # 2-1. 시작점
    workflow.set_entry_point("classify_intent")

    # 2-2. 의도 분류 분기
    workflow.add_conditional_edges(
        "classify_intent",
        lambda state: state.get("intent"),  # state의 'intent' 값 확인
        {
            "admission_question": "transform_query",  # 입시 질문 -> 쿼리 변환
            "general_chat": "generate_normal_answer"  # 일반 잡담 -> 일반 답변
        }
    )

    # 2-3. RAG 경로
    workflow.add_edge("transform_query", "retrieve_documents")

    # 2-4. RAG 검증 분기
    workflow.add_conditional_edges(
        "retrieve_documents",
        edge_grade_documents,  # 검증 함수 실행
        {
            "generate_rag": "generate_rag_answer",  # 관련성 높음 -> RAG 답변
            "generate_normal": "generate_normal_answer"  # 관련성 낮음 -> 일반 답변
        }
    )

    # 2-5. 종료점
    workflow.add_edge("generate_rag_answer", END)
    workflow.add_edge("generate_normal_answer", END)

    # --- 3. 그래프 컴파일 ---
    print("LangGraph 컴파일 중...")
    app = workflow.compile()
    print("LangGraph 컴파일 완료.")
    return app


# --- FastAPI 앱에서 사용할 컴파일된 그래프 ---
# 이 부분은 FastAPI 서버 시작 시(main.py) 한번만 호출되어야 합니다.
# 하지만 현재 구조(app.state.vector_store)에서는
# vector_store가 로드된 후 그래프를 생성해야 합니다.
# 우선 빈 그래프(None)로 두고, main.py에서 초기화하도록 수정합니다.
compiled_graph = None


def get_compiled_graph(vector_store: any):
    """
    FastAPI 서버 시작 시 호출되어 컴파일된 그래프를 반환합니다.
    (Vector Store가 업데이트되면 다시 호출될 수 있도록 수정)
    """
    global compiled_graph
    print("컴파일된 LangGraph 인스턴스 생성/업데이트 중...")
    compiled_graph = build_graph(vector_store)
    return compiled_graph


def get_graph_app():
    """라우터에서 사용할 컴파일된 그래프 인스턴스를 반환합니다."""
    if compiled_graph is None:
        print("경고: 그래프가 아직 컴파일되지 않았습니다. (Vector Store 로딩 전일 수 있음)")
        # 임시로 빈 그래프라도 반환하거나 (이 경우 vector_store가 None)
        # 아니면 에러를 발생시켜야 하지만, 우선 로딩 중임을 가정
        return None
    return compiled_graph


if __name__ == "__main__":
    graph = get_compiled_graph(None)
    print(graph.get_graph().draw_ascii())
