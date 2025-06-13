# -*- coding: utf-8 -*-

# TODO: Ensure tmdb_get is imported or defined if it's not a global or built-in helper.
# from kodicek import tmdb_get # Example: if tmdb_get is in kodicek.py
# or from .utils import tmdb_get # Example: if it's in a utils.py in the same directory

def search_tmdb(query, tmdb_get_func):
    """
    Searches TMDB using multi search, with language fallback and fuzzy alias.
    """
    langs = ["cs-CZ", "en-US"]  # ➋ Prioritize Czech, fallback to English
    
    for lang in langs:
        # ➊ multi search → we get both tv and movie results
        params = {"query": query, "language": lang}
        # Note: The original prompt mentioned include_language=en-US for the cs-CZ call.
        # The pseudocode implements a loop. If 'cs-CZ' should also include 'en-US' results
        # simultaneously (e.g. for missing fields), the tmdb_get call would need modification.
        # Current implementation strictly tries 'cs-CZ' then 'en-US'.
        if lang == "cs-CZ":
            # If you want cs-CZ results to potentially include English titles/overviews when Czech is missing
            # params["include_adult"] = False # Example, adjust as needed
            # params["include_image_language"] = "cs,null" # Prioritize Czech images
            pass # No specific include_language for the primary, as per pseudocode logic of separate calls

        res = tmdb_get_func("/search/multi", params)
        if res and res.get("results"):
            return res["results"]
            
    # ➌ Last attempt with alias if the original query yielded no results in any language
    alt_query = query.replace(" a ", " and ")
    if alt_query != query:
        # Recursive call with the alternative query
        # Pass the tmdb_get_func along
        return search_tmdb(alt_query, tmdb_get_func)
        
    return []

if __name__ == '__main__':
    # Example usage (requires a mock or real tmdb_get function)
    def mock_tmdb_get(endpoint, params):
        print(f"Mock TMDB GET: {endpoint} with params {params}")
        if params["query"] == "Test Show" and params["language"] == "cs-CZ":
            return {"results": [{"id": 1, "name": "Test Show CS", "media_type": "tv"}]}
        if params["query"] == "Test Show" and params["language"] == "en-US":
            return {"results": [{"id": 1, "name": "Test Show EN", "media_type": "tv"}]}
        if params["query"] == "NonExistent a Show" and params["language"] == "cs-CZ":
            return {"results": []}
        if params["query"] == "NonExistent a Show" and params["language"] == "en-US":
            return {"results": []}
        if params["query"] == "NonExistent and Show" and params["language"] == "cs-CZ":
            return {"results": [{"id": 2, "name": "NonExistent and Show CS (from alias)", "media_type": "movie"}]}
        return {"results": []}

    print("Searching for 'Test Show':")
    results = search_tmdb("Test Show", mock_tmdb_get)
    print(f"Results: {results}\n")

    print("Searching for 'NonExistent a Show' (will try alias):")
    results_alias = search_tmdb("NonExistent a Show", mock_tmdb_get)
    print(f"Results: {results_alias}\n")

    print("Searching for 'Only English Show' (mock needs to be adjusted to test this path):")
    # To test this, mock_tmdb_get should return empty for cs-CZ and results for en-US
    def mock_tmdb_get_en_fallback(endpoint, params):
        print(f"Mock TMDB GET (EN Fallback): {endpoint} with params {params}")
        if params["query"] == "Only English Show" and params["language"] == "cs-CZ":
            return {"results": []}
        if params["query"] == "Only English Show" and params["language"] == "en-US":
            return {"results": [{"id": 3, "name": "Only English Show EN", "media_type": "tv"}]}
        return {"results": []}
    results_en = search_tmdb("Only English Show", mock_tmdb_get_en_fallback)
    print(f"Results: {results_en}\n")
