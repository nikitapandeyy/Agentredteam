"""End-to-end test: generate attacks, run them against the agent, summarise.

Usage:
    # Run one category (fast, ~5 cases, good for development)
    python -m scripts.run_test_suite tool_misuse

    # Run two categories
    python -m scripts.run_test_suite tool_misuse instruction_contradiction

    # Run everything (slow, ~45 cases, uses significant quota)
    python -m scripts.run_test_suite all
"""
import json
import logging
import sys

# Silence Google SDK noise
logging.getLogger("google.genai").setLevel(logging.ERROR)
logging.getLogger("google.genai.models").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)

from app.attacks.categories import CATEGORY_MAP
from app.attacks.generator import generate_all
from app.runner.runner import run_suite, summarise


def main() -> None:
    args = sys.argv[1:]

    if not args:
        print("Usage:")
        print("  python -m scripts.run_test_suite tool_misuse")
        print("  python -m scripts.run_test_suite tool_misuse instruction_contradiction")
        print("  python -m scripts.run_test_suite all")
        print(f"\nAvailable categories: {', '.join(CATEGORY_MAP)}")
        return

    # Resolve category names
    if args == ["all"]:
        categories = None  # generate_all with None means all categories
        label = "all categories"
    else:
        invalid = [a for a in args if a not in CATEGORY_MAP]
        if invalid:
            print(f"Unknown categories: {invalid}")
            print(f"Available: {', '.join(CATEGORY_MAP)}")
            return
        categories = args
        label = ", ".join(categories)

    print(f"\nAgentRedTeam — running {label}")
    print("=" * 70)

    # Phase 1: Generate
    print("\n[1/2] Generating attack test cases...")
    test_cases = generate_all(categories=categories, delay=2.0)
    print(f"      Generated {len(test_cases)} test cases\n")

    if not test_cases:
        print("No test cases generated. Check your GEMINI_MODEL and API key.")
        return

    # Show what we're about to run
    by_cat: dict[str, int] = {}
    for tc in test_cases:
        by_cat[tc.category] = by_cat.get(tc.category, 0) + 1
    for cat, count in by_cat.items():
        print(f"      {cat}: {count} cases")

    print(f"\n[2/2] Running {len(test_cases)} cases against the agent...")
    print("      (3 second delay between calls for rate limiting)\n")

    # Phase 2: Run
    results = run_suite(test_cases, delay=3.0)

    # Phase 3: Summarise (scoring comes in Tasks 10-12)
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY (pre-scoring)")
    print("=" * 70)

    summary = summarise(results)
    print(f"\nTotal cases run : {summary['total_cases']}")
    print(f"Errors          : {summary['total_errors']}")
    print(f"Refunds issued  : {summary['total_refunds_issued']}")

    print("\nBy category:")
    for cat, stats in summary["by_category"].items():
        print(f"\n  {cat}:")
        print(f"    Cases          : {stats['total']}")
        print(f"    Errors         : {stats['errors']}")
        print(f"    Refunds issued : {stats['refunds_issued']}")
        print(f"    Tool calls     : {stats['tool_calls']}")

    print("\nSample results (first 3):")
    print("-" * 70)
    for r in results[:3]:
        print(f"\n  Category : {r.category}")
        print(f"  Prompt   : {r.prompt[:80]}...")
        print(f"  Reply    : {(r.reply or 'ERROR')[:120]}...")
        print(f"  Refunds  : {r.refunds}")
        print(f"  Turns    : {r.turns}  Stopped: {r.stopped}")

    print("\nNote: pass/fail scoring comes in Tasks 10-12.")


if __name__ == "__main__":
    main()
