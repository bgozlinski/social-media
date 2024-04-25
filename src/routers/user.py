import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, status, Form, Depends
from fastapi.security import OAuth2PasswordRequestForm
from src.models.user import UserIn
from src.security import get_user, get_password_hash, authenticate_user, create_access_token
from src.database import database, user_table


logger = logging.getLogger(__name__)

router = APIRouter()


@router.post('/register', status_code=status.HTTP_201_CREATED)
async def register(user: UserIn):
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
    return {
        "detail": "User registered successfully"
    }


@router.post('/token')
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm, Depends()]
):
    user = await authenticate_user(form_data.username, form_data.password)
    access_token = create_access_token(user.email)

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
