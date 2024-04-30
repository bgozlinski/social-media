import logging
import os
import tempfile
import aiofiles
from fastapi import APIRouter, HTTPException, UploadFile, status
from libs.b2 import s3_upload_file

logger = logging.getLogger(__name__)

router = APIRouter()

CHUNK_SIZE = 1024 * 1024


@router.post('/upload', status_code=status.HTTP_201_CREATED)
async def upload_file(file: UploadFile):
    """
    Uploads a file to an S3 bucket, handling it chunk by chunk to manage memory usage.

    This function reads an uploaded file in chunks, temporarily saves it to disk, and then uploads it to
    an S3 bucket. The temporary file is deleted after the upload. Errors in the process raise an HTTP
    exception, and an error message is logged.

    Args:
    file (UploadFile): The file uploaded by the user, provided through FastAPI's UploadFile object, which
                       handles streaming and storage of upload files.

    Returns:
    dict: A dictionary containing the URL of the uploaded file in the S3 bucket and a message indicating
          successful upload.

    Raises:
    HTTPException: An exception with a 500 status code indicating an internal server error if any part of the
                   file handling or upload process fails.
    """
    try:
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            filename = temp_file.name
        logger.info(f"Temporary file will be saved as {filename}")

        async with aiofiles.open(filename, "wb") as f:
            while chunk := await file.read(CHUNK_SIZE):
                await f.write(chunk)

        file_url = s3_upload_file(local_file=filename, file_name=file.filename)

    except Exception as e:
        logger.error("Failed to process file upload", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    finally:
        os.unlink(filename)

    return {"detail": f"Successfully uploaded {file.filename}", "file_url": file_url}
