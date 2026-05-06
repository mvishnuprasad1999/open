# src/llm/rerank.py

import os
import httpx

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")


def rerank_results(query: str, results: list):
    if not OPENROUTER_API_KEY:
        return results  # fallback

    prompt = f"""
You are a smart search ranking AI.

Query: {query}

Results:
{results}

Return only the most relevant results in order (max 5).
"""

    response = httpx.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "mistralai/mistral-7b-instruct",
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=30
    )

    try:
        return response.json()["choices"][0]["message"]["content"]
    except:
        return results