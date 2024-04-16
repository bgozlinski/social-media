import logging

from fastapi import FastAPI
from src.routers.post import router as post_router
from src.routers.user import router as user_router
from contextlib import asynccontextmanager
from src.database import database

from src.logging_conf import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Asynchronous context manager for managing the lifespan of the application.

    This context manager ensures that the database connection is established
    when the application starts and cleanly disconnected when the application
    stops. This is crucial for resources that need to be released properly
    to avoid resource leaking or other side effects.

    Args:
    app (FastAPI): An instance of the FastAPI application to which this lifespan
                   is tied.

    Yields:
    None: This context manager does not yield any value but ensures database
          connection management.
    """
    configure_logging()
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(post_router, prefix="")
app.include_router(user_router, prefix="")
