from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import Base, engine
from app.routers.knowledge import router as knowledge_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.3.1",
    description="API principale della piattaforma MRA Studio.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(knowledge_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "message": "MRA API",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": "0.3.1",
    }


@app.get("/version", tags=["system"])
def version() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "0.3.1",
        "environment": settings.app_env,
    }
