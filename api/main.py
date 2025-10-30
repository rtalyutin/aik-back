from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from starlette.middleware.cors import CORSMiddleware
from dishka.integrations.fastapi import (
    setup_dishka,
)

from core import ioc
from core.handlers.handlers import core_register_api_handlers

from logger import setup_logging

from config import get_config
from application.job_matcher import http as job_matcher_http
from core.auth import auth_router

config = get_config()
setup_logging(config, service_name="api")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    logger.info("Starting application")
    yield
    logger.info("Stopping application")


app = FastAPI(
    lifespan=lifespan,
)

core_register_api_handlers(app)

container = ioc.make_ioc(with_fast_api=True)
setup_dishka(container=container, app=app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(job_matcher_http.job_matcher_resume_router, prefix="/api")
app.include_router(job_matcher_http.job_matcher_statistic_router, prefix="/api")
app.include_router(job_matcher_http.job_matcher_vacancy_router, prefix="/api")
