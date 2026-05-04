from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List

from src.db_core import dbmodel, crud
from src.pydentic import model
from src.db_core.db import engine, get_db
from src.db_core.auth import verify_password, create_access_token, get_current_user
from src.cloudinary_utils import upload_image

dbmodel.Base.metadata.create_all(bind=engine)

app = FastAPI()


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


# ---------- CREATE / UPDATE PROFILE ----------
@app.post("/create-profile", response_model=model.UserOut)
def create_profile(
    name:str = Form(...),
    username: str = Form(...),
    profile_title: str = Form(None),
    profile_description: str = Form(None),
    file: UploadFile = File(None),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    image_url, public_id = None, None

    if file:
        result = upload_image(file=file)
        image_url = result["url"]
        public_id = result["public_id"]

    return crud.update_full_profile(
        db, user_id,name, username, profile_title, profile_description, image_url, public_id
    )


# ---------- GET PROFILE ----------
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
    if len(files) > 5:
        raise HTTPException(400, "Max 5 images")

    post = crud.create_post(db, user_id, title, content)

    for f in files:
        r = upload_image(file=f)
        crud.add_post_image(db, post.id, r["url"], r["public_id"])

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