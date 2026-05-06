# src/db_core/embeddings.py

import os
import httpx
import numpy as np
from dotenv import load_dotenv

load_dotenv()

def get_embedding(text: str) -> list:
    token = os.getenv('HF_TOKEN', '')
    if not token:
        raise ValueError("HF_TOKEN not found")

    api_url = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    response = httpx.post(
        api_url,
        json={"inputs": text},
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"HF error {response.status_code}: {response.text[:100]}")

    result = response.json()

    # Mean pooling
    if isinstance(result, list) and len(result) > 0:
        if isinstance(result[0], list):
            embedding = np.mean(result, axis=0)
            return embedding.tolist()
        return result

    raise Exception("Invalid embedding response")


# 🔥 IMPORTANT FIX
def to_pgvector(vec: list) -> str:
    return "[" + ",".join(map(str, vec)) + "]"