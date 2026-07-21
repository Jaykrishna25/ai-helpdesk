"""Agent 4 - RAG Response. Grounds an answer in retrieved KB chunks.
Production: prompt-augmented LLM (Bedrock Claude / GPT) with citation. Demo:
returns the best-matching approved answer verbatim with source grounding, so
responses are always faithful (no hallucination possible).
"""
from .base import BaseAgent, AgentContext

class RAGResponseAgent(BaseAgent):
    name = "RAGResponseAgent"
    def run(self, ctx: AgentContext, db=None):
        if ctx.retrieved:
            best = ctx.retrieved[0]["kb"]
            src = best.source_url or f"KB#{best.knowledge_id}"
            ctx.answer = f"{best.answer}\n\n(Source: {src})"
        else:
            ctx.answer = ""
        ctx.log(self.name, f"answer_len={len(ctx.answer)}")
        return ctx
