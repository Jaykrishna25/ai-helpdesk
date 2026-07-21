"""Semantic retrieval over the approved KnowledgeBase.

Demo: in-Python cosine ranking over embeddings stored on each KB row.
Production: Amazon OpenSearch k-NN or pgvector ivfflat index (see schema.sql).
"""
from .embeddings import embed, cosine
from ..models import KnowledgeBase

def search(db, query: str, department_id=None, top_k: int = 4):
    q = embed(query)
    rows = db.query(KnowledgeBase).filter(KnowledgeBase.status == "approved")
    if department_id:
        rows = rows.filter(KnowledgeBase.department_id == department_id)
    scored = []
    for kb in rows.all():
        if not kb.embedding:
            continue
        scored.append((cosine(q, kb.embedding), kb))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{"score": round(float(s), 4), "kb": kb} for s, kb in scored[:top_k]]
