from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PIPEDRIVE_API_TOKEN: str
    PIPEDRIVE_PIPELINE_ID: int = 2
    PIPEDRIVE_STAGE_CONTRATO_ID: int = 9

    TRELLO_API_KEY: str
    TRELLO_TOKEN: str
    TRELLO_WORKSPACE_NAME: str = "Talent Agency"
    TRELLO_ORG_ID: str = ""

    ANTHROPIC_API_KEY: str

    WEBHOOK_SECRET: str = ""
    PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
