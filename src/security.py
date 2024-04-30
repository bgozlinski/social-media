import logging
import datetime
from typing import Optional, Annotated, Literal

from fastapi import HTTPException, status, Depends
from fastapi.security import OAuth2PasswordBearer

from jose import jwt

from src.database import database, user_table
from passlib.context import CryptContext

from src.config import config

# Configure logger for the current module
logger = logging.getLogger(__name__)

# Create a password context for hashing passwords using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def create_credentials_exception(detail: str) -> HTTPException:
    """
    Create a standardized HTTP exception for credential issues.

    This function constructs an HTTP exception specifically for authentication failures, including
    the setting of WWW-Authenticate headers.

    Args:
        detail (str): A message detailing the reason for the exception.

    Returns:
        HTTPException: The constructed HTTP exception with a 401 status code.
    """
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def access_token_expire_minutes() -> int:
    return 30


def confirm_token_expire_minutes() -> int:
    return 1440


def create_access_token(email: str) -> str:
    """
    Generates a JWT access token for a given email.

    This token includes an expiration time (default 30 minutes from creation) and is encoded with
    the application's secret key.

    Args:
        email (str): The email address to encode within the JWT.

    Returns:
        str: The encoded JWT access token.
    """
    logger.debug(f"Creating access token for {email}")

    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=access_token_expire_minutes())

    jwt_data = {
        "sub": email,
        "exp": expire,
        "type": "access"
    }

    encoded_jwt = jwt.encode(claims=jwt_data,
                             key=config.SECRET_KEY,
                             algorithm=config.ALGORITHM
                             )
    return encoded_jwt


def create_confirmation_token(email: str) -> str:
    """
    Generates a JWT confirmation token for a given email.

    This token includes an expiration time (default 1440 minutes from creation) and is specifically
    intended for email confirmation processes.

    Args:
        email (str): The email address to encode within the JWT.

    Returns:
        str: The encoded JWT confirmation token.
    """
    logger.debug(f"Creating confirmation token for {email}")

    expire = datetime.datetime.utcnow() + datetime.timedelta(minutes=confirm_token_expire_minutes())

    jwt_data = {
        "sub": email,
        "exp": expire,
        "type": "confirmation"
    }

    encoded_jwt = jwt.encode(claims=jwt_data,
                             key=config.SECRET_KEY,
                             algorithm=config.ALGORITHM
                             )
    return encoded_jwt


def get_subject_for_token_type(
        token: str,
        type: Literal["access", "confirmation"]
) -> str:
    """
    Extracts the subject (email) from a JWT for a specific token type (access or confirmation).

    This function validates the token, checks its type, and extracts the email subject if valid.
    It handles token expiration and format errors by raising appropriate HTTP exceptions.

    Args:
        token (str): The JWT from which to extract the subject.
        type (Literal["access", "confirmation"]): The expected type of the token.

    Returns:
        str: The email encoded in the token.

    Raises:
        HTTPException: If the token is expired, invalid, or does not match the expected type.
    """
    try:
        payload = jwt.decode(token=token, key=config.SECRET_KEY, algorithms=[config.ALGORITHM])
    except jwt.ExpiredSignatureError as e:
        raise create_credentials_exception("Token has expired") from e
    except jwt.JWTError as e:
        raise create_credentials_exception("Invalid Token") from e

    email = payload.get("sub")
    if email is None:
        raise create_credentials_exception("Token is missing 'sub' field")

    token_type = payload.get("type")
    if token_type is None or token_type != type:
        raise create_credentials_exception(f"Token type {token_type} does not match {type}")

    return email


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
    """
    Authenticates a user by their email and password.

    Verifies the user's password and checks if the user's email is confirmed. Raises an HTTP
    exception for authentication failure.

    Args:
        email (str): The user's email.
        password (str): The user's password.

    Returns:
        dict: The authenticated user's record if successful.

    Raises:
        HTTPException: For any authentication or confirmation issues.
    """
    logger.debug(f"Authenticating user {email}")
    user = await get_user(email)

    if not user:
        raise create_credentials_exception("Invalid email or password")
    if not verify_password(password, user.password):
        raise create_credentials_exception("Invalid email or password")
    if not user.confirmed:
        raise create_credentials_exception("User has not confirmed email")

    return user


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> Optional[dict]:
    """
    Retrieves the current user based on a provided JWT access token.

    Decodes the token to obtain the user's email and fetches the user record from the database.
    Raises an exception if the token is invalid or the user cannot be found.

    Args:
        token (Annotated[str, Depends(oauth2_scheme)]): The JWT access token.

    Returns:
        dict | None: The user's record if found, otherwise raises an exception.

    Raises:
        HTTPException: If the user cannot be located or the token is invalid.
    """
    email = get_subject_for_token_type(token, "access")
    user = await get_user(email=email)

    if user is None:
        raise create_credentials_exception("Could not found User for this token")
    return user
