import xbmcvfs
import io
import json
import xbmcaddon
import os
import xbmc # For xbmc.log

# For maximum compatibility (all platforms)
try:
    from xbmc import translatePath
except ImportError:
    from xbmcvfs import translatePath

PROFILE = translatePath(xbmcaddon.Addon().getAddonInfo('profile'))
HISTORY_FILE = os.path.join(PROFILE, "history.json")
SEARCH_HISTORY_FILE = os.path.join(PROFILE, "search_history.json") # New file for search history
MAX_HISTORY = 100
MAX_SEARCH_HISTORY = 50 # Can be different from playback history, e.g. 50

def ensure_profile_dir():
    """Ensures the profile directory exists."""
    if not xbmcvfs.exists(PROFILE):
        xbmc.log(f"Kodicek History: Profile directory does not exist. Attempting to create: {PROFILE}", level=xbmc.LOGINFO)
        if xbmcvfs.mkdirs(PROFILE):
            xbmc.log(f"Kodicek History: Successfully created profile directory: {PROFILE}", level=xbmc.LOGINFO)
        else:
            xbmc.log(f"Kodicek History: Failed to create profile directory: {PROFILE}", level=xbmc.LOGERROR)
            # If directory creation fails, subsequent operations will likely fail too.

def load_history():
    """Loads the playback history from the JSON file."""
    ensure_profile_dir()
    xbmc.log(f"Kodicek: Attempting to load playback history from {HISTORY_FILE}", level=xbmc.LOGINFO)

    if not xbmcvfs.exists(HISTORY_FILE):
        xbmc.log(f"Kodicek History: Playback history file does not exist: {HISTORY_FILE}", level=xbmc.LOGINFO)
        return []

    try:
        with io.open(HISTORY_FILE, 'r', encoding='utf8') as f:
            history_data = json.load(f)
            xbmc.log(f"Kodicek: Loaded playback history: {len(history_data)} items", level=xbmc.LOGINFO)
            return history_data
    except Exception as e:
        xbmc.log(f"Kodicek History: Error loading playback history file {HISTORY_FILE}: {e}", level=xbmc.LOGERROR)
        try:
            if xbmcvfs.delete(HISTORY_FILE):
                xbmc.log(f"Kodicek History: Deleted corrupted playback history file {HISTORY_FILE}", level=xbmc.LOGWARNING)
            else:
                xbmc.log(f"Kodicek History: Failed to delete corrupted playback history file {HISTORY_FILE}", level=xbmc.LOGERROR)
        except Exception as delete_e:
            xbmc.log(f"Kodicek History: Error during attempt to delete corrupted playback history file {HISTORY_FILE}: {delete_e}", level=xbmc.LOGERROR)
        return []

def save_history(history):
    """Saves the playback history to the JSON file, limiting to MAX_HISTORY items."""
    ensure_profile_dir()
    xbmc.log(f"Kodicek: Saving playback history to {HISTORY_FILE}", level=xbmc.LOGINFO)

    try:
        with io.open(HISTORY_FILE, 'w', encoding='utf8') as f:
            json.dump(history[:MAX_HISTORY], f, ensure_ascii=False, indent=2)
        xbmc.log(f"Kodicek History: Successfully saved playback history to {HISTORY_FILE}", level=xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Kodicek History: Error saving playback history file {HISTORY_FILE}: {e}", level=xbmc.LOGERROR)

def add_to_history(item):
    """Adds an item to the playback history, ensuring no duplicates based on 'ident'."""
    history = load_history()
    item_ident = item.get('ident')
    if item_ident is not None:
        history = [h for h in history if h.get('ident') != item_ident]
    else:
        xbmc.log(f"Kodicek History: Item added to playback history is missing 'ident': {item.get('name', 'Unknown item')}", level=xbmc.LOGWARNING)

    history.insert(0, item)
    save_history(history)

# --- Search History Functions ---

def load_search_history():
    """Loads the search history from the JSON file."""
    ensure_profile_dir()
    xbmc.log(f"Kodicek: Attempting to load search history from {SEARCH_HISTORY_FILE}", level=xbmc.LOGINFO)

    if not xbmcvfs.exists(SEARCH_HISTORY_FILE):
        xbmc.log(f"Kodicek History: Search history file does not exist: {SEARCH_HISTORY_FILE}", level=xbmc.LOGINFO)
        return []

    try:
        with io.open(SEARCH_HISTORY_FILE, 'r', encoding='utf8') as f:
            search_history_data = json.load(f)
            xbmc.log(f"Kodicek: Loaded search history: {len(search_history_data)} items", level=xbmc.LOGINFO)
            return search_history_data
    except Exception as e:
        xbmc.log(f"Kodicek History: Error loading search history file {SEARCH_HISTORY_FILE}: {e}", level=xbmc.LOGERROR)
        try:
            if xbmcvfs.delete(SEARCH_HISTORY_FILE):
                xbmc.log(f"Kodicek History: Deleted corrupted search history file {SEARCH_HISTORY_FILE}", level=xbmc.LOGWARNING)
            else:
                xbmc.log(f"Kodicek History: Failed to delete corrupted search history file {SEARCH_HISTORY_FILE}", level=xbmc.LOGERROR)
        except Exception as delete_e:
            xbmc.log(f"Kodicek History: Error during attempt to delete corrupted search history file {SEARCH_HISTORY_FILE}: {delete_e}", level=xbmc.LOGERROR)
        return []

def save_search_history(search_history):
    """Saves the search history to the JSON file, limiting to MAX_SEARCH_HISTORY items."""
    ensure_profile_dir()
    xbmc.log(f"Kodicek: Saving search history to {SEARCH_HISTORY_FILE}", level=xbmc.LOGINFO)

    try:
        with io.open(SEARCH_HISTORY_FILE, 'w', encoding='utf8') as f:
            json.dump(search_history[:MAX_SEARCH_HISTORY], f, ensure_ascii=False, indent=2)
        xbmc.log(f"Kodicek History: Successfully saved search history to {SEARCH_HISTORY_FILE}", level=xbmc.LOGINFO)
    except Exception as e:
        xbmc.log(f"Kodicek History: Error saving search history file {SEARCH_HISTORY_FILE}: {e}", level=xbmc.LOGERROR)

def add_to_search_history(item):
    """Adds a search query item to the search history.
    Item is expected to be a dict, e.g., {"query": "search term", "timestamp": 123}
    Ensures no duplicate queries.
    """
    search_history = load_search_history()
    
    current_query = item.get('query')
    if current_query is not None:
        # Remove previous occurrences of the same query
        search_history = [h for h in search_history if h.get('query') != current_query]
    else:
        xbmc.log(f"Kodicek History: Item added to search history is missing 'query': {item}", level=xbmc.LOGWARNING)
        # Optionally, don't add items without a query, or handle as an error
        return 

    search_history.insert(0, item)
    save_search_history(search_history)

# Example test call (can be removed or commented out for production)
# if __name__ == '__main__':
#     # This block is for local testing if you run this script directly (not in Kodi)
#     # It requires mocking xbmc, xbmcaddon, xbmcvfs, translatePath
#     print("Simulating history operations (requires mocks for Kodi environment)")
#     # Mocking example (very basic)
#     class MockAddon:
#         def getAddonInfo(self, info_id):
#             if info_id == 'profile':
#                 return "mock_profile_path"
#             return "mock_addon"
#     xbmcaddon.Addon = MockAddon
#     # Further mocks needed for xbmcvfs, xbmc.log, translatePath
