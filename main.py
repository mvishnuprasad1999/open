from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session,joinedload
from sqlalchemy import text
from typing import List, Optional

from src.db_core import crud, dbmodel
from src.pydentic import model
from src.db_core.db import get_db
from src.db_core.auth import get_current_user_optional, verify_password, create_access_token, get_current_user
from src.cloudinary_utils import upload_image
from src.db_core.embeddings import get_embedding,to_pgvector
from sqlalchemy import text
from src.rerank import rerank_results
from src.rag_chat import chat_with_rag, retrieve_context
from src.pydentic.model import ChatRequest, ChatResponse

from src.db_core.init_db import init
init()  # ← must be first, before other imports

from fastapi import FastAPI
# ... rest of your imports

app = FastAPI()


# ---------- ROOT ----------

@app.get("/")
def welcome():
    return {"message": "welcome to open"}


# =========================
# SIGNUP
# =========================

@app.post("/signup", response_model=model.Token)
def signup(
    user: model.UserCreate,
    db: Session = Depends(get_db)
):

    existing = crud.get_user_by_email(db, user.email)

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Email already exists"
        )

    new_user = crud.create_user(
        db,
        user.email,
        user.password
    )

    token = create_access_token({
        "sub": new_user.id
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_profile_complete": new_user.is_profile_complete
    }


# =========================
# LOGIN
# =========================

@app.post("/login", response_model=model.Token)
def login(
    user: model.UserLogin,
    db: Session = Depends(get_db)
):

    db_user = crud.get_user_by_email(
        db,
        user.email
    )

    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    if not verify_password(
        user.password,
        db_user.hashed_password
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials"
        )

    token = create_access_token({
        "sub": db_user.id
    })

    return {
        "access_token": token,
        "token_type": "bearer",
        "is_profile_complete": db_user.is_profile_complete
    }


# =========================
# CREATE PROFILE
# =========================

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

    image_url = None
    public_id = None

    if file:

        uploaded = upload_image(file=file)

        image_url = uploaded["url"]
        public_id = uploaded["public_id"]

    user = crud.update_full_profile(
        db,
        user_id,
        name,
        username,
        profile_title,
        profile_description,
        image_url,
        public_id
    )

    return user


# =========================
# GET CURRENT USER
# =========================

@app.get("/me")
def get_profile(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):

    user = crud.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # followers / following count
    followers_count = db.query(dbmodel.Follow).filter(
        dbmodel.Follow.following_id == user.id
    ).count()

    following_count = db.query(dbmodel.Follow).filter(
        dbmodel.Follow.follower_id == user.id
    ).count()

    # ✅ GET USER POSTS
    posts = (
        db.query(dbmodel.Post)
        .options(joinedload(dbmodel.Post.images))
        .filter(dbmodel.Post.user_id == user.id)
        .order_by(dbmodel.Post.id.desc())
        .all()
    )

    post_list = []

    for post in posts:

        likes_count = db.query(dbmodel.Like).filter(
            dbmodel.Like.post_id == post.id
        ).count()

        saves_count = db.query(dbmodel.Save).filter(
            dbmodel.Save.post_id == post.id
        ).count()

        post_list.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url,
                    "public_id": img.public_id
                }
                for img in post.images
            ],
            "likes_count": likes_count,
            "saves_count": saves_count,
        })

    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "name": user.name,
        "profile_title": user.profile_title,
        "profile_description": user.profile_description,
        "image_url": user.profile_image,

        "followers_count": followers_count,
        "following_count": following_count,

        # ✅ added posts
        "posts": post_list
    }


# =========================
# GET ALL USERS
# =========================

@app.get("/users", response_model=List[model.UserOut])
def get_users(
    db: Session = Depends(get_db)
):

    users = db.query(dbmodel.User).all()

    for user in users:

        user.followers_count = db.query(
            dbmodel.Follow
        ).filter(
            dbmodel.Follow.following_id == user.id
        ).count()

        user.following_count = db.query(
            dbmodel.Follow
        ).filter(
            dbmodel.Follow.follower_id == user.id
        ).count()

    return users


# =========================
# GET USER BY ID
# =========================

