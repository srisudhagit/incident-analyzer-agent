from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.agent import investigate_with_rca

app = FastAPI()


class InvestigateRequest(BaseModel):
    service: str
    symptom: str


@app.get("/health")
def health():
    return {"status": "running"}


@app.post("/investigate-phase1")
def investigate_phase1_api(req: InvestigateRequest):
    """Phase 1: Investigation with evidence gathering"""
    try:
        from app.agent import investigate_phase1
        result = investigate_phase1(req.service, req.symptom)
        return result.model_dump()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/investigate")
def investigate_api(req: InvestigateRequest):
    """Phase 1.5: Investigation + RCA Synthesis (RECOMMENDED)"""
    try:
        result = investigate_with_rca(req.service, req.symptom)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))