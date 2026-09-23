"""Data models for attack test cases.

A TestCase is one complete, ready-to-run adversarial input. It carries
everything the runner needs: the prompt to send, which order to use,
what the attacker is trying to achieve, and metadata for the report.
"""
from datetime import datetime, timezone
from typing import Any
import uuid

from pydantic import BaseModel, Field


class TestCase(BaseModel):
    """One generated adversarial test case, ready to run against the agent."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    template_id: str
    category: str
    prompt: str            # the complete attack message to send to the agent
    order_id: str | None   # which order the runner should use, if any
    attacker_goal: str     # plain English: what a successful attack achieves
    filled_slots: dict[str, Any]  # what the generator put in each slot
    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    model_config = {"frozen": True}  # test cases are immutable once created


class TestResult(BaseModel):
    """The agent's response to one TestCase, plus scoring fields (filled later)."""

    test_case_id: str
    category: str
    prompt: str
    reply: str | None
    tool_calls: list[dict]
    refunds: list[dict]
    turns: int
    stopped: str
    rule_passed: bool | None = None   # filled by Task 10
    judge_passed: bool | None = None  # filled by Task 11
    passed: bool | None = None        # final verdict, filled by Task 12
    failure_reason: str | None = None
