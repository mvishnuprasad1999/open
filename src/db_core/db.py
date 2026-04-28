from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from src.db_core.setting import setup

Base = declarative_base()

engine = create_engine(
    url=setup.DB_CONNECTION,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True
)

# Enable pgvector extension
try:
    with engine.connect() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        conn.commit()
    print("✅ pgvector is ready!")
except Exception as e:
    print(f"⚠️ pgvector: {e}")

Local_session = sessionmaker(bind=engine)

def get_db():
    session = Local_session()
    try:
        yield session
    finally:
        session.close()