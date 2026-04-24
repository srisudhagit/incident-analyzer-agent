import json
import logging
from app.state import IncidentState, StepTrace
from app.planner import plan_next_step
from app.mcp_client import call_tool_sync
from app.rca import synthesize_rca
from app.rag.retrieve import filter_retrieved_context, retrieve_context
from app.rag.store_incident import store_resolved_incident
from app.rag.evidence_ranker import rank_evidence_for_rag
import time

logging.basicConfig(level=logging.INFO)

MAX_STEPS = 3
RAG_EVIDENCE_LIMIT = 2


def add_usage(token_usage: dict, usage):
    if not usage:
        return

    prompt_tokens = (
        getattr(usage, "prompt_tokens", None)
        or getattr(usage, "input_tokens", 0)
        or 0
    )

    completion_tokens = (
        getattr(usage, "completion_tokens", None)
        or getattr(usage, "output_tokens", 0)
        or 0
    )

    total_tokens = getattr(usage, "total_tokens", 0) or 0

    token_usage["prompt_tokens"] += prompt_tokens
    token_usage["completion_tokens"] += completion_tokens
    token_usage["total_tokens"] += total_tokens


def summarize_result(tool_name: str, raw_result: str) -> str:
    if not raw_result:
        return f"{tool_name} returned no data (MCP call failed)"

    try:
        parsed = json.loads(raw_result)

        if tool_name == "get_logs":
            if isinstance(parsed, list) and parsed:
                messages = [item.get("message", "") for item in parsed[:3] if isinstance(item, dict)]
                return f"Log evidence: {' | '.join(messages)}" if messages else "Log evidence present"
            return "Logs returned but empty"

        if tool_name == "get_metrics":
            if isinstance(parsed, dict):
                metrics = parsed.get("metrics", {})
                if metrics:
                    important = ", ".join([f"{k}={v}" for k, v in list(metrics.items())[:5]])
                    return f"Metric evidence: {important}"
            return "Metrics returned but empty"

        if tool_name == "get_recent_deployments":
            if isinstance(parsed, list) and parsed:
                notes = [item.get("note", "") for item in parsed[:2] if isinstance(item, dict)]
                return f"Deployment evidence: {' | '.join(notes)}" if notes else "Deployment data present"
            return "Deployment history returned but empty"

        return f"{tool_name} returned structured data"

    except Exception:
        return f"{tool_name} returned raw output: {raw_result[:300]}"


def build_retrieval_query(service: str, symptom: str, evidence: list[str]) -> str:
    return f"""
service: {service}
symptom: {symptom}
evidence:
{" ".join(evidence)}
""".strip()


def investigate_phase1(service: str, symptom: str) -> tuple[IncidentState, dict]:
    state = IncidentState(service=service, symptom=symptom)

    llm_observability = {
        "planner_calls": 0,
        "rca_calls": 0,
        "total_llm_calls": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "total_tokens": 0
    }

    for step_num in range(1, MAX_STEPS + 1):
        decision, usage = plan_next_step(state)

        llm_observability["planner_calls"] += 1
        llm_observability["total_llm_calls"] += 1
        add_usage(llm_observability, usage)

        if decision.enough_evidence or decision.next_tool is None:
            state.enough_evidence = True
            state.steps_taken.append(
                StepTrace(
                    step=step_num,
                    chosen_tool=None,
                    reason=decision.reason,
                    observation_summary="Investigation complete - enough evidence"
                )
            )
            break

        tool_name = decision.next_tool
        raw_result = call_tool_sync(tool_name, {"service": service})
        summary = summarize_result(tool_name, raw_result)

        state.tools_called.append(tool_name)
        state.sources.append(f"mcp:{tool_name}")
        state.evidence.append(summary)
        state.steps_taken.append(
            StepTrace(
                step=step_num,
                chosen_tool=tool_name,
                reason=decision.reason,
                observation_summary=summary
            )
        )

    return state, llm_observability


def investigate_with_rca(service: str, symptom: str) -> dict:
    state, llm_observability = investigate_phase1(service, symptom)

    start_time = time.time()
    rag_evidence_used = []

    if has_usable_evidence(state.evidence):
        try:
            rag_evidence_used = rank_evidence_for_rag(
                service=service,
                symptom=symptom,
                evidence=state.evidence,
                limit=RAG_EVIDENCE_LIMIT
            )

            if not rag_evidence_used:
                rag_evidence_used = state.evidence[:RAG_EVIDENCE_LIMIT]

            query = build_retrieval_query(service, symptom, rag_evidence_used)
            retrieved = retrieve_context(query)
            retrieved = filter_retrieved_context(service, retrieved)
            
            logging.info("RAG evidence used: %s", rag_evidence_used)
            logging.info("RAG query: %s", query)
            logging.info("Retrieved context: %s", retrieved)

        except Exception as e:
            logging.exception("RAG retrieval failed: %s", e)
            retrieved = []

        state.retrieved_context = retrieved

        existing_sources = set(state.sources)
        for item in retrieved:
            source = item.get("source")
            if source and source not in existing_sources:
                state.sources.append(source)
                existing_sources.add(source)

        if not retrieved:
            state.sources.append("rag:none")

    rca, rca_usage = synthesize_rca(
        service=state.service,
        symptom=state.symptom,
        evidence=state.evidence,
        tools_called=state.tools_called,
        steps_taken=[step.model_dump() for step in state.steps_taken],
        retrieved_context=state.retrieved_context,
        sources=state.sources
    )

    llm_observability["rca_calls"] += 1
    llm_observability["total_llm_calls"] += 1
    add_usage(llm_observability, rca_usage)

    try:
        if rca.confidence == "high" and state.evidence and not all_tools_failed(state.evidence):
            stored_incident_id = store_resolved_incident(
                service=state.service,
                symptom=state.symptom,
                root_cause=rca.likely_root_cause,
                evidence=state.evidence
            )
        else:
            stored_incident_id = None
    except Exception as e:
        logging.exception("Failed to store resolved incident: %s", e)
        stored_incident_id = None

    latency_ms = int((time.time() - start_time) * 1000)
    
    return {
        **state.model_dump(),
        "rag_evidence_used": rag_evidence_used,
        "likely_root_cause": rca.likely_root_cause,
        "confidence": rca.confidence,
        "recommended_actions": rca.recommended_actions,
        "analysis_summary": rca.analysis_summary,
        "stored_incident_id": stored_incident_id,
        "llm_observability": llm_observability,
        "latency_ms": latency_ms
    }
    
def all_tools_failed(evidence: list[str]) -> bool:
    return bool(evidence) and all(
        "returned no data" in e.lower() or "mcp call failed" in e.lower()
        for e in evidence
    )


def has_usable_evidence(evidence: list[str]) -> bool:
    return bool(evidence) and not all_tools_failed(evidence)