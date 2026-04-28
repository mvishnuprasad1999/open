from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    DB_CONNECTION: str
    SECRET_KEY:str
    ALGORITHM:str
    CLOUDINARY_API_KEY_SECRET:str
    CLOUDINARY_NAME:str
    CLOUDINARY_APIKEY:str



setup = Settings()

