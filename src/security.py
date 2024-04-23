import logging
import datetime
from typing import Optional

from fastapi import HTTPException, status

from jose import jwt

from src.database import database, user_table
from passlib.context import CryptContext

from src.config import config

# Configure logger for the current module
logger = logging.getLogger(__name__)

# Create a password context for hashing passwords using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"])


credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def access_token_expire_minutes() -> int:
    return 30


def create_access_token(email: str) -> str:
    logger.debug(f"Creating access token for {email}")

    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=access_token_expire_minutes())

    jwt_data = {
        "sub": email,
        "exp": expire,
    }

    encoded_jwt = jwt.encode(claims=jwt_data,
                             key=config.SECRET_KEY,
                             algorithm=config.ALGORITHM
                             )
    return encoded_jwt


def get_password_hash(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password (str): The plaintext password to hash.

    Returns:
        str: The hashed password.
    """
    return pwd_context.hash(password)


def verify_password(plain_pwd: str, hashed_pwd: str) -> bool:
    """
    Verify a plaintext password against a hashed password.

    Args:
        plain_pwd (str): The plaintext password to verify.
        hashed_pwd (str): The hashed password to verify against.

    Returns:
        bool: True if the password matches, otherwise False.
    """
    return pwd_context.verify(plain_pwd, hashed_pwd)


async def get_user(email: str) -> Optional[dict]:
    """
    Asynchronously retrieve a user's record from the database by their email address.

    This function fetches a single user entry from the database. It logs the operation and
    uses an SQL query to look up the user by their email. The function returns the user's
    record as a dictionary if found, otherwise it returns None.

    Args:
        email (str): The email address of the user to be retrieved.

    Returns:
        dict | None: A dictionary containing user data if the user is found, otherwise None.

    """
    logger.debug(f"Getting user {email}")

    query = user_table.select().where(user_table.c.email == email)
    result = await database.fetch_one(query)

    if result:
        return result


async def authenticate_user(email: str, password: str) -> dict:
    logger.debug(f"Authenticating user {email}")
    user = await get_user(email)

    if not user:
        raise credentials_exception
    if not verify_password(password, user.password):
        raise credentials_exception

    return user


async def get_current_user(token: str) -> Optional[dict]:

    try:
        payload = jwt.decode(token=token, key=config.SECRET_KEY, algorithms=[config.ALGORITHM])
        email = payload.get("sub")

        if email is None:
            raise credentials_exception

    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.JWTError as e:
        raise credentials_exception from e

    user = await get_user(email=email)

    if user is None:
        raise credentials_exception
    return user
