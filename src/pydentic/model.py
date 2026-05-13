from pydantic import BaseModel, EmailStr
from typing import List, Optional


# =========================
# AUTH
# =========================

class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str
    is_profile_complete: bool


# =========================
# USER
# =========================

class UserOut(BaseModel):
    id: int
    email: EmailStr

    name: Optional[str]
    username: Optional[str]

    profile_title: Optional[str]
    profile_image: Optional[str]
    profile_description: Optional[str]

    is_profile_complete: bool

    followers_count: Optional[int] = 0
    following_count: Optional[int] = 0

    class Config:
        from_attributes = True


class UserMiniOut(BaseModel):
    id: int
    email: EmailStr

    name: Optional[str] = None
    username: Optional[str] = None

    profile_title: Optional[str] = None
    profile_image: Optional[str] = None
    profile_description: Optional[str] = None

    is_profile_complete: bool = False

    followers_count: int = 0
    following_count: int = 0

    is_following: bool = False

    class Config:
        from_attributes = True


# =========================
# POST IMAGE
# =========================

class PostImageOut(BaseModel):
    image_url: str

    class Config:
        from_attributes = True


# =========================
# POST
# =========================

class PostOut(BaseModel):
    id: int

    title: str
    content: str

    user_id: int
    user: UserMiniOut

    images: List[PostImageOut]

    likes_count: Optional[int] = 0
    saves_count: Optional[int] = 0

    is_liked: Optional[bool] = False
    is_saved: Optional[bool] = False

    class Config:
        from_attributes = True



# =========================
# FOLLOW
# =========================

class FollowCreate(BaseModel):
    following_id: int


class FollowOut(BaseModel):
    id: int

    follower_id: int
    following_id: int

    class Config:
        from_attributes = True


# =========================
# LIKE
# =========================

class LikeCreate(BaseModel):
    post_id: int


class LikeOut(BaseModel):
    id: int

    user_id: int
    post_id: int

    class Config:
        from_attributes = True


# =========================
# SAVE
# =========================

class SaveCreate(BaseModel):
    post_id: int


class SaveOut(BaseModel):
    id: int

    user_id: int
    post_id: int

    class Config:
        from_attributes = True
 
 
# ── existing models stay as-is ──
 
# ── NEW: Chat models ──
 
class ChatMessage(BaseModel):
    role: str          # "user" or "assistant"
    content: str
 
class ChatRequest(BaseModel):
    query: str
    history: List[ChatMessage] = []   # full conversation so far
 
class ChatResponse(BaseModel):
    answer: str
    context_used: Optional[str] = None   # optional: show what DB data was pulled


# task

class TaskImageOut(BaseModel):
    image_url: str

    class Config:
        from_attributes = True

class TaskSolutionOut(BaseModel):
    id: int
    content: str

    user: UserMiniOut

    class Config:
        from_attributes = True

class TaskOut(BaseModel):
    id: int

    title: str
    content: str

    user_id: int

    user: UserMiniOut

    images: List[TaskImageOut] = []

    solutions: List[TaskSolutionOut] = []

    class Config:
        from_attributes = True