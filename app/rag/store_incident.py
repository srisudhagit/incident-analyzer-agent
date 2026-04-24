import uuid
import logging
from app.rag.store import incident_collection

logging.basicConfig(level=logging.INFO)


def store_resolved_incident(
    service: str,
    symptom: str,
    root_cause: str,
    evidence: list[str],
) -> str:
    incident_id = f"auto_incident_{uuid.uuid4()}"

    doc = f"""
Service: {service}
Symptom: {symptom}
Evidence: {' | '.join(evidence)}
Root cause: {root_cause}
Resolution: Generated from automated investigation
""".strip()

    incident_collection.add(
        documents=[doc],
        ids=[incident_id],
        metadatas=[{
            "source": f"incident:{incident_id}",
            "service": service,
            "kind": "auto_generated"
        }]
    )

    logging.info("Stored resolved incident: %s", incident_id)
    return incident_id