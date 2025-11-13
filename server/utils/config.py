import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from sentence_transformers import CrossEncoder

# .env 파일에서 환경 변수 로드
load_dotenv()


class Settings(BaseSettings):
    # Azure OpenAI 설정
    AOAI_API_KEY: str
    AOAI_ENDPOINT: str
    AOAI_DEPLOY_GPT4O: str
    AOAI_DEPLOY_EMBED_3_LARGE: str
    AOAI_API_VERSION: str

    # Langfuse 설정
    LANGFUSE: bool
    LANGFUSE_PUBLIC_KEY: str
    LANGFUSE_SECRET_KEY: str
    LANGFUSE_BASE_URL: str

    API_BASE_URL: str
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Debate Arena API"

    # CORS 설정
    BACKEND_CORS_ORIGINS: list[str] = ["*"]

    # SQLite 데이터베이스 설정
    DB_PATH: str = "history.db"
    SQLALCHEMY_DATABASE_URI: str = f"sqlite:///./{DB_PATH}"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)

    def get_reranker(self):
        # RAG Reranking에 널리 사용되는 경량 모델
        model_name = 'local_models/ms-marco-reranker'
        return CrossEncoder(model_name)

    def get_llm(self):
        """Azure OpenAI LLM 인스턴스를 반환합니다."""
        return AzureChatOpenAI(
            openai_api_key=self.AOAI_API_KEY,
            azure_endpoint=self.AOAI_ENDPOINT,
            azure_deployment=self.AOAI_DEPLOY_GPT4O,
            api_version=self.AOAI_API_VERSION,
            temperature=0.7,
            streaming=True,  # 스트리밍 활성화
        )

    def get_embeddings(self):
        """Azure OpenAI Embeddings 인스턴스를 반환합니다."""
        return AzureOpenAIEmbeddings(
            model=self.AOAI_DEPLOY_EMBED_3_LARGE,
            openai_api_version=self.AOAI_API_VERSION,
            api_key=self.AOAI_API_KEY,
            azure_endpoint=self.AOAI_ENDPOINT,
        )



# 설정 인스턴스 생성
settings = Settings()


# 편의를 위한 함수들, 하위 호환성을 위해 유지
def get_llm():
    return settings.get_llm()


def get_embeddings():
    return settings.get_embeddings()

def get_reranker():
    return settings.get_reranker()


if __name__ == "__main__":
    print(settings)