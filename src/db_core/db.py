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

# =========================
# PGVECTOR EXTENSION
# =========================
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    print("✅ pgvector ready")
except Exception as e:
    print("⚠️ pgvector error:", e)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)


# =========================
# DB SESSION DEPENDENCY
# =========================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# =========================
# AUTO TABLE CREATION (FIX)
# =========================
# IMPORTANT: must import models BEFORE create_all
from src.db_core import dbmodel  # 👈 THIS IS REQUIRED

Base.metadata.create_all(bind=engine)

print("✅ All tables ensured (users, posts, tasks, etc.)")