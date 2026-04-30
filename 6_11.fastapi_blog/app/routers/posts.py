from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import SessionLocal, get_db
from ..models import Comment, Like, Post, User
from ..services.notifications import notify_post_owner_new_comment, notify_post_owner_new_like

router = APIRouter(prefix="/posts", tags=["posts"])


def _notify_comment_task(post_id: int, commenter_id: int, commenter_username: str, preview: str) -> None:
    db = SessionLocal()
    try:
        notify_post_owner_new_comment(db, post_id, commenter_id, commenter_username, preview)
    finally:
        db.close()


def _notify_like_task(post_id: int, liker_id: int, liker_username: str) -> None:
    db = SessionLocal()
    try:
        notify_post_owner_new_like(db, post_id, liker_id, liker_username)
    finally:
        db.close()


@router.post("/", response_model=schemas.PostRead, status_code=status.HTTP_201_CREATED)
def create_post(
    data: schemas.PostCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = Post(title=data.title, content=data.content, author_id=current.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/mine", response_model=list[schemas.PostRead])
def list_my_posts(db: Session = Depends(get_db), current: User = Depends(get_current_user)):
    """Optional: posts authored by the current user."""
    return (
        db.query(Post)
        .filter(Post.author_id == current.id)
        .order_by(Post.created_at.desc())
        .all()
    )


@router.get("/", response_model=list[schemas.PostRead])
def list_posts(db: Session = Depends(get_db)):
    return db.query(Post).order_by(Post.created_at.desc()).all()


@router.get("/{post_id}", response_model=schemas.PostDetail)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    comment_count = db.query(func.count(Comment.id)).filter(Comment.post_id == post_id).scalar() or 0
    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar() or 0
    return schemas.PostDetail(
        id=post.id,
        title=post.title,
        content=post.content,
        author_id=post.author_id,
        created_at=post.created_at,
        comment_count=int(comment_count),
        like_count=int(like_count),
    )


@router.put("/{post_id}", response_model=schemas.PostRead)
def update_post(
    post_id: int,
    data: schemas.PostUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can update this post")
    if data.title is None and data.content is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nothing to update")
    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content
    db.commit()
    db.refresh(post)
    return post


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.author_id != current.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the author can delete this post")
    db.delete(post)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{post_id}/comments/", response_model=schemas.CommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(
    post_id: int,
    data: schemas.CommentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    comment = Comment(post_id=post_id, user_id=current.id, text=data.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    background_tasks.add_task(
        _notify_comment_task,
        post_id,
        current.id,
        current.username,
        data.text[:500],
    )
    return comment


@router.get("/{post_id}/comments/", response_model=list[schemas.CommentRead])
def list_comments(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at.asc()).all()


@router.post("/{post_id}/like/", response_model=schemas.LikeToggleResponse)
def toggle_like(
    post_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    existing = db.query(Like).filter(Like.post_id == post_id, Like.user_id == current.id).first()
    if existing:
        db.delete(existing)
        db.commit()
        like_count = db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar() or 0
        return schemas.LikeToggleResponse(liked=False, like_count=int(like_count), message="Like removed")
    like = Like(post_id=post_id, user_id=current.id)
    db.add(like)
    db.commit()
    like_count = db.query(func.count(Like.id)).filter(Like.post_id == post_id).scalar() or 0
    background_tasks.add_task(_notify_like_task, post_id, current.id, current.username)
    return schemas.LikeToggleResponse(liked=True, like_count=int(like_count), message="Post liked")


@router.get("/{post_id}/likes/", response_model=schemas.LikesSummary)
def list_likes(post_id: int, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    likes = db.query(Like).filter(Like.post_id == post_id).order_by(Like.id.asc()).all()
    return schemas.LikesSummary(count=len(likes), likes=likes)
