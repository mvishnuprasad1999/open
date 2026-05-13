# from sqlalchemy import create_engine, text
# from sqlalchemy.orm import sessionmaker, declarative_base
# from src.db_core.setting import setup

# Base = declarative_base()

# engine = create_engine(
#     setup.DB_CONNECTION,
#     pool_size=5,
#     max_overflow=10,
#     pool_pre_ping=True
# )

# # enable pgvector
# try:
#     with engine.connect() as conn:
#         conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
#         conn.commit()
#     print("✅ pgvector ready")
# except Exception as e:
#     print("⚠️ pgvector error:", e)

# SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# def get_db():
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()


from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from src.db_core.setting import setup

Base = declarative_base()

engine = create_engine(
    setup.DB_CONNECTION,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

# =========================
# DB SESSION
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# PGVECTOR SETUP
# =========================
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    print("✅ pgvector ready")
except Exception as e:
    print("⚠️ pgvector error:", e)


# =========================
# IMPORTANT FIX: LOAD MODELS
# =========================
# 🔥 THIS IS THE KEY FIX (ALL MODELS MUST BE IMPORTED)
from src.db_core import dbmodel

# If Task is in separate file, ensure it's explicitly imported too:
try:
    from src.db_core.dbmodel import Task, TaskImage, TaskSolution
except Exception as e:
    print("⚠️ Task models import issue:", e)


# =========================
# CREATE ALL TABLES
# =========================
Base.metadata.create_all(bind=engine)

print("✅ All tables ensured: users, posts, tasks, likes, saves, follows")