from typing import Any
import uuid
import json
import asyncio
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langfuse.langchain import CallbackHandler

from workflow.state import AgentType, DebateState
from workflow.graph import create_debate_graph

from utils.config import settings


# API 경로를 /api/v1로 변경
router = APIRouter(
    prefix="/api/v1/workflow",
    tags=["workflow"],
    responses={404: {"description": "Not found"}},
)


class WorkflowRequest(BaseModel):
    topic: str
    max_rounds: int = 3
    enable_rag: bool = True


class WorkflowResponse(BaseModel):
    status: str = "success"
    result: Any = None


async def debate_generator(debate_graph, initial_state, config):
    # 그래프에서 청크 스트리밍

    for chunk in debate_graph.stream(
        initial_state,
        # config={"callbacks": [langfuse_handler]},
        config=config,
        subgraphs=True,
        stream_mode="updates",
    ):
        if not chunk:
            continue

        node = chunk[0] if len(chunk) > 0 else None
        if not node or node == ():
            continue

        node_name = node[0]
        role = node_name.split(":")[0]
        subgraph = chunk[1]
        subgraph_node = subgraph.get("update_state", None)

        if subgraph_node:
            response = subgraph_node.get("response", None)
            debate_state = subgraph_node.get("debate_state", None)
            messages = debate_state.get("messages", [])
            round = debate_state.get("current_round")
            max_rounds = debate_state.get("max_rounds")
            docs = debate_state.get("docs", {})
            topic = debate_state.get("topic")

            state = {
                "role": role,
                "response": response,
                "topic": topic,
                "messages": messages,
                "current_round": round,
                "max_rounds": max_rounds,
                "docs": docs,
            }

            event_data = {"type": "update", "data": state}
            yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
            print(event_data)

            await asyncio.sleep(0.01)

    # 디베이트 종료 메시지
    yield f"data: {json.dumps({'type': 'end', 'data': {}}, ensure_ascii=False)}\n\n"


# 엔드포인트 경로 수정 (/debate/stream -> 유지)
@router.post("/debate/stream")
async def stream_debate_workflow(request: WorkflowRequest):
    topic = request.topic
    max_rounds = request.max_rounds
    enable_rag = request.enable_rag

    session_id = str(uuid.uuid4())
    debate_graph = create_debate_graph(enable_rag, session_id)

    initial_state: DebateState = {
        "topic": topic,
        "messages": [],
        "current_round": 1,
        "max_rounds": max_rounds,
        "prev_node": "START",  # 이전 노드 START로 설정
        "docs": {},  # RAG 결과 저장
    }

    config = {}
    if settings.LANGFUSE:
        langfuse_handler = CallbackHandler()
        config["callbacks"] = [langfuse_handler]

    # 스트리밍 응답 반환
    return StreamingResponse(
        debate_generator(debate_graph, initial_state, config),
        media_type="text/event-stream",
    )
