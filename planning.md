# FitFindr — planning.md

> Complete this document before writing any implementation code.
> Your spec and agent diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Your planning.md will be reviewed as part of your submission.
> Update it before starting any stretch features.

---

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
Looks through the database of listings for used clothing items that match user's criteria (description of item, size, and max budget). It returns a list of matching listings.

**Input parameters:**
description (str): Description of the desired item (e.g., "vintage graphic shirt", "blue jeans", "hoodie").
size (str | None): Size the user wants (e.g., "S", "M", "L", "W30"); if not required, then None.
max_price (float | None): Maximum price the user is ready to pay; if not required, then None.

**What it returns:**
List of listing dicts sorted by relevance score, from high to low. Each listing dict will have the following keys: "id": str, "title": str, "description": str, "category": str, "style_tags": list[str], "size": str, "condition": str, "price": float, "colors": list[str], "brand": str | None, "platform": str. Empty list [] when there are no matching listings — no exceptions here.

**What happens if it fails or returns nothing:**
Returns []. The agent will detect that an empty list was received from search_listings, set "session['error']" to an explanation of what happened (that there were no suitable items found) and some suggestions for user (to adjust search criteria, for example), and return from the function without calling other functions.

---

### Tool 2: suggest_outfit

**What it does:**
Uses LLM (Groq llama-3.3-70b-versatile) to suggest one or two complete outfit ideas to wear with the selected thrifted item, using the items in the user's closet.


**Input parameters:**
new_item (dict): Selected listing object from search_listings — title, category, colors, style_tags, description
wardrobe (dict): Dictionary representing the user's closet with an "items" key that holds a list of item dictionaries, each containing: name, category, colors, style_tags, notes


**What it returns:**
Non-empty string suggesting outfits.

**What happens if it fails or returns nothing:**
If the list of wardrobe items (i.e., wardrobe['items']) is empty, send another request to LLM with different prompts about stylistic suggestions for the new item.

---

### Tool 3: create_fit_card

**What it does:**
Generates an Instagram/TikTok-like caption using an LLM that features the thrifted item and outfit.

**Input parameters:**
outfit (str): The suggested outfit string output from suggest_outfit.
new_item (dict): The thrifting item chosen (used for title, price, and platform).

**What it returns:**
A brief 2-4 sentence caption string that includes the name of the item, its price, and the platform. Makes use of LLM with temperature of 1.0.

**What happens if it fails or returns nothing:**
In case the outfit parameter is empty or contains only whitespace, an appropriate error string message is returned rather than an exception.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
1. Receive the query from the user.
2. Get search details (description, size, max_price).
3. Invoke the search_listings() function.
4. If there is no return data:
     - Put the error message into the session state.
     - Return.
5. Else:
     - Assign the first return value to selected_item.
6. Invoke suggest_outfit(selected_item, wardrobe).
7. Assign the returned outfit to outfit_suggestion.
8. Invoke create_fit_card(outfit_suggestion, selected_item).
9. Assign the output caption to fit_card.
10. Return the session state.

---

## State Management

**How does information from one tool get passed to the next?**
- The agent stores information in the session dictionary while working.

- An example of the session structure follows:

session = {
    "selected_item": None,
    "outfit_suggestion": None,
    "fit_card": None,
    "error": None
}

- The selected item from the search_listings function is stored in the selected_item.

- The recommended outfit from suggest_outfit is stored in outfit_suggestion.

- The created fit card from create_fit_card function is stored in fit_card.

- Information is transferred between tools in the form of a session.

---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query |Let user know there were no matches for his search criteria|
| suggest_outfit | Wardrobe is empty |Give user styling suggestions in general|
| create_fit_card | Outfit input is missing or incomplete |Generate an informative error message instead of a caption|

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

User query (natural language)
    │
    ▼
┌─────────────────────────────────┐
│          _parse_query()         │
│  regex → description, size,     │
│          max_price              │
└────────────────┬────────────────┘
                 │ session["parsed"]
                 ▼
┌─────────────────────────────────┐
│       search_listings()         │
│  filter by price + size         │
│  score by keyword overlap        │
│  sort descending                │
└────────────────┬────────────────┘
                 │
        ┌────────┴────────┐
        │                 │
   results=[]         results=[item,...]
        │                 │
        ▼                 ▼
  session["error"]   session["selected_item"] = results[0]
  return early ◄──── (early exit)
                          │
                          ▼
          ┌───────────────────────────┐
          │      suggest_outfit()     │
          │  new_item + wardrobe      │
          │  LLM → outfit string      │
          └──────────────┬────────────┘
                         │ session["outfit_suggestion"]
                         ▼
          ┌───────────────────────────┐
          │     create_fit_card()     │
          │  outfit + new_item        │
          │  LLM → caption string     │
          └──────────────┬────────────┘
                         │ session["fit_card"]
                         ▼
                   Return session

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:** 
Claude will be responsible for implementing each tool individually. For every tool, I will provide Claude with the specifications from this planning document along with its inputs, outputs, and failure modes. I will ask ChatGPT to generate Python implementations of these tools according to the required function signature. I will ensure that the parameter values used by the code agree with the specifications provided.

**Milestone 4 — Planning loop and state management:**
For the planning loop and state management component, I will provide the Planning Loop, State Management subsection along with the Architecture Diagram. I will then ask Claude to generate the run_agent() implementation which will take care of storing variables into a session dictionary and calling tools accordingly. I will make sure that the agent stops itself once the value returned by search_listings() becomes an empty list.
---

## A Complete Interaction (Step by Step)

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.

**Example user query:** "I'm looking for a vintage graphic tee under $30. I mostly wear baggy jeans and chunky sneakers. What's out there and how would I style it?"

**Step 1:**
The user inputs:

"I am searching for an old graphic t-shirt that costs less than $30. I generally prefer loose-fitting jeans along with chunky sneakers."

The bot executes:

search_listings(
    description="old graphic t-shirt",
    size=None,
    max_price=30
)

Output:

[
    {
        "title": "Faded Band T-Shirt",
        "price": 22,
        "platform": "Depop"
    }
]

**Step 2:**
The selected item is saved as:

session["selected_item"]

The bot executes:

suggest_outfit(
    selected_item,
    wardrobe
)

Output:

Match this faded band T-shirt with your loose-fitting jeans along with chunky sneakers.

**Step 3:**
The outfit suggestion is saved as:

session["outfit_suggestion"]

The bot executes:

create_fit_card(
    outfit_suggestion,
    selected_item
)

Output:

Found this faded band T-shirt for $22 and I swear it was meant for my loose-fitting jeans 😍 thrift finds never disappoint

**Final output to user:**
Selected Item

Faded Band T-Shirt - $22

Outfit Suggestion

Match this faded band T-shirt with your loose-fitting jeans along with chunky sneakers.

Fit Card

Found this faded band T-shirt for $22 and I swear it was meant for my loose-fitting jeans 😍 thrift finds never disappoint