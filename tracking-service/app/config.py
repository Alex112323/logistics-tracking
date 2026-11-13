from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://tracking:tracking_pass@tracking-db:5432/logistics"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()