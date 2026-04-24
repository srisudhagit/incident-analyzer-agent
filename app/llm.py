import json
import os
from dotenv import load_dotenv
from openai import OpenAI
from app.models import InvestigateResponse

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


SYSTEM_PROMPT = """
You are a backend incident investigation assistant.
Return JSON only with these fields:
- likely_root_cause: string
- confidence: one of low, medium, high
- evidence: array of short strings
- recommended_actions: array of short strings

Rules:
- Use the provided logs and metrics as evidence
- Be concise
- Do not add markdown

Be concise. Do not add markdown.
"""


def investigate_with_llm(service: str, symptom: str, logs: list[str], metrics: dict) -> InvestigateResponse:
    prompt = f"""
Service: {service}
Symptom: {symptom}

Logs:
{logs}

Metrics:
{metrics}

Analyze this like a backend production incident.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            timeout=10.0
        )

        text = response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        text = json.dumps({
            "likely_root_cause": "Unable to analyze (API error)",
            "confidence": "low",
            "evidence": [str(e)],
            "recommended_actions": ["Check OpenAI API status"]
        })
    
    data = json.loads(text)
    return InvestigateResponse(**data)