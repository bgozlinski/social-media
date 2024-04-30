import logging
from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks
from src.models.user import UserIn
from src.database import database, user_table
from src.security import (
    get_user,
    get_password_hash,
    authenticate_user,
    create_access_token,
    get_subject_for_token_type,
    create_confirmation_token
)

from src import tasks

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(
        user: UserIn,
        background_tasks: BackgroundTasks,
        request: Request
):
    """
    Registers a new user and sends a confirmation email.

    This function creates a new user with the given email and hashed password in the database.
    If the email is already registered, it raises an HTTP exception. After registering,
    it enqueues a background task to send a registration confirmation email.

    Args:
        user (UserIn): The user input model containing the email and password.
        background_tasks (BackgroundTasks): Background tasks manager for asynchronous job execution.
        request (Request): The request object.

    Returns:
        dict: A success message indicating that the user was created and an email confirmation was sent.
    """
    if await get_user(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered'
        )

    hashed_password = get_password_hash(user.password)

    query = user_table.insert().values(
        email=user.email,
        password=hashed_password
    )

    logger.debug(query)

    await database.execute(query)
    background_tasks.add_task(
        tasks.send_user_registration_email,
        user.email,
        confirmation_url=request.url_for(
            "confirm_email", token=create_confirmation_token(user.email)
        ),
    )
    return {
        "detail": "User created successfully. Please confirm your email."
    }


@router.post('/token')
async def login(user: UserIn):
    """
    Authenticates a user and returns an access token.

    This function verifies the user's email and password. If authentication is successful,
    it generates and returns an access token.

    Args:
        user (UserIn): The user input model containing the email and password.

    Returns:
        dict: A dictionary containing the bearer access token and token type.
    """
    user = await authenticate_user(user.email, user.password)
    access_token = create_access_token(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }


@router.get('/confirm/{token}')
async def confirm_email(token: str):
    """
    Confirms a user's email based on a provided confirmation token.

    This function updates the user's status in the database to confirmed if the provided token is valid.
    It raises an HTTP exception if the token is invalid or expired.

    Args:
        token (str): The confirmation token sent to the user's email.

    Returns:
        dict: A message indicating the user's email confirmation status.
    """
    email = get_subject_for_token_type(token=token, type="confirmation")
    query = (
        user_table.update().where(user_table.c.email == email).values(confirmed=True)
    )

    logger.debug(query)

    await database.execute(query)
    return {
        "detail": "User confirmed"
    }