@app.get("/user/{user_id}")
def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[int] = Depends(get_current_user_optional)
):

    # 1. Get user
    user = crud.get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    # 2. Followers count
    followers_count = db.query(dbmodel.Follow).filter(
        dbmodel.Follow.following_id == user.id
    ).count()

    # 3. Following count
    following_count = db.query(dbmodel.Follow).filter(
        dbmodel.Follow.follower_id == user.id
    ).count()

    # 4. Get user posts with images
    posts = (
        db.query(dbmodel.Post)
        .options(joinedload(dbmodel.Post.images))
        .filter(dbmodel.Post.user_id == user_id)
        .order_by(dbmodel.Post.id.desc())
        .all()
    )

    post_list = []

    for post in posts:

        likes_count = db.query(dbmodel.Like).filter(
            dbmodel.Like.post_id == post.id
        ).count()

        saves_count = db.query(dbmodel.Save).filter(
            dbmodel.Save.post_id == post.id
        ).count()

        is_liked = False

        if current_user:
            is_liked = db.query(dbmodel.Like).filter(
                dbmodel.Like.post_id == post.id,
                dbmodel.Like.user_id == current_user
            ).first() is not None

        post_list.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "user_id": post.user_id,
            "images": post.images,
            "likes_count": likes_count,
            "saves_count": saves_count,
            "is_liked": is_liked,
        })

    # 5. FINAL RESPONSE (FIXED IMAGE FIELD HERE)
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "name": user.name,
        "profile_title": user.profile_title,
        "profile_description": user.profile_description,

        # ✅ FIXED HERE (NO image_url column in DB)
        "image_url": user.profile_image,

        "followers_count": followers_count,
        "following_count": following_count,

        "posts": post_list
    }


# =========================
# CREATE POST
# =========================

@app.post("/create-post", response_model=model.PostOut)
def create_post(
    title: str = Form(...),
    content: str = Form(...),
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):

    post = crud.create_post(db, user_id, title, content)

    for f in files:
        uploaded = upload_image(file=f)

        crud.add_post_image(
            db,
            post.id,
            uploaded["url"],
            uploaded["public_id"]
        )

    db.commit()

    # 🔥 IMPORTANT: reload with images
    post = (
        db.query(dbmodel.Post)
        .options(joinedload(dbmodel.Post.images))
        .filter(dbmodel.Post.id == post.id)
        .first()
    )

    return post


# =========================
# GET POSTS (WITH IMAGES)
# =========================

@app.get("/posts")
def get_posts(
    db: Session = Depends(get_db),
    current_user: Optional[int] = Depends(get_current_user_optional)
):

    posts = (
        db.query(dbmodel.Post)
        .options(
            joinedload(dbmodel.Post.user),
            joinedload(dbmodel.Post.images)
        )
        .order_by(dbmodel.Post.id.desc())
        .all()
    )

    result = []

    for post in posts:

        is_liked = False
        is_saved = False
        is_following = False

        if current_user:

            # LIKE
            like = db.query(
                dbmodel.Like
            ).filter(
                dbmodel.Like.user_id == current_user,
                dbmodel.Like.post_id == post.id
            ).first()

            # SAVE
            save = db.query(
                dbmodel.Save
            ).filter(
                dbmodel.Save.user_id == current_user,
                dbmodel.Save.post_id == post.id
            ).first()

            # FOLLOW
            follow = db.query(
                dbmodel.Follow
            ).filter(
                dbmodel.Follow.follower_id == current_user,
                dbmodel.Follow.following_id == post.user_id
            ).first()

            is_liked = like is not None
            is_saved = save is not None
            is_following = follow is not None

        likes_count = db.query(
            dbmodel.Like
        ).filter(
            dbmodel.Like.post_id == post.id
        ).count()

        saves_count = db.query(
            dbmodel.Save
        ).filter(
            dbmodel.Save.post_id == post.id
        ).count()

        result.append({

            "id": post.id,
            "title": post.title,
            "content": post.content,
            "user_id": post.user_id,

            "user": {
                "id": post.user.id,
                "email": post.user.email,
                "name": post.user.name,
                "username": post.user.username,
                "profile_title": post.user.profile_title,
                "profile_image": post.user.profile_image,
                "profile_description": post.user.profile_description,
                "is_following": is_following,
            },

            "images": [
                {
                    "id": image.id,
                    "image_url": image.image_url,
                    "public_id": image.public_id
                }
                for image in post.images
            ],

            "likes_count": likes_count,
            "saves_count": saves_count,

            "is_liked": is_liked,
            "is_saved": is_saved,
            "is_following": is_following,
        })

    return result

