# src/rag_chat.py
# RAG + LLM Chat Service
# Add this file to your project, then wire the router into main.py

import os
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import text
from src.db_core.embeddings import get_embedding, to_pgvector

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "openrouter/free"  


# ─────────────────────────────────────────────
# 1. Vector search: fetch relevant users + posts
# ─────────────────────────────────────────────
def retrieve_context(query: str, db: Session, top_k: int = 5) -> str:
    """
    Embeds the query, runs similarity search against users and posts,
    and returns a formatted context string for the LLM.
    """
    query_embedding = get_embedding(query)
    emb_str = to_pgvector(query_embedding)

    # --- Similar users ---
    user_rows = db.execute(text("""
        SELECT id, name, username, profile_title, profile_description,
               embedding <-> :emb AS distance
        FROM users
        WHERE embedding IS NOT NULL
        ORDER BY embedding <-> :emb
        LIMIT :k
    """), {"emb": emb_str, "k": top_k}).fetchall()

    # --- Similar posts ---
    post_rows = db.execute(text("""
        SELECT p.id, p.title, p.content, u.username,
               p.embedding <-> :emb AS distance
        FROM posts p
        JOIN users u ON p.user_id = u.id
        WHERE p.embedding IS NOT NULL
        ORDER BY p.embedding <-> :emb
        LIMIT :k
    """), {"emb": emb_str, "k": top_k}).fetchall()

    # --- Build context string ---
    context_parts = []

    if user_rows:
        context_parts.append("### Relevant Users Found in Database:")
        for r in user_rows:
            context_parts.append(
                f"- **{r[2]}** ({r[1]}): {r[3] or 'No title'} | {r[4] or 'No description'}"
            )

    if post_rows:
        context_parts.append("\n### Relevant Posts Found in Database:")
        for r in post_rows:
            context_parts.append(
                f"- Post by @{r[3]}: **{r[1]}**\n  {r[2][:300]}{'...' if len(r[2]) > 300 else ''}"
            )

    if not context_parts:
        return "No relevant data found in the database for this query."

    return "\n".join(context_parts)


# ─────────────────────────────────────────────
# 2. LLM call with RAG context + chat history
# ─────────────────────────────────────────────
def build_system_prompt(context: str) -> str:
    return f"""You are a helpful AI assistant for a social platform.

You have access to the following real data from the platform's database:

{context}

Instructions:
- Use the database context above to answer accurately about users and posts on this platform.
- If the question is about something NOT in the database, answer using your general knowledge.
- Be concise, friendly, and helpful.
- When mentioning users, refer to them by @username.
- If asked a follow-up question, use both the context and conversation history to answer.
"""


def chat_with_rag(
    query: str,
    history: list,   # list of {{"role": "user"|"assistant", "content": str}}
    db: Session
) -> str:
    """
    Full RAG pipeline:
    1. Retrieve context from DB via vector search
    2. Build system prompt with context
    3. Send to LLM with full conversation history
    4. Return answer
    """

    # Step 1: Retrieve DB context
    context = retrieve_context(query, db)

    # Step 2: Build messages array
    system_prompt = build_system_prompt(context)

    messages = [{"role": "system", "content": system_prompt}]

    # Include previous conversation turns (last 10 for token efficiency)
    for turn in history[-10:]:
        messages.append({"role": turn["role"], "content": turn["content"]})

    # Add current user question
    messages.append({"role": "user", "content": query})

    # Step 3: Call LLM
    try:
        response = httpx.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://your-app.com",  # Update this
            },
            json={
                "model": LLM_MODEL,
                "messages": messages,
                "max_tokens": 1024,
                "temperature": 0.7,
            },
            timeout=60,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating response: {str(e)}"