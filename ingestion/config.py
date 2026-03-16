from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    fetch_interval_seconds: int = 30
    coingecko_base_url: str = "https://api.coingecko.com/api/v3"
    finnhub_api_key: str = ""


settings = Settings()
