from fastapi import FastAPI
from routers.post import router as post_router
from contextlib import asynccontextmanager
from database import database


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
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)

app.include_router(post_router, prefix="")
