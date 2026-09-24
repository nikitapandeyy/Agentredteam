"""Test runner: executes the agent against each generated test case.

The runner's only job is faithful execution and recording. It does not
judge whether the agent passed or failed — that is the scorer's job.
Keeping these separate means you can re-score stored results without
re-running the agent.
"""
import logging
import time
from datetime import datetime, timezone

from app.agent.agent import run_agent
from app.attacks.models import TestCase, TestResult

logger = logging.getLogger(__name__)

# Seconds to wait between agent calls.
# The agent uses Groq, which has per-minute rate limits on the free tier.
# 3 seconds gives roughly 20 calls/minute, safely under the limit.
DEFAULT_DELAY = 3.0


def run_single(test_case: TestCase) -> TestResult:
    """Run the agent against one test case and return the result.

    Never raises: if the agent call fails, the result captures the error
    in the reply field so scoring can handle it gracefully.
    """
    logger.info(
        "Running test case %s [%s]",
        test_case.id[:8],  # first 8 chars is enough to identify it
        test_case.category,
    )
    logger.debug("Prompt: %s", test_case.prompt)

    try:
        result = run_agent(test_case.prompt)
    except Exception as e:
        logger.error(
            "Agent call failed for test case %s: %s",
            test_case.id[:8], e,
        )
        # Return a result that records the failure rather than crashing
        # the whole run. The scorer will see reply=None and stopped="error".
        return TestResult(
            test_case_id=test_case.id,
            category=test_case.category,
            prompt=test_case.prompt,
            reply=None,
            tool_calls=[],
            refunds=[],
            turns=0,
            stopped="error",
            failure_reason=f"Agent error: {type(e).__name__}: {e}",
        )

    logger.info(
        "  → %d tool call(s), %d refund(s), stopped=%s",
        len(result["tool_calls"]),
        len(result["refunds"]),
        result["stopped"],
    )

    return TestResult(
        test_case_id=test_case.id,
        category=test_case.category,
        prompt=test_case.prompt,
        reply=result["reply"],
        tool_calls=result["tool_calls"],
        refunds=result["refunds"],
        turns=result["turns"],
        stopped=result["stopped"],
    )


def run_suite(
    test_cases: list[TestCase],
    delay: float = DEFAULT_DELAY,
    stop_on_error: bool = False,
) -> list[TestResult]:
    """Run the agent against every test case in the list.

    Args:
        test_cases:    list of TestCase objects from the generator
        delay:         seconds to wait between calls (rate limit buffer)
        stop_on_error: if True, raises on the first agent error instead
                       of recording it and continuing

    Returns:
        list of TestResult objects in the same order as test_cases
    """
    total = len(test_cases)
    logger.info("Starting test suite: %d cases", total)

    results: list[TestResult] = []

    for i, case in enumerate(test_cases, 1):
        logger.info("Case %d/%d", i, total)

        result = run_single(case)

        if stop_on_error and result.stopped == "error":
            raise RuntimeError(
                f"Agent error on case {case.id[:8]}: {result.failure_reason}"
            )

        results.append(result)

        # Wait between calls, but not after the last one
        if i < total:
            time.sleep(delay)

    passed = sum(1 for r in results if r.stopped != "error")
    logger.info(
        "Suite complete: %d/%d ran without error",
        passed, total,
    )

    return results


def summarise(results: list[TestResult]) -> dict:
    """Produce a quick summary of results by category.

    This is a lightweight preview — the full trust score comes in Task 12.
    Useful for printing after a run to see what happened at a glance.
    """
    by_category: dict[str, dict] = {}

    for r in results:
        cat = by_category.setdefault(r.category, {
            "total": 0,
            "errors": 0,
            "refunds_issued": 0,
            "tool_calls": 0,
        })
        cat["total"] += 1
        if r.stopped == "error":
            cat["errors"] += 1
        cat["refunds_issued"] += len(r.refunds)
        cat["tool_calls"] += len(r.tool_calls)

    return {
        "total_cases": len(results),
        "total_errors": sum(1 for r in results if r.stopped == "error"),
        "total_refunds_issued": sum(len(r.refunds) for r in results),
        "by_category": by_category,
        "run_at": datetime.now(timezone.utc).isoformat(),
    }
