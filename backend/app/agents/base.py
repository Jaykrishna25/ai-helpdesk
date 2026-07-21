"""Base agent + shared message envelope for inter-agent communication."""
from dataclasses import dataclass, field
from typing import Any, Dict

@dataclass
class AgentContext:
    """Blackboard passed between agents during one request (shared memory)."""
    student_id: str = ""
    session_id: str = ""
    department_id: int | None = None
    query: str = ""
    normalized_query: str = ""
    intent: str = "Unknown"
    intent_conf: float = 0.0
    entities: Dict[str, Any] = field(default_factory=dict)
    retrieved: list = field(default_factory=list)
    answer: str = ""
    confidence: float = 0.0
    decision: str = ""          # 'answer' | 'ticket'
    ticket_id: str | None = None
    trace: list = field(default_factory=list)  # audit of agent hops

    def log(self, agent: str, msg: str):
        self.trace.append({"agent": agent, "msg": msg})

class BaseAgent:
    name = "BaseAgent"
    def run(self, ctx: AgentContext, db=None) -> AgentContext:
        raise NotImplementedError
