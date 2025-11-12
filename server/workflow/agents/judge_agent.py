from workflow.agents.agent import Agent
from workflow.state import AgentType
from typing import Dict, Any


class JudgeAgent(Agent):

    def __init__(self, k: int = 2, session_id: str = None):
        super().__init__(
            system_prompt="당신은 공정하고 논리적인 토론 심판입니다. 양측의 주장을 면밀히 검토하고 객관적으로 평가해주세요.",
            role=AgentType.JUDGE,
            k=k,
            session_id=session_id,
        )

    def _create_prompt(self, state: Dict[str, Any]) -> str:

        debate_summary = self._build_debate_summary(state)

        return f"""
            다음은 '{state['topic']}'에 대한 찬반 토론입니다. 각 측의 주장을 분석하고 평가해주세요.
            
            다음은 이 주제와 관련된 객관적인 정보입니다:
                {state.get("context", "")}
                
            토론 내용:
            {debate_summary}
            
            위 토론을 분석하여 다음을 포함하는 심사 평가를 해주세요:
            1. 양측 주장의 핵심 요약
            2. 각 측이 사용한 주요 논리와 증거의 강점과 약점
            3. 전체 토론의 승자와 그 이유
            4. 양측 모두에게 개선점 제안
            
            최대 500자 이내로 작성해주세요.
            """

    def _build_debate_summary(self, state: Dict[str, Any]) -> str:

        summary = ""

        # 모든 메시지 순회
        for message in state["messages"]:
            role = message["role"]
            content = message["content"]

            # 역할에 따른 표시 이름
            role_name = (
                AgentType.to_korean(role) if hasattr(AgentType, "to_korean") else role
            )

            # 요약에 메시지 추가
            summary += f"\n\n{role_name}: {content}"

        return summary
