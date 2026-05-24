from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.capture import router as capture_router
from app.api.classify import router as classify_router
from app.api.demo import router as demo_router
from app.api.export import router as export_router
from app.api.health import router as health_router
from app.api.history import router as history_router
from app.api.parse import router as parse_router
from app.api.profiles import router as profiles_router

app = FastAPI(title="JOLT API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(profiles_router)
app.include_router(classify_router)
app.include_router(parse_router)
app.include_router(capture_router)
app.include_router(export_router)
app.include_router(history_router)
app.include_router(demo_router)