# =========================
# logged user POST
# =========================

@app.get("/my-posts", response_model=List[model.PostOut])
def my_posts(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):

    return (
        db.query(dbmodel.Post)
        .options(joinedload(dbmodel.Post.images))
        .filter(dbmodel.Post.user_id == user_id)
        .order_by(dbmodel.Post.id.desc())
        .all()
    )

# =========================
# GET POSTS BY USER ID
# =========================

# @app.get("/user-posts/{user_id}", response_model=List[model.PostOut])
# def get_user_posts(
#     user_id: int,
#     db: Session = Depends(get_db),
# ):
#     posts_data = (
#         db.query(dbmodel.Post)
#         .options(
#             joinedload(dbmodel.Post.images),
#             joinedload(dbmodel.Post.user),
#         )
#         .filter(dbmodel.Post.user_id == user_id)
#         .order_by(dbmodel.Post.id.desc())
#         .all()
#     )

#     result = []

#     for post in posts_data:
#         likes_count = (
#             db.query(dbmodel.Like)
#             .filter(dbmodel.Like.post_id == post.id)
#             .count()
#         )

#         saves_count = (
#             db.query(dbmodel.Save)
#             .filter(dbmodel.Save.post_id == post.id)
#             .count()
#         )

#         result.append({
#             "id": post.id,
#             "title": post.title,
#             "content": post.content,
#             "user_id": post.user_id,
#             "user": post.user,
#             "images": post.images,
#             "likes_count": likes_count,
#             "saves_count": saves_count,
#             "is_liked": False,
#         })

#     return result
# =========================
# GET POSTS BY USER ID
# =========================

@app.get("/user-posts/{user_id}", response_model=List[model.PostOut])
def get_user_posts(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[int] = Depends(get_current_user_optional)
):

    posts_data = (
        db.query(dbmodel.Post)
        .options(
            joinedload(dbmodel.Post.images),
            joinedload(dbmodel.Post.user),
        )
        .filter(dbmodel.Post.user_id == user_id)
        .order_by(dbmodel.Post.id.desc())
        .all()
    )

    result = []

    for post in posts_data:

        # -------------------
        # counts
        # -------------------

        likes_count = (
            db.query(dbmodel.Like)
            .filter(dbmodel.Like.post_id == post.id)
            .count()
        )

        saves_count = (
            db.query(dbmodel.Save)
            .filter(dbmodel.Save.post_id == post.id)
            .count()
        )

        followers_count = (
            db.query(dbmodel.Follow)
            .filter(dbmodel.Follow.following_id == post.user.id)
            .count()
        )

        following_count = (
            db.query(dbmodel.Follow)
            .filter(dbmodel.Follow.follower_id == post.user.id)
            .count()
        )

        # -------------------
        # states
        # -------------------

        is_liked = False
        is_saved = False
        is_following = False

        if current_user:

            is_liked = (
                db.query(dbmodel.Like)
                .filter(
                    dbmodel.Like.post_id == post.id,
                    dbmodel.Like.user_id == current_user
                )
                .first()
                is not None
            )

            is_saved = (
                db.query(dbmodel.Save)
                .filter(
                    dbmodel.Save.post_id == post.id,
                    dbmodel.Save.user_id == current_user
                )
                .first()
                is not None
            )

            is_following = (
                db.query(dbmodel.Follow)
                .filter(
                    dbmodel.Follow.follower_id == current_user,
                    dbmodel.Follow.following_id == post.user.id
                )
                .first()
                is not None
            )

        # -------------------
        # final response
        # -------------------

        result.append({

            "id": post.id,
            "title": post.title,
            "content": post.content,
            "user_id": post.user_id,

            "user": {
                "id": post.user.id,
                "email": post.user.email,
                "name": post.user.name,
                "username": post.user.username,
                "profile_title": post.user.profile_title,
                "profile_description": post.user.profile_description,
                "profile_image": post.user.profile_image,

                "followers_count": followers_count,
                "following_count": following_count,

                "is_following": is_following,
            },

            "images": [
                {
                    "id": image.id,
                    "image_url": image.image_url,
                    "public_id": image.public_id
                }
                for image in post.images
            ],

            "likes_count": likes_count,
            "saves_count": saves_count,

            "is_liked": is_liked,
            "is_saved": is_saved,
        })

    return result

