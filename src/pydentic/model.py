from pydantic import BaseModel, EmailStr
from typing import List, Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name:Optional[str]
    username: Optional[str]
    profile_title: Optional[str]
    profile_image: Optional[str]
    profile_description: Optional[str]
    is_profile_complete: bool

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    is_profile_complete: bool


class PostImageOut(BaseModel):
    image_url: str

    class Config:
        from_attributes = True


class PostOut(BaseModel):
    id: int
    title: str
    content: str
    images: List[PostImageOut]
    user: UserOut 
    user_id: int

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