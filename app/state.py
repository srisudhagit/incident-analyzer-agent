from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from uuid import uuid4

ToolName = Literal["get_logs", "get_metrics", "get_recent_deployments"]


class StepTrace(BaseModel):
    step: int
    chosen_tool: Optional[ToolName]
    reason: str
    observation_summary: Optional[str] = None


class IncidentState(BaseModel):
    investigation_id: str = Field(
        default_factory=lambda: str(uuid4())
    )

    service: str
    symptom: str

    tools_called: List[ToolName] = Field(default_factory=list)
    steps_taken: List[StepTrace] = Field(default_factory=list)

    evidence: List[str] = Field(default_factory=list)
    sources: List[str] = Field(default_factory=list)

    retrieved_context: List[Dict] = Field(default_factory=list)

    enough_evidence: bool = False
    