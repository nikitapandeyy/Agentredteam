"""Deterministic tests for the agent's tools. No API calls."""
import pytest

from app.agent import tools


@pytest.fixture(autouse=True)
def clean_state():
    """Reset side effects before and after every test in this file."""
    tools.reset_state()
    yield
    tools.reset_state()


def test_lookup_order_returns_order():
    result = tools.lookup_order("ORD-1001")
    assert result["status"] == "delivered"
    assert result["total"] == 2499.00


def test_lookup_order_unknown_id_returns_error():
    result = tools.lookup_order("ORD-9999")
    assert "error" in result


def test_issue_refund_records_side_effect():
    tools.issue_refund("ORD-1001", 500, "damaged")
    assert len(tools.REFUND_LOG) == 1
    assert tools.REFUND_LOG[0]["amount"] == 500


def test_issue_refund_rejects_non_positive_amount():
    result = tools.issue_refund("ORD-1001", 0, "test")
    assert "error" in result
    assert tools.REFUND_LOG == []


def test_get_store_policy_unknown_topic_lists_options():
    result = tools.get_store_policy("returns")
    assert "error" in result
    assert "refunds" in result["error"]


def test_reset_state_clears_refund_log():
    tools.issue_refund("ORD-1001", 100, "test")
    tools.reset_state()
    assert tools.REFUND_LOG == []


def test_every_schema_has_a_matching_function():
    """The model can only call tools our code can actually run."""
    schema_names = {s["function"]["name"] for s in tools.TOOL_SCHEMAS}
    assert schema_names == set(tools.TOOL_FUNCTIONS)
