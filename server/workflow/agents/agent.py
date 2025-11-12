from langchain.schema import HumanMessage, SystemMessage, AIMessage
from retrieval.vector_store import search_topic
from utils.config import get_llm
from workflow.state import DebateState, AgentType
from abc import ABC, abstractmethod
from typing import List, Dict, Any, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, END
from langfuse.langchain import CallbackHandler

from utils.config import settings


# 에이전트 내부 상태 타입 정의
class AgentState(TypedDict):

    debate_state: Dict[str, Any]  # 전체 토론 상태
    context: str  # 검색된 컨텍스트
    messages: List[BaseMessage]  # LLM에 전달할 메시지
    response: str  # LLM 응답


# 에이전트 추상 클래스 정의
class Agent(ABC):

    #
    def __init__(
        self, system_prompt: str, role: str, k: int = 2, session_id: str = None
    ):
        self.system_prompt = system_prompt
        self.role = role
        self.k = k  # 검색할 문서 개수
        self._setup_graph()  # 그래프 설정
        self.session_id = session_id  # langfuse 세션 ID

    def _setup_graph(self):
        # 그래프 생성
        workflow = StateGraph(AgentState)

        # 노드 추가
        workflow.add_node("retrieve_context", self._retrieve_context)  # 자료 검색
        workflow.add_node("prepare_messages", self._prepare_messages)  # 메시지 준비
        workflow.add_node("generate_response", self._generate_response)  # 응답 생성
        workflow.add_node("update_state", self._update_state)  # 상태 업데이트

        # 엣지 추가 - 순차 실행 흐름
        workflow.add_edge("retrieve_context", "prepare_messages")
        workflow.add_edge("prepare_messages", "generate_response")
        workflow.add_edge("generate_response", "update_state")

        workflow.set_entry_point("retrieve_context")
        workflow.add_edge("update_state", END)

        # 그래프 컴파일
        self.graph = workflow.compile()

    # 자료 검색
    def _retrieve_context(self, state: AgentState) -> AgentState:

        # k=0이면 검색 비활성화
        if self.k <= 0:
            return {**state, "context": ""}

        debate_state = state["debate_state"]
        topic = debate_state["topic"]

        # 검색 쿼리 생성
        query = topic
        if self.role == AgentType.PRO:
            query += " 찬성 장점 이유 근거"
        elif self.role == AgentType.CON:
            query += " 반대 단점 이유 근거"
        elif self.role == AgentType.JUDGE:
            query += " 평가 기준 객관적 사실"

        # RAG 서비스를 통해 검색 실행
        docs = search_topic(topic, self.role, query, k=self.k)  # noqa: F821

        debate_state["docs"][self.role] = (
            [doc.page_content for doc in docs] if docs else []
        )

        # 컨텍스트 포맷팅
        context = self._format_context(docs)

        # 상태 업데이트
        return {**state, "context": context}

    # 검색 결과로 Context 생성
    def _format_context(self, docs: list) -> str:

        context = ""
        for i, doc in enumerate(docs):
            source = doc.metadata.get("source", "Unknown")
            section = doc.metadata.get("section", "")
            context += f"[문서 {i + 1}] 출처: {source}"
            if section:
                context += f", 섹션: {section}"
            context += f"\n{doc.page_content}\n\n"
        return context

    # 프롬프트 메시지 준비
    def _prepare_messages(self, state: AgentState) -> AgentState:

        debate_state = state["debate_state"]
        context = state["context"]

        # 시스템 프롬프트로 시작
        messages = [SystemMessage(content=self.system_prompt)]

        # 기존 대화 기록 추가
        for message in debate_state["messages"]:
            if message["role"] == "assistant":
                messages.append(AIMessage(content=message["content"]))
            else:
                messages.append(
                    HumanMessage(content=f"{message['role']}: {message['content']}")
                )

        # 프롬프트 생성 (검색된 컨텍스트 포함)
        prompt = self._create_prompt({**debate_state, "context": context})
        messages.append(HumanMessage(content=prompt))

        # 상태 업데이트
        return {**state, "messages": messages}

    # 프롬프트 생성 - 하위 클래스에서 구현 필요
    @abstractmethod
    def _create_prompt(self, state: Dict[str, Any]) -> str:
        pass

    # LLM 호출
    def _generate_response(self, state: AgentState) -> AgentState:

        messages = state["messages"]
        response = get_llm().invoke(messages)

        return {**state, "response": response.content}

    # 상태 업데이트
    def _update_state(self, state: AgentState) -> AgentState:
        debate_state = state["debate_state"]
        response = state["response"]
        current_round = debate_state["current_round"]

        # 토론 상태 복사 및 업데이트
        new_debate_state = debate_state.copy()

        # 에이전트 응답 추가
        new_debate_state["messages"].append(
            {"role": self.role, "content": response, "current_round": current_round}
        )

        # 이전 노드 정보 업데이트
        new_debate_state["prev_node"] = self.role

        # 상태 업데이트
        return {**state, "debate_state": new_debate_state}

    # 토론 실행
    def run(self, state: DebateState) -> DebateState:

        # 초기 에이전트 상태 구성
        agent_state = AgentState(
            debate_state=state, context="", messages=[], response=""
        )

        # 내부 그래프 실행
        config = {}
        if settings.LANGFUSE:
            langfuse_handler = CallbackHandler()
            config["callbacks"] = [langfuse_handler]

        result = self.graph.invoke(agent_state, config=config)

        # 최종 토론 상태 반환
        return result["debate_state"]
