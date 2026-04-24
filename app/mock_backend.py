from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import random

app = FastAPI(title="Mock Backend Systems", version="1.0.0")


SERVICES = [
    "api-gateway",
    "auth-service",
    "payment-service",
    "order-service",
    "notification-service",
]


class LogEntry(BaseModel):
    timestamp: str
    level: str
    service: str
    message: str


class DeploymentEntry(BaseModel):
    timestamp: str
    service: str
    version: str
    status: str
    note: str


def iso(minutes_ago: int) -> str:
    return (datetime.utcnow() - timedelta(minutes=minutes_ago)).isoformat() + "Z"


# 5 realistic incident scenarios
SCENARIOS: Dict[str, Dict[str, Any]] = {
    "api-gateway": {
        "symptom": "502 spike from upstream",
        "logs": [
            "ERROR Upstream auth-service returned 503",
            "WARN Increased retry count for /login",
            "ERROR Request timeout waiting for auth-service",
            "INFO Circuit breaker opened for auth-service",
        ],
        "metrics": {
            "cpu_percent": 41,
            "memory_percent": 58,
            "error_rate_percent": 8.3,
            "request_rate_rps": 340,
            "p95_latency_ms": 920,
            "upstream_auth_5xx_percent": 14.1,
        },
        "deployments": [
            {"version": "2.4.1", "status": "success", "minutes_ago": 180, "note": "No recent risky change"}
        ],
    },
    "auth-service": {
        "symptom": "login failures after release",
        "logs": [
            "ERROR Token validation timeout while calling Redis",
            "ERROR Failed to parse auth config: missing issuer field",
            "WARN Increased 401 responses for login requests",
            "INFO Recent config reload detected",
        ],
        "metrics": {
            "cpu_percent": 52,
            "memory_percent": 61,
            "error_rate_percent": 11.7,
            "request_rate_rps": 210,
            "p95_latency_ms": 760,
            "redis_latency_ms": 180,
        },
        "deployments": [
            {"version": "3.1.4", "status": "success", "minutes_ago": 12, "note": "Config refactor deployed recently"}
        ],
    },
    "payment-service": {
        "symptom": "503 spike during payment processing",
        "logs": [
            "ERROR DB connection pool timeout",
            "ERROR Database connections near max",
            "WARN Retry attempts increasing for charge requests",
            "ERROR Failed to persist payment transaction",
        ],
        "metrics": {
            "cpu_percent": 72,
            "memory_percent": 68,
            "error_rate_percent": 15.2,
            "request_rate_rps": 125,
            "p95_latency_ms": 1340,
            "db_connections_active": 97,
            "db_connections_max": 100,
        },
        "deployments": [
            {"version": "1.8.7", "status": "success", "minutes_ago": 95, "note": "No immediate release correlation"}
        ],
    },
    "order-service": {
        "symptom": "order placement latency spike",
        "logs": [
            "WARN Downstream payment-service latency increased",
            "ERROR Timed out waiting for payment authorization",
            "WARN Pending order queue depth increasing",
            "INFO Falling back to delayed order confirmation flow",
        ],
        "metrics": {
            "cpu_percent": 49,
            "memory_percent": 54,
            "error_rate_percent": 6.4,
            "request_rate_rps": 170,
            "p95_latency_ms": 1480,
            "pending_queue_depth": 83,
        },
        "deployments": [
            {"version": "4.0.2", "status": "success", "minutes_ago": 240, "note": "Stable deployment"}
        ],
    },
    "notification-service": {
        "symptom": "notification delays and dropped sends",
        "logs": [
            "WARN Rate limit exceeded from email provider",
            "ERROR Failed to enqueue email job",
            "WARN Retry backoff triggered for provider responses",
            "INFO SMS provider healthy",
        ],
        "metrics": {
            "cpu_percent": 36,
            "memory_percent": 47,
            "error_rate_percent": 4.9,
            "request_rate_rps": 90,
            "p95_latency_ms": 540,
            "email_provider_429_percent": 18.6,
            "queue_depth": 61,
        },
        "deployments": [
            {"version": "2.9.0", "status": "success", "minutes_ago": 420, "note": "No recent deployment"}
        ],
    },
}


def add_log_timestamps(service: str, messages: List[str]) -> List[LogEntry]:
    levels = ["INFO", "WARN", "ERROR"]
    entries: List[LogEntry] = []
    for idx, msg in enumerate(messages):
        level = "ERROR" if "ERROR" in msg else "WARN" if "WARN" in msg else random.choice(levels)
        entries.append(
            LogEntry(
                timestamp=iso(10 - idx),
                level=level,
                service=service,
                message=msg,
            )
        )
    return entries


def add_noise_logs(service: str) -> List[LogEntry]:
    noise = [
        "INFO Health check passed",
        "INFO Request completed successfully",
        "WARN Minor latency increase observed",
        "INFO Background cleanup job finished",
    ]
    sample = random.sample(noise, k=2)
    return [
        LogEntry(timestamp=iso(25 + i), level="INFO", service=service, message=msg)
        for i, msg in enumerate(sample)
    ]


def slightly_vary_metrics(metrics: Dict[str, Any]) -> Dict[str, Any]:
    varied = {}
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            if "percent" in key or "latency" in key or "connections" in key or "rate" in key or "depth" in key:
                delta = random.uniform(-3, 3)
                new_value = value + delta
                varied[key] = round(max(new_value, 0), 1)
            else:
                varied[key] = value
        else:
            varied[key] = value
    return varied


def build_deployments(service: str) -> List[DeploymentEntry]:
    items = []
    for dep in SCENARIOS[service]["deployments"]:
        items.append(
            DeploymentEntry(
                timestamp=iso(dep["minutes_ago"]),
                service=service,
                version=dep["version"],
                status=dep["status"],
                note=dep["note"],
            )
        )
    return items


@app.get("/services")
def get_services():
    return {
        "services": SERVICES
    }


@app.get("/logs/{service}", response_model=List[LogEntry])
def get_logs(
    service: str,
    limit: int = Query(default=8, ge=1, le=50),
    include_noise: bool = Query(default=True),
):
    if service not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown service")

    scenario_logs = add_log_timestamps(service, SCENARIOS[service]["logs"])
    noise_logs = add_noise_logs(service) if include_noise else []
    combined = sorted(scenario_logs + noise_logs, key=lambda x: x.timestamp, reverse=True)

    return combined[:limit]


@app.get("/metrics/{service}")
def get_metrics(service: str):
    if service not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown service")

    base = SCENARIOS[service]["metrics"]
    current = slightly_vary_metrics(base)

    return {
        "service": service,
        "timestamp": iso(0),
        "metrics": current,
    }


@app.get("/deployments/{service}", response_model=List[DeploymentEntry])
def get_deployments(service: str):
    if service not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown service")

    return build_deployments(service)


@app.get("/incident/{service}")
def get_incident(service: str):
    if service not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Unknown service")

    scenario = SCENARIOS[service]
    return {
        "service": service,
        "symptom": scenario["symptom"],
        "timestamp": iso(0),
    }


@app.get("/scenario")
def get_all_scenarios():
    return {
        "count": len(SCENARIOS),
        "scenarios": [
            {
                "service": service,
                "symptom": data["symptom"],
            }
            for service, data in SCENARIOS.items()
        ],
    }