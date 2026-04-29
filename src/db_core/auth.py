from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from src.db_core.setting import setup

SECRET_KEY = setup.SECRET_KEY
ALGORITHM = setup.ALGORITHM

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Hash
# def hash_password(password: str):
#     return pwd_context.hash(password)

# # Verify
# def verify_password(plain, hashed):
#     return pwd_context.verify(plain, hashed)
import bcrypt

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )

# Token
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=60)

    to_encode.update({
        "exp": expire,
        "sub": str(data["sub"])   # ✅ always string
    })

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Get current user
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        return int(user_id)   # ✅ return int directly

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")