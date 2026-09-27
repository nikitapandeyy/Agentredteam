"""Database storage layer for AgentRedTeam."""
import json
import logging

from app.attacks.models import TestCase, TestResult
from app.db.connection import get_connection
from app.scoring.trust_score import TrustReport

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Test runs
# ---------------------------------------------------------------------------


def save_run_placeholder(
    run_id: str,
    agent_name: str,
    started_at,
) -> None:
    """Insert a minimal run record so test_cases can reference it.

    Called before the pipeline starts. save_run() updates this
    record with the full results when the pipeline completes.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO test_runs (id, agent_name, started_at, total_cases)
                VALUES (%s, %s, %s, 0)
                ON CONFLICT (id) DO NOTHING
                """,
                (run_id, agent_name, started_at),
            )
    logger.info("Created placeholder run record %s", run_id)


def save_run(report: TrustReport) -> None:
    """Insert or update a test run record."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO test_runs
                    (id, agent_name, started_at, completed_at, trust_score,
                     total_cases, total_passed, total_failed, total_undecided, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    completed_at    = EXCLUDED.completed_at,
                    trust_score     = EXCLUDED.trust_score,
                    total_cases     = EXCLUDED.total_cases,
                    total_passed    = EXCLUDED.total_passed,
                    total_failed    = EXCLUDED.total_failed,
                    total_undecided = EXCLUDED.total_undecided,
                    summary         = EXCLUDED.summary
                """,
                (
                    report.run_id,
                    report.agent_name,
                    report.started_at,
                    report.completed_at,
                    report.trust_score,
                    report.total_cases,
                    report.total_passed,
                    report.total_failed,
                    report.total_undecided,
                    report.summary,
                ),
            )
    logger.info("Saved run %s (score=%d)", report.run_id, report.trust_score)


def list_runs(limit: int = 20) -> list[dict]:
    """Return recent test runs, newest first."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, agent_name, started_at, completed_at,
                       trust_score, total_cases, total_passed,
                       total_failed, summary
                FROM test_runs
                ORDER BY started_at DESC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cur.fetchall()

    return [
        {
            "run_id": r[0],
            "agent_name": r[1],
            "started_at": r[2].isoformat() if r[2] else None,
            "completed_at": r[3].isoformat() if r[3] else None,
            "trust_score": r[4],
            "total_cases": r[5],
            "total_passed": r[6],
            "total_failed": r[7],
            "summary": r[8],
        }
        for r in rows
    ]


def get_run(run_id: str) -> dict | None:
    """Return one run by ID, with its category breakdown."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, agent_name, started_at, completed_at,
                       trust_score, total_cases, total_passed,
                       total_failed, total_undecided, summary
                FROM test_runs WHERE id = %s
                """,
                (run_id,),
            )
            row = cur.fetchone()

            if row is None:
                return None

            cur.execute(
                """
                SELECT category,
                       COUNT(*) AS total,
                       SUM(CASE WHEN passed = TRUE  THEN 1 ELSE 0 END) AS passed,
                       SUM(CASE WHEN passed = FALSE THEN 1 ELSE 0 END) AS failed
                FROM test_results
                WHERE run_id = %s
                GROUP BY category
                ORDER BY category
                """,
                (run_id,),
            )
            cats = cur.fetchall()

            cur.execute(
                """
                SELECT category, prompt, reply, failure_reason
                FROM test_results
                WHERE run_id = %s AND passed = FALSE
                ORDER BY category
                """,
                (run_id,),
            )
            failures = cur.fetchall()

    return {
        "run_id": row[0],
        "agent_name": row[1],
        "started_at": row[2].isoformat() if row[2] else None,
        "completed_at": row[3].isoformat() if row[3] else None,
        "trust_score": row[4],
        "total_cases": row[5],
        "total_passed": row[6],
        "total_failed": row[7],
        "total_undecided": row[8],
        "summary": row[9],
        "categories": [
            {
                "category": c[0],
                "total": int(c[1]),
                "passed": int(c[2] or 0),
                "failed": int(c[3] or 0),
            }
            for c in cats
        ],
        "failures": [
            {
                "category": f[0],
                "prompt": f[1][:200],
                "reply": (f[2] or "")[:300],
                "failure_reason": f[3],
            }
            for f in failures
        ],
    }


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

def save_test_cases(cases: list[TestCase], run_id: str) -> None:
    """Bulk insert test cases for a run."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO test_cases
                    (id, run_id, template_id, category, prompt,
                     order_id, attacker_goal, filled_slots, generated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                [
                    (
                        case.id,
                        run_id,
                        case.template_id,
                        case.category,
                        case.prompt,
                        case.order_id,
                        case.attacker_goal,
                        json.dumps(case.filled_slots),
                        case.generated_at,
                    )
                    for case in cases
                ],
            )
    logger.info("Saved %d test cases for run %s", len(cases), run_id)


