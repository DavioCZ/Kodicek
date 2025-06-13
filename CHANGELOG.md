# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-06-06

### Added
- Added "Filmy" (Movies) and "Seriály" (Series) items to the main menu in `kodicek.py`.
  - These items currently lead to placeholder functions that display a notification.
  - Routing for these new actions (`movies` and `series`) has been added to the `router` function.
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

## [1.2.0] - 2025-06-13

### Changed
- Vylepšeno vyhledávání na TMDB (`search_tmdb`):
    - Přidána tolerance roku (`year_fuzz`) pro flexibilnější vyhledávání. Funkce nyní zkouší přesný rok, poté roky v rozsahu ±`year_fuzz` a nakonec vyhledávání bez roku.
- Upraveno párování roku v `process_tmdb_selection` při skórování souborů z Webshare:
    - Rok v názvu souboru je nyní porovnáván s rokem z TMDB s tolerancí ±1 rok.
- Vylepšeno vyhledávání na Webshare v `process_tmdb_selection`:
    - Primární vyhledávání na Webshare nyní používá název z TMDb očištěný od roku (`strip_year(title)`).
    - Přidány další fallback vyhledávací pokusy, pokud primární selže:
        1. Název z TMDb (očištěný) + rok z TMDb.
        2. Originální název z TMDb (očištěný) bez roku.
        3. Originální název z TMDb (očištěný) + rok z TMDb.
- Přidána funkce `strip_year(title)` pro odstranění roku z názvu.
    - Tato funkce je nyní použita pro přípravu dotazů pro TMDB a Webshare, aby se primárně vyhledávalo podle názvu bez roku, zatímco rok samotný je použit pro fuzzy vyhledávání na TMDB a skórování na Webshare.
    - Normalizovaný název pro párování v `process_tmdb_selection` (`normalized_tmdb_title`) je nyní také založen na názvu bez roku.

## [1.3.0] - 2025-06-13

### Added
- **Rozšířená podpora pro seriály:**
    - Implementována plná navigace pro seriály: Výběr seriálu → Výběr sezóny → Výběr epizody.
    - Metadata (názvy, popisy, obrázky) pro seriály, sezóny a epizody jsou načítány z TMDB API.
    - Pro epizody je konstruován specifický dotaz pro Webshare (`{Název seriálu} S{číslo série}E{číslo epizody} + {Český/EN název dílu} + {rok seriálu}`).
- **Nové helper funkce v `kodicek.py`:**
    - `tmdb_api_request`: Univerzální funkce pro volání TMDB API.
    - `_tmdb_get_for_search_module`: Wrapper pro `tmdb_api_request` používaný novou `search_tmdb` funkcí.
    - `get_banner_image_url`: Získává URL pro banner/backdrop z TMDB položky.
- **Konstanta `UI_LANG`**: Přidána do `kodicek.py` pro specifikaci jazyka UI prvků a TMDB dat (nastaveno na "cs-CZ").

### Changed
- **Vyhledávání přes TMDB (`resources/lib/tmdb.py`):**
    - Přepnuto na endpoint `/search/multi` pro současné vyhledávání filmů a seriálů.
    - Implementována podpora pro více jazyků: primárně `cs-CZ`, fallback na `en-US`.
    - Přidán fuzzy alias pro vyhledávací dotaz (nahrazuje `" a "` za `" and "`).
- **Zpracování výsledků vyhledávání v `kodicek.py` (`action="search"`):**
    - Nyní využívá `new_search_tmdb` z `resources/lib/tmdb.py`.
    - Rozlišuje `media_type` ('movie' vs 'tv') z výsledků `/search/multi`.
    - Filmy vedou na `action=process_tmdb_selection`.
    - Seriály vedou na novou akci `action=show_seasons`.
- **Refaktorována funkce `get_tmdb_details` v `kodicek.py`:**
    - Nyní využívá novou helper funkci `tmdb_api_request`.
    - Rozšířena o `external_ids` v `append_to_response`.
- **Použití `urllib.parse.quote(string, encoding='utf-8')`:**
    - Zajištěno správné kódování URL parametrů obsahujících názvy/titulky.

## [Unreleased]

### Removed
* Streamuj.tv integration completely removed.

### Added
- Added Streamuj.tv search functionality:
  - Updated the `search()` method in `resources/lib/streamuj.py` to use the Streamuj.tv XHR POST endpoint (`/ajax/search`). This involves sending a JSON payload (`{"term": query, "limit": limit, "type": "video"}`) and parsing the JSON response. This replaces the previous GET request to `/api/search` for improved compatibility with the current Streamuj.tv API.
  - The `_request()` method in `resources/lib/streamuj.py` continues to use a standard User-Agent (`Mozilla/5.0...`) via the `_headers()` method for all requests made by `StreamujHoster`.
  - The previous scraping-specific regular expression `_SEARCH_ITEM_RE` is still present in `streamuj.py` but is not used by the active `search` method.
  - In `kodicek.py`:
    - Added a new route `action="search_streamuj"` in the `router` function.
    - Added a new menu item "[COLOR gold]Vyhledávání – test Streamuj[/COLOR]" to `display_main_menu()`. This item is non-folder and directly triggers the search.
    - Implemented the `search_streamuj()` function, which:
      - Prompts the user for a search term.
      - Uses the `StreamujHoster.search()` method to find results.
      - If one result is found, attempts to play it directly.
      - If multiple results are found, displays them in a list for the user to select and play.
      - Shows a notification if no results are found or if a stream URL cannot be obtained.
    - Added a helper function `add_dir()` to `kodicek.py` for creating directory items, used by the new menu entry.
