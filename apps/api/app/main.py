from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routes.admin import router as admin_router
from app.routes.auth import router as auth_router
from app.routes.chat import router as chat_router
from app.routes.health import router as health_router
from app.routes.journal import router as journal_router
from app.routes.me import router as me_router
from app.routes.rag import router as rag_router

app = FastAPI(
    title=settings.app_name,
    description="Evidence-grounded, spiritually informed AI guidance service.",
    version="0.1.0",
    debug=settings.debug,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(rag_router)
app.include_router(journal_router)
app.include_router(admin_router)
app.include_router(me_router)
