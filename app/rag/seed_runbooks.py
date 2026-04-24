import os
from app.rag.store import runbook_collection

RUNBOOK_DIR = "data/runbooks"


def seed_runbooks():
    docs = []
    ids = []
    metadatas = []

    for filename in os.listdir(RUNBOOK_DIR):
        if not filename.endswith(".txt"):
            continue

        path = os.path.join(RUNBOOK_DIR, filename)
        with open(path, "r") as f:
            content = f.read()

        doc_id = filename.replace(".txt", "")
        docs.append(content)
        ids.append(doc_id)
        metadatas.append({"source": f"runbook:{doc_id}"})

    if ids:
        existing = runbook_collection.get(ids=ids)
        existing_ids = set(existing.get("ids", []))
        new_docs, new_ids, new_meta = [], [], []

        for doc, doc_id, meta in zip(docs, ids, metadatas):
            if doc_id not in existing_ids:
                new_docs.append(doc)
                new_ids.append(doc_id)
                new_meta.append(meta)

        if new_ids:
            runbook_collection.add(
                documents=new_docs,
                ids=new_ids,
                metadatas=new_meta
            )

    print("Runbooks seeded")


if __name__ == "__main__":
    seed_runbooks()