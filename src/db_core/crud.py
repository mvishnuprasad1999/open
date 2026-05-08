from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException
from src.db_core.dbmodel import User
from src.db_core import dbmodel
from src.db_core.auth import hash_password
import cloudinary.uploader
from src.db_core.embeddings import get_embedding


# =========================
# USERS
# =========================

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, email: str, password: str):
    user = User(
        email=email,
        hashed_password=hash_password(password)
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# =========================
# PROFILE UPDATE
# =========================

def update_full_profile(
    db,
    user_id,
    name,
    username,
    title,
    desc,
    image_url,
    public_id
):
    user = get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # username uniqueness
    if username:
        existing = db.query(User).filter(
            User.username == username
        ).first()

        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )

        user.username = username

    if name:
        user.name = name

    if title:
        user.profile_title = title

    if desc:
        user.profile_description = desc

    # image replace
    if image_url:

        if user.profile_image_id:
            cloudinary.uploader.destroy(user.profile_image_id)

        user.profile_image = image_url
        user.profile_image_id = public_id

    user.is_profile_complete = True

    # embedding
    text = f"""
    {user.username or ''}
    {user.name or ''}
    {user.profile_title or ''}
    {user.profile_description or ''}
    """

    user.embedding = get_embedding(text)

    db.commit()
    db.refresh(user)

    return user


# =========================
# POSTS
# =========================

def create_post(db, user_id, title, content):

    post = dbmodel.Post(
        user_id=user_id,
        title=title,
        content=content
    )

    text = f"{title} {content}"

    post.embedding = get_embedding(text)

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


def add_post_image(db, post_id, url, pid):

    img = dbmodel.PostImage(
        post_id=post_id,
        image_url=url,
        public_id=pid
    )

    db.add(img)
    db.commit()

    return img


# =========================
# GET POSTS
# =========================

def get_posts(db):

    posts = db.query(dbmodel.Post).options(
        joinedload(dbmodel.Post.user),
        joinedload(dbmodel.Post.images)
    ).all()

    # attach counts
    for post in posts:

        post.likes_count = db.query(
            dbmodel.Like
        ).filter(
            dbmodel.Like.post_id == post.id
        ).count()

        post.saves_count = db.query(
            dbmodel.Save
        ).filter(
            dbmodel.Save.post_id == post.id
        ).count()

    return posts


# =========================
# LIKE POST
# =========================

def like_post(db, uid, pid):

    existing = db.query(dbmodel.Like).filter(
        dbmodel.Like.user_id == uid,
        dbmodel.Like.post_id == pid
    ).first()

    if existing:
        return {"msg": "already liked"}

    like = dbmodel.Like(
        user_id=uid,
        post_id=pid
    )

    db.add(like)
    db.commit()

    return {"msg": "liked"}


# =========================
# SAVE POST
# =========================

def save_post(db, uid, pid):

    existing = db.query(dbmodel.Save).filter(
        dbmodel.Save.user_id == uid,
        dbmodel.Save.post_id == pid
    ).first()

    if existing:
        return {"msg": "already saved"}

    save = dbmodel.Save(
        user_id=uid,
        post_id=pid
    )

    db.add(save)
    db.commit()

    return {"msg": "saved"}


# =========================
# FOLLOW USER
# =========================

def follow(db, uid, target):

    # self follow block
    if uid == target:
        raise HTTPException(
            status_code=400,
            detail="You cannot follow yourself"
        )

    # check target exists
    target_user = get_user_by_id(db, target)

    if not target_user:
        raise HTTPException(
            status_code=404,
            detail="Target user not found"
        )

    # duplicate follow check
    existing = db.query(dbmodel.Follow).filter(
        dbmodel.Follow.follower_id == uid,
        dbmodel.Follow.following_id == target
    ).first()

    if existing:
        return {"msg": "already followed"}

    follow_obj = dbmodel.Follow(
        follower_id=uid,
        following_id=target
    )

    db.add(follow_obj)
    db.commit()

    return {"msg": "followed"}