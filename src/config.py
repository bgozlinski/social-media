from typing import Optional
from pydantic_settings import SettingsConfigDict, BaseSettings
from functools import lru_cache


class BaseConfig(BaseSettings):
    ENV_STATE: Optional[str] = None
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class GlobalConfig(BaseConfig):
    DATABASE_URL: Optional[str] = None
    DB_FORCE_ROLL_BACK: bool = False
    SECRET_KEY: Optional[str] = None
    ALGORITHM: str = "HS256"
    MAILGUN_API_KEY: Optional[str] = None
    MAILGUN_DOMAIN: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    AWS_REGION: Optional[str] = None
    DEEPAI_API_KEY: Optional[str] = None


class DevConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="DEV_")


class ProdConfig(GlobalConfig):
    model_config = SettingsConfigDict(env_prefix="PROD_")


class TestConfig(GlobalConfig):
    DATABASE_URL: str = "sqlite:///test.db"
    DB_FORCE_ROLL_BACK: bool = True
    SECRET_KEY: str = "test"
    ALGORITHM: str = "HS256"

    model_config = SettingsConfigDict(env_prefix="TEST_")


@lru_cache()
def get_config(env_state: str):
    configs = {
        "dev": DevConfig,
        "prod": ProdConfig,
        "test": TestConfig
    }

    return configs[env_state]()


config = get_config(BaseConfig().ENV_STATE)
