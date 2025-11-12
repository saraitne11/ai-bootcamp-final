from workflow.agents.con_agent import ConAgent
from workflow.agents.judge_agent import JudgeAgent
from workflow.agents.pro_agent import ProAgent
from workflow.agents.round_manager import RoundManager
from workflow.state import DebateState, AgentType
from langgraph.graph import StateGraph, END


def create_debate_graph(enable_rag: bool = True, session_id: str = ""):

    # 그래프 생성
    workflow = StateGraph(DebateState)

    # 에이전트 인스턴스 생성 - enable_rag에 따라 검색 문서 수 결정
    k_value = 2 if enable_rag else 0
    pro_agent = ProAgent(k=k_value, session_id=session_id)
    con_agent = ConAgent(k=k_value, session_id=session_id)
    judge_agent = JudgeAgent(k=k_value, session_id=session_id)
    round_manager = RoundManager()

    # 노드 추가
    workflow.add_node(AgentType.PRO, pro_agent.run)
    workflow.add_node(AgentType.CON, con_agent.run)
    workflow.add_node(AgentType.JUDGE, judge_agent.run)
    workflow.add_node("INCREMENT_ROUND", round_manager.run)
    workflow.add_edge(AgentType.PRO, AgentType.CON)  # 찬성 → 조건부 라우팅
    workflow.add_edge(AgentType.CON, "INCREMENT_ROUND")  # 반대 → 조건부 라우팅

    workflow.add_conditional_edges(
        "INCREMENT_ROUND",
        lambda s: (
            AgentType.JUDGE if s["current_round"] > s["max_rounds"] else AgentType.PRO
        ),
        [AgentType.JUDGE, AgentType.PRO],
    )

    workflow.set_entry_point(AgentType.PRO)
    workflow.add_edge(AgentType.JUDGE, END)

    # 그래프 컴파일
    return workflow.compile()


if __name__ == "__main__":

    graph = create_debate_graph(True)

    print(graph.get_graph().draw_ascii())
    # graph_image = graph.get_graph().draw_mermaid_png()
    #
    # output_path = "debate_graph.png"
    # with open(output_path, "wb") as f:
    #     f.write(graph_image)
    #
    # import subprocess
    #
    # subprocess.run(["open", output_path])
