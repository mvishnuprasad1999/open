# src/db_core/embeddings.py

import os
import httpx
import numpy as np
from dotenv import load_dotenv

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

API_URL = "https://router.huggingface.co/hf-inference/models/sentence-transformers/all-MiniLM-L6-v2/pipeline/feature-extraction"


def get_embedding(text: str) -> list:
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }

    response = httpx.post(
        API_URL,
        json={"inputs": text},
        headers=headers,
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(response.text)

    result = response.json()

    # mean pooling
    if isinstance(result[0], list):
        return np.mean(result, axis=0).tolist()

    return result


# 🔥 REQUIRED FIX
def to_pgvector(vec: list) -> str:
    return "[" + ",".join(map(str, vec)) + "]"