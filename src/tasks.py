import logging
import httpx
from databases import Database
from src.database import post_table
from src.config import config
from json import JSONDecodeError

logger = logging.getLogger(__name__)


class APIResponseError(Exception):
    pass


async def send_simple_email(
        to: str,
        subject: str,
        body: str
):
    """
    Sends a simple email using the Mailgun API.

    This function asynchronously sends an email to a specified recipient with a given subject and body. It uses
    the Mailgun service to manage email delivery.

    Args:
        to (str): The recipient's email address.
        subject (str): The subject line of the email.
        body (str): The main text content of the email.

    Returns:
        httpx.Response: The response from the Mailgun API.

    Raises:
        APIResponseError: If the HTTP request to the Mailgun API fails.
    """
    logger.debug(f"Sending email to '{to[:3]}' with subject '{subject[:20]}'")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"https://api.mailgun.net/v3/{config.MAILGUN_DOMAIN}/messages",
                auth=("api", config.MAILGUN_API_KEY),
                data={"from": f"Bgozl <mailgun@{config.MAILGUN_DOMAIN}>",
                      "to": [to],
                      "subject": subject,
                      "text": body
                      }
            )
            response.raise_for_status()

            logger.info(response.content)

            return response

        except httpx.HTTPStatusError as e:
            raise APIResponseError(
                f"API request failed with status code {e.response.status_code}"
            ) from e


async def send_user_registration_email(
        email: str,
        confirmation_url: str
):
    """
    Sends an email to a new user containing a link to confirm their email address.

    This function constructs a welcome message with a confirmation URL and uses `send_simple_email` to send it.

    Args:
        email (str): The new user's email address.
        confirmation_url (str): The URL the user must visit to confirm their email.

    Returns:
        httpx.Response: The response from the email sending function, `send_simple_email`.
    """
    return await send_simple_email(
        email,
        "Successfully signed up",
        (
            f"Hi {email}! You have successfully signed up to the Social-Media REST API."
            " Please confirm your email by clicking on the"
            f" following link: {confirmation_url}"
        )
    )


async def _generate_cute_creature_api(prompt: str):
    """
    Generates an image from a text prompt using the DeepAI Text2Img API.

    This function posts a prompt to the DeepAI API and expects a URL in response that links to the generated image.
    It handles any HTTP status errors or JSON parsing errors by raising a custom `APIResponseError`.

    Args:
        prompt (str): The text prompt used to generate the image.

    Returns:
        dict: The JSON response containing the URL of the generated image.

    Raises:
        APIResponseError: If there is an issue with the API request or response.
    """
    logger.debug(f"Generating Cute Creature")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.deepai.org/api/text2img",
                data={"text": prompt},
                headers={"api-key": config.DEEPAI_API_KEY},
                timeout=60
            )
            logger.debug(response)
            response.raise_for_status()
            return response.json()

        except httpx.HTTPStatusError as e:
            raise APIResponseError(
                f"API request failed with status code {e.response.status_code}"
            ) from e
        except (JSONDecodeError, TypeError) as e:
            raise APIResponseError("API response with parsing failed") from e


async def generate_and_add_to_post(
        email: str,
        post_id: int,
        post_url: str,
        database: Database,
        prompt: str = "A cat is sitting on chair",
):
    """
    Generates an image based on a prompt and updates a database record with the image URL.

    This function first calls `_generate_cute_creature_api` to generate an image, then updates a specific post
    in the database with the URL of the generated image. If image generation fails, it sends an error notification
    email to the user.

    Args:
        email (str): The email address of the user associated with the post.
        post_id (int): The database ID of the post to update.
        post_url (str): The URL of the post where the image will be added.
        database (Database): The database connection object.
        prompt (str, optional): The text prompt used to generate the image. Defaults to "A cat is sitting on chair".

    Returns:
        dict | httpx.Response: The response from the image generation API or the error email sending function.
    """
    try:
        response = await _generate_cute_creature_api(prompt)
    except APIResponseError as e:
        return await send_simple_email(
            email,
            "Error in generating image",
            f"Hi {email}!\nAn error occurred while generating image: {e}"
        )

    logger.debug(f"Connecting to database to update post")

    query = (
        post_table.update().
        where(post_table.c.id == post_id)
        .values(image_url=response["output_url"])
    )

    logger.debug(query)

    await database.execute(query)

    logger.debug(f"Database connection in background task closed")

    return response
