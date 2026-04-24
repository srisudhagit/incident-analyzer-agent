import json
import os
from typing import Optional, Literal
from dotenv import load_dotenv
from pydantic import BaseModel
from openai import OpenAI
from app.state import IncidentState

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

ToolName = Literal["get_logs", "get_metrics", "get_recent_deployments"]


class PlannerDecision(BaseModel):
    next_tool: Optional[ToolName]
    reason: str
    enough_evidence: bool


SYSTEM_PROMPT = """
You are an incident investigation planner who makes efficient decisions.

Available tools:
- get_logs: concrete error messages and signatures
- get_metrics: capacity, latency, saturation, error spikes
- get_recent_deployments: regressions after releases

Rules:
- Prefer one tool at a time
- Prefer stopping after 2 steps when evidence is strong
- Only use deployments if logs/metrics are inconclusive
- Do not repeat tools already called
- Return JSON only with:
  next_tool, reason, enough_evidence
"""


def plan_next_step(state: IncidentState):
    prompt = f"""
Service: {state.service}
Symptom: {state.symptom}

Tools already called:
{state.tools_called if state.tools_called else "None"}

Evidence so far:
{chr(10).join(f'- {e}' for e in state.evidence) if state.evidence else "None"}

Decide the next best tool or stop.

Evidence sufficiency policy:
- Stop if at least 2 distinct tools have returned useful evidence.
- Stop if current evidence contains one direct failure signal and one supporting signal.
- Continue if evidence is missing, failed, weak, or contradictory.
- Do not repeat already-called tools.
- Only use deployments when change correlation is needed.

Return JSON only:
{{
  "next_tool": "get_logs | get_metrics | get_recent_deployments | null",
  "reason": "string",
  "enough_evidence": true/false
}}
"""

    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]
    )

    usage = response.usage
    data = json.loads(response.output_text)
    decision = PlannerDecision(**data)

    if decision.next_tool in state.tools_called:
        return PlannerDecision(
            next_tool=None,
            reason="Tool already used. Stopping to avoid repeated tool calls.",
            enough_evidence=True
        ), usage

    return decision, usage