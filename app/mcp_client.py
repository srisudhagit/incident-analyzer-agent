import asyncio
import json
import logging
import httpx

logging.basicConfig(level=logging.INFO)

MCP_SERVER_URL = "http://127.0.0.1:8001"


async def call_tool(tool_name: str, args: dict) -> str:
    """Call tools via HTTP-based MCP server."""
    try:
        url = f"{MCP_SERVER_URL}/call_tool"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, params={"tool_name": tool_name}, json=args)
            resp.raise_for_status()
            data = resp.json()
            result = data.get("result", {})
            return json.dumps(result)

    except Exception as e:
        logging.error("MCP HTTP error for tool=%s args=%s: %s", tool_name, args, e)
        return ""


def call_tool_sync(tool_name: str, args: dict) -> str:
    try:
        return asyncio.run(call_tool(tool_name, args))
    except Exception as e:
        logging.error("Error calling tool=%s args=%s error=%s", tool_name, args, e)
        return ""


async def fetch_tool_data(service: str) -> dict:
    logs_text = await call_tool("get_logs", {"service": service})
    metrics_text = await call_tool("get_metrics", {"service": service})

    try:
        logs = json.loads(logs_text) if logs_text else []
    except json.JSONDecodeError:
        logs = []

    try:
        metrics = json.loads(metrics_text) if metrics_text else {}
    except json.JSONDecodeError:
        metrics = {}

    return {"logs": logs, "metrics": metrics}


def fetch_tool_data_sync(service: str) -> dict:
    try:
        return asyncio.run(fetch_tool_data(service))
    except Exception as e:
        logging.error("Error fetching tool data for service=%s error=%s", service, e)
        return {"logs": [], "metrics": {}}


async def fetch_tool_data(service: str) -> dict:
    logs_text = await call_tool("get_logs", {"service": service})
    metrics_text = await call_tool("get_metrics", {"service": service})

    try:
        logs = json.loads(logs_text) if logs_text else []
    except json.JSONDecodeError:
        logs = []

    try:
        metrics = json.loads(metrics_text) if metrics_text else {}
    except json.JSONDecodeError:
        metrics = {}

    return {
        "logs": logs,
        "metrics": metrics
    }


def fetch_tool_data_sync(service: str) -> dict:
    try:
        return asyncio.run(fetch_tool_data(service))
    except Exception as e:
        logging.error("Error fetching tool data for service=%s error=%s", service, e)
        return {"logs": [], "metrics": {}}