# =========================
# DELETE POST
# =========================
@app.delete("/post/{post_id}")
def delete_post(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):

    # 1. Get post
    post = (
        db.query(dbmodel.Post)
        .filter(dbmodel.Post.id == post_id)
        .first()
    )

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # 2. Check ownership
    if post.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this post")

    # 3. Delete images (DB + optional Cloudinary)
    for img in post.images:
        try:
            # optional: delete from cloudinary
            # cloudinary.uploader.destroy(img.public_id)
            pass
        except Exception:
            pass

        db.delete(img)

    # 4. Delete post
    db.delete(post)
    db.commit()

    return {"message": "Post deleted successfully"}

# =========================
# LIKE POST
# =========================
@app.post("/like/{post_id}")
def like(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user),
):
    existing_like = (
        db.query(dbmodel.Like)
        .filter(
            dbmodel.Like.post_id == post_id,
            dbmodel.Like.user_id == user_id,
        )
        .first()
    )

    if existing_like is None:
        new_like = dbmodel.Like(
            post_id=post_id,
            user_id=user_id,
        )
        db.add(new_like)
        db.commit()

    likes_count = (
        db.query(dbmodel.Like)
        .filter(dbmodel.Like.post_id == post_id)
        .count()
    )

    return {
        "msg": "liked",
        "likes_count": likes_count,
        "is_liked": True,
    }


