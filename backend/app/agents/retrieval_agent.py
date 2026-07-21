"""Agent 3 - Knowledge Retrieval. Semantic top-K search over approved KB."""
from .base import BaseAgent, AgentContext
from ..rag.vector_store import search
from ..config import settings

class KnowledgeRetrievalAgent(BaseAgent):
    name = "KnowledgeRetrievalAgent"
    def run(self, ctx: AgentContext, db=None):
        ctx.retrieved = search(db, ctx.normalized_query,
                               department_id=ctx.department_id, top_k=settings.TOP_K)
        top = ctx.retrieved[0]["score"] if ctx.retrieved else 0.0
        ctx.log(self.name, f"retrieved={len(ctx.retrieved)} top_score={top}")
        return ctx
