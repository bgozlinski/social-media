import logging
import httpx
from src.config import config

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
            f"Hi {email}! Yoou have successfulklt signed up to the Social-Media REST API."
            " Please confirm your email by clicking on the"
            f" following link: {confirmation_url}"
        )
    )
