"""Central configuration. Reads env vars; safe local defaults for demo."""
import os

class Settings:
    APP_NAME = "AI Student Help Desk"
    # SQLite for zero-config demo; swap DATABASE_URL for Postgres+pgvector in prod
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./helpdesk.db")
    JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALG = "HS256"
    JWT_EXPIRE_MIN = int(os.getenv("JWT_EXPIRE_MIN", "480"))
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.85"))
    TOP_K = int(os.getenv("TOP_K", "4"))
    # Confidence weights: w1*retrieval + w2*similarity + w3*llm
    W_RETRIEVAL = 0.4
    W_SIMILARITY = 0.3
    W_LLM = 0.3
    EMBED_DIM = 384
    # Notifications: 'console' logs to DB; 'ses' uses Amazon SES (boto3)
    NOTIFY_BACKEND = os.getenv("NOTIFY_BACKEND", "console")

settings = Settings()
