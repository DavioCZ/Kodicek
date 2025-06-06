# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-06-06

### Added
- Implemented playback history functionality:
  - Created `history.py` with functions to load, save, and add items to a JSON-based history file (`history.json`) stored in the addon's profile directory.
  - History is limited to the last 100 items, with duplicates (based on 'ident') being removed and the newest entry added to the top.
  - Added robust directory creation and error handling for history file operations, including logging and attempting to delete corrupted history files.
- Integrated history into `kodicek.py`:
  - Imported `add_to_history` and `load_history` from `history.py`.
  - In the `play` action, after successfully obtaining a stream URL, an item containing `ident`, `name`, `timestamp`, and `type` is added to the history.
  - Added a "Historie" (History) item to the main menu (`display_main_menu`).
  - Implemented a new `history` action in the router to display saved history items.
  - History items are displayed with their name and last watched time. Clicking a history item re-initiates playback.

### Changed
- Enhanced `get_stream_link` function in `kodicek.py`:
  - Tries multiple parameter combinations (`video_stream`, `file_download`, no `download_type`) when requesting a stream link from the Webshare API.
  - Added detailed logging for request parameters and raw XML responses.
  - Displays a Kodi notification if a stream link cannot be obtained after all attempts.
- Enhanced `play` action in `kodicek.py`:
  - Added more verbose logging throughout the playback initiation process, with a `[PLAY]` prefix for easier log filtering.
  - Ensures user credentials and Webshare token are re-validated or re-fetched before attempting to get a stream link.
  - Displays Kodi notifications for errors encountered during the play action (e.g., missing ident, login failure, failure to get stream link).
- Improved `ListItem` handling in `kodicek.py` for better playback compatibility:
  - Added a `get_mimetype(filename)` helper function to determine common video MIME types based on file extensions.
  - Set `IsPlayable` property to `true` for `ListItem` objects in search results.
  - In the `play` action, the `ListItem` passed to `xbmcplugin.setResolvedUrl()` now:
    - Includes necessary HTTP headers (User-Agent, Cookie with Webshare token) appended to the stream URL, separated by `|`.
    - Has its `MimeType` property set using the `get_mimetype` function.
  - Has its `IsPlayable` property set to `true`.
- Updated `display_main_menu` in `kodicek.py` to use the standard Kodi search icon (`DefaultAddonsSearch.png`) for the "Vyhledat" (Search) menu item.
  - Modified the `initiate_search` action in `kodicek.py` to directly process the search and display results, instead of using `Container.Update`. This fixes an issue where pressing "back" after a search would return to the search input prompt instead of the main menu. Search queries are now also added to history.
  - Added detailed logging to `history.py` and `kodicek.py` to trace history saving/loading paths and function calls for easier debugging.
- Refactored `history.py` to use `xbmcvfs` for file and directory operations (checking existence, creating directories, deleting files) and `translatePath` for resolving profile paths, enhancing cross-platform compatibility and adherence to Kodi best practices.
- Refactored search functionality in `kodicek.py` to fix a UX bug:
  - The main menu "Vyhledat" (Search) item now calls `action=search&ask=1`.
  - The `action=initiate_search` logic has been removed and its functionality merged into `action=search`.
  - The `action=search` now only displays the keyboard input dialog if the `ask=1` parameter is present.
  - If `ask=1` is not present and no `what` (search term) parameter is provided, a menu is displayed showing "Nové vyhledávání..." (New Search) and recent search history items. This prevents the keyboard from appearing unexpectedly on navigating back or when no explicit search action is taken.
- Separated playback history and search history:
  - `history.py` now includes functions (`load_search_history`, `save_search_history`, `add_to_search_history`) to manage search queries in a separate `search_history.json` file.
  - `kodicek.py` updated to use these new functions:
    - Search queries are now saved to `search_history.json` via `add_to_search_history`.
    - The "Vyhledávání" (Search) menu, when no active search is performed, now displays past search queries from `load_search_history`.
    - The "Historie" (History) menu (`action=history`) now correctly displays only playback history from `history.json` (managed by `load_history` and `add_to_history`) and its title is updated to "Historie přehrávání".
- Restructured main menu and history views in `kodicek.py`:
  - Main menu now has "Vyhledat film/seriál" (opens keyboard for new search) and a "Historie" folder.
  - The "Historie" folder, when selected, displays a "Historie vyhledávání" sub-folder (links to `action=search` to show past search queries) at the top.
  - Directly below the "Historie vyhledávání" sub-folder, the playback history (recently watched items) is listed, newest first.
  - This change ensures that the keyboard for search only appears when "Vyhledat film/seriál" is explicitly chosen, and provides a consolidated "Historie" section.

## [Unreleased]

### Added
- Initial project setup.
