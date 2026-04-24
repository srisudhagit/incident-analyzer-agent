from typing import List, Literal
from pydantic import BaseModel


class InvestigateRequest(BaseModel):
    service: str
    symptom: str


class InvestigateResponse(BaseModel):
    likely_root_cause: str
    confidence: Literal["low", "medium", "high"]
    steps_taken: List[str]
    evidence: List[str]
    recommended_actions: List[str]
    sources: List[str]