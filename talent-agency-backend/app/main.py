import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import settings
from app.routers import manual, webhooks


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)
    logger.info("Talent Agency Automation API starting up on port %s", settings.PORT)
    yield
    logger.info("Talent Agency Automation API shutting down")


app = FastAPI(
    title="Talent Agency Automation API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(webhooks.router, prefix="/webhooks")
app.include_router(manual.router, prefix="/manual")


@app.get("/")
async def root() -> dict:
    return {
        "status": "ok",
        "service": "talent-agency-automation",
        "version": "1.0.0",
    }
