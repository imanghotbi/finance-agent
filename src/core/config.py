from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import SecretStr
from typing import Optional , Dict



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
    mongo_collection_name: str = 'market_analysis'

    #log info
    log_level:str = "INFO"
    log_file_path:str = "logs/app.log"
    log_max_bytes:int = 30 * 1024 * 1024 #30 MB
    log_backup_count:int = 5

    #crawl info
    default_headers:Dict[str,str] = {'sec-ch-ua-mobile': '?0','sec-fetch-dest': 'empty','sec-fetch-mode': 'cors','sec-fetch-site': 'same-origin','user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'}
    rahavard_base_url:str = "https://rahavard365.com/api/v2/"
    sahamyab_base_url:str = "https://www.sahamyab.com/"
    rapid_api_key:SecretStr
    rapid_api_host:str = "twitter154.p.rapidapi.com"
    rapid_base_url:str = "https://twitter154.p.rapidapi.com/search/"
    proxy_url:str
    tavily_base_url:str = "https://api.tavily.com/"
    tavily_api_key:SecretStr

    #model config
    model_name:str = 'deepseek-ai/deepseek-v3.1-terminus'
    model_api_key:SecretStr
    max_tokens:Optional[int] = 20000
    top_p:float = 0.0

    @property
    def mongo_uri(self):
        if self.mongo_username is None or self.mongo_password.get_secret_value() is None:
            return f"mongodb://{self.mongo_endpoint}"
        encoded_password = quote_plus(self.mongo_password.get_secret_value())
        return f"mongodb://{self.mongo_username}:{encoded_password}@{self.mongo_endpoint}"


settings = Settings()