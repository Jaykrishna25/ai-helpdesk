"""Embedding provider.

Production: sentence-transformers 'all-MiniLM-L6-v2' (384-dim) or Amazon
Bedrock Titan embeddings. Demo fallback: a deterministic hashed bag-of-words
vector so the system runs fully offline with cosine similarity behaving
sensibly. The interface is identical, so swapping in a real model requires no
call-site changes.
"""
import hashlib
import math
import re
from ..config import settings

_DIM = settings.EMBED_DIM
_model = None
_backend = "hash"

def _try_load_model():
    global _model, _backend
    if _model is not None:
        return
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
        _model = SentenceTransformer("all-MiniLM-L6-v2")
        _backend = "minilm"
    except Exception:
        _model = False  # sentinel: unavailable
        _backend = "hash"

_TOKEN = re.compile(r"[a-z0-9]+")

def _hash_embed(text: str):
    vec = [0.0] * _DIM
    tokens = _TOKEN.findall(text.lower())
    for i, tok in enumerate(tokens):
        # unigram + positional bigram hashing for a little word-order signal
        for feat in (tok, tokens[i - 1] + "_" + tok if i else "^" + tok):
            h = int(hashlib.md5(feat.encode()).hexdigest(), 16)
            vec[h % _DIM] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]

def embed(text: str):
    _try_load_model()
    if _model:
        v = _model.encode(text, normalize_embeddings=True)
        return v.tolist()
    return _hash_embed(text)

def backend_name():
    _try_load_model()
    return _backend

def cosine(a, b):
    return sum(x * y for x, y in zip(a, b))  # inputs are L2-normalized
