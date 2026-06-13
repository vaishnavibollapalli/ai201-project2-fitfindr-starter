# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

# FitFindr 🛍️

An AI-powered thrift styling agent that finds secondhand clothing, builds outfits from your wardrobe, and generates a shareable fit card — all from a single natural language query.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_key_here
```

Run the styled Flask interface:
```bash
python flask_app.py
```

Open `http://127.0.0.1:5000` in your browser.

---

## Tool Inventory

### Tool 1 — `search_listings(description, size, max_price)`

**Purpose:** Searches the 40-item mock listings dataset for secondhand clothing matching the user's request.

**Inputs:**
- `description` (str) — keywords describing the item (e.g. `"vintage graphic tee"`)
- `size` (str | None) — size to filter by, case-insensitive substring match; `None` skips size filtering
- `max_price` (float | None) — maximum price inclusive; `None` skips price filtering

**Returns:** A list of listing dicts sorted by relevance score (highest first). Each dict has: `id` (str), `title` (str), `description` (str), `category` (str), `style_tags` (list[str]), `size` (str), `condition` (str), `price` (float), `colors` (list[str]), `brand` (str | None), `platform` (str). Returns `[]` on no match — never raises an exception.

**Relevance scoring:** Keyword overlap between the user description and each listing's title, description, category, style tags, colors, and brand. Listings with zero overlap are dropped before sorting.

---

### Tool 2 — `suggest_outfit(new_item, wardrobe)`

**Purpose:** Uses Groq LLM (llama-3.3-70b-versatile) to suggest 1–2 complete outfit combinations pairing the thrifted item with pieces from the user's wardrobe.

**Inputs:**
- `new_item` (dict) — a listing dict returned by `search_listings`
- `wardrobe` (dict) — wardrobe dict with an `"items"` key containing a list of wardrobe item dicts

**Returns:** A non-empty string with outfit suggestions naming specific wardrobe pieces and styling tips. If `wardrobe["items"]` is empty, returns general styling advice instead of crashing or returning `""`.

---

### Tool 3 — `create_fit_card(outfit, new_item)`

**Purpose:** Uses Groq LLM to generate a casual, shareable Instagram/TikTok caption for the outfit.

**Inputs:**
- `outfit` (str) — the outfit suggestion string from `suggest_outfit`
- `new_item` (dict) — the listing dict for the thrifted item

**Returns:** A 2–4 sentence caption mentioning the item name, price, and platform naturally. Uses LLM temperature 1.0 for variety across runs. If `outfit` is empty or whitespace-only, returns a descriptive error string — does not raise an exception.

---

## How the Planning Loop Works

The agent uses a sequential loop with one critical branch point after `search_listings`:

```
1. Parse user query with regex:
   → Extract max_price  (patterns: "under $30", "less than $40", "$25 max")
   → Extract size       (patterns: "size M", "XL", "W30", "US 8")
   → Remainder → description (filler phrases like "looking for" stripped)

2. Call search_listings(description, size, max_price)

3. CHECK: results empty?
   YES → session["error"] = specific message naming the failed constraint
         and telling user what to try → return early
         do NOT call suggest_outfit or create_fit_card
   NO  → session["selected_item"] = results[0]  (top relevance score)

4. Call suggest_outfit(selected_item, wardrobe)
   → session["outfit_suggestion"] = result

5. Call create_fit_card(outfit_suggestion, selected_item)
   → session["fit_card"] = result

6. Return session
```

The agent never calls `suggest_outfit` or `create_fit_card` on empty input.

---

## State Management

All state lives in a single session dict:

```python
session = {
    "query":             str,        # original user query
    "parsed":            dict,       # extracted description / size / max_price
    "search_results":    list,       # all matching listing dicts
    "selected_item":     dict,       # results[0] — passed directly to suggest_outfit
    "wardrobe":          dict,       # user's wardrobe — passed into suggest_outfit
    "outfit_suggestion": str,        # suggest_outfit output → create_fit_card input
    "fit_card":          str,        # create_fit_card output
    "error":             str | None, # set on early termination; None on success
}
```

- `search_listings` returns a list → `results[0]` stored as `session["selected_item"]`  
- `session["selected_item"]` passed directly to `suggest_outfit` as `new_item` — no user re-entry  
- `suggest_outfit` return stored as `session["outfit_suggestion"]`  
- `session["outfit_suggestion"]` passed directly to `create_fit_card` as `outfit` — no user re-entry

---

## Error Handling

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| `search_listings` | No listings match query constraints | Sets `session["error"]`: *"No listings found for '[query]' [in size X] [under $Y]. Try broadening your search — remove the size filter, raise your budget, or use more general keywords."* Returns early without calling outfit tools. |
| `suggest_outfit` | Wardrobe is empty (`wardrobe["items"] == []`) | Sends LLM a different prompt asking for general styling advice — returns a useful string instead of crashing or returning `""`. |
| `create_fit_card` | `outfit` is empty or whitespace-only | Returns: `"Error: No outfit suggestion was provided, so a fit card could not be generated."` — does not raise an exception. |

**Concrete example from testing:**

Query: `"designer ballgown size XXS under $5"` → `search_listings` returns `[]` → agent sets:
```
session["error"] = 'No listings found for "designer ballgown" in size XXS under $5.
Try broadening your search — remove the size filter, raise your budget, or use
more general keywords (e.g. "tee" instead of "graphic tee").'
```
`suggest_outfit` and `create_fit_card` are never called. UI shows error in listing panel; outfit and fit card panels are empty.

---

## Spec Reflection

**One way the spec helped:** Writing the planning loop in `planning.md` with explicit conditional logic — specifically the branch on `search_listings` returning empty — meant the guard clause in `run_agent()` was the first thing coded after initializing the session. Without the spec it would have been easy to wire all three tools sequentially and discover the empty-input bug only during testing.

**One way implementation diverged from spec:** The spec left query parsing open ("regex, string splitting, or LLM"). I initially planned to use the LLM for parsing. In practice, LLM-based parsing added a full extra API call per query, introducing latency and variability. Regex proved reliable enough since price and size signals in natural language follow predictable patterns. Switching to regex made the agent faster and removed a source of non-determinism.

---

## AI Usage

**Instance 1 — `search_listings` implementation:**  
I gave Claude the Tool 1 spec block from `planning.md` (inputs with types, return value with field list, failure mode) and asked it to implement the function using `load_listings()` from the data loader with keyword scoring and filters. Claude generated a version using `in` matching against a concatenated text blob. I reviewed it against the spec and added: (1) dropping zero-score listings before sorting (required by spec), and (2) normalizing size comparison to lowercase on both sides, since the dataset has mixed casing like `"S/M"` and `"XL (oversized)"` that a strict match would miss.

**Instance 2 — `run_agent()` planning loop:**  
I gave Claude the Planning Loop and State Management sections of `planning.md` along with the ASCII architecture diagram. Claude generated a version of `run_agent()` that called all three tools in sequence without checking whether `search_listings` returned results. I revised it to add the early-return branch and changed the error message from a generic "no results found" to the specific format that names the failed constraints and suggests next steps.