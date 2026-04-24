import os
import json
from app.rag.store import incident_collection

INCIDENT_DIR = "data/incidents"


def seed_incidents():
    docs = []
    ids = []
    metadatas = []

    for filename in os.listdir(INCIDENT_DIR):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(INCIDENT_DIR, filename)
        with open(path, "r") as f:
            item = json.load(f)

        doc_text = f"""
Service: {item['service']}
Symptom: {item['symptom']}
Evidence: {' | '.join(item['evidence'])}
Root cause: {item['root_cause']}
Resolution: {' | '.join(item['resolution'])}
        """.strip()

        doc_id = item["id"]

        docs.append(doc_text)
        ids.append(doc_id)
        metadatas.append({
            "source": f"incident:{doc_id}",
            "service": item["service"]
        })

    if docs:
        incident_collection.add(
            documents=docs,
            ids=ids,
            metadatas=metadatas
        )

    print(f"Seeded {len(docs)} incidents")


if __name__ == "__main__":
    seed_incidents()