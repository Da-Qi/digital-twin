from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://dtadmin:dtpassword@localhost:5432/digitaltwin"
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    embedding_model: str = "BAAI/bge-large-en-v1.5"
    cors_origins: list[str] = ["http://localhost:3000"]
    max_upload_size_mb: int = 50
    chunk_size: int = 800
    chunk_overlap: int = 100
    retriever_top_k: int = 8
    memory_top_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
