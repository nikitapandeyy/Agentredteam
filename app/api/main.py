"""FastAPI application for AgentRedTeam.

Endpoints:
  POST /run-test-suite    Run a full attack suite and return the report
  GET  /report/{run_id}  Retrieve a stored report by ID
  GET  /runs             List recent test runs
  GET  /health           Health check (used by Cloud Run in Task 19)
"""
import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.attacks.categories import CATEGORY_MAP
from app.attacks.generator import generate_all
from app.db.connection import create_tables
from app.db.storage import (
    get_run,
    list_runs,
    save_run,
    save_test_cases,
    save_test_results,
)
from app.runner.runner import run_suite
from app.scoring.judge import judge_suite
from app.scoring.rules import apply_rules_to_suite
from app.scoring.trust_score import compute_trust_score

logger = logging.getLogger(__name__)

# Silence Google SDK noise
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google.genai.models").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(
    title="AgentRedTeam",
    description=(
        "A crash-test tool for AI agents. "
        "Generates adversarial attacks, runs them against the target agent, "
        "and returns a trust score showing where the agent broke and how badly."
    ),
    version="0.1.0",
)

# CORS allows the dashboard (running on a different port/domain) to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],    # tightened in Task 19 (production)
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup() -> None:
    """Create database tables on startup if they don't exist."""
    try:
        create_tables()
        logger.info("Database ready")
    except Exception as e:
        logger.error("Database setup failed: %s", e)


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class RunTestSuiteRequest(BaseModel):
    categories: list[str] | None = None    # None = run all categories
    agent_name: str = "Customer Support Agent"

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "categories": ["tool_misuse", "data_exfiltration"],
                    "agent_name": "Customer Support Agent v1",
                }
            ]
        }
    }


class RunTestSuiteResponse(BaseModel):
    run_id: str
    trust_score: int
    total_cases: int
    total_passed: int
    total_failed: int
    summary: str
    message: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
async def health() -> dict:
    """Health check endpoint used by Cloud Run."""
    return {"status": "ok", "service": "agentredteam"}


@app.get("/runs")
async def get_runs(
    limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[dict]:
    """List recent test runs, newest first."""
    try:
        return list_runs(limit=limit)
    except Exception as e:
        logger.error("Failed to list runs: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/report/{run_id}")
async def get_report(run_id: str) -> dict:
    """Retrieve a stored trust report by run ID."""
    try:
        report = get_run(run_id)
    except Exception as e:
        logger.error("Failed to get report %s: %s", run_id, e)
        raise HTTPException(status_code=500, detail=str(e))

    if report is None:
        raise HTTPException(
            status_code=404,
            detail=f"No report found for run ID: {run_id}",
        )

    return report


@app.post("/run-test-suite", response_model=RunTestSuiteResponse)
async def run_test_suite(request: RunTestSuiteRequest) -> RunTestSuiteResponse:
    """Run a full adversarial test suite against the agent.

    This endpoint runs the complete pipeline:
    1. Generate attack test cases using Gemini
    2. Run each attack against the target agent (Groq)
    3. Score results with rules + LLM judge
    4. Compute trust score
    5. Save everything to the database
    6. Return the trust report

    Takes 1-5 minutes depending on how many categories are selected.
    """
    # Validate categories
    if request.categories:
        invalid = [c for c in request.categories if c not in CATEGORY_MAP]
        if invalid:
            raise HTTPException(
                status_code=422,
                detail=f"Unknown categories: {invalid}. "
                       f"Valid: {list(CATEGORY_MAP.keys())}",
            )

    run_id = str(uuid.uuid4())[:8]
    started_at = datetime.now(timezone.utc)

    logger.info(
        "Starting test suite run %s (categories=%s)",
        run_id, request.categories or "all",
    )

    try:
        # Step 1: Generate
        logger.info("[%s] Generating test cases...", run_id)
        cases = generate_all(
            categories=request.categories,
            delay=2.0,
        )

        if not cases:
            raise HTTPException(
                status_code=500,
                detail="No test cases were generated. Check your GEMINI_API_KEY.",
            )

        # Step 2: Create the run record first so test_cases can
        # reference it via the foreign key constraint
        from app.db.storage import save_run_placeholder
        save_run_placeholder(run_id, request.agent_name, started_at)

        # Step 3: Save test cases (run record now exists)
        save_test_cases(cases, run_id)

        # Step 4: Run against agent
        logger.info("[%s] Running %d cases against agent...", run_id, len(cases))
        results = run_suite(cases, delay=3.0)

        # Step 5: Score — rules
        logger.info("[%s] Applying rule-based scoring...", run_id)
        rule_scored = apply_rules_to_suite(results)

        # Step 6: Score — judge
        logger.info("[%s] Applying LLM judge...", run_id)
        final_results = judge_suite(rule_scored, delay=2.0)

        # Step 7: Compute trust report
        report = compute_trust_score(
            final_results,
            run_id=run_id,
            agent_name=request.agent_name,
            started_at=started_at,
        )

        # Step 8: Save results and report
        save_test_results(final_results, run_id)
        save_run(report)

        logger.info(
            "[%s] Complete. Score=%d, passed=%d/%d",
            run_id, report.trust_score,
            report.total_passed, report.total_cases,
        )

        return RunTestSuiteResponse(
            run_id=run_id,
            trust_score=report.trust_score,
            total_cases=report.total_cases,
            total_passed=report.total_passed,
            total_failed=report.total_failed,
            summary=report.summary,
            message=f"Run {run_id} complete. Retrieve the full report at /report/{run_id}",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("[%s] Pipeline failed: %s", run_id, e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {type(e).__name__}: {e}",
        )
