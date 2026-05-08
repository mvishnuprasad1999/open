from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from src.db_core.db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String, unique=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)

    profile_image_id = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    profile_title = Column(String, nullable=True)
    profile_description = Column(String, nullable=True)

    is_profile_complete = Column(Boolean, default=False)

    embedding = Column(Vector(384))

    posts = relationship("Post", back_populates="user")

    # FOLLOW RELATIONSHIPS
    followers = relationship(
        "Follow",
        foreign_keys="Follow.following_id",
        back_populates="following_user"
    )

    following = relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        back_populates="follower_user"
    )

    # LIKES
    likes = relationship("Like", back_populates="user")

    # SAVES
    saves = relationship("Save", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    title = Column(String)
    content = Column(Text)

    embedding = Column(Vector(384))

    user = relationship("User", back_populates="posts")

    images = relationship("PostImage", back_populates="post")

    likes = relationship("Like", back_populates="post")

    saves = relationship("Save", back_populates="post")


class PostImage(Base):
    __tablename__ = "post_images"

    id = Column(Integer, primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id"))

    image_url = Column(String)
    public_id = Column(String)

    post = relationship("Post", back_populates="images")


class Like(Base):
    __tablename__ = "likes"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))

    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")


class Save(Base):
    __tablename__ = "saves"

    id = Column(Integer, primary_key=True)

    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))

    user = relationship("User", back_populates="saves")
    post = relationship("Post", back_populates="saves")


class Follow(Base):
    __tablename__ = "follows"

    id = Column(Integer, primary_key=True)

    follower_id = Column(Integer, ForeignKey("users.id"))
    following_id = Column(Integer, ForeignKey("users.id"))

    follower_user = relationship(
        "User",
        foreign_keys=[follower_id],
        back_populates="following"
    )

    following_user = relationship(
        "User",
        foreign_keys=[following_id],
        back_populates="followers"
    )