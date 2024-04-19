import logging

from fastapi import APIRouter, HTTPException, status
from src.models.user import UserIn
from src.security import get_user, get_password_hash, verify_password
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
