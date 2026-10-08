from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_BUCKET: str = "uploads"
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    POPPLER_PATH: str = ""
    SOFFICE_PATH: str = r"C:\Program Files\LibreOffice\program\soffice.exe"
    OPENAI_API_KEY: str = ""
    TESSERACT_PATH: str = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    class Config:
        env_file = ".env"


settings = Settings()