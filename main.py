from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List

from src.db_core import crud, dbmodel
from src.pydentic import model
from src.db_core.db import get_db
from src.db_core.auth import verify_password, create_access_token, get_current_user
from src.cloudinary_utils import upload_image
from src.db_core.embeddings import get_embedding,to_pgvector
from sqlalchemy import text
from src.rerank import rerank_results


app = FastAPI()


# ---------- ROOT ----------
@app.get("/")
def welcome():
    return {"message": "welcome to open"}


# ---------- SIGNUP ----------
@app.post("/signup", response_model=model.Token)
def signup(user: model.UserCreate, db: Session = Depends(get_db)):
    if crud.get_user_by_email(db, user.email):
        raise HTTPException(400, "Email already exists")

    new_user = crud.create_user(db, user.email, user.password)

    token = create_access_token({"sub": new_user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_profile_complete": new_user.is_profile_complete
    }


# ---------- LOGIN ----------
@app.post("/login", response_model=model.Token)
def login(user: model.UserLogin, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_email(db, user.email)

    if not db_user or not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, "Invalid credentials")

    token = create_access_token({"sub": db_user.id})

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_profile_complete": db_user.is_profile_complete
    }


# ---------- PROFILE ----------
@app.post("/create-profile", response_model=model.UserOut)
def create_profile(
    name: str = Form(...),
    username: str = Form(...),
    profile_title: str = Form(None),
    profile_description: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    image_url, public_id = None, None

    if file:
        r = upload_image(file=file)
        image_url = r["url"]
        public_id = r["public_id"]

    # 🔥 BETTER EMBEDDING TEXT
    text_data = f"""
    Name: {name}
    Username: {username}
    Title: {profile_title}
    Skills: {profile_description}
    """

    embedding = get_embedding(text_data)

    user = crud.update_full_profile(
        db, user_id, name, username,
        profile_title, profile_description,
        image_url, public_id
    )

    user.embedding = embedding
    db.commit()

    return user

@app.get("/me", response_model=model.UserOut)
def get_profile(db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return crud.get_user_by_id(db, user_id)


# ---------- POSTS ----------
@app.post("/create-post", response_model=model.PostOut)
def create_post(
    title: str = Form(...),
    content: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    post = crud.create_post(db, user_id, title, content)

    embedding = get_embedding(f"{title} {content}")
    post.embedding = embedding

    for f in files:
        r = upload_image(file=f)
        crud.add_post_image(db, post.id, r["url"], r["public_id"])

    db.commit()
    return post

@app.get("/posts", response_model=List[model.PostOut])
def posts(db: Session = Depends(get_db)):
    return crud.get_posts(db)


@app.post("/like/{post_id}")
def like(post_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return crud.like_post(db, user_id, post_id)


@app.post("/save/{post_id}")
def save(post_id: int, db: Session = Depends(get_db), user_id: int = Depends(get_current_user)):
    return crud.save_post(db, user_id, post_id)


@app.post("/follow/{user_id}")
def follow(user_id: int, db: Session = Depends(get_db), current: int = Depends(get_current_user)):
    return crud.follow(db, current, user_id)


# ---------- RAG SEARCH ----------




@app.get("/search-users")
def search_users(query: str, db: Session = Depends(get_db)):
    query_embedding = get_embedding(query)
    emb_str = to_pgvector(query_embedding)

    rows = db.execute(text("""
        SELECT id, username, profile_description,
               embedding <-> :emb AS distance
        FROM users
        WHERE embedding IS NOT NULL
        ORDER BY embedding <-> :emb
        LIMIT 10
    """), {"emb": emb_str}).fetchall()

    # ✅ FILTER (important)
    filtered = [
        {
            "id": r[0],
            "username": r[1],
            "desc": r[2],
            "score": float(r[3])
        }
        for r in rows if r[3] < 1.5
    ]

    # ✅ OPTIONAL LLM RERANK
    final = rerank_results(query, filtered)

    return final


@app.get("/search-posts")
def search_posts(query: str, db: Session = Depends(get_db)):
    query_embedding = get_embedding(query)
    emb_str = to_pgvector(query_embedding)

    rows = db.execute(text("""
        SELECT id, title, content,
               embedding <-> :emb AS distance
        FROM posts
        WHERE embedding IS NOT NULL
        ORDER BY embedding <-> :emb
        LIMIT 10
    """), {"emb": emb_str}).fetchall()

    return [
        {
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "score": float(r[3])
        }
        for r in rows if r[3] < 1.5
    ]