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
from fastapi import APIRouter, HTTPException, Request, Depends
from src.database import comment_table, post_table, database, like_table
from src.models.user import User
from src.security import get_current_user, oauth2_scheme


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
    logger.info(f"Finding post with id: {post_id}")

    query = post_table.select().where(post_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_one(query)


@router.post("/post", response_model=UserPost, status_code=201)
async def create_post(
        post: UserPostIn,
        current_user: Annotated[User, Depends(get_current_user)]
) -> dict:
    logger.info("Creating post")

    data = {**post.model_dump(), "user_id": current_user.id}
    query = post_table.insert().values(data)

    logger.debug(query)

    last_record_id = await database.execute(query)
    return {
        **data,
        "id": last_record_id
    }


class PostSorting(str, Enum):
    new = "new"
    old = "old"
    most_likes = "most_likes"


@router.get("/post", response_model=List[UserPostWithLikes], status_code=200)
async def get_all_posts(
        sorting: PostSorting = PostSorting.new
):
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
    logger.info("Getting comments on post")

    query = comment_table.select().where(comment_table.c.id == post_id)

    logger.debug(query)

    return await database.fetch_all(query)


@router.get("/post/{post_id}", response_model=UserPostWithComments)
async def get_post_with_comments(post_id: int):
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
