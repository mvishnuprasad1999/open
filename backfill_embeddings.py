from src.db_core.db import SessionLocal
from src.db_core.dbmodel import User, Post
from src.db_core.embeddings import get_embedding

def backfill_embeddings():
    db = SessionLocal()
    try:
        print("🔄 Processing Users...")
        users = db.query(User).all()
        print(f"Found {len(users)} users")
        
        for user in users:
            text = f"{user.username or ''} {user.profile_description or ''}".strip()
            if text:
                try:
                    user.embedding = get_embedding(text)
                    print(f"✅ User {user.id} embedded")
                except Exception as e:
                    print(f"❌ Error on User {user.id}: {e}")

        print("\n🔄 Processing Posts...")
        posts = db.query(Post).all()
        print(f"Found {len(posts)} posts")
        
        for post in posts:
            text = f"{post.title or ''} {post.content or ''}".strip()
            if text:
                try:
                    post.embedding = get_embedding(text)
                    print(f"✅ Post {post.id} embedded")
                except Exception as e:
                    print(f"❌ Error on Post {post.id}: {e}")

        db.commit()
        print("\n🎉 SUCCESS!")
    except Exception as e:
        print(f"\n💥 ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    backfill_embeddings()
