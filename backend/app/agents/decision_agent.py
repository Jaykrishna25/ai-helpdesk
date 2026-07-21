"""Agent 6 - Decision. Answer vs. escalate-to-ticket on the 85% threshold."""
from .base import BaseAgent, AgentContext
from ..config import settings

class DecisionAgent(BaseAgent):
    name = "DecisionAgent"
    def run(self, ctx: AgentContext, db=None):
        ctx.decision = "answer" if ctx.confidence >= settings.CONFIDENCE_THRESHOLD and ctx.answer else "ticket"
        ctx.log(self.name, f"decision={ctx.decision} (thr={settings.CONFIDENCE_THRESHOLD})")
        return ctx
