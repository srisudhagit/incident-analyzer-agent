"""
RCA (Root Cause Analysis) Synthesis Module

Converts investigation evidence into final diagnosis with:
- Likely root cause
- Confidence level (low/medium/high)
- Recommended actions
- Analysis summary

Now includes:
- step trace
- retrieved RAG context
- sources
"""

import json
import os
import logging
from typing import Literal, Any
from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class RCAResult(BaseModel):
    service: str
    symptom: str
    likely_root_cause: str
    confidence: Literal["low", "medium", "high"]
    recommended_actions: list[str]
    analysis_summary: str


RCA_SYSTEM_PROMPT = """
You are an expert backend incident investigator synthesizing evidence into a root cause analysis.

You will receive:
- service
- symptom
- tools called
- step trace
- evidence collected
- retrieved runbooks / prior incidents
- sources

Your job:
1. infer the most likely technical root cause
2. estimate confidence (low / medium / high)
3. recommend 3-5 concrete remediation actions
4. provide a short analysis summary

Rules:
- be evidence-based
- use retrieved context only as supporting evidence, not as unquestioned truth
- if evidence is weak or conflicting, lower confidence
- do not invent facts not present in evidence or retrieved context
- return JSON only

Return exactly:
{
  "likely_root_cause": "string",
  "confidence": "low | medium | high",
  "recommended_actions": ["string", "string"],
  "analysis_summary": "string"
}
"""


def _format_steps(steps_taken: list[dict[str, Any]]) -> str:
    if not steps_taken:
        return "None"

    return "\n".join(
        f"- step {step.get('step')}: "
        f"tool={step.get('chosen_tool')} | "
        f"reason={step.get('reason')} | "
        f"observation={step.get('observation_summary')}"
        for step in steps_taken
    )


def _format_retrieved_context(retrieved_context: list[dict[str, Any]]) -> str:
    if not retrieved_context:
        return "None"

    blocks = []
    for item in retrieved_context:
        source = item.get("source", "unknown")
        content = item.get("content", "")
        blocks.append(f"[{source}]\n{content}")

    return "\n\n".join(blocks)


def synthesize_rca(
    service: str,
    symptom: str,
    evidence: list[str],
    tools_called: list[str],
    steps_taken: list[dict[str, Any]] | None = None,
    retrieved_context: list[dict[str, Any]] | None = None,
    sources: list[str] | None = None,
) -> RCAResult:
    """
    Synthesize root cause analysis from investigation evidence and retrieved context.
    """

    steps_taken = steps_taken or []
    retrieved_context = retrieved_context or []
    sources = sources or []

    prompt = f"""
Incident Investigation Summary

Service: {service}
Symptom: {symptom}

Tools Called:
{", ".join(tools_called) if tools_called else "None"}

Step Trace:
{_format_steps(steps_taken)}

Evidence Collected:
{chr(10).join(f"- {e}" for e in evidence) if evidence else "None"}

Retrieved Context:
{_format_retrieved_context(retrieved_context)}

Sources:
{chr(10).join(f"- {s}" for s in sources) if sources else "None"}

Based on this investigation, synthesize a root cause analysis.
Return JSON with:
likely_root_cause, confidence, recommended_actions, analysis_summary
"""

    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": RCA_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]
        )

        usage = response.usage
        content = response.output_text
        data = json.loads(content)

        return RCAResult(
            service=service,
            symptom=symptom,
            likely_root_cause=data.get("likely_root_cause", "Unknown"),
            confidence=data.get("confidence", "low"),
            recommended_actions=data.get("recommended_actions", []),
            analysis_summary=data.get("analysis_summary", "")
        ), usage

    except json.JSONDecodeError as e:
        logging.error("Failed to parse RCA response: %s", e)
        return RCAResult(
            service=service,
            symptom=symptom,
            likely_root_cause="Unable to synthesize RCA",
            confidence="low",
            recommended_actions=["Review collected evidence manually"],
            analysis_summary="JSON parsing error in RCA synthesis"
        )
    except Exception as e:
        logging.error("RCA synthesis error: %s", e)
        rca_result = RCAResult(
                service=service,
                symptom=symptom,
                likely_root_cause=data.get("likely_root_cause", "Unknown"),
                confidence=data.get("confidence", "low"),
                recommended_actions=data.get("recommended_actions", []),
                analysis_summary=data.get("analysis_summary", "")
            )

    return rca_result, response.usage