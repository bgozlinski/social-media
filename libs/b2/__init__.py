import logging
from functools import lru_cache
import boto3
from src.config import config

logger = logging.getLogger(__name__)


@lru_cache()
def s3_client():
    logger.debug("Creating S3 client")
    session = boto3.Session(
        aws_access_key_id=config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
        region_name=config.AWS_REGION,
    )
    return session.client('s3')


def s3_upload_file(local_file: str, file_name: str):
    client = s3_client()
    bucket_name = config.S3_BUCKET_NAME
    logger.debug(f"Uploading {local_file} to S3 as {file_name}")

    client.upload_file(
        Filename=local_file,
        Bucket=bucket_name,
        Key=file_name
    )

    download_url = f"https://{bucket_name}.s3.amazonaws.com/{file_name}"

    logger.debug(f"Uploaded {local_file} to S3 and got download url {download_url}")

    return download_url
