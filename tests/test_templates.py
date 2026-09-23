"""Structural tests for the template library. No API calls."""
from app.attacks.templates import TEMPLATES, TEMPLATE_MAP, TEMPLATES_BY_CATEGORY
from app.attacks.categories import CATEGORY_MAP


def test_all_templates_reference_valid_category():
    """Every template must belong to a defined category."""
    for t in TEMPLATES:
        assert t.category in CATEGORY_MAP, (
            f"Template '{t.id}' references unknown category '{t.category}'"
        )


def test_all_template_ids_are_unique():
    ids = [t.id for t in TEMPLATES]
    assert len(ids) == len(set(ids)), "Duplicate template IDs found"


def test_slots_match_template_placeholders():
    """Every slot listed must appear in the template string."""
    for t in TEMPLATES:
        for slot in t.slots:
            assert f"{{{slot}}}" in t.template, (
                f"Template '{t.id}' lists slot '{slot}' "
                f"but it does not appear in the template string"
            )


def test_template_map_covers_all_templates():
    assert set(TEMPLATE_MAP.keys()) == {t.id for t in TEMPLATES}


def test_every_category_has_at_least_one_template():
    """No category should be left without any attack templates."""
    for category_name in CATEGORY_MAP:
        assert category_name in TEMPLATES_BY_CATEGORY, (
            f"Category '{category_name}' has no templates"
        )
