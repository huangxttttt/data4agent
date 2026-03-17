from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "url4sub"
    app_version: str = "0.1.0"
    api_v1_prefix: str = "/api/v1"
    llm_base_url: str = "https://api.deepseek.com/v1"
    llm_api_key: str = "sk-c126f08be9674fb88dec2eb6929d5756"
    llm_model: str = "deepseek-chat"
    llm_chunk_max_chars: int = 8000
    llm_chunk_concurrency: int = 3
    llm_total_max_chars: int = 100000
    llm_request_retries: int = 2
    llm_retry_backoff_seconds: float = 1.0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
