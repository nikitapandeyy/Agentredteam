"""Test the attack generator against a single template.

Usage:
    python -m scripts.test_generator                  # uses tool_misuse_exceed_total
    python -m scripts.test_generator exfil_email_direct
    python -m scripts.test_generator contradiction_authority_claim
"""
import json
import logging
import sys

from app.attacks.generator import generate_from_template
from app.attacks.templates import TEMPLATE_MAP

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s  %(message)s",
)


def main() -> None:
    template_id = sys.argv[1] if len(sys.argv) > 1 else "tool_misuse_exceed_total"

    if template_id not in TEMPLATE_MAP:
        print(f"Unknown template: {template_id}")
        print(f"Available: {', '.join(sorted(TEMPLATE_MAP))}")
        return

    template = TEMPLATE_MAP[template_id]
    print(f"Generating {template.variations} variations for: {template_id}")
    print(f"Category: {template.category}")
    print(f"Attacker goal: {template.context.get('attacker_goal')}")
    print("=" * 70)

    cases = generate_from_template(template, delay=1.5)

    for i, case in enumerate(cases, 1):
        print(f"\nVariation {i}:")
        print(f"  Prompt: {case.prompt}")
        print(f"  Slots:  {json.dumps(case.filled_slots, indent=4)}")
        print(f"  ID:     {case.id}")

    print(f"\n{len(cases)}/{template.variations} cases generated successfully")


if __name__ == "__main__":
    main()
