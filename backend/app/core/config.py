from pydantic_settings import BaseSettings #type:ignore


class Settings(BaseSettings):
    PROJECT_NAME: str = "Sentinel-AI"
    SECRET_KEY: str = "SUPER_SECRET_LOCAL_KEY_CHANGE_IN_PRODUCTION"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 hours

    class Config:
        env_file = ".env"


settings = Settings()