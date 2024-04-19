import logging
from src.database import database, user_table
from passlib.context import CryptContext

# Configure logger for the current module
logger = logging.getLogger(__name__)

# Create a password context for hashing passwords using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"])


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


async def get_user(email: str) -> dict | None:
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
