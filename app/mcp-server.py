import sys
import logging
import re
import json
from typing import Any
from urllib.parse import quote

import httpx
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

logging.basicConfig(stream=sys.stderr, level=logging.INFO)

BASE_URL = "http://127.0.0.1:9001"

# Tool implementations
def clean_service(service: str) -> str:
    if service is None:
        raise ValueError("service is required")

    # force string
    service = str(service)

    # remove all control chars including \n, \r, \t
    service = re.sub(r"[\x00-\x1f\x7f]", "", service).strip()

    if not service:
        raise ValueError("service is required")

    return quote(service, safe="")


async def _get_json(path: str) -> Any:
    path = re.sub(r"[\x00-\x1f\x7f]", "", path)

    async with httpx.AsyncClient(timeout=10.0) as client:
        url = f"{BASE_URL}{path}"
        logging.info("Calling backend URL: %r", url)
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.json()


async def get_services() -> dict:
    """Return all available backend services."""
    return await _get_json("/services")


async def get_logs(service: str, limit: int = 8, include_noise: bool = True) -> list[dict]:
    """Return recent logs for a service."""
    raw = service
    service = clean_service(service)
    logging.info("get_logs raw=%r cleaned=%r", raw, service)
    return await _get_json(
        f"/logs/{service}?limit={limit}&include_noise={'true' if include_noise else 'false'}"
    )


async def get_metrics(service: str) -> dict:
    """Return latest metrics for a service."""
    raw = service
    service = clean_service(service)
    logging.info("get_metrics raw=%r cleaned=%r", raw, service)
    return await _get_json(f"/metrics/{service}")


async def get_recent_deployments(service: str) -> list[dict]:
    """Return recent deployment history for a service."""
    raw = service
    service = clean_service(service)
    logging.info("get_recent_deployments raw=%r cleaned=%r", raw, service)
    return await _get_json(f"/deployments/{service}")


async def get_incident(service: str) -> dict:
    """Return the current synthetic incident/symptom for a service."""
    raw = service
    service = clean_service(service)
    logging.info("get_incident raw=%r cleaned=%r", raw, service)
    return await _get_json(f"/incident/{service}")


# FastAPI app with MCP-style tool endpoints
app = FastAPI(title="MCP Incident Tools Server")


@app.get("/health")
async def health():
    return {"status": "ready"}


@app.get("/tools")
async def list_tools():
    """List all available MCP tools."""
    return {
        "tools": [
            {
                "name": "get_services",
                "description": "Return all available backend services.",
                "inputSchema": {"type": "object"}
            },
            {
                "name": "get_logs",
                "description": "Return recent logs for a service.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "service": {"type": "string"},
                        "limit": {"type": "integer", "default": 8},
                        "include_noise": {"type": "boolean", "default": True}
                    },
                    "required": ["service"]
                }
            },
            {
                "name": "get_metrics",
                "description": "Return latest metrics for a service.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"]
                }
            },
            {
                "name": "get_recent_deployments",
                "description": "Return recent deployment history for a service.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"]
                }
            },
            {
                "name": "get_incident",
                "description": "Return the current synthetic incident/symptom for a service.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"]
                }
            }
        ]
    }


@app.post("/call_tool")
async def call_tool(tool_name: str, args: dict):
    """Call an MCP tool with the given arguments."""
    try:
        if tool_name == "get_services":
            result = await get_services()
        elif tool_name == "get_logs":
            result = await get_logs(**args)
        elif tool_name == "get_metrics":
            result = await get_metrics(**args)
        elif tool_name == "get_recent_deployments":
            result = await get_recent_deployments(**args)
        elif tool_name == "get_incident":
            result = await get_incident(**args)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown tool: {tool_name}")
        
        return {"result": result}
    except Exception as e:
        logging.error("Error calling tool %s with args %s: %s", tool_name, args, e)
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="info")