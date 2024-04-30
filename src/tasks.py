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
