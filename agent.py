"""
agent.py

The FitFindr planning loop. Orchestrates the three tools in response to a
natural language user query, passing state between them via a session dict.

Usage:
    from agent import run_agent
    from utils.data_loader import get_example_wardrobe

    result = run_agent(
        query="vintage graphic tee under $30, size M",
        wardrobe=get_example_wardrobe(),
    )
    print(result["fit_card"])
    print(result["error"])   # None on success
"""

import re

from tools import search_listings, suggest_outfit, create_fit_card


# ── session state ─────────────────────────────────────────────────────────────

def _new_session(query: str, wardrobe: dict) -> dict:
    """Initialize and return a fresh session dict for one user interaction."""
    return {
        "query": query,
        "parsed": {},
        "search_results": [],
        "selected_item": None,
        "wardrobe": wardrobe,
        "outfit_suggestion": None,
        "fit_card": None,
        "error": None,
    }


# ── query parsing ─────────────────────────────────────────────────────────────

def _parse_query(query: str) -> dict:
    """
    Extract description, size, and max_price from a natural language query.

    Strategy: regex for price and size, remainder becomes description.

    Returns a dict with keys: description (str), size (str|None), max_price (float|None)
    """
    text = query.strip()

    # Extract max_price — look for patterns like "under $30", "less than $40", "$25 max"
    max_price = None
    price_patterns = [
        r"under\s*\$?(\d+(?:\.\d+)?)",
        r"less\s+than\s*\$?(\d+(?:\.\d+)?)",
        r"below\s*\$?(\d+(?:\.\d+)?)",
        r"\$(\d+(?:\.\d+)?)\s*(?:max|or less|and under)",
        r"(?:max|maximum)\s*\$?(\d+(?:\.\d+)?)",
        r"\$(\d+(?:\.\d+)?)\s*(?:budget)",
    ]
    for pattern in price_patterns:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            max_price = float(m.group(1))
            text = re.sub(pattern, "", text, flags=re.IGNORECASE).strip()
            break

    # Extract size — look for common size tokens
    size = None
    size_pattern = r"\b(XXS|XS|S/M|M/L|XL/XXL|XXL|XL|size\s+\w+|W\d{2}(?:\s+L\d{2})?|US\s*\d+(?:\.\d+)?)\b"
    m = re.search(size_pattern, text, re.IGNORECASE)
    if m:
        size = m.group(1).strip()
        # Normalize "size M" → "M"
        size = re.sub(r"(?i)^size\s+", "", size).strip()
        text = re.sub(size_pattern, "", text, flags=re.IGNORECASE).strip()

    # Also handle standalone single-letter sizes not caught above
    if size is None:
        standalone = re.search(r"\bsize\s+([A-Z]{1,3})\b", text, re.IGNORECASE)
        if standalone:
            size = standalone.group(1).upper()
            text = text[:standalone.start()] + text[standalone.end():]

    # Clean up leftover punctuation/connector words
    description = re.sub(r"\s+", " ", text).strip(" ,.-")
    # Remove filler phrases that dilute keyword matching
    for filler in ["i'm looking for", "looking for", "i want", "i need",
                   "can you find", "find me", "searching for", "help me find"]:
        description = re.sub(filler, "", description, flags=re.IGNORECASE).strip(" ,.")
    # Strip leading articles (a, an, the) left over after filler removal
    description = re.sub(r"^(a|an|the)\s+", "", description, flags=re.IGNORECASE).strip()

    return {
        "description": description or query,
        "size": size,
        "max_price": max_price,
    }


# ── planning loop ─────────────────────────────────────────────────────────────

def run_agent(query: str, wardrobe: dict) -> dict:
    """
    Main agent entry point. Runs the FitFindr planning loop for a single
    user interaction and returns the completed session dict.

    Planning loop logic:
        1. Parse query → extract description, size, max_price
        2. Call search_listings() with parsed params
           → If empty: set error, return early (do NOT proceed to outfit tools)
           → If results: pick top result as selected_item
        3. Call suggest_outfit(selected_item, wardrobe)
        4. Call create_fit_card(outfit_suggestion, selected_item)
        5. Return session

    Args:
        query:    Natural language user request
        wardrobe: User's wardrobe dict

    Returns:
        Session dict. Check session["error"] first — if not None, the interaction
        ended early and outfit_suggestion / fit_card will be None.
    """
    # Step 1: Initialize session
    session = _new_session(query, wardrobe)

    # Step 2: Parse the query
    parsed = _parse_query(query)
    session["parsed"] = parsed

    # Step 3: Search listings
    results = search_listings(
        description=parsed["description"],
        size=parsed["size"],
        max_price=parsed["max_price"],
    )
    session["search_results"] = results

    # Step 4: Check results — branch here
    if not results:
        # Build a helpful, specific error message
        parts = []
        if parsed["max_price"]:
            parts.append(f"under ${parsed['max_price']:.0f}")
        if parsed["size"]:
            parts.append(f"in size {parsed['size']}")
        constraint_str = " ".join(parts)

        session["error"] = (
            f"No listings found for \"{parsed['description']}\""
            + (f" {constraint_str}" if constraint_str else "")
            + ". Try broadening your search — remove the size filter, raise your budget, "
            "or use more general keywords (e.g. 'tee' instead of 'graphic tee')."
        )
        return session

    # Step 5: Select top result
    session["selected_item"] = results[0]

    # Step 6: Suggest outfit using the selected item and wardrobe
    outfit = suggest_outfit(session["selected_item"], wardrobe)
    session["outfit_suggestion"] = outfit

    # Step 7: Create fit card
    fit_card = create_fit_card(outfit, session["selected_item"])
    session["fit_card"] = fit_card

    # Step 8: Return completed session
    return session


# ── CLI test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json, os, sys
    sys.path.insert(0, os.path.dirname(__file__))

    # Load example wardrobe directly from schema file for CLI test
    schema_path = os.path.join(os.path.dirname(__file__), "data", "wardrobe_schema.json")
    with open(schema_path, encoding="utf-8") as f:
        schema_data = json.load(f)
    example_wardrobe = schema_data["example_wardrobe"]
    empty_wardrobe = schema_data["empty_wardrobe"]

    print("=== Happy path: graphic tee ===\n")
    session = run_agent(
        query="looking for a vintage graphic tee under $30",
        wardrobe=example_wardrobe,
    )
    if session["error"]:
        print(f"Error: {session['error']}")
    else:
        print(f"Parsed: {session['parsed']}")
        print(f"Found: {session['selected_item']['title']} — ${session['selected_item']['price']}")
        print(f"\nOutfit:\n{session['outfit_suggestion']}")
        print(f"\nFit card:\n{session['fit_card']}")

    print("\n\n=== No-results path ===\n")
    session2 = run_agent(
        query="designer ballgown size XXS under $5",
        wardrobe=example_wardrobe,
    )
    print(f"Error message: {session2['error']}")