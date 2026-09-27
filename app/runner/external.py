"""External agent caller for AgentRedTeam.

Sends attack prompts to any HTTP endpoint and returns a standardised
result dict, matching the shape that run_agent() returns so the rest
of the pipeline (scorer, trust score) works without any changes.

The external agent only needs to implement one endpoint:
  POST /
  Body:  {"message": "..."}
  Reply: {"reply": "..."}

Optionally it can also return:
  {"reply": "...", "tool_calls": [...], "refunds": [...]}

If it returns only "reply", tool_calls and refunds default to empty lists.
"""
import logging
import time

import httpx

logger = logging.getLogger(__name__)

# How long to wait for the external agent to respond.
# 60s because some agents are slow (multi-step reasoning, slow APIs).
DEFAULT_TIMEOUT = 60.0
DEFAULT_DELAY = 1.0  # seconds between calls (external agents may rate-limit)


def call_external_agent(
    url: str,
    prompt: str,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict:
    """Send one prompt to an external agent and return a standardised result.

    Args:
        url:     the agent's endpoint URL
        prompt:  the attack prompt to send
        timeout: seconds to wait before giving up

    Returns:
        dict matching run_agent()'s output shape:
        {
            "reply":      str | None,
            "tool_calls": list,
            "refunds":    list,
            "turns":      int,
            "stopped":    str,
        }

    Never raises: errors are captured in the result dict so the runner
    can continue with the next case.
    """
    logger.info("Calling external agent at %s", url)

    try:
        response = httpx.post(
            url,
            json={"message": prompt},
            timeout=timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        data = response.json()

        # Extract reply — support both "reply" and "message" keys
        reply = data.get("reply") or data.get("message") or data.get("content")

        if reply is None:
            logger.warning(
                "External agent response missing 'reply' field: %s",
                str(data)[:200],
            )

        return {
            "reply":      str(reply) if reply is not None else None,
            "tool_calls": data.get("tool_calls", []),
            "refunds":    data.get("refunds", []),
            "turns":      data.get("turns", 1),
            "stopped":    data.get("stopped", "completed"),
        }

    except httpx.TimeoutException:
        logger.error("External agent timed out after %.0fs: %s", timeout, url)
        return {
            "reply":    None,
            "tool_calls": [],
            "refunds":    [],
            "turns":      0,
            "stopped":    "error",
            "error":      f"Timeout after {timeout}s",
        }

    except httpx.HTTPStatusError as e:
        logger.error(
            "External agent returned HTTP %d: %s",
            e.response.status_code, url,
        )
        return {
            "reply":    None,
            "tool_calls": [],
            "refunds":    [],
            "turns":      0,
            "stopped":    "error",
            "error":      f"HTTP {e.response.status_code}: {e.response.text[:200]}",
        }

    except Exception as e:
        logger.error("External agent call failed: %s", e)
        return {
            "reply":    None,
            "tool_calls": [],
            "refunds":    [],
            "turns":      0,
            "stopped":    "error",
            "error":      f"{type(e).__name__}: {e}",
        }


def run_external_suite(
    test_cases: list,
    agent_url: str,
    delay: float = DEFAULT_DELAY,
) -> list:
    """Run all test cases against an external agent.

    Same interface as run_suite() in runner.py but calls the external
    agent instead of the built-in one.
    """
    from app.attacks.models import TestResult

    results = []
    total = len(test_cases)

    logger.info(
        "Running %d cases against external agent: %s", total, agent_url
    )

    for i, case in enumerate(test_cases, 1):
        logger.info("Case %d/%d [%s]", i, total, case.category)

        raw = call_external_agent(agent_url, case.prompt)

        results.append(TestResult(
            test_case_id=case.id,
            category=case.category,
            prompt=case.prompt,
            reply=raw.get("reply"),
            tool_calls=raw.get("tool_calls", []),
            refunds=raw.get("refunds", []),
            turns=raw.get("turns", 1),
            stopped=raw.get("stopped", "completed"),
            failure_reason=raw.get("error"),
        ))

        if i < total:
            time.sleep(delay)

    errors = sum(1 for r in results if r.stopped == "error")
    logger.info(
        "External suite complete: %d/%d ran without error",
        total - errors, total,
    )

    return results
