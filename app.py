"""
app.py

Gradio interface for FitFindr. Run with:
    python app.py

Then open the localhost URL shown in your terminal.
"""

import json
import os

import gradio as gr

from agent import run_agent


# ── wardrobe loaders ──────────────────────────────────────────────────────────

def _load_wardrobes():
    schema_path = os.path.join(os.path.dirname(__file__), "data", "wardrobe_schema.json")
    with open(schema_path, encoding="utf-8") as f:
        data = json.load(f)
    return data["example_wardrobe"], data["empty_wardrobe"]


# ── query handler ─────────────────────────────────────────────────────────────

def handle_query(user_query: str, wardrobe_choice: str) -> tuple[str, str, str]:
    """
    Called by Gradio when the user submits a query.

    Args:
        user_query:      The text the user typed into the search box.
        wardrobe_choice: Either "Example wardrobe" or "Empty wardrobe (new user)".

    Returns:
        (listing_text, outfit_suggestion, fit_card) — three strings for the panels.
    """
    # Step 1: Guard against empty query
    if not user_query or not user_query.strip():
        return "Please enter a search query to get started.", "", ""

    # Step 2: Select wardrobe
    example_wardrobe, empty_wardrobe = _load_wardrobes()
    wardrobe = example_wardrobe if wardrobe_choice == "Example wardrobe" else empty_wardrobe

    # Step 3: Run agent
    session = run_agent(query=user_query.strip(), wardrobe=wardrobe)

    # Step 4: Handle error path
    if session["error"]:
        return session["error"], "", ""

    # Step 5: Format listing text
    item = session["selected_item"]
    price = item.get("price", "")
    price_str = f"${price:.2f}" if isinstance(price, (int, float)) else str(price)

    listing_text = (
        f"🏷️  {item.get('title', 'Unknown item')}\n"
        f"💰  {price_str}\n"
        f"📦  Condition: {item.get('condition', 'unknown').title()}\n"
        f"📏  Size: {item.get('size', 'not listed')}\n"
        f"🛍️  Platform: {item.get('platform', 'unknown').title()}\n"
        f"🎨  Colors: {', '.join(item.get('colors', []))}\n"
    )
    if item.get("brand"):
        listing_text += f"👕  Brand: {item['brand']}\n"
    listing_text += f"\n{item.get('description', '')}"

    return listing_text, session["outfit_suggestion"], session["fit_card"]


# ── interface ─────────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "vintage graphic tee under $30",
    "90s track jacket in size M",
    "flowy midi skirt under $40",
    "black combat boots size 8",
    "designer ballgown size XXS under $5",   # deliberate no-results test
]

def build_interface():
    with gr.Blocks(title="FitFindr") as demo:
        gr.Markdown("""
# FitFindr 🛍️
Find secondhand pieces and get outfit ideas based on your wardrobe.
Describe what you're looking for — include size and price if you want to filter.
        """)

        with gr.Row():
            query_input = gr.Textbox(
                label="What are you looking for?",
                placeholder="e.g. vintage graphic tee under $30, size M",
                lines=2,
                scale=3,
            )
            wardrobe_choice = gr.Radio(
                choices=["Example wardrobe", "Empty wardrobe (new user)"],
                value="Example wardrobe",
                label="Wardrobe",
                scale=1,
            )

        submit_btn = gr.Button("Find it", variant="primary")

        with gr.Row():
            listing_output = gr.Textbox(
                label="🛍️ Top listing found",
                lines=8,
                interactive=False,
            )
            outfit_output = gr.Textbox(
                label="👗 Outfit idea",
                lines=8,
                interactive=False,
            )
            fitcard_output = gr.Textbox(
                label="✨ Your fit card",
                lines=8,
                interactive=False,
            )

        gr.Examples(
            examples=[[q, "Example wardrobe"] for q in EXAMPLE_QUERIES],
            inputs=[query_input, wardrobe_choice],
            label="Try these queries",
        )

        submit_btn.click(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )
        query_input.submit(
            fn=handle_query,
            inputs=[query_input, wardrobe_choice],
            outputs=[listing_output, outfit_output, fitcard_output],
        )

    return demo


if __name__ == "__main__":
    demo = build_interface()
    demo.launch()