# ---------------------------------------------------------------------------
# Test results
# ---------------------------------------------------------------------------

def save_test_results(results: list[TestResult], run_id: str) -> None:
    """Bulk insert scored test results for a run."""
    def get_passed(r: TestResult) -> bool | None:
        if r.rule_passed is True:
            return True
        if r.rule_passed is False:
            return False
        if r.judge_passed is True:
            return True
        if r.judge_passed is False:
            return False
        return None

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.executemany(
                """
                INSERT INTO test_results
                    (test_case_id, run_id, category, prompt, reply,
                     tool_calls, refunds, turns, stopped,
                     rule_passed, judge_passed, passed, failure_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                [
                    (
                        r.test_case_id,
                        run_id,
                        r.category,
                        r.prompt,
                        r.reply,
                        json.dumps(r.tool_calls),
                        json.dumps(r.refunds),
                        r.turns,
                        r.stopped,
                        r.rule_passed,
                        r.judge_passed,
                        get_passed(r),
                        r.failure_reason,
                    )
                    for r in results
                ],
            )
    logger.info("Saved %d results for run %s", len(results), run_id)


def get_comparison(run_id_a: str, run_id_b: str) -> dict | None:
    """Compare two runs and return a structured diff.

    Returns None if either run is not found.

    The comparison shows:
    - Score delta (run_b - run_a)
    - Per-category pass/fail changes
    - Failures that are new in run_b (regressions)
    - Failures from run_a that are gone in run_b (fixes)
    """
    run_a = get_run(run_id_a)
    run_b = get_run(run_id_b)

    if run_a is None or run_b is None:
        return None

    # Build category maps for easy lookup
    cats_a = {c["category"]: c for c in (run_a.get("categories") or [])}
    cats_b = {c["category"]: c for c in (run_b.get("categories") or [])}

    # All categories across both runs
    all_cats = sorted(set(list(cats_a.keys()) + list(cats_b.keys())))

    category_diffs = []
    for cat in all_cats:
        a = cats_a.get(cat, {"total": 0, "passed": 0, "failed": 0})
        b = cats_b.get(cat, {"total": 0, "passed": 0, "failed": 0})

        failed_a = int(a.get("failed") or 0)
        failed_b = int(b.get("failed") or 0)
        passed_a = int(a.get("passed") or 0)
        passed_b = int(b.get("passed") or 0)

        category_diffs.append({
            "category": cat,
            "run_a": {
                "passed": passed_a,
                "failed": failed_a,
                "total": int(a.get("total") or 0),
            },
            "run_b": {
                "passed": passed_b,
                "failed": failed_b,
                "total": int(b.get("total") or 0),
            },
            "failed_delta": failed_b - failed_a,   # negative = improvement
            "passed_delta": passed_b - passed_a,   # positive = improvement
            "status": (
                "improved" if failed_b < failed_a
                else "regressed" if failed_b > failed_a
                else "unchanged"
            ),
        })

    # Score delta
    score_a = run_a.get("trust_score") or 0
    score_b = run_b.get("trust_score") or 0
    score_delta = score_b - score_a

    # Failures in run_b that weren't in run_a (new regressions)
    prompts_a = {f["prompt"][:100] for f in (run_a.get("failures") or [])}
    new_failures = [
        f for f in (run_b.get("failures") or [])
        if f["prompt"][:100] not in prompts_a
    ]

    # Failures in run_a that are gone in run_b (fixed)
    prompts_b = {f["prompt"][:100] for f in (run_b.get("failures") or [])}
    fixed_failures = [
        f for f in (run_a.get("failures") or [])
        if f["prompt"][:100] not in prompts_b
    ]

    return {
        "run_a": {
            "run_id": run_id_a,
            "trust_score": score_a,
            "total_cases": run_a.get("total_cases", 0),
            "total_passed": run_a.get("total_passed", 0),
            "total_failed": run_a.get("total_failed", 0),
            "agent_name": run_a.get("agent_name", ""),
            "started_at": run_a.get("started_at", ""),
        },
        "run_b": {
            "run_id": run_id_b,
            "trust_score": score_b,
            "total_cases": run_b.get("total_cases", 0),
            "total_passed": run_b.get("total_passed", 0),
            "total_failed": run_b.get("total_failed", 0),
            "agent_name": run_b.get("agent_name", ""),
            "started_at": run_b.get("started_at", ""),
        },
        "score_delta": score_delta,
        "verdict": (
            "improved" if score_delta > 0
            else "regressed" if score_delta < 0
            else "unchanged"
        ),
        "categories": category_diffs,
        "new_failures": new_failures[:5],    # worst 5 regressions
        "fixed_failures": fixed_failures[:5], # best 5 fixes
    }
