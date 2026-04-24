import numpy as np
from app.rag.store import embedding_fn


def cosine_similarity(a, b) -> float:
    a = np.array(a)
    b = np.array(b)

    denominator = np.linalg.norm(a) * np.linalg.norm(b)
    if denominator == 0:
        return 0.0

    return float(np.dot(a, b) / denominator)


def rank_evidence_for_rag(
    service: str,
    symptom: str,
    evidence: list[str],
    limit: int = 2
) -> list[str]:
    if not evidence:
        return []

    query = f"service: {service}\nsymptom: {symptom}"

    query_embedding = embedding_fn([query])[0]
    evidence_embeddings = embedding_fn(evidence)

    scored = []

    for item, emb in zip(evidence, evidence_embeddings):
        scored.append({
            "evidence": item,
            "score": cosine_similarity(query_embedding, emb)
        })

    scored.sort(key=lambda x: x["score"], reverse=True)

    return [item["evidence"] for item in scored[:limit]]