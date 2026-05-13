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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# pgvector only — no model imports here
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    print("✅ pgvector ready")
except Exception as e:
    print("⚠️ pgvector error:", e)