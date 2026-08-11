"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.services.database import initialize_database


def create_app() -> FastAPI:
    initialize_database()
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Backend API for the Enterprise RAG Knowledge Assistant.",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(api_router, prefix=settings.api_prefix)

    @application.get("/", tags=["System"], include_in_schema=False)
    async def root() -> dict[str, str]:
        return {"message": settings.app_name, "docs": "/docs"}

    return application


app = create_app()
