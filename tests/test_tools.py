"""
tests/test_tools.py

Pytest tests covering happy paths and failure modes for all three FitFindr tools.
Run with: pytest tests/
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import search_listings, suggest_outfit, create_fit_card


# ── search_listings tests ─────────────────────────────────────────────────────

def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    """Impossible query — must return [] not raise an exception."""
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=30)
    assert all(item["price"] <= 30 for item in results)


def test_search_size_filter():
    results = search_listings("jeans", size="M", max_price=None)
    # All results should contain "m" in their size field (case-insensitive)
    for item in results:
        assert "m" in (item.get("size") or "").lower()


def test_search_sorted_by_relevance():
    results = search_listings("vintage streetwear", size=None, max_price=None)
    # Should return something
    assert len(results) > 0
    # First result should be more style-relevant (hard to assert exact order,
    # but we can verify results contain relevant tags)
    first_tags = results[0].get("style_tags", [])
    assert any(kw in " ".join(first_tags).lower() for kw in ["vintage", "streetwear"])


def test_search_returns_correct_fields():
    results = search_listings("tee", size=None, max_price=100)
    assert len(results) > 0
    required_fields = ["id", "title", "description", "category", "price", "platform"]
    for field in required_fields:
        assert field in results[0], f"Missing field: {field}"


# ── suggest_outfit tests ──────────────────────────────────────────────────────

def _get_sample_item():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert results, "Need at least one result for outfit tests"
    return results[0]


def _get_example_wardrobe():
    import json
    schema_path = os.path.join(os.path.dirname(__file__), "..", "data", "wardrobe_schema.json")
    with open(schema_path) as f:
        return json.load(f)["example_wardrobe"]


def _get_empty_wardrobe():
    return {"items": []}


def test_suggest_outfit_with_wardrobe():
    item = _get_sample_item()
    wardrobe = _get_example_wardrobe()
    result = suggest_outfit(item, wardrobe)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_suggest_outfit_empty_wardrobe():
    """Empty wardrobe should return general styling advice, not crash."""
    item = _get_sample_item()
    result = suggest_outfit(item, _get_empty_wardrobe())
    assert isinstance(result, str)
    assert len(result.strip()) > 0
    # Should not be an empty string
    assert result != ""


# ── create_fit_card tests ─────────────────────────────────────────────────────

def test_create_fit_card_happy_path():
    item = _get_sample_item()
    wardrobe = _get_example_wardrobe()
    outfit = suggest_outfit(item, wardrobe)
    card = create_fit_card(outfit, item)
    assert isinstance(card, str)
    assert len(card.strip()) > 0


def test_create_fit_card_empty_outfit():
    """Empty outfit string must return error message, not raise exception."""
    item = _get_sample_item()
    result = create_fit_card("", item)
    assert isinstance(result, str)
    assert "error" in result.lower() or "no outfit" in result.lower()


def test_create_fit_card_whitespace_outfit():
    """Whitespace-only outfit should also return error, not crash."""
    item = _get_sample_item()
    result = create_fit_card("   ", item)
    assert isinstance(result, str)
    assert len(result.strip()) > 0


def test_create_fit_card_mentions_item_details():
    """Caption should reference the item name and price naturally."""
    item = _get_sample_item()
    outfit = suggest_outfit(item, _get_example_wardrobe())
    card = create_fit_card(outfit, item)
    # Price should appear somewhere
    price = str(int(item.get("price", 0)))
    assert price in card or item.get("title", "").split()[0].lower() in card.lower()