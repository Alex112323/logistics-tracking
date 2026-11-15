from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    rabbitmq_url: str
    exchange_name: str = "tracking"
    poll_interval_ms: int = 100
    batch_size: int = 100

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()