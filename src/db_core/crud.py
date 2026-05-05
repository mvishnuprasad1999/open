from sqlalchemy.orm import Session
from fastapi import HTTPException
from src.db_core.dbmodel import User
from src.db_core import dbmodel
from src.db_core.auth import hash_password
import cloudinary.uploader


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


def update_full_profile(db, user_id,name, username, title, desc, image_url, public_id):
    user = get_user_by_id(db, user_id)

    # username uniqueness check
    if username:
        existing = db.query(User).filter(User.username == username).first()
        if existing and existing.id != user_id:
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = username
    if name:
        user.name = name    

    if title:
        user.profile_title = title

    if desc:
        user.profile_description = desc

    if image_url:
        if user.profile_image_id:
            cloudinary.uploader.destroy(user.profile_image_id)

        user.profile_image = image_url
        user.profile_image_id = public_id

    user.is_profile_complete = True

    db.commit()
    db.refresh(user)
    return user


# ---------- POSTS ----------
def create_post(db, user_id, title, content):
    post = dbmodel.Post(user_id=user_id, title=title, content=content)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def add_post_image(db, post_id, url, pid):
    img = dbmodel.PostImage(post_id=post_id, image_url=url, public_id=pid)
    db.add(img)
    db.commit()


from sqlalchemy.orm import joinedload

def get_posts(db):
    return db.query(dbmodel.Post).options(joinedload(dbmodel.Post.user)).all()


def like_post(db, uid, pid):
    db.add(dbmodel.Like(user_id=uid, post_id=pid))
    db.commit()
    return {"msg": "liked"}


def save_post(db, uid, pid):
    db.add(dbmodel.Save(user_id=uid, post_id=pid))
    db.commit()
    return {"msg": "saved"}


def follow(db, uid, target):
    db.add(dbmodel.Follow(follower_id=uid, following_id=target))
    db.commit()
    return {"msg": "followed"}