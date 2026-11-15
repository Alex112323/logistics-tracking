from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    rabbitmq_url: str
    exchange_name: str = "tracking"
    queue_name: str = "events.raw"
    routing_key_status: str = "shipment.status_changed"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()