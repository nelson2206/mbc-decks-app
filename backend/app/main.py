"""FastAPI application entry point."""
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect

from app.core.config import settings
from app.db.session import engine
from app.db.models import Base
from app.db.migrations import run_migrations
from app.api.endpoints import auth, decks, interview, generate, audit, credentials


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend MBC Decks · generación de presentaciones MBC con sistema multi-agente y auditoría visual.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def init_db():
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            Base.metadata.create_all(bind=engine)
        run_migrations(engine)

    @app.get("/health", tags=["health"])
    def health():
        return {"status": "ok", "app": settings.app_name, "version": settings.app_version}

    app.include_router(auth.router)
    app.include_router(decks.router)
    app.include_router(interview.router)
    app.include_router(generate.router)
    app.include_router(audit.router)
    app.include_router(credentials.router)

    return app


app = create_app()
