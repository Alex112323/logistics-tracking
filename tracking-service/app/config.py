from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://tracking:tracking_pass@tracking-db:5432/logistics"
    redis_url: str = "redis://tracking-cache:6379/0"  
    status_ttl_sec: int = 3600              
    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()