import streamlit as st
from langchain.schema import Document
from typing import List, Literal
from duckduckgo_search import DDGS
from langchain.schema import HumanMessage, SystemMessage
from utils.config import get_llm


def improve_search_query(
    topic: str,
    role: Literal["PRO_AGENT", "CON_AGENT", "JUDGE_AGENT"] = "JUDGE_AGENT",
) -> List[str]:

    template = "'{topic}'에 대해 {perspective} 웹검색에 적합한 3개의 검색어를 제안해주세요. 각 검색어는 25자 이내로 작성하고 콤마로 구분하세요. 검색어만 제공하고 설명은 하지 마세요."

    perspective_map = {
        "PRO_AGENT": "찬성하는 입장을 뒷받침할 수 있는 사실과 정보를 찾고자 합니다.",
        "CON_AGENT": "반대하는 입장을 뒷받침할 수 있는 사실과 정보를 찾고자 합니다.",
        "JUDGE_AGENT": "객관적인 사실과 정보를 찾고자 합니다.",
    }

    prompt = template.format(topic=topic, perspective=perspective_map[role])

    messages = [
        SystemMessage(
            content="당신은 검색 전문가입니다. 주어진 주제에 대해 가장 관련성 높은 검색어를 제안해주세요."
        ),
        HumanMessage(content=prompt),
    ]

    # 스트리밍 응답 받기
    response = get_llm().invoke(messages)

    # ,로 구분된 검색어 추출
    suggested_queries = [q.strip() for q in response.content.split(",")]

    return suggested_queries[:3]


def get_search_content(
    improved_queries: str,
    language: str = "ko",
    max_results: int = 5,
) -> List[Document]:

    try:
        documents = []

        ddgs = DDGS()

        # 각 개선된 검색어에 대해 검색 수행
        for query in improved_queries:
            try:
                # 검색 수행
                results = ddgs.text(
                    query,
                    region=language,
                    safesearch="moderate",
                    timelimit="y",  # 최근 1년 내 결과
                    max_results=max_results,
                )

                if not results:
                    continue

                # 검색 결과 처리
                for result in results:
                    title = result.get("title", "")
                    body = result.get("body", "")
                    url = result.get("href", "")

                    if body:
                        documents.append(
                            Document(
                                page_content=body,
                                metadata={
                                    "source": url,
                                    "section": "content",
                                    "topic": title,
                                    "query": query,
                                },
                            )
                        )

            except Exception as e:
                st.warning(f"검색 중 오류 발생: {str(e)}")

        return documents

    except Exception as e:
        st.error(f"검색 서비스 오류 발생: {str(e)}")
        return []
