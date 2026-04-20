from sqlalchemy.orm import Session

from ..models import Post, User
from .email import send_email_sync


def notify_post_owner_new_comment(
    db: Session,
    post_id: int,
    commenter_id: int,
    commenter_username: str,
    comment_preview: str,
) -> None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id == commenter_id:
        return
    owner = db.query(User).filter(User.id == post.author_id).first()
    if not owner or not owner.email:
        return
    subject = f"New comment on your post: {post.title[:80]}"
    body = (
        f"Hi {owner.username},\n\n"
        f"{commenter_username} commented on your post \"{post.title}\":\n\n"
        f"{comment_preview[:500]}\n"
    )
    send_email_sync(owner.email, subject, body)


def notify_post_owner_new_like(
    db: Session,
    post_id: int,
    liker_id: int,
    liker_username: str,
) -> None:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post or post.author_id == liker_id:
        return
    owner = db.query(User).filter(User.id == post.author_id).first()
    if not owner or not owner.email:
        return
    subject = f"Your post was liked: {post.title[:80]}"
    body = f"Hi {owner.username},\n\n{liker_username} liked your post \"{post.title}\".\n"
    send_email_sync(owner.email, subject, body)
