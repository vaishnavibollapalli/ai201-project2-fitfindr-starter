"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os
import json

from dotenv import load_dotenv
from groq import Groq

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


def _load_listings():
    """Load listings from data/listings.json."""
    data_path = os.path.join(os.path.dirname(__file__), "data", "listings.json")
    with open(data_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> list[dict]:
    """
    Search the mock listings dataset for items matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A list of matching listing dicts sorted by relevance score (highest first).
        Each dict has: id, title, description, category, style_tags (list), size,
        condition, price (float), colors (list), brand, platform.
        Returns an empty list if nothing matches — does NOT raise an exception.
    """
    try:
        listings = _load_listings()
    except Exception:
        return []

    # Step 1: Filter by price
    if max_price is not None:
        listings = [l for l in listings if l.get("price", 9999) <= max_price]

    # Step 2: Filter by size (case-insensitive substring match)
    if size:
        size_lower = size.lower()
        listings = [
            l for l in listings
            if size_lower in (l.get("size") or "").lower()
        ]

    # Step 3: Score by keyword overlap with description
    keywords = [w.lower() for w in description.replace(",", " ").split() if len(w) > 2]

    def score(listing):
        text = " ".join([
            listing.get("title", ""),
            listing.get("description", ""),
            listing.get("category", ""),
            " ".join(listing.get("style_tags", [])),
            " ".join(listing.get("colors", [])),
            listing.get("brand") or "",
        ]).lower()
        return sum(1 for kw in keywords if kw in text)

    scored = [(score(l), l) for l in listings]

    # Step 4: Drop zero-score results
    scored = [(s, l) for s, l in scored if s > 0]

    # Step 5: Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return [l for _, l in scored]


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offers general styling advice for the item.
    """
    client = _get_groq_client()

    item_summary = (
        f"Item: {new_item.get('title', 'Unknown item')}\n"
        f"Category: {new_item.get('category', 'unknown')}\n"
        f"Colors: {', '.join(new_item.get('colors', []))}\n"
        f"Style tags: {', '.join(new_item.get('style_tags', []))}\n"
        f"Description: {new_item.get('description', '')}"
    )

    wardrobe_items = wardrobe.get("items", [])

    if not wardrobe_items:
        # Empty wardrobe — give general styling advice
        prompt = (
            f"A user is considering buying this thrifted item:\n\n{item_summary}\n\n"
            "They don't have a wardrobe on file yet. Give them 1–2 general outfit ideas: "
            "what types of pieces pair well with this item, what vibe or aesthetic it suits, "
            "and any specific styling tips (tucking, layering, footwear, etc.). "
            "Be specific and conversational — not generic fashion-magazine advice."
        )
    else:
        # Format wardrobe for the prompt
        wardrobe_text = "\n".join(
            f"- {item.get('name', 'unnamed')} ({item.get('category', '')}): "
            f"colors {', '.join(item.get('colors', []))}; "
            f"tags {', '.join(item.get('style_tags', []))}"
            for item in wardrobe_items
        )
        prompt = (
            f"A user is considering buying this thrifted item:\n\n{item_summary}\n\n"
            f"Their current wardrobe includes:\n{wardrobe_text}\n\n"
            "Suggest 1–2 complete outfit combinations using the new item and specific named "
            "pieces from their wardrobe. Name the exact wardrobe pieces you're pairing. "
            "Include any styling tips (tucking, layering, shoe choice, etc.). "
            "Be specific, practical, and conversational."
        )

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=400,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Could not generate outfit suggestion: {e}"


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, returns a descriptive error message string.
    """
    # Guard against empty outfit
    if not outfit or not outfit.strip():
        return (
            "Error: No outfit suggestion was provided, so a fit card could not be generated. "
            "Please make sure suggest_outfit ran successfully before calling create_fit_card."
        )

    item_name = new_item.get("title", "thrifted find")
    price = new_item.get("price", "")
    platform = new_item.get("platform", "")

    price_str = f"${price:.0f}" if isinstance(price, (int, float)) else str(price)

    prompt = (
        f"Write a 2–4 sentence Instagram/TikTok caption for this thrift find and outfit.\n\n"
        f"Item: {item_name}\n"
        f"Price: {price_str}\n"
        f"Platform: {platform}\n"
        f"Outfit: {outfit}\n\n"
        "Rules:\n"
        "- Sound like a real person posting an OOTD — casual and authentic, not a product listing\n"
        "- Mention the item name, price, and platform naturally (once each)\n"
        "- Capture the specific vibe of the outfit in concrete terms\n"
        "- Include 1–2 relevant emojis\n"
        "- Do NOT start with 'I' or 'Just'\n"
        "Return only the caption text, nothing else."
    )

    try:
        client = _get_groq_client()
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=1.0,  # Higher temp for variety
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error generating fit card: {e}"