# =========================
# SAVE POST
# =========================
@app.post("/save/{post_id}")
def save(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    return crud.save_post(db, user_id, post_id)

@app.get("/user-following/{user_id}")
def get_user_following(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[int] = Depends(get_current_user_optional)
):

    user = (
        db.query(dbmodel.User)
        .filter(dbmodel.User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # get follow rows
    following_rows = (
        db.query(dbmodel.Follow)
        .filter(dbmodel.Follow.follower_id == user_id)
        .all()
    )

    result = []

    for row in following_rows:

        # get actual followed user
        following_user = (
            db.query(dbmodel.User)
            .filter(dbmodel.User.id == row.following_id)
            .first()
        )

        if not following_user:
            continue

        is_following = False

        if current_user:

            follow = (
                db.query(dbmodel.Follow)
                .filter(
                    dbmodel.Follow.follower_id == current_user,
                    dbmodel.Follow.following_id == following_user.id
                )
                .first()
            )

            is_following = follow is not None

        followers_count = (
            db.query(dbmodel.Follow)
            .filter(
                dbmodel.Follow.following_id == following_user.id
            )
            .count()
        )

        following_count = (
            db.query(dbmodel.Follow)
            .filter(
                dbmodel.Follow.follower_id == following_user.id
            )
            .count()
        )

        result.append({

            "id": following_user.id,
            "name": following_user.name,
            "username": following_user.username,
            "profile_title": following_user.profile_title,
            "profile_description": following_user.profile_description,
            "image_url": following_user.profile_image,

            "followers_count": followers_count,
            "following_count": following_count,

            "is_following": is_following,
        })

    return result


# =========================
# GET SAVED POSTS (FIXED)
# =========================
@app.get("/saved-posts", response_model=List[model.PostOut])
def get_saved_posts(
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    posts_data = (
        db.query(dbmodel.Post)
        .options(
            joinedload(dbmodel.Post.images),
            joinedload(dbmodel.Post.user),
        )
        .join(dbmodel.Save, dbmodel.Save.post_id == dbmodel.Post.id)
        .filter(dbmodel.Save.user_id == user_id)
        .order_by(dbmodel.Save.id.desc())
        .all()
    )

    result = []

    for post in posts_data:
        likes_count = db.query(dbmodel.Like).filter(
            dbmodel.Like.post_id == post.id
        ).count()

        saves_count = db.query(dbmodel.Save).filter(
            dbmodel.Save.post_id == post.id
        ).count()

        is_liked = db.query(dbmodel.Like).filter(
            dbmodel.Like.post_id == post.id,
            dbmodel.Like.user_id == user_id,
        ).first() is not None

        result.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "user_id": post.user_id,
            "user": post.user,
            "images": post.images,
            "likes_count": likes_count,
            "saves_count": saves_count,
            "is_liked": is_liked,
        })

    return result



# =========================
# UNSAVE POST
# =========================
@app.delete("/save/{post_id}")
def unsave(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):

    save = (
        db.query(dbmodel.Save)
        .filter(
            dbmodel.Save.user_id == user_id,
            dbmodel.Save.post_id == post_id
        )
        .first()
    )

    if not save:
        raise HTTPException(status_code=404, detail="Save not found")

    db.delete(save)
    db.commit()

    return {"msg": "unsaved"}

# =========================
# FOLLOW USER
# =========================

@app.post("/follow/{user_id}")
def follow(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)
):

    # prevent self follow
    if current_user == user_id:
        raise HTTPException(
            status_code=400,
            detail="You cannot follow yourself"
        )

    # check existing follow
    existing_follow = db.query(
        dbmodel.Follow
    ).filter(
        dbmodel.Follow.follower_id == current_user,
        dbmodel.Follow.following_id == user_id
    ).first()

    # already following
    if existing_follow:
        return {
            "message": "Already following",
            "is_following": True
        }

    # create follow
    new_follow = dbmodel.Follow(
        follower_id=current_user,
        following_id=user_id
    )

    db.add(new_follow)
    db.commit()

    return {
        "message": "Followed successfully",
        "is_following": True
    }
# =========================
# UNFOLLOW USER         
# =========================
@app.delete("/follow/{user_id}")
def unfollow(

    user_id: int,

    db: Session = Depends(get_db),
    current_user: int = Depends(get_current_user)

):

    follow = db.query(
        dbmodel.Follow
    ).filter(
        dbmodel.Follow.follower_id == current_user,
        dbmodel.Follow.following_id == user_id
    ).first()

    if not follow:
        raise HTTPException(
            status_code=404,
            detail="Follow not found"
        )

    db.delete(follow)
    db.commit()

    return {"msg": "unfollowed"}    # <-- DELETE TO HERE # <-- DELETE TO HERE

# =========================
# UNLIKE POST
# =========================

@app.delete("/like/{post_id}")
def unlike(
    post_id: int,
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    like = db.query(dbmodel.Like).filter(
        dbmodel.Like.user_id == user_id,
        dbmodel.Like.post_id == post_id
    ).first()

    if like:
        db.delete(like)
        db.commit()

    likes_count = (
        db.query(dbmodel.Like)
        .filter(dbmodel.Like.post_id == post_id)
        .count()
    )

    return {
        "msg": "unliked",
        "likes_count": likes_count,
        "is_liked": False,
    }





# =========================
# UNFOLLOW USER
# =========================


# ---------- RAG SEARCH ----------




@app.get("/search-users")
def search_users(query: str, db: Session = Depends(get_db)):
    query_embedding = get_embedding(query)
    emb_str = to_pgvector(query_embedding)

    rows = db.execute(text("""
        SELECT id, username, profile_title, profile_description,
               embedding <-> :emb AS distance
        FROM users
        WHERE embedding IS NOT NULL
        ORDER BY embedding <-> :emb
        LIMIT 10
    """), {"emb": emb_str}).fetchall()

    results = [
        {
            "id": r[0],
            "username": r[1],
            "profile_title": r[2],
            "desc": r[3],
            "score": float(r[4])
        }
        for r in rows
    ]

    if not results:
        fallback = db.execute(text("""
            SELECT id, username, profile_title, profile_description
            FROM users
            WHERE username ILIKE :q OR profile_description ILIKE :q
            LIMIT 10
        """), {"q": f"%{query}%"}).fetchall()

        return [
            {
                "id": r[0],
                "username": r[1],
                "profile_title": r[2],
                "desc": r[3],
                "score": 999
            }
            for r in fallback
        ]

    try:
        final = rerank_results(query, results)
        return final if final else results
    except Exception as e:
        print("RERANK ERROR:", e)
        return results


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

    results = [
        {
            "id": r[0],
            "title": r[1],
            "content": r[2],
            "score": float(r[3])
        }
        for r in rows
    ]

    # fallback if empty
    if not results:
        fallback = db.execute(text("""
            SELECT id, title, content
            FROM posts
            WHERE title ILIKE :q OR content ILIKE :q
            LIMIT 10
        """), {"q": f"%{query}%"}).fetchall()

        return [
            {
                "id": r[0],
                "title": r[1],
                "content": r[2],
                "score": 999
            }
            for r in fallback
        ]

    return results


@app.post("/chat", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    db: Session = Depends(get_db),
    # Remove the line below if you want unauthenticated chat:
    # user_id: int = Depends(get_current_user)
):
    """
    RAG-powered chat endpoint.
    
    Flow:
    1. Vector search users + posts for relevant context
    2. Inject context into LLM system prompt
    3. LLM answers using context + general knowledge + chat history
    
    Body:
    {
        "query": "Who are the best React developers?",
        "history": [
            {"role": "user", "content": "previous question"},
            {"role": "assistant", "content": "previous answer"}
        ]
    }
    """
    history = [{"role": m.role, "content": m.content} for m in request.history]
    
    answer = chat_with_rag(
        query=request.query,
        history=history,
        db=db
    )
    
    # Optionally return the context used (useful for debugging / "sources" UI)
    context = retrieve_context(request.query, db)
    
    return ChatResponse(answer=answer, context_used=context)
 
 
# ---------- CONTEXT PREVIEW (optional debug endpoint) ----------
@app.get("/context-preview")
def context_preview(query: str, db: Session = Depends(get_db)):
    """
    Preview what DB context would be injected for a given query.
    Useful for debugging your RAG pipeline.
    """
    context = retrieve_context(query, db)
    return {"query": query, "context": context}





# =========================
# CREATE TASK
# =========================

@app.post("/create-task")
def create_task(

    title: str = Form(...),
    content: str = Form(...),

    files: List[UploadFile] = File([]),

    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)

):

    user = db.query(dbmodel.User).filter(
        dbmodel.User.id == user_id
    ).first()

    task = dbmodel.Task(
        title=title,
        content=content,
        user_id=user_id
    )

    db.add(task)
    db.commit()
    db.refresh(task)

    # upload images
    for f in files:

        uploaded = upload_image(file=f)

        image = dbmodel.TaskImage(
            task_id=task.id,
            image_url=uploaded["url"],
            public_id=uploaded["public_id"]
        )

        db.add(image)

    db.commit()

    return {
        "message": "Task created",
        "task_id": task.id
    }


# =========================
# GET TASKS
# =========================

@app.get("/tasks")
def get_tasks(db: Session = Depends(get_db)):

    tasks = (
        db.query(dbmodel.Task)
        .options(
            joinedload(dbmodel.Task.user),
            joinedload(dbmodel.Task.images),
            joinedload(dbmodel.Task.solutions)
                .joinedload(dbmodel.TaskSolution.user),

            joinedload(dbmodel.Task.solutions)
                .joinedload(dbmodel.TaskSolution.replies)
                .joinedload(dbmodel.TaskSolution.user),
        )
        .order_by(dbmodel.Task.id.desc())
        .all()
    )

    result = []

    def build_reply(reply):

        return {
            "id": reply.id,
            "content": reply.content,
            "parent_id": reply.parent_id,

            "user": {
                "id": reply.user.id if reply.user else None,
                "username": reply.user.username if reply.user else "",
                "name": reply.user.name if reply.user else "",
                "profile_image": reply.user.profile_image if reply.user else "",
            }
        }

    for task in tasks:

        top_level_solutions = [
            s for s in task.solutions
            if s.parent_id is None
        ]

        solutions_data = []

        for sol in top_level_solutions:

            replies_data = []

            for r in sol.replies:
                replies_data.append(build_reply(r))

            solutions_data.append({

                "id": sol.id,
                "content": sol.content,
                "parent_id": sol.parent_id,

                "user": {
                    "id": sol.user.id if sol.user else None,
                    "username": sol.user.username if sol.user else "",
                    "name": sol.user.name if sol.user else "",
                    "profile_image": sol.user.profile_image if sol.user else "",
                },

                "replies": replies_data
            })

        result.append({

            "id": task.id,
            "title": task.title,
            "content": task.content,

            "created_at": (
                task.created_at.isoformat()
                if task.created_at else None
            ),

            "user_id": task.user.id,

            "user": {
                "id": task.user.id,
                "username": task.user.username,
                "name": task.user.name,
                "profile_image": task.user.profile_image
            },

            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url
                }
                for img in task.images
            ],

            "solutions": solutions_data
        })

    return result


