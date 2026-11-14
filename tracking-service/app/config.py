from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://tracking:tracking_pass@tracking-db:5432/logistics"
    redis_url: str = "redis://tracking-cache:6379/0"  
    status_ttl_sec: int = 3600
    
    rabbitmq_url: str = "amqp://guest:guest@tracking-broker:5672/"
    exchange_name: str = "tracking"
    routing_key_status: str = "shipment.status_changed"           
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()