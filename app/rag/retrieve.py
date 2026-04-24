from app.rag.store import runbook_collection, incident_collection
import logging

logging.basicConfig(level=logging.INFO)

def filter_retrieved_context(service: str, docs: list[dict]) -> list[dict]:
    filtered = []

    for doc in docs:
        text = f"{doc.get('source', '')} {doc.get('content', '')}".lower()

        if service.lower() in text:
            filtered.append(doc)

    return filtered

def retrieve_context(query: str, k_runbooks: int = 2, k_incidents: int = 2):
    logging.info("RAG query: %s", query)
    logging.info("Runbook count: %s", runbook_collection.count())
    logging.info("Incident count: %s", incident_collection.count())

    runbook_results = runbook_collection.query(
        query_texts=[query],
        n_results=k_runbooks
    )

    incident_results = incident_collection.query(
        query_texts=[query],
        n_results=k_incidents
    )

    logging.info("Runbook results: %s", runbook_results)
    logging.info("Incident results: %s", incident_results)

    runbook_docs = runbook_results.get("documents", [[]])[0] if runbook_results.get("documents") else []
    runbook_meta = runbook_results.get("metadatas", [[]])[0] if runbook_results.get("metadatas") else []

    incident_docs = incident_results.get("documents", [[]])[0] if incident_results.get("documents") else []
    incident_meta = incident_results.get("metadatas", [[]])[0] if incident_results.get("metadatas") else []

    results = []

    for i, doc in enumerate(runbook_docs):
        meta = runbook_meta[i] if i < len(runbook_meta) and runbook_meta[i] else {}
        results.append({
            "type": "runbook",
            "source": meta.get("source", "runbook:unknown"),
            "content": doc
        })

    for i, doc in enumerate(incident_docs):
        meta = incident_meta[i] if i < len(incident_meta) and incident_meta[i] else {}
        results.append({
            "type": "incident",
            "source": meta.get("source", "incident:unknown"),
            "content": doc
        })

    logging.info("Normalized retrieved context: %s", results)
    return results