@app.post("/task-solution/{task_id}")
def add_solution(
    task_id: int,
    content: str = Form(...),
    parent_id: Optional[int] = Form(None),   # ADD THIS
    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)
):
    task = db.query(dbmodel.Task).filter(dbmodel.Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    solution = dbmodel.TaskSolution(
        task_id=task_id,
        user_id=user_id,
        content=content,
        parent_id=parent_id   # ADD THIS
    )

    db.add(solution)
    db.commit()
    return {"message": "Solution added"}

# =========================
# DELETE TASK
# =========================

@app.delete("/task/{task_id}")
def delete_task(

    task_id: int,

    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)

):

    task = (
        db.query(dbmodel.Task)
        .options(
            joinedload(dbmodel.Task.images),
            joinedload(dbmodel.Task.solutions)
        )
        .filter(dbmodel.Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    # only owner can delete
    if task.user_id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Not allowed"
        )

    # delete images from cloudinary (optional)
    for image in task.images:

        try:
            # cloudinary.uploader.destroy(image.public_id)
            pass
        except:
            pass

        db.delete(image)

    # delete solutions
    for solution in task.solutions:
        db.delete(solution)

    # delete task
    db.delete(task)

    db.commit()

    return {
        "message": "Task deleted successfully"
    }


# =========================
# MY TASKS
# =========================

@app.get("/my-tasks")
def my_tasks(

    db: Session = Depends(get_db),
    user_id: int = Depends(get_current_user)

):

    tasks = (
        db.query(dbmodel.Task)
        .options(
            joinedload(dbmodel.Task.user),
            joinedload(dbmodel.Task.images),
            joinedload(dbmodel.Task.solutions)
        )
        .filter(dbmodel.Task.user_id == user_id)
        .order_by(dbmodel.Task.id.desc())
        .all()
    )

    result = []

    for task in tasks:

        result.append({

            "id": task.id,
            "title": task.title,
            "content": task.content,

            "user": {
                "id": task.user.id,
                "username": task.user.username,
                "name": task.user.name,
                "profile_image": task.user.profile_image
            },

            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url
                }
                for img in task.images
            ],

            "solutions_count": len(task.solutions)
        })

    return result


