import logging
from enum import Enum
from typing import List, Annotated
from src.models.post import (
    UserPost,
    UserPostIn,
    Comment,
    CommentIn,
    UserPostWithComments,
    PostLike,
    PostLikeIn,
    UserPostWithLikes
)
import sqlalchemy
from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks, Request
from src.database import comment_table, post_table, database, like_table
from src.models.user import User
from src.security import get_current_user, oauth2_scheme
from src.tasks import generate_and_add_to_post


router = APIRouter()

logger = logging.getLogger(__name__)


select_post_and_likes = (
    sqlalchemy.select(post_table, sqlalchemy.func.count(like_table.c.id).label('likes'))
    .select_from(post_table.outerjoin(like_table))
    .group_by(post_table.c.id)
)


async def find_post(
        post_id: int
) -> UserPost:
    """
    Retrieve a post by its ID.

    Args:
    post_id (int): The unique identifier of the post.

    Returns:
    UserPost: The post retrieved from the database.
    """
    logger.info(f"Finding post with id: {post_id}")

    query = post_table.select().where(post_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(
        post: UserPostIn,
        current_user: Annotated[User, Depends(get_current_user)],
        background_tasks: BackgroundTasks,
        request: Request,
        prompt: str = None
) -> dict:
    """
    Create a new user post and optionally trigger background tasks based on provided prompt.

    Args:
    post (UserPostIn): The post input model containing the content of the post.
    current_user (User): The current authenticated user.
    background_tasks (BackgroundTasks): Background tasks manager for asynchronous job execution.
    request (Request): The request object.
    prompt (str, optional): Optional prompt for triggering additional background tasks.

    Returns:
    dict: The newly created post with additional metadata.
    """
    logger.info("Creating post")

    data = {**post.model_dump(), "user_id": current_user.id}
    query = post_table.insert().values(data)

    logger.debug(query)

    last_record_id = await database.execute(query)

    if prompt:
        background_tasks.add_task(
            generate_and_add_to_post,
            current_user.email,
            last_record_id,
            request.url_for("get_post_with_comments", post_id=last_record_id),
            database,
            prompt
        )

    return {
        **data,
        "id": last_record_id
    }


class PostSorting(str, Enum):
    """
    Enum for sorting posts in different ways.
    """
    new = "new"
    old = "old"
    most_likes = "most_likes"


@router.get("/post", response_model=List[UserPostWithLikes], status_code=200)
async def get_all_posts(
        sorting: PostSorting = PostSorting.new
):
    """
    Retrieve all posts sorted based on the specified sorting criteria.

    Args:
    sorting (PostSorting): The sorting criteria for the posts (new, old, most_likes).

    Returns:
    List[UserPostWithLikes]: A list of posts with like counts.
    """
    logger.info("Getting all posts")

    if sorting == PostSorting.new:
        query = select_post_and_likes.order_by(like_table.c.id.desc())
    elif sorting == PostSorting.old:
        query = select_post_and_likes.order_by(like_table.c.id.asc())
    elif sorting == PostSorting.most_likes:
        query = select_post_and_likes.order_by(sqlalchemy.desc("likes"))

    logger.debug(query)

    return await database.fetch_all(query)


@router.post("/comment", response_model=Comment, status_code=201)
async def create_comment(
        comment: CommentIn,
        current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    """
    Create a new comment on a specific post, checking first if the post exists.

    Args:
    comment (CommentIn): The input model for the comment.
    current_user (User): The current authenticated user.

    Returns:
    dict: The newly created comment with additional metadata.
    """
    logger.info("Creating comment")

    post = await find_post(comment.post_id)
    if not post:
        logger.error(f"No post with id: {comment.post_id}")
        raise HTTPException(status_code=404, detail="Post not found")

    data = {**comment.model_dump(), "user_id": current_user.id}
    query = comment_table.insert().values(data)

    logger.debug(query)

    last_record_id = await database.execute(query)

    return {
        **data,
        "id": last_record_id
    }


@router.get("/post/{post_id}/comment", response_model=List[Comment])
async def get_comments_on_post(
        post_id: int
):
    """
    Retrieve all comments on a specific post.

    Args:
    post_id (int): The unique identifier of the post to retrieve comments for.

    Returns:
    List[Comment]: A list of comments associated with the specified post.
    """
    logger.info("Getting comments on post")

    query = comment_table.select().where(comment_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_all(query)


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
    """
    Retrieve a post and its associated comments by the post ID.

    Args:
    post_id (int): The unique identifier of the post.

    Returns:
    UserPostWithComments: The post along with its comments.
    """
    logger.info("Getting post with comments")

    query = select_post_and_likes.where(post_table.c.id == post_id)

    logger.debug(query)

    post = await database.fetch_one(query)
    if not post:
        logger.error(f"No post with id: {post_id}")
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "post": post,
        "comments": await get_comments_on_post(post_id),
    }


@router.post("/like", response_model=PostLike, status_code=201)
async def like_post(
        like: PostLikeIn,
        current_user: Annotated[User, Depends(get_current_user)]
):
    """
    Record a like on a post by a user, verifying first if the post exists.

    Args:
    like (PostLikeIn): The input model for the like.
    current_user (User): The current authenticated user.

    Returns:
    PostLike: The newly created like record.
    """
    logger.info("Liking post")

    post = await find_post(like.post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    data = {
        **like.model_dump(),
        "user_id": current_user.id
    }

    query = like_table.insert().values(data)

    logger.debug(query)

    last_record_id = await database.execute(query)

    return {
        **data,
        "id": last_record_id
    }