- Integrated Streamuj.tv resolver:
  - Added `StreamujHoster` class import and initialization in `kodicek.py`'s `HOSTERS` list.
  - Added settings for Streamuj.tv username (`st_user`), password (`st_pass`), and preferred CDN location (`st_loc`) to `resources/settings.xml`.
- Added "Vyhledávání - test" item to the main menu in `kodicek.py`.
  - This item triggers a new `search_test` action.
  - The `search_test` action prompts the user for a search term using an input dialog.
  - It then performs a Webshare search with the entered term and displays the results, prefixed with "[TEST]".
  - This is for basic testing of the search functionality.
- Initial TMDb integration for movie searching:
  - Added setting in `resources/settings.xml` for TMDb API key.
  - Implemented `get_tmdb_api_key()` to retrieve the key in `kodicek.py`.
  - Added `search_tmdb()` and `get_tmdb_details()` functions for interacting with the TMDb API (movies and TV shows, though currently focused on movies).
  - Modified the `search` action in `kodicek.py`:
    - Parses the search query for a potential year.
    - If TMDb API key is present, searches TMDb for movies.
    - If TMDb results are found, they are displayed to the user with title, year, overview, and poster.
    - Added a new `process_tmdb_selection` action:
      - Triggered when a user selects a TMDb result.
      - Fetches detailed TMDb info (currently logged, for future use).
      - Uses the selected TMDb item's title and year to perform a refined search on Webshare.
      - Displays Webshare results based on the TMDb selection.
    - If no TMDb results are found, the plugin falls back to searching Webshare with the original user query.
- Implemented smart filtering and scoring of Webshare results in `process_tmdb_selection` action:
  - Added `normalize_text()` helper function for cleaning and standardizing titles for comparison.
  - After selecting a TMDb item, Webshare search results are fetched.
  - Each Webshare file is scored based on matching the normalized TMDb title, year, language indicators (CZ, SK, EN), and quality keywords (1080p, 720p, bluray, etc.).
  - Non-video files are penalized.
  - Results are sorted by score, and the score is displayed alongside the filename.
  - TMDb metadata (poster, plot, genre, etc.) is used to enrich the `ListItem` for the sorted Webshare results.
- Initial project setup.

### Changed
- Updated `TASK_LIST.md` with a detailed plan for TMDb integration (API key, search, details, images) and Webshare result filtering (name/year matching, scoring algorithm, file type filtering).
- **Vylepšeno vyhledávání epizod na Webshare (`play_episode` v `kodicek.py`):**
  - Funkce `build_episode_queries` byla přepsána tak, aby generovala širší spektrum variant dotazů pro epizody. Nově zahrnuje:
    - Krátké formáty čísel sezón a epizod (např. `S1E1`, `1x1`) vedle plných formátů (`S01E01`, `01x01`), včetně variant s mezerou (např. `S01 E01`).
    - Různé kombinace s/bez názvu epizody a s/bez roku vydání seriálu.
    - Upravené pořadí generovaných dotazů pro optimalizaci šance na nalezení relevantních výsledků.
  - Přidána nová pomocná funkce `filter_episode_results` pro filtrování výsledků z Webshare. Tato funkce zajišťuje, že vrácené soubory obsahují normalizovaný název seriálu A zároveň jeden z relevantních vzorů kódu epizody (např. `s01e01`, `01x01`, `s1e1`, `1x1`), čímž se zvyšuje relevance nalezených zdrojů.
  - Funkce `play_episode` nyní po každém dotazu na Webshare volá `filter_episode_results`. Pokračuje v iteraci dalšími variantami dotazů pouze pokud aktuální dotaz po filtraci nevrátí žádné relevantní výsledky.
  - Rozšířeno logování v `play_episode` tak, aby zobrazovalo počet původních výsledků z Webshare a počet výsledků po aplikaci `filter_episode_results`.
  - Zvýšen limit pro `search_webshare` na 100 výsledků, aby bylo více dat pro filtrování.
- Enhanced the scoring logic in `process_tmdb_selection` for stricter and more accurate filtering of Webshare results:
  - Implemented a `MIN_SCORE_THRESHOLD` (set to 3.0). Files scoring below this are discarded.
  - Title matching is stricter: `normalized_tmdb_title` must be a substring of `fname_normalized`. If not, the file is heavily penalized (score = -100). A successful match grants a +3.0 bonus.
  - Year matching: If TMDb year is present and matches in `fname_normalized`, score +2.0. If TMDb year is present but not found in filename, score -1.0.
  - Language scoring adjusted: `.cz.dab` and `.sk.dab` added to Czech and Slovak language tags. Slovak bonus set to 1.5.
  - Quality scoring expanded: Added `2160p`/`4k` (+2.0 bonus). Added `web` as a general web-dl/webrip indicator. Penalizes CAM/TS/TC rips by -3.0.
  - File type check now includes `.mpg`, `.mpeg`, `.iso` as valid video extensions. Non-video files get a score of -200.
  - Logging for scored/rejected files now includes the score formatted to two decimal places.
  - Notification message updated if no files meet the threshold after filtering.

### Fixed
- Corrected the regular expression `_SOURCE_RE` in `resources/lib/streamuj.py` to properly capture source URLs from Streamuj.tv, resolving a `SyntaxError` related to mismatched parentheses.
- **Opravena chyba "Invalid setting type" pro `tmdb_skip_specials`:**
  - Přidána definice `tmdb_skip_specials` (typ `bool`, default `true`) do `resources/settings.xml`.
  - Volání `addon.getSettingBool("tmdb_skip_specials")` v `kodicek.py` (funkce `show_seasons`) bylo ošetřeno pomocí `try-except TypeError`, aby se předešlo chybě, pokud nastavení chybí nebo má nesprávný typ. V takovém případě se použije výchozí hodnota `True`.
