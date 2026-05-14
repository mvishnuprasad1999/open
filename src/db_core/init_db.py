from src.db_core.db import Base, engine
from sqlalchemy import text

# Import all models here so they register to Base
from src.db_core.dbmodel import (
    User, Post, PostImage,
    Like, Save, Follow,
    Task, TaskImage, TaskSolution
)

def init():
    Base.metadata.create_all(bind=engine)
    print("✅ All tables ensured")

    # ✅ ADD THIS — safely adds created_at if it doesn't exist yet
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE task_solutions
            ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();
        """))
        conn.commit()
    print("✅ task_solutions.created_at ensured")