from src.db_core.db import Base, engine

# Import all models here so they register to Base
from src.db_core.dbmodel import (
    User, Post, PostImage,
    Like, Save, Follow,
    Task, TaskImage, TaskSolution
)

def init():
    Base.metadata.create_all(bind=engine)
    print("✅ All tables ensured")