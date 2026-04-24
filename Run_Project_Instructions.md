# Running the Incident Analyzer Agent

This guide explains how to set up and run the system locally.

The system consists of three services:

-   Mock Backend --- Simulates logs, metrics, and deployments
-   MCP Server --- Executes investigation tools
-   Agent API --- Runs planner, RAG retrieval, and RCA synthesis

------------------------------------------------------------------------

## Prerequisites

Install the following:

-   Python 3.9 or higher
-   pip
-   virtual environment support
-   OpenAI API key

------------------------------------------------------------------------

## Step 1 --- Clone the Repository

``` bash
git clone https://github.com/<your-username>/incident-analyzer-agent.git
cd incident-analyzer-agent
```

------------------------------------------------------------------------

## Step 2 --- Create Virtual Environment

``` bash
python3 -m venv venv
```

Activate:

``` bash
source venv/bin/activate
```

------------------------------------------------------------------------

## Step 3 --- Install Dependencies

``` bash
pip install -r requirements.txt
```

If requirements.txt is not available:

``` bash
pip install fastapi uvicorn httpx chromadb python-dotenv openai
```

------------------------------------------------------------------------

## Step 4 --- Configure Environment Variables

Create a `.env` file:

``` bash
touch .env
```

Add:

    OPENAI_API_KEY=your_openai_api_key_here

------------------------------------------------------------------------

## Step 5 --- Seed Runbooks and Incident Memory (One-Time Setup)

``` bash
python -m app.rag.seed_runbooks
python -m app.rag.seed_incidents
```

------------------------------------------------------------------------

## Step 6 --- Start Services

Open three terminals.

### Terminal 1 --- Mock Backend

``` bash
uvicorn app.mock_backend:app --port 9001
```

### Terminal 2 --- MCP Server

``` bash
python app/mcp-server.py
```

### Terminal 3 --- Agent API

``` bash
uvicorn app.main:app --reload --port 8000
```

------------------------------------------------------------------------

## Step 7 --- Test the System

``` bash
curl -X POST http://127.0.0.1:8000/investigate \
  -H "Content-Type: application/json" \
  -d '{
    "service": "order-service",
    "symptom": "order placement latency spike"
  }'
```

------------------------------------------------------------------------

## Ports Used

  Component      Port   Purpose
  -------------- ------ ------------------------
  Mock Backend   9001   Simulated services
  MCP Server     8001   Tool execution
  Agent API      8000   Investigation workflow

------------------------------------------------------------------------

## Minimal Run Checklist

1)  Install dependencies\
2)  Set OPENAI_API_KEY\
3)  Start backend (9001)\
4)  Start MCP server (8001)\
5)  Start agent API (8000)\
6)  Send test request

