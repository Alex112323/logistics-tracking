from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    redis_url: str
    rabbitmq_url: str
    status_ttl_sec: int = 86400
    exchange_name: str = "tracking"
    routing_key_status: str = "shipment.status_changed"
    jwt_secret_key: str
    admin_username: str
    admin_password: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()