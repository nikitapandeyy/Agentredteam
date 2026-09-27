"""Test runner: executes the agent against each generated test case.

Supports two modes:
  1. Built-in agent (default): calls the Groq-powered demo agent directly
  2. External agent: sends HTTP requests to any URL the user provides

The runner's only job is faithful execution and recording. It does not
judge whether the agent passed or failed — that is the scorer's job.
"""
import logging
import time
from datetime import datetime, timezone

from app.agent.agent import run_agent
from app.attacks.models import TestCase, TestResult

logger = logging.getLogger(__name__)

DEFAULT_DELAY = 3.0  # seconds between built-in agent calls
EXTERNAL_DELAY = 1.0  # external agents may have their own rate limits


def run_single(
    test_case: TestCase,
    agent_url: str | None = None,
) -> TestResult:
    """Run the agent against one test case and return the result.

    Args:
        test_case: the attack to run
        agent_url: if provided, calls this HTTP endpoint instead of
                   the built-in agent

    Never raises: errors are captured in the result so the suite continues.
    """
    logger.info(
        "Running %s [%s] against %s",
        test_case.id[:8],
        test_case.category,
        agent_url or "built-in agent",
    )

    try:
        if agent_url:
            from app.runner.external import call_external_agent
            result = call_external_agent(agent_url, test_case.prompt)
        else:
            result = run_agent(test_case.prompt)

    except Exception as e:
        logger.error(
            "Agent call failed for %s: %s", test_case.id[:8], e
        )
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
        len(result.get("tool_calls", [])),
        len(result.get("refunds", [])),
        result.get("stopped", "?"),
    )

    return TestResult(
        test_case_id=test_case.id,
        category=test_case.category,
        prompt=test_case.prompt,
        reply=result.get("reply"),
        tool_calls=result.get("tool_calls", []),
        refunds=result.get("refunds", []),
        turns=result.get("turns", 1),
        stopped=result.get("stopped", "completed"),
    )


def run_suite(
    test_cases: list[TestCase],
    delay: float | None = None,
    stop_on_error: bool = False,
    agent_url: str | None = None,
) -> list[TestResult]:
    """Run the agent against every test case in the list.

    Args:
        test_cases:    list of TestCase objects from the generator
        delay:         seconds between calls. Defaults to 3s for the
                       built-in agent, 1s for external agents.
        stop_on_error: if True, raises on the first error
        agent_url:     if provided, calls this URL instead of built-in agent

    Returns:
        list of TestResult objects in the same order as test_cases
    """
    if delay is None:
        delay = EXTERNAL_DELAY if agent_url else DEFAULT_DELAY

    total = len(test_cases)
    mode = f"external ({agent_url})" if agent_url else "built-in agent"
    logger.info("Starting suite: %d cases against %s", total, mode)

    results: list[TestResult] = []

    for i, case in enumerate(test_cases, 1):
        logger.info("Case %d/%d", i, total)
        result = run_single(case, agent_url=agent_url)

        if stop_on_error and result.stopped == "error":
            raise RuntimeError(
                f"Agent error on {case.id[:8]}: {result.failure_reason}"
            )

        results.append(result)

        if i < total:
            time.sleep(delay)

    errors = sum(1 for r in results if r.stopped == "error")
    logger.info(
        "Suite complete: %d/%d ran without error",
        total - errors, total,
    )

    return results


def summarise(results: list[TestResult]) -> dict:
    """Quick summary of results by category before scoring."""
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