# =========================
# GET TASKS BY USER ID
# =========================

@app.get("/user-tasks/{user_id}")
def get_user_tasks(

    user_id: int,

    db: Session = Depends(get_db)

):

    user = (
        db.query(dbmodel.User)
        .filter(dbmodel.User.id == user_id)
        .first()
    )

    if not user:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    tasks = (
        db.query(dbmodel.Task)
        .options(
            joinedload(dbmodel.Task.user),
            joinedload(dbmodel.Task.images),
            joinedload(dbmodel.Task.solutions)
        )
        .filter(dbmodel.Task.user_id == user_id)
        .order_by(dbmodel.Task.id.desc())
        .all()
    )

    result = []

    for task in tasks:

        result.append({

            "id": task.id,
            "title": task.title,
            "content": task.content,

            "user": {
                "id": task.user.id,
                "username": task.user.username,
                "name": task.user.name,
                "profile_image": task.user.profile_image
            },

            "images": [
                {
                    "id": img.id,
                    "image_url": img.image_url
                }
                for img in task.images
            ],

            "solutions_count": len(task.solutions)
        })

    return result

# =========================
# GET SINGLE TASK
# =========================

@app.get("/task/{task_id}")
def get_single_task(

    task_id: int,

    db: Session = Depends(get_db)

):

    task = (
        db.query(dbmodel.Task)
        .options(
            joinedload(dbmodel.Task.user),
            joinedload(dbmodel.Task.images),
            joinedload(dbmodel.Task.solutions)
            .joinedload(dbmodel.TaskSolution.user)
        )
        .filter(dbmodel.Task.id == task_id)
        .first()
    )

    if not task:
        raise HTTPException(
            status_code=404,
            detail="Task not found"
        )

    return {

        "id": task.id,
        "title": task.title,
        "content": task.content,

        "user": {
            "id": task.user.id,
            "username": task.user.username,
            "name": task.user.name,
            "profile_image": task.user.profile_image
        },

        "images": [
            {
                "id": img.id,
                "image_url": img.image_url
            }
            for img in task.images
        ],

        "solutions": [
            {
                "id": sol.id,
                "content": sol.content,

                "user": {
                    "id": sol.user.id,
                    "username": sol.user.username,
                    "name": sol.user.name,
                    "profile_image": sol.user.profile_image
                }
            }
            for sol in task.solutions
        ]
    }