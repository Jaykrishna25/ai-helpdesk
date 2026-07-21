"""Agent 5 - Confidence Evaluation.
Confidence = 0.4*RetrievalScore + 0.3*SimilarityScore + 0.3*LLMConfidence
"""
from .base import BaseAgent, AgentContext
from ..config import settings

class ConfidenceEvaluationAgent(BaseAgent):
    name = "ConfidenceEvaluationAgent"
    def run(self, ctx: AgentContext, db=None):
        if not ctx.retrieved:
            ctx.confidence = 0.0
            ctx.log(self.name, "no retrieval -> conf=0")
            return ctx
        top = ctx.retrieved[0]["score"]                     # RetrievalScore
        # SimilarityScore: margin between #1 and #2 sharpens confidence
        second = ctx.retrieved[1]["score"] if len(ctx.retrieved) > 1 else 0.0
        similarity = max(0.0, min(1.0, top + (top - second)))
        llm_conf = ctx.intent_conf                          # proxy for LLM self-confidence
        c = (settings.W_RETRIEVAL * top +
             settings.W_SIMILARITY * similarity +
             settings.W_LLM * llm_conf)
        ctx.confidence = round(min(c, 0.99), 3)
        ctx.log(self.name, f"retrieval={top} sim={round(similarity,3)} llm={llm_conf} -> conf={ctx.confidence}")
        return ctx
