r"""
Quick manual test for Google Gemini web search grounding.

Usage (PowerShell on Windows):
  cd C:\Apps\TouristGuideLocal ; .\venv\Scripts\Activate.ps1 ; python scripts/test_gemini_web_search.py --query "Art-kino Croatia Rijeka" --host "Lovran, Croatia"

Requirements:
  - Root .env with GOOGLE_AI_API_KEY set (Gemini Developer API)
  - Optional: set --model to override (default: gemini-2.5-pro)
"""

import argparse
import os
import sys

try:
    from dotenv import load_dotenv, find_dotenv
except Exception:  # pragma: no cover
    load_dotenv = None
    find_dotenv = None


def main():
    parser = argparse.ArgumentParser(description="Test Gemini web search grounding for a location query")
    parser.add_argument("--query", type=str, default="Art-kino Croatia Rijeka", help="Attraction/location query text")
    parser.add_argument("--host", type=str, default="Lovran, Croatia", help="Host base location for context")
    parser.add_argument("--model", type=str, default="gemini-2.5-pro", help="Gemini model (e.g., gemini-2.5-pro or gemini-2.5-flash)")
    args = parser.parse_args()

    # Load .env from repo root if available
    if load_dotenv:
        loaded = False
        if find_dotenv:
            path = find_dotenv(usecwd=True)
            if path:
                load_dotenv(path)
                loaded = True
        if not loaded:
            # Fallback: attempt ../.env relative to this script
            dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
            if os.path.exists(dotenv_path):
                load_dotenv(dotenv_path)

    google_key = os.environ.get("GOOGLE_AI_API_KEY")
    if not google_key:
        print("ERROR: GOOGLE_AI_API_KEY not set in environment (.env)", file=sys.stderr)
        sys.exit(1)

    try:
        from google import genai as genai_client
        from google.genai import types as genai_types
    except Exception as e:  # pragma: no cover
        print(f"ERROR: google-genai SDK not installed: {e}", file=sys.stderr)
        print("Install with: pip install google-genai", file=sys.stderr)
        sys.exit(1)

    client = genai_client.Client(api_key=google_key)

    # Compose system + user with explicit grounding expectations
    system_instruction = (
        "You are a Croatian tourism expert. Use Google Search tools to gather brief, factual context "
        "about the attraction and its neighborhood. Cite domains in parentheses when appropriate."
    )

    user_prompt = f"""
    Attraction: {args.query}
    Host Base: {args.host}

    Task:
    - What it is and the experience (ambience/programming, typical visit length)
    - Practical details if available (rating sentiment, budget range)
    - How it relates to staying in {args.host} (simple transport/time)
    - Suggest a pairing nearby for a short itinerary
    - Include 1-2 concise grounded facts with domain citations like (site.com) if tools retrieve them

    Output: Two short paragraphs plus a "Good to know" bullet list (3-4 bullets). Avoid placeholders.
    """

    contents = f"System instructions:\n{system_instruction}\n\nUser request:\n{user_prompt}".strip()

    print(f"Model: {args.model}")
    print("Query:", args.query)
    print()

    try:
        resp = client.models.generate_content(
            model=args.model,
            contents=contents,
            config={"tools": [{"google_search": {}}]}
        )
    except Exception as e:
        print(f"ERROR calling Gemini: {e}", file=sys.stderr)
        sys.exit(2)

    text = getattr(resp, "text", "").strip()
    print("=== Gemini Output ===")
    print(text)

    # Attempt to surface grounding metadata if present
    if hasattr(resp, 'candidates') and resp.candidates:
        candidate = resp.candidates[0]
        if hasattr(candidate, 'grounding_metadata'):
            gm = candidate.grounding_metadata
            print("\n=== Grounding Metadata (summary) ===")
            try:
                if hasattr(gm, 'web_search_queries') and gm.web_search_queries:
                    print("Search Queries:", ", ".join(gm.web_search_queries))
                if hasattr(gm, 'grounding_chunks') and gm.grounding_chunks:
                    print("Grounding Chunks:", len(gm.grounding_chunks))
                    for i, chunk in enumerate(gm.grounding_chunks[:3]):  # Show first 3
                        if hasattr(chunk, 'web') and hasattr(chunk.web, 'title'):
                            print(f"  {i+1}. {chunk.web.title}")
            except Exception as e:
                print(f"Error parsing grounding metadata: {e}")

    print()


if __name__ == "__main__":
    main()


