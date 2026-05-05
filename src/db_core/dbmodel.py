from pgvector.sqlalchemy import Vector as PGVector
from sqlalchemy import Column, Integer, String, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from src.db_core.db import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name=Column(String, unique=True)
    username = Column(String, unique=True)
    hashed_password = Column(String)

    profile_image_id = Column(String, nullable=True)
    profile_image = Column(String, nullable=True)
    profile_title = Column(String, nullable=True)
    profile_description = Column(String, nullable=True)

    is_profile_complete = Column(Boolean, default=False)
    from pgvector.sqlalchemy import Vector

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

    embedding = Column(PGVector(1536))  # 👈 ADD THIS

    posts = relationship("Post", back_populates="user")

    posts = relationship("Post", back_populates="user")


class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    content = Column(Text)

    user = relationship("User", back_populates="posts")
    images = relationship("PostImage", back_populates="post")


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
    user_id = Column(Integer)
    post_id = Column(Integer)


class Save(Base):
    __tablename__ = "saves"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    post_id = Column(Integer)


class Follow(Base):
    __tablename__ = "follows"
    id = Column(Integer, primary_key=True)
    follower_id = Column(Integer)
    following_id = Column(Integer)