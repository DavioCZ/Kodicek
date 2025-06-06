# -*- coding: utf-8 -*-
import sys
import os
import urllib.parse
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import requests
import hashlib
import time # Added for history timestamp
import json # Added for TMDb JSON parsing
from xml.etree import ElementTree as ET
from history import add_to_history, load_history, add_to_search_history, load_search_history # Updated imports
try:
    from md5crypt import md5crypt # Assuming this is available in Kodi's Python environment
except ImportError:
    xbmc.log("Kodíček: md5crypt module not found. Please ensure it is installed or available.", level=xbmc.LOGERROR)
    md5crypt = None # Allow the script to load but login will fail

addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
BASE_URL_PLUGIN = sys.argv[0] # Renamed to avoid conflict if BASE_URL is used for API
plugin_name = "Kodíček"
REALM = ':Webshare:'
WEBSHARE_API_BASE_URL = "https://webshare.cz/api/" # Renamed for clarity
TMDB_API_BASE_URL = "https://api.themoviedb.org/3/"

# Global session object
_session = requests.Session()
_session.headers.update({'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"})

def get_credentials():
    username = addon.getSetting("ws_username")
    password = addon.getSetting("ws_password")
    if not username or not password:
        xbmcgui.Dialog().notification(plugin_name, addon.getLocalizedString(30101), xbmcgui.NOTIFICATION_ERROR) # Assuming 30101 is "Webshare credentials missing"
        addon.openSettings()
        return None, None
    return username, password

def get_tmdb_api_key():
    tmdb_key = addon.getSetting("tmdb_api_key")
    if not tmdb_key:
        xbmcgui.Dialog().notification(plugin_name, "Chybí TMDb API klíč v nastavení!", xbmcgui.NOTIFICATION_ERROR)
        # addon.openSettings() # Might be too aggressive to open settings here, let the user do it.
        return None
    return tmdb_key

def api_call(endpoint, data=None, method='post', base_url=WEBSHARE_API_BASE_URL): # Added base_url parameter
    url = base_url + endpoint
    if base_url == WEBSHARE_API_BASE_URL and not endpoint.endswith('/'): # Webshare expects trailing slash
        url += "/"
        
    try:
        if method == 'post':
            response = _session.post(url, data=data, timeout=10)
        else: # get
            response = _session.get(url, params=data, timeout=10)
        response.raise_for_status()
        return response.content # Return raw content for XML parsing
    except requests.exceptions.RequestException as e:
        xbmc.log(f"Kodíček: API call to {url} failed: {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, f"API Error: {e}", xbmcgui.NOTIFICATION_ERROR)
        return None

def is_xml_ok(xml_root):
    if xml_root is None:
        return False
    status_node = xml_root.find('status')
    if status_node is not None and status_node.text == 'OK':
        return True
    message_node = xml_root.find('message')
    error_message = message_node.text if message_node is not None else "Unknown API error"
    xbmc.log(f"Kodíček: API call not OK. Message: {error_message}", level=xbmc.LOGERROR)
    # xbmcgui.Dialog().notification(plugin_name, f"API Error: {error_message}", xbmcgui.NOTIFICATION_ERROR) # Can be too noisy
    return False

def login_webshare(username, password):
    if md5crypt is None:
        xbmcgui.Dialog().notification(plugin_name, "md5crypt module is missing.", xbmcgui.NOTIFICATION_ERROR)
        return None

    salt_response_content = api_call('salt', {'username_or_email': username}, base_url=WEBSHARE_API_BASE_URL)
    if not salt_response_content:
        return None
    
    try:
        salt_xml = ET.fromstring(salt_response_content)
    except ET.ParseError as e:
        xbmc.log(f"Kodíček: Failed to parse salt XML: {e}. Response: {salt_response_content}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "Login error: Invalid salt response.", xbmcgui.NOTIFICATION_ERROR)
        return None

    if not is_xml_ok(salt_xml):
        xbmcgui.Dialog().notification(plugin_name, "Login error: Could not get salt.", xbmcgui.NOTIFICATION_ERROR)
        return None
    
    salt_node = salt_xml.find('salt')
    if salt_node is None or not salt_node.text:
        xbmc.log("Kodíček: Salt not found in XML response.", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "Login error: Salt missing.", xbmcgui.NOTIFICATION_ERROR)
        return None
    salt = salt_node.text

    try:
        # Ensure password and salt are bytes for md5crypt and hashlib
        password_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        username_bytes = username.encode('utf-8')
        realm_bytes = REALM.encode('utf-8')

        crypted_pass = md5crypt(password_bytes, salt_bytes)
        # md5crypt might return str or bytes depending on version, ensure bytes for hashlib
        if isinstance(crypted_pass, str):
            crypted_pass_bytes = crypted_pass.encode('utf-8')
        else:
            crypted_pass_bytes = crypted_pass
            
        encrypted_pass_sha1 = hashlib.sha1(crypted_pass_bytes).hexdigest()
        
        # Ensure encrypted_pass_sha1 is bytes for digest calculation
        encrypted_pass_sha1_bytes = encrypted_pass_sha1.encode('utf-8')
        
        pass_digest = hashlib.md5(username_bytes + realm_bytes + encrypted_pass_sha1_bytes).hexdigest()
    except Exception as e:
        xbmc.log(f"Kodíček: Error during password encryption: {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "Login error: Encryption failed.", xbmcgui.NOTIFICATION_ERROR)
        return None

    login_data = {
        'username_or_email': username,
        'password': encrypted_pass_sha1, # API expects SHA1 of crypted pass
        'digest': pass_digest,
        'keep_logged_in': '1'
    }
    
    login_response_content = api_call('login', login_data, base_url=WEBSHARE_API_BASE_URL)
    if not login_response_content:
        return None

    try:
        login_xml = ET.fromstring(login_response_content)
    except ET.ParseError as e:
        xbmc.log(f"Kodíček: Failed to parse login XML: {e}. Response: {login_response_content}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "Login error: Invalid server response.", xbmcgui.NOTIFICATION_ERROR)
        return None

    if not is_xml_ok(login_xml):
        message = "Login failed. Check credentials or API status."
        msg_node = login_xml.find('message')
        if msg_node is not None and msg_node.text:
            message = msg_node.text
        xbmcgui.Dialog().notification(plugin_name, message, xbmcgui.NOTIFICATION_ERROR)
        return None
        
    token_node = login_xml.find('token')
    if token_node is not None and token_node.text:
        xbmc.log("Kodíček: Login successful.", level=xbmc.LOGINFO)
        return token_node.text
    else:
        xbmc.log("Kodíček: Token not found in login response.", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "Login error: Token missing.", xbmcgui.NOTIFICATION_ERROR)
        return None

def search_webshare(token, query):
    search_params = {
        'wst': token,
        'what': query,
        'category': 'video', # Default to video, can be made a setting
        'limit': 30, # As per original kodicek
        'sort': 'rating' # Example sort
    }
    # Webshare search is POST, ensure api_call handles it correctly
    search_response_content = api_call('search', search_params, method='post', base_url=WEBSHARE_API_BASE_URL)
    
    if not search_response_content:
        return []

    try:
        search_xml = ET.fromstring(search_response_content)
    except ET.ParseError as e:
        xbmc.log(f"Kodíček: Failed to parse search XML: {e}. Response: {search_response_content}", level=xbmc.LOGERROR)
        return []

    if not is_xml_ok(search_xml):
        return []

    files_list = []
    for file_elem in search_xml.iter('file'):
        file_data = {
            'ident': file_elem.findtext('ident'),
            'name': file_elem.findtext('name'),
            'size': int(file_elem.findtext('size', '0')),
            # Add other relevant fields if needed, e.g., 'thumb', 'duration'
        }
        if file_data['ident'] and file_data['name']:
            files_list.append(file_data)
    
    return files_list

def get_stream_link(token, ident):
    # Zkusíme s různými variantami požadavku
    possible_params = [
        {'wst': token, 'ident': ident, 'download_type': 'video_stream'},
        {'wst': token, 'ident': ident, 'download_type': 'file_download'},
        {'wst': token, 'ident': ident}
    ]
    for link_params in possible_params:
        xbmc.log(f"Kodíček: get_stream_link - Requesting link with params: {link_params}", level=xbmc.LOGINFO)
        link_response_content = api_call('file_link', link_params, method='post', base_url=WEBSHARE_API_BASE_URL)
        if not link_response_content:
            xbmc.log(f"Kodíček: get_stream_link - No response content from api_call for ident: {ident}", level=xbmc.LOGERROR)
            continue
        try:
            response_text_for_log = link_response_content.decode('utf-8', errors='replace')
        except Exception:
            response_text_for_log = str(link_response_content)
        xbmc.log(f"Kodíček: get_stream_link - file_link XML response for ident {ident}: {response_text_for_log}", level=xbmc.LOGINFO)
        try:
            link_xml = ET.fromstring(link_response_content)
        except ET.ParseError as e:
            xbmc.log(f"Kodíček: Failed to parse link XML: {e}. Raw response was logged above.", level=xbmc.LOGERROR)
            continue
        # Zkontroluj OK stav
        status_node = link_xml.find('status')
        if status_node is None or status_node.text != 'OK':
            xbmc.log(f"Kodíček: get_stream_link - XML status not OK ({status_node.text if status_node is not None else 'none'}). Raw response was logged above.", level=xbmc.LOGERROR)
            continue
        link_node = link_xml.find('link')
        if link_node is not None and link_node.text:
            xbmc.log(f"Kodíček: get_stream_link - Successfully found link for ident {ident}: {link_node.text}", level=xbmc.LOGINFO)
            return link_node.text
    # Pokud žádný link není, vypiš vše do notifikace
    xbmcgui.Dialog().notification(
        plugin_name, 
        f"Nepodařilo se získat stream link! Zkontroluj log Kodi (kodíček plugin).", 
        xbmcgui.NOTIFICATION_ERROR, 7000
    )
    return None

def get_mimetype(filename):
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'mp4':
            return 'video/mp4'
        elif ext == 'mkv':
            return 'video/x-matroska'
        elif ext == 'avi':
            return 'video/x-msvideo'
        elif ext == 'ts':
            return 'video/mp2t'
        # Add more common video extensions if needed
    return 'application/octet-stream' # Default

# --- Helper Functions ---
def normalize_text(text):
    """
    Normalizes text for comparison:
    - Converts to lowercase.
    - Replaces common separators (space, underscore, dot) with a single dot.
    - Removes basic diacritics (can be expanded with unidecode or similar if available).
    """
    if not text:
        return ""
    text = text.lower()
    # Basic diacritics removal for Czech/Slovak - can be improved
    replacements = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i', 'ň': 'n',
        'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y',
        'ž': 'z', 'ľ': 'l', 'ĺ': 'l', 'ŕ': 'r', 'ä': 'a', 'ô': 'o'
    }
    for char_from, char_to in replacements.items():
        text = text.replace(char_from, char_to)
    
    # Replace common separators with a dot
    text = text.replace(' ', '.').replace('_', '.').replace('-', '.')
    # Remove other non-alphanumeric characters (except dots for separation)
    import re
    text = re.sub(r'[^\w.]', '', text) # Keep word characters and dots
    text = re.sub(r'\.+', '.', text) # Replace multiple dots with a single dot
    return text.strip('.')


# --- TMDb Functions ---
def search_tmdb(api_key, query, year=None, media_type='movie', language='cs-CZ'):
    """
    Searches TMDb for movies or TV shows.
    media_type can be 'movie' or 'tv'.
    Returns a list of results or None on error.
    """
    if not api_key:
        xbmc.log("Kodíček: TMDb API key is missing for search_tmdb.", level=xbmc.LOGERROR)
        return None

    endpoint = f"search/{media_type}"
    params = {
        'api_key': api_key,
        'query': query,
        'language': language
    }
    if year:
        if media_type == 'movie':
            params['year'] = year
        elif media_type == 'tv':
            params['first_air_date_year'] = year
    
    xbmc.log(f"Kodíček: Searching TMDb ({media_type}): Query='{query}', Year='{year}', Lang='{language}'", level=xbmc.LOGINFO)
    
    try:
        # Using _session for consistency, though api_call could be adapted
        response = _session.get(TMDB_API_BASE_URL + endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data and 'results' in data:
            xbmc.log(f"Kodíček: TMDb search found {len(data['results'])} results.", level=xbmc.LOGINFO)
            return data['results']
        else:
            xbmc.log(f"Kodíček: TMDb search returned no results or unexpected format for query: {query}", level=xbmc.LOGINFO)
            return []
            
    except requests.exceptions.RequestException as e:
        xbmc.log(f"Kodíček: TMDb API call to {endpoint} failed: {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, f"TMDb Error: {e}", xbmcgui.NOTIFICATION_ERROR)
        return None
    except json.JSONDecodeError as e:
        xbmc.log(f"Kodíček: Failed to parse TMDb JSON response: {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "TMDb Error: Invalid response.", xbmcgui.NOTIFICATION_ERROR)
        return None

def get_tmdb_details(api_key, tmdb_id, media_type='movie', language='cs-CZ'):
    """
    Fetches details for a specific movie or TV show from TMDb.
    media_type can be 'movie' or 'tv'.
    Returns a dictionary of details or None on error.
    """
    if not api_key:
        xbmc.log("Kodíček: TMDb API key is missing for get_tmdb_details.", level=xbmc.LOGERROR)
        return None
    if not tmdb_id:
        xbmc.log("Kodíček: TMDb ID is missing for get_tmdb_details.", level=xbmc.LOGERROR)
        return None

    endpoint = f"{media_type}/{tmdb_id}"
    params = {
        'api_key': api_key,
        'language': language,
        'append_to_response': 'credits,images,videos' # Example: get more data
    }
    
    xbmc.log(f"Kodíček: Fetching TMDb details ({media_type}) for ID: {tmdb_id}, Lang='{language}'", level=xbmc.LOGINFO)

    try:
        response = _session.get(TMDB_API_BASE_URL + endpoint, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        xbmc.log(f"Kodíček: TMDb details fetched successfully for ID: {tmdb_id}", level=xbmc.LOGINFO)
        return data
            
    except requests.exceptions.RequestException as e:
        xbmc.log(f"Kodíček: TMDb API call to {endpoint} (details) failed: {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, f"TMDb Error: {e}", xbmcgui.NOTIFICATION_ERROR)
        return None
    except json.JSONDecodeError as e:
        xbmc.log(f"Kodíček: Failed to parse TMDb JSON details response: {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "TMDb Error: Invalid details response.", xbmcgui.NOTIFICATION_ERROR)
        return None

# --- End TMDb Functions ---

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get("action")

    username, password = get_credentials()
    if not username or not password: # Credentials dialog shown by get_credentials
        if action: # Only end directory if it was an action, not initial load
             xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return

    token = addon.getSetting('token')
    if not token: # Try to login if no token stored
        xbmc.log("Kodíček: No token found, attempting login.", level=xbmc.LOGINFO)
        token = login_webshare(username, password)
        if token:
            addon.setSetting('token', token)
        else:
            xbmc.log("Kodíček: Login failed, cannot proceed.", level=xbmc.LOGERROR)
            if action: xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
    else: # Validate existing token (optional, but good practice)
        # For simplicity, this example doesn't re-validate on every action.
        # The example plugin has a revalidate() function that checks user_data.
        pass

    if action == "search": # Changed from elif to if, and new logic below
        xbmc.log(f"Kodíček: Action 'search' entered. Params: {params}", level=xbmc.LOGINFO)
        
        what_to_search = params.get("what") 
        ask_for_input = params.get("ask") == "1"

        if ask_for_input:
            xbmc.log(f"Kodíček: 'search' action with ask=1. Opening input dialog.", level=xbmc.LOGINFO)
            search_term_from_dialog = xbmcgui.Dialog().input(f"{plugin_name} – Vyhledat film/seriál", type=xbmcgui.INPUT_ALPHANUM)
            if search_term_from_dialog:
                what_to_search = search_term_from_dialog
                xbmc.log(f"Kodíček: User entered query: {what_to_search}", level=xbmc.LOGINFO)
                # Add to search history
                search_history_item = {
                    "query": what_to_search,
                    "timestamp": int(time.time())
                }
                add_to_search_history(search_history_item)
                xbmc.log(f"Kodíček: Added to SEARCH history: {search_history_item}", level=xbmc.LOGINFO)
            else:
                xbmc.log(f"Kodíček: User cancelled search input dialog.", level=xbmc.LOGINFO)
                what_to_search = None # Ensure it's None to show history menu

        if what_to_search:
            xbmc.log(f"Kodíček: Performing Webshare search for: {what_to_search}", level=xbmc.LOGINFO) # Clarified log

            # --- TMDb Integration Start ---
            tmdb_api_key = get_tmdb_api_key()
            tmdb_results_to_display = []

            if tmdb_api_key:
                parsed_query_for_tmdb = what_to_search
                parsed_year_for_tmdb = None
                # Try to parse year if query ends with 4 digits (e.g., "Movie Title 2023")
                if len(what_to_search) > 5 and what_to_search[-4:].isdigit() and what_to_search[-5] == ' ':
                    parsed_query_for_tmdb = what_to_search[:-5].strip()
                    parsed_year_for_tmdb = what_to_search[-4:]
                    xbmc.log(f"Kodíček: Parsed for TMDb - Query: '{parsed_query_for_tmdb}', Year: '{parsed_year_for_tmdb}'", level=xbmc.LOGINFO)

                # Search for movies on TMDb
                tmdb_movie_results = search_tmdb(tmdb_api_key, parsed_query_for_tmdb, year=parsed_year_for_tmdb, media_type='movie')
                if tmdb_movie_results:
                    xbmc.log(f"Kodíček: Found {len(tmdb_movie_results)} movie results from TMDb.", level=xbmc.LOGINFO)
                    tmdb_results_to_display.extend(tmdb_movie_results)
                
                # Optionally, search for TV shows if no movies or based on user preference (future enhancement)
                # For now, focusing on movies. If you want to add TV, uncomment and adapt:
                # if not tmdb_movie_results: # Example: search TV if no movies found
                #    tmdb_tv_results = search_tmdb(tmdb_api_key, parsed_query_for_tmdb, year=parsed_year_for_tmdb, media_type='tv')
                #    if tmdb_tv_results:
                #        xbmc.log(f"Kodíček: Found {len(tmdb_tv_results)} TV results from TMDb.", level=xbmc.LOGINFO)
                #        tmdb_results_to_display.extend(tmdb_tv_results) # Need to handle media_type difference

            if tmdb_results_to_display:
                xbmcplugin.setPluginCategory(addon_handle, f"TMDb Výsledky pro: {what_to_search}")
                xbmcplugin.setContent(addon_handle, 'movies') # or 'tvshows' or 'videos'

                for item in tmdb_results_to_display:
                    media_type = 'movie' # Assuming movie for now, adjust if TV shows are mixed
                    tmdb_id = item.get('id')
                    title = item.get('title') if media_type == 'movie' else item.get('name')
                    overview = item.get('overview', '')
                    poster_path = item.get('poster_path')
                    release_date = item.get('release_date') if media_type == 'movie' else item.get('first_air_date')
                    year = release_date[:4] if release_date and len(release_date) >= 4 else ""

                    display_title = f"{title} ({year})" if year else title
                    li = xbmcgui.ListItem(label=display_title)
                    
                    info_labels = {'title': title, 'plot': overview}
                    if year:
                        info_labels['year'] = int(year)
                    
                    art_data = {}
                    if poster_path:
                        art_data['thumb'] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                        art_data['poster'] = f"https://image.tmdb.org/t/p/w500{poster_path}"
                        # art_data['fanart'] = f"https://image.tmdb.org/t/p/original{item.get('backdrop_path')}" # If backdrop is needed
                    
                    li.setArt(art_data)
                    li.setInfo('video', info_labels)
                    li.setProperty('IsPlayable', 'false') # It's a folder leading to selection/Webshare

                    url = f"{BASE_URL_PLUGIN}?action=process_tmdb_selection&tmdb_id={tmdb_id}&media_type={media_type}&title={urllib.parse.quote(title)}&year={year}"
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
                
                xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
                return # Stop here, TMDb results are shown
            
            else: # No TMDb results, proceed to Webshare search with original query
                xbmc.log("Kodíček: No results from TMDb, proceeding with Webshare search.", level=xbmc.LOGINFO)
            # --- TMDb Integration End ---

            # Proceed with Webshare search (original logic if no TMDb results or API key issue)
            files = search_webshare(token, what_to_search) 
            if not files:
                xbmcgui.Dialog().notification(plugin_name, "Nic nebylo nalezeno na Webshare.", xbmcgui.NOTIFICATION_INFO)
                # Display search history/options menu even if no results, allowing new search
                xbmcplugin.setPluginCategory(addon_handle, f"Vyhledávání (nic pro '{what_to_search}')")
                li_new_search = xbmcgui.ListItem(label="Nové vyhledávání...")
                li_new_search.setArt({'icon': 'DefaultAddonsSearch.png'})
                url_new_search = f"{BASE_URL_PLUGIN}?action=search&ask=1"
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_new_search, listitem=li_new_search, isFolder=True)
                xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

            else:
                xbmcplugin.setPluginCategory(addon_handle, f"Výsledky pro: {what_to_search}")
                xbmcplugin.setContent(addon_handle, 'videos')
                for file_item in files:
                    li = xbmcgui.ListItem(label=file_item["name"])
                    size_bytes = file_item.get("size", 0)
                    if size_bytes > 1024*1024*1024: # GB
                        size_str = f"{size_bytes/(1024*1024*1024):.2f} GB"
                    elif size_bytes > 1024*1024: # MB
                        size_str = f"{size_bytes/(1024*1024):.2f} MB"
                    elif size_bytes > 1024: # KB
                        size_str = f"{size_bytes/1024:.0f} KB"
                    else:
                        size_str = f"{size_bytes} B"
                    
                    li.setInfo("video", {"title": file_item["name"], "size": size_bytes, "plot": f"Velikost: {size_str}"})
                    li.setProperty('IsPlayable', 'true')
                    url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'])}"
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
                xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
        else:
            # Display search history and "New Search" option
            xbmc.log(f"Kodíček: No search term. Displaying search history/options.", level=xbmc.LOGINFO)
            xbmcplugin.setPluginCategory(addon_handle, "Vyhledávání")

            li_new_search = xbmcgui.ListItem(label="Nové vyhledávání...")
            li_new_search.setArt({'icon': 'DefaultAddonsSearch.png'})
            url_new_search = f"{BASE_URL_PLUGIN}?action=search&ask=1"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_new_search, listitem=li_new_search, isFolder=True)

            search_history_items = load_search_history() # Use new function
            past_searches_displayed = False
            if search_history_items:
                for item in search_history_items: # Already newest first due to insert(0)
                    query_text = item.get("query")
                    if query_text:
                        display_label = f"Hledáno: {query_text}"
                        try:
                            timestamp_str = time.strftime('%d.%m.%y %H:%M', time.localtime(item['timestamp'])) # Shorter year
                            display_label_with_time = f"{display_label} ({timestamp_str})"
                        except:
                            display_label_with_time = display_label

                        li = xbmcgui.ListItem(label=display_label_with_time)
                        url_past_search = f"{BASE_URL_PLUGIN}?action=search&what={urllib.parse.quote(query_text)}"
                        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_past_search, listitem=li, isFolder=True)
                        past_searches_displayed = True
            
            if not past_searches_displayed:
                # Optional: xbmcgui.Dialog().notification(plugin_name, "Historie vyhledávání je prázdná.", xbmcgui.NOTIFICATION_INFO, displaytime=2000)
                pass

            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

    elif action == "play":
        xbmc.log(f"Kodíček: [PLAY] Action entered. Params: {params}", level=xbmc.LOGINFO)
        ident = params.get("ident")
        file_name_for_playback = params.get("name", "Přehrávaný soubor")

        if not ident:
            xbmc.log("Kodíček: [PLAY] No ident found in params.", level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(plugin_name, "Chybí ident souboru.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
            return

        xbmc.log(f"Kodíček: [PLAY] Attempting playback for ident: {ident} ({file_name_for_playback})", level=xbmc.LOGINFO)

        # Pro jistotu znovu získáme token
        username, password = get_credentials()
        if not username or not password:
            xbmc.log("Kodíček: [PLAY] Credentials missing. Can't play.", level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(plugin_name, "Chybí přihlašovací údaje.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
            return

        token = addon.getSetting('token')
        if not token:
            xbmc.log("Kodíček: [PLAY] No token found, trying to login.", level=xbmc.LOGINFO)
            token = login_webshare(username, password)
            if token:
                addon.setSetting('token', token)
            else:
                xbmc.log("Kodíček: [PLAY] Login failed during playback.", level=xbmc.LOGERROR)
                xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se přihlásit k Webshare.", xbmcgui.NOTIFICATION_ERROR)
                xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
                return

        # Pokusíme se získat stream link
        stream_url = get_stream_link(token, ident)
        if not stream_url:
            xbmc.log(f"Kodíček: [PLAY] get_stream_link failed for ident: {ident}", level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se získat odkaz ke stažení/přehrání.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
            return

        # Prepare headers for Kodi
        headers_dict = {
            'User-Agent': _session.headers.get('User-Agent', 'Mozilla/5.0'), # Use session's UA or a default
            'Cookie': f'wst={token}'
        }
        headers_str = urllib.parse.urlencode(headers_dict)
        
        path_with_headers = f"{stream_url}|{headers_str}"
        xbmc.log(f"Kodíček: [PLAY] Original Stream URL: {stream_url}", level=xbmc.LOGINFO)
        xbmc.log(f"Kodíček: [PLAY] Path with headers for Kodi: {path_with_headers}", level=xbmc.LOGINFO)

        li = xbmcgui.ListItem(path=path_with_headers)
        li.setInfo("video", {"title": file_name_for_playback})
        li.setProperty('IsPlayable', 'true')
        
        mimetype = get_mimetype(file_name_for_playback) 
        li.setMimeType(mimetype)
        xbmc.log(f"Kodíček: [PLAY] Set MimeType to: {mimetype} for filename: {file_name_for_playback}", level=xbmc.LOGINFO)
        
        # Pokud máš artwork nebo thumb, můžeš zde nastavit
        # li.setArt({'thumb': 'URL_na_náhled', 'icon': 'URL_na_ikonu'})

        # Add to history
        history_item = {
            "ident": ident,
            "name": file_name_for_playback,
            "timestamp": int(time.time()),
            "type": "video",
        }
        xbmc.log(f"Kodíček: Calling add_to_history for played item: {file_name_for_playback}", level=xbmc.LOGINFO)
        add_to_history(history_item)
        xbmc.log(f"Kodíček: [PLAY] Added to history: {history_item}", level=xbmc.LOGINFO)

        xbmcplugin.setResolvedUrl(addon_handle, True, li)
        xbmc.log(f"Kodíček: [PLAY] setResolvedUrl called. Should now play.", level=xbmc.LOGINFO)

    elif action == "history":
        xbmc.log(f"Kodíček: Action 'history' entered.", level=xbmc.LOGINFO)
        xbmc.log(f"Kodíček: Calling load_history for history view.", level=xbmc.LOGINFO)
        history_items = load_history() # This correctly loads playback history
        if not history_items:
            xbmc.log(f"Kodíček: Playback history is empty.", level=xbmc.LOGINFO)
            xbmcgui.Dialog().notification(plugin_name, "Historie přehrávání je prázdná.", xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
            return

        xbmcplugin.setPluginCategory(addon_handle, "Historie přehrávání") # Clarify title
        xbmcplugin.setContent(addon_handle, 'videos')
        for item in history_items: # These are playback items
            # Ensure item is a playback item, not an old search query if history file was mixed
            if not item.get("ident") or not item.get("name") or item.get("type") != "video":
                xbmc.log(f"Kodíček: Skipping non-playback item in history: {item}", level=xbmc.LOGINFO)
                continue

            li = xbmcgui.ListItem(label=item["name"])
            try:
                timestamp_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(item['timestamp']))
            except Exception: 
                timestamp_str = "Neznámé datum"
            
            plot_info = f"Naposledy přehráno: {timestamp_str}"
            # item.get("type") should always be "video" here now
            # plot_info += f"\nTyp: {item.get('type', 'video')}" 

            li.setInfo("video", {"title": item["name"], "plot": plot_info})
            li.setProperty('IsPlayable', 'true')
            url = f"{BASE_URL_PLUGIN}?action=play&ident={item['ident']}&name={urllib.parse.quote(item['name'])}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle)

    elif action == "show_combined_history":
        display_combined_history()
    
    elif action == "process_tmdb_selection":
        process_tmdb_selection(params, token)

    elif action == 'movies':
        movies(params)
    elif action == 'series':
        series(params)

    else: # No action or unknown action - show main menu
        display_main_menu()

def process_tmdb_selection(params, token):
    tmdb_id = params.get('tmdb_id')
    media_type = params.get('media_type', 'movie')
    title = params.get('title', '') # Already URL decoded by parse_qsl
    year = params.get('year', '')

    xbmc.log(f"Kodíček: Processing TMDb selection: ID={tmdb_id}, Type={media_type}, Title='{title}', Year='{year}'", level=xbmc.LOGINFO)

    tmdb_api_key = get_tmdb_api_key()
    detailed_tmdb_item = None
    if tmdb_api_key and tmdb_id:
        detailed_tmdb_item = get_tmdb_details(tmdb_api_key, tmdb_id, media_type)
        if detailed_tmdb_item:
            xbmc.log(f"Kodíček: Fetched details for TMDb ID {tmdb_id}: {detailed_tmdb_item.get('title') or detailed_tmdb_item.get('name')}", level=xbmc.LOGINFO)
            # Update title and year from detailed info if available and more precise
            title = detailed_tmdb_item.get('title') if media_type == 'movie' else detailed_tmdb_item.get('name', title)
            release_date = detailed_tmdb_item.get('release_date') if media_type == 'movie' else detailed_tmdb_item.get('first_air_date')
            if release_date and len(release_date) >= 4:
                year = release_date[:4]
        else:
            xbmc.log(f"Kodíček: Could not fetch details for TMDb ID {tmdb_id}. Using passed title/year.", level=xbmc.LOGWARNING)

    # Prepare TMDb data for matching
    normalized_tmdb_title = normalize_text(title)
    tmdb_year_str = str(year) if year else ""
    xbmc.log(f"Kodíček: Normalized TMDb title for matching: '{normalized_tmdb_title}', Year: '{tmdb_year_str}'", level=xbmc.LOGINFO)

    # Search Webshare using a broader query initially (e.g., just title, or title + year)
    # The scoring will then refine this.
    webshare_search_query = title
    if tmdb_year_str:
         webshare_search_query = f"{title} {tmdb_year_str}" # Use original title for WS search, normalization for scoring

    xbmc.log(f"Kodíček: Searching Webshare with query: '{webshare_search_query}'", level=xbmc.LOGINFO)
    webshare_files = search_webshare(token, webshare_search_query)

    if not webshare_files:
        xbmcgui.Dialog().notification(plugin_name, f"Pro '{title}' nebyly na Webshare nalezeny žádné soubory.", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
        return

    scored_files = []
    MIN_SCORE_THRESHOLD = 3.0 # Define a minimum score threshold

    for ws_file in webshare_files:
        fname_normalized = normalize_text(ws_file.get('name', ''))
        score = 0.0 # Use float for scores

        # --- Stricter Matching Logic ---

        # 1. Hard exclusion if normalized TMDb title is not part of the filename
        #    Also, ensure the core part of the title is present.
        #    Example: if tmdb is "spiderman", filename must contain "spiderman"
        #    This is a basic substring check. More advanced fuzzy matching could be used if available.
        core_tmdb_title_parts = normalized_tmdb_title.split('.')
        # Require at least one significant part of the title to be present if title has multiple words
        # or the whole title if it's a single word.
        # This is a simple heuristic; can be refined.
        # For "spider.man", it checks if "spider" or "man" is in fname_normalized.
        # For "spiderman", it checks if "spiderman" is in fname_normalized.
        
        # More direct: Check if the full normalized_tmdb_title is in fname_normalized
        if normalized_tmdb_title not in fname_normalized:
            # If the exact normalized title isn't there, try a more lenient check for parts.
            # This is to catch cases like "Spider-Man" (normalized "spider.man") vs "Spider Man Uncased"
            # However, the primary goal is stricter filtering, so we might make this penalty high.
            # For now, let's implement the direct exclusion as suggested.
            score = -100 # Heavily penalize or mark for exclusion
            xbmc.log(f"Kodíček: File '{fname_normalized}' rejected: TMDb title '{normalized_tmdb_title}' not found.", level=xbmc.LOGDEBUG)
        else:
            # If the exact normalized title is found, give a significant bonus
            score += 3.0 # Increased base score for title match

        # 2. Year Matching (if score is still potentially positive)
        if score > -10: # Proceed only if not hard-excluded
            if tmdb_year_str: # If TMDb has a year
                if tmdb_year_str in fname_normalized:
                    score += 2.0  # Strong bonus for year match
                else:
                    # Penalize if year is expected but not found.
                    # This helps differentiate "Movie Title" from "Movie Title The Series" if year is specific.
                    score -= 1.0
            # If TMDb has no year, we don't penalize for year in filename, but don't reward either.

        # --- Language Scoring (remains similar, adjust weights if needed) ---
        if score > -10:
            lang_bonus = 0.0
            if any(lang_tag in fname_normalized for lang_tag in ['.cz', '.cze', '.cesky', '.dabing.cz', '.cz.dab']):
                lang_bonus = 2.0
            elif any(lang_tag in fname_normalized for lang_tag in ['.sk', '.svk', '.slovensky', '.dabing.sk', '.sk.dab']):
                lang_bonus = 1.5 # SK slightly lower or same as CZ based on preference
            elif any(lang_tag in fname_normalized for lang_tag in ['.en', '.eng', '.english']):
                lang_bonus = 0.5
            score += lang_bonus

        # --- Quality Scoring (remains similar, adjust weights if needed) ---
        if score > -10:
            quality_bonus = 0.0
            if '2160p' in fname_normalized or '4k' in fname_normalized: quality_bonus = 2.0
            elif '1080p' in fname_normalized or '1080i' in fname_normalized: quality_bonus = 1.5
            elif '720p' in fname_normalized or '720i' in fname_normalized: quality_bonus = 1.0
            elif 'bluray' in fname_normalized: quality_bonus = 1.2
            elif 'webrip' in fname_normalized or 'web-dl' in fname_normalized or 'web' in fname_normalized : quality_bonus = 0.8
            elif 'dvdrip' in fname_normalized or 'dvd' in fname_normalized : quality_bonus = 0.5
            # Penalize CAM/TS/TC heavily if detected
            if any(bad_quality in fname_normalized for bad_quality in ['.cam.', '.ts.', '.tc.', '.camrip.', '.telesync.']):
                quality_bonus -= 3.0
            score += quality_bonus
        
        # --- File Type Check (ensure it's a video file) ---
        original_filename = ws_file.get('name', '').lower()
        is_video_file = any(original_filename.endswith(ext) for ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.ts', '.mpg', '.mpeg', '.iso'])
        if not is_video_file:
            score = -200 # Definitely exclude non-video files

        # --- Final Check against Threshold ---
        if score >= MIN_SCORE_THRESHOLD:
            scored_files.append({'file': ws_file, 'score': score, 'normalized_name': fname_normalized})
            xbmc.log(f"Kodíček: Scored file: '{ws_file['name']}' (Normalized: '{fname_normalized}') -> Score: {score:.2f}", level=xbmc.LOGDEBUG)
        else:
            xbmc.log(f"Kodíček: File '{ws_file['name']}' (Normalized: '{fname_normalized}') did NOT meet threshold. Score: {score:.2f}", level=xbmc.LOGDEBUG)


    # Sort files by score in descending order
    scored_files.sort(key=lambda x: x['score'], reverse=True)

    if not scored_files:
        xbmcgui.Dialog().notification(plugin_name, f"Pro '{title} ({year})': žádné dostatečně relevantní soubory na Webshare.", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
        return

    xbmcplugin.setPluginCategory(addon_handle, f"Webshare zdroje pro: {title} ({year}) - Seřazeno")
    xbmcplugin.setContent(addon_handle, 'videos')

    for scored_item in scored_files:
        file_item = scored_item['file']
        display_label = f"[S: {scored_item['score']:.1f}] {file_item['name']}"
        li = xbmcgui.ListItem(label=display_label)
        
        size_bytes = file_item.get("size", 0)
        if size_bytes > 1024*1024*1024: size_str = f"{size_bytes/(1024*1024*1024):.2f} GB"
        elif size_bytes > 1024*1024: size_str = f"{size_bytes/(1024*1024):.2f} MB"
        elif size_bytes > 1024: size_str = f"{size_bytes/1024:.0f} KB"
        else: size_str = f"{size_bytes} B"
        
        plot_info = f"Velikost: {size_str}\nNormalizovaný název: {scored_item['normalized_name']}"
        
        # Use TMDb info for art and richer plot if available
        art_data = {}
        if detailed_tmdb_item:
            info_labels = {
                'title': detailed_tmdb_item.get('title', file_item['name']), # Prefer TMDb title
                'originaltitle': detailed_tmdb_item.get('original_title', file_item['name']),
                'plot': detailed_tmdb_item.get('overview', plot_info),
                'plotoutline': detailed_tmdb_item.get('overview', plot_info),
                'tagline': detailed_tmdb_item.get('tagline'),
                'rating': detailed_tmdb_item.get('vote_average'),
                'votes': detailed_tmdb_item.get('vote_count'),
                'premiered': detailed_tmdb_item.get('release_date'),
                'year': int(year) if year and year.isdigit() else None,
                'genre': ", ".join([g['name'] for g in detailed_tmdb_item.get('genres', [])]),
                'mediatype': 'video', # or 'movie' / 'tvshow'
                'size': size_bytes
            }
            poster = detailed_tmdb_item.get('poster_path')
            fanart = detailed_tmdb_item.get('backdrop_path')
            if poster: art_data['thumb'] = art_data['poster'] = f"https://image.tmdb.org/t/p/w500{poster}"
            if fanart: art_data['fanart'] = f"https://image.tmdb.org/t/p/original{fanart}"
            li.setArt(art_data)
            li.setInfo('video', info_labels)
        else:
            li.setInfo("video", {"title": file_item["name"], "size": size_bytes, "plot": plot_info})

        li.setProperty('IsPlayable', 'true')
        url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'])}"
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        
    xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

def movies(params):
    xbmcgui.Dialog().notification(plugin_name, "Zde bude seznam filmů.", xbmcgui.NOTIFICATION_INFO, 2500)
    xbmcplugin.endOfDirectory(addon_handle)

def series(params):
    xbmcgui.Dialog().notification(plugin_name, "Zde bude seznam seriálů.", xbmcgui.NOTIFICATION_INFO, 2500)
    xbmcplugin.endOfDirectory(addon_handle)

def display_combined_history():
    xbmcplugin.setPluginCategory(addon_handle, "Historie")

    # Folder for Search History
    li_search_history_folder = xbmcgui.ListItem(label="Historie vyhledávání")
    li_search_history_folder.setArt({'icon': 'DefaultAddonsSearch.png', 'thumb': 'DefaultAddonsSearch.png'})
    url_search_history_folder = f"{BASE_URL_PLUGIN}?action=search" # Shows search history list
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_search_history_folder, listitem=li_search_history_folder, isFolder=True)

    # Playback History Items
    history_items = load_history() # This correctly loads playback history
    if not history_items:
        xbmc.log(f"Kodíček: Playback history is empty (within combined view).", level=xbmc.LOGINFO)
        # Optional: xbmcgui.Dialog().notification(plugin_name, "Historie přehrávání je prázdná.", xbmcgui.NOTIFICATION_INFO, 2000)
        pass # Continue to end directory even if empty, search history folder is still there

    # xbmcplugin.setContent(addon_handle, 'videos') # Set content type for playback items
    # It might be better to set content type only if there are videos, or rely on individual item types.
    # For a mixed list (folder + items), sometimes it's left unset at category level.

    for item in history_items:
        if not item.get("ident") or not item.get("name") or item.get("type") != "video":
            xbmc.log(f"Kodíček: Skipping non-playback item in combined_history: {item}", level=xbmc.LOGINFO)
            continue

        li = xbmcgui.ListItem(label=item["name"])
        try:
            timestamp_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(item['timestamp']))
        except Exception:
            timestamp_str = "Neznámé datum"
        
        plot_info = f"Naposledy přehráno: {timestamp_str}"
        li.setInfo("video", {"title": item["name"], "plot": plot_info})
        li.setProperty('IsPlayable', 'true')
        # Ensure name is URL-encoded for the parameters
        url = f"{BASE_URL_PLUGIN}?action=play&ident={item['ident']}&name={urllib.parse.quote(item['name'])}"
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
    
    xbmcplugin.endOfDirectory(addon_handle)


def display_main_menu():
    # Item for initiating a new search (opens keyboard)
    li_new_search_main_menu = xbmcgui.ListItem(label="Vyhledat film/seriál")
    li_new_search_main_menu.setArt({'icon': 'DefaultAddonsSearch.png', 'thumb': 'DefaultAddonsSearch.png'})
    url_new_search_main_menu = f"{BASE_URL_PLUGIN}?action=search&ask=1" # This will trigger the keyboard
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_new_search_main_menu, listitem=li_new_search_main_menu, isFolder=True)

    # Filmy (nová položka)
    listitem_movies = xbmcgui.ListItem(label="Filmy")
    listitem_movies.setArt({'icon': 'DefaultMovies.png'}) # Changed icon
    url_movies = f"{BASE_URL_PLUGIN}?action=movies"
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_movies, listitem=listitem_movies, isFolder=True)

    # Seriály (nová položka)
    listitem_series = xbmcgui.ListItem(label="Seriály")
    listitem_series.setArt({'icon': 'DefaultTVShows.png'})
    url_series = f"{BASE_URL_PLUGIN}?action=series"
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_series, listitem=listitem_series, isFolder=True)

    # Main "Historie" folder
    li_history_folder = xbmcgui.ListItem(label="Historie")
    li_history_folder.setArt({'icon': 'DefaultFolder.png', 'thumb': 'DefaultFolder.png'})
    url_history_folder = f"{BASE_URL_PLUGIN}?action=show_combined_history" # Changed action
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_history_folder, listitem=li_history_folder, isFolder=True)

    xbmcplugin.endOfDirectory(addon_handle)


if __name__ == "__main__":
    # Clear stored token on startup for fresh login, or implement revalidation
    # addon.setSetting('token', '') # Uncomment to force login every time Kodi starts or addon is run
    
    # Check if settings are filled on first run of a route
    args = sys.argv[2]
    if args.startswith('?'):
        args = args[1:]

    # If it's an initial call (no specific action), and credentials are not set,
    # get_credentials() will open settings. We should not proceed to router if that's the case.
    # However, router needs to be called for the initial screen.
    # This logic is a bit tricky with Kodi's plugin flow.
    
    # A simple check: if no username/password, and it's the initial call, menu() might not have items.
    # The get_credentials() call at the start of router handles opening settings.
    
    router(args)
