from pydantic_settings import BaseSettings, SettingsConfigDict
class Settings(BaseSettings):
    app_name: str = "MRA API"
    app_version: str = "0.6.0"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://mra:mra_dev_password@postgres:5432/mra"
    cors_origins: str = "http://localhost:5173"
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]
settings = Settings()
