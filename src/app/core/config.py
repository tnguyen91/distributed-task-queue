from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Distributed Task Queue"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/taskqueue"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    secret_key: str = "CHANGE-ME-IN-PRODUCTION"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    class ConfigDict:
        env_file = ".env"


settings = Settings()