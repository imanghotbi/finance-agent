from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional



class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore',
        env_ignore_empty=True 
    )
    
    # mongo endpoint
    mongo_endpoint:str
    mongo_db_name:str
    mongo_username: Optional[str] = None
    mongo_password: Optional[SecretStr] = None

    #log info
    log_level:str = "INFO"
    log_file_path:str = "logs/app.log"
    log_max_bytes:int = 30 * 1024 * 1024 #30 MB
    log_backup_count:int = 5

    @property
    def mongo_uri(self):
        if self.mongo_username is None or self.mongo_password.get_secret_value() is None:
            return f"mongodb://{self.mongo_endpoint}"
        encoded_password = quote_plus(self.mongo_password.get_secret_value())
        return f"mongodb://{self.mongo_username}:{encoded_password}@{self.mongo_endpoint}"


settings = Settings()