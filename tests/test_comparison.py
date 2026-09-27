"""Tests for run comparison logic. No API calls, no database."""
import pytest
from unittest.mock import patch

from app.db.storage import get_comparison


def make_run(run_id, score, passed, failed, categories=None, failures=None):
    """Build a minimal run dict for testing."""
    return {
        "run_id": run_id,
        "trust_score": score,
        "total_cases": passed + failed,
        "total_passed": passed,
        "total_failed": failed,
        "agent_name": "Test Agent",
        "started_at": "2026-09-27T00:00:00+00:00",
        "categories": categories or [],
        "failures": failures or [],
    }


def compare(run_a_data, run_b_data):
    """Helper: patch get_run and call get_comparison."""
    def mock_get_run(run_id):
        if run_id == "run_a":
            return run_a_data
        if run_id == "run_b":
            return run_b_data
        return None

    with patch("app.db.storage.get_run", side_effect=mock_get_run):
        return get_comparison("run_a", "run_b")


class TestScoreDelta:

    def test_improvement(self):
        result = compare(
            make_run("run_a", score=57, passed=9, failed=15),
            make_run("run_b", score=84, passed=18, failed=6),
        )
        assert result["score_delta"] == 27
        assert result["verdict"] == "improved"

    def test_regression(self):
        result = compare(
            make_run("run_a", score=90, passed=18, failed=2),
            make_run("run_b", score=70, passed=14, failed=6),
        )
        assert result["score_delta"] == -20
        assert result["verdict"] == "regressed"

    def test_unchanged(self):
        result = compare(
            make_run("run_a", score=75, passed=15, failed=5),
            make_run("run_b", score=75, passed=15, failed=5),
        )
        assert result["score_delta"] == 0
        assert result["verdict"] == "unchanged"


class TestCategoryDiffs:

    def test_category_improvement(self):
        cats_a = [{"category": "tool_misuse", "passed": 3, "failed": 6, "total": 9}]
        cats_b = [{"category": "tool_misuse", "passed": 7, "failed": 2, "total": 9}]

        result = compare(
            make_run("run_a", 60, 3, 6, categories=cats_a),
            make_run("run_b", 85, 7, 2, categories=cats_b),
        )

        cat = next(c for c in result["categories"] if c["category"] == "tool_misuse")
        assert cat["failed_delta"] == -4      # 4 fewer failures
        assert cat["passed_delta"] == 4       # 4 more passes
        assert cat["status"] == "improved"

    def test_category_regression(self):
        cats_a = [{"category": "scope_bypass", "passed": 8, "failed": 1, "total": 9}]
        cats_b = [{"category": "scope_bypass", "passed": 4, "failed": 5, "total": 9}]

        result = compare(
            make_run("run_a", 90, 8, 1, categories=cats_a),
            make_run("run_b", 60, 4, 5, categories=cats_b),
        )

        cat = next(c for c in result["categories"] if c["category"] == "scope_bypass")
        assert cat["status"] == "regressed"
        assert cat["failed_delta"] == 4

    def test_new_category_in_run_b(self):
        """A category that only appears in run_b should show up."""
        cats_b = [{"category": "role_confusion", "passed": 2, "failed": 1, "total": 3}]

        result = compare(
            make_run("run_a", 100, 9, 0, categories=[]),
            make_run("run_b", 90, 11, 1, categories=cats_b),
        )

        cat_names = [c["category"] for c in result["categories"]]
        assert "role_confusion" in cat_names


class TestFailureTracking:

    def test_new_failure_detected(self):
        """A failure in run_b that wasn't in run_a is a regression."""
        failures_b = [{"prompt": "new attack prompt", "category": "scope_bypass",
                       "reply": "sure here is a recipe", "failure_reason": "off topic"}]

        result = compare(
            make_run("run_a", 100, 9, 0, failures=[]),
            make_run("run_b", 90, 8, 1, failures=failures_b),
        )

        assert len(result["new_failures"]) == 1
        assert result["new_failures"][0]["prompt"] == "new attack prompt"

    def test_fixed_failure_detected(self):
        """A failure in run_a that's gone in run_b is a fix."""
        failures_a = [{"prompt": "old attack prompt", "category": "tool_misuse",
                       "reply": "issuing refund", "failure_reason": "bad refund"}]

        result = compare(
            make_run("run_a", 85, 8, 1, failures=failures_a),
            make_run("run_b", 100, 9, 0, failures=[]),
        )

        assert len(result["fixed_failures"]) == 1
        assert result["fixed_failures"][0]["prompt"] == "old attack prompt"

    def test_returns_none_for_missing_run(self):
        def mock_get_run(run_id):
            return None

        with patch("app.db.storage.get_run", side_effect=mock_get_run):
            result = get_comparison("missing_a", "missing_b")

        assert result is None
