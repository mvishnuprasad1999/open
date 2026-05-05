from src.db_core.embeddings import get_embedding

try:
    print("🔄 Testing Groq embedding...")
    result = get_embedding("Hello, testing Groq!")
    print(f"✅ Success! Embedding length: {len(result)}")
    print(f"First 5 values: {result[:5]}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
