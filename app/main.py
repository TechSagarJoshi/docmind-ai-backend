from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import routes_pdf, routes_files, routes_convert, routes_profile

app = FastAPI(title="DocMind AI API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_pdf.router)
app.include_router(routes_files.router)
app.include_router(routes_convert.router)
app.include_router(routes_profile.router)   # ← MUST come AFTER app = FastAPI(...)


@app.get("/")
def health():
    return {"status": "ok", "service": "DocMind AI"}