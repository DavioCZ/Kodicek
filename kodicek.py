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
import re # For strip_year
from xml.etree import ElementTree as ET
from history import add_to_history, load_history, add_to_search_history, load_search_history # Updated imports
from resources.lib.tmdb import search_tmdb as new_search_tmdb # New TMDB search

addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
BASE_URL_PLUGIN = sys.argv[0] 
plugin_name = "Kodíček"
REALM = ':Webshare:'
WEBSHARE_API_BASE_URL = "https://webshare.cz/api/"
TMDB_API_BASE_URL = "https://api.themoviedb.org/3/"
UI_LANG = "cs-CZ" # Default language for UI elements and TMDB season/episode info

_session = requests.Session()
_session.headers.update({'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"})

HOSTERS = [
    ...
]

YEAR_RE = re.compile(r"\b(19|20)\d{2}\b")

def strip_year(title: str) -> str:
    if not title:
        return ""
    cleaned = YEAR_RE.sub("", title)
    return " ".join(cleaned.split())

def get_credentials():
    username = addon.getSetting("ws_username")
    password = addon.getSetting("ws_password")
    if not username or not password:
        xbmcgui.Dialog().notification(plugin_name, addon.getLocalizedString(30101), xbmcgui.NOTIFICATION_ERROR)
        addon.openSettings()
        return None, None
    return username, password

def get_tmdb_api_key():
    tmdb_key = addon.getSetting("tmdb_api_key")
    if not tmdb_key:
        xbmcgui.Dialog().notification(plugin_name, "Chybí TMDb API klíč v nastavení!", xbmcgui.NOTIFICATION_ERROR)
        return None
    return tmdb_key

def api_call(endpoint, data=None, method='post', base_url=WEBSHARE_API_BASE_URL):
    url = base_url + endpoint
    if base_url == WEBSHARE_API_BASE_URL and not endpoint.endswith('/'):
        url += "/"
        
    try:
        if method == 'post':
            response = _session.post(url, data=data, timeout=10)
        else: # get
            response = _session.get(url, params=data, timeout=10)
        response.raise_for_status()
        return response.content
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
    return False

def login_webshare(username, password):
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
    # salt = salt_node.text # Salt is not used in the new double MD5 method

    try:
        password_bytes = password.encode('utf-8')
        username_bytes = username.encode('utf-8')
        realm_bytes = REALM.encode('utf-8')
        
        ws_password_hash_h1 = hashlib.md5(password_bytes).hexdigest()
        ws_password_hash_final = hashlib.md5(ws_password_hash_h1.encode('utf-8')).hexdigest()
        ws_password_hash_final_bytes = ws_password_hash_final.encode('utf-8')
        
        pass_digest = hashlib.md5(username_bytes + realm_bytes + ws_password_hash_final_bytes).hexdigest()
        
    except Exception as e:
        xbmc.log(f"Kodíček: Error during password encryption (hashlib): {e}", level=xbmc.LOGERROR)
        xbmcgui.Dialog().notification(plugin_name, "Login error: Encryption failed (hashlib).", xbmcgui.NOTIFICATION_ERROR)
        return None

    login_data = {
        'username_or_email': username,
        'password': ws_password_hash_final,
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
        'category': 'video',
        'limit': 100, # Increased limit as per suggestion
        'sort': 'rating'
    }
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
        }
        if file_data['ident'] and file_data['name']:
            files_list.append(file_data)
    return files_list

def get_stream_link(token, ident):
    possible_params = [
        {'wst': token, 'ident': ident, 'download_type': 'video_stream'},
        {'wst': token, 'ident': ident, 'download_type': 'file_download'},
        {'wst': token, 'ident': ident}
    ]
    for link_params in possible_params:
        link_response_content = api_call('file_link', link_params, method='post', base_url=WEBSHARE_API_BASE_URL)
        if not link_response_content: continue
        try:
            link_xml = ET.fromstring(link_response_content)
        except ET.ParseError: continue
        if not is_xml_ok(link_xml): continue
        link_node = link_xml.find('link')
        if link_node is not None and link_node.text:
            return link_node.text
    xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se získat stream link!", xbmcgui.NOTIFICATION_ERROR, 7000)
    return None

def get_mimetype(filename):
    if '.' in filename:
        ext = filename.rsplit('.', 1)[1].lower()
        if ext == 'mp4': return 'video/mp4'
        elif ext == 'mkv': return 'video/x-matroska'
        elif ext == 'avi': return 'video/x-msvideo'
        elif ext == 'ts': return 'video/mp2t'
    return 'application/octet-stream'

def normalize_text(text):
    if not text: return ""
    text = text.lower()
    replacements = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e', 'í': 'i', 'ň': 'n',
        'ó': 'o', 'ř': 'r', 'š': 's', 'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y',
        'ž': 'z', 'ľ': 'l', 'ĺ': 'l', 'ŕ': 'r', 'ä': 'a', 'ô': 'o'
    }
    for char_from, char_to in replacements.items():
        text = text.replace(char_from, char_to)
    text = text.replace(' ', '.').replace('_', '.').replace('-', '.')
    text = re.sub(r'[^\w.]', '', text) # Keep alphanumeric, underscore, and dot
    text = re.sub(r'\.+', '.', text)   # Replace multiple dots with a single dot
    return text.strip('.')

# --- TMDb Functions ---
def tmdb_api_request(api_key, endpoint, params=None, method='get'):
    if not api_key:
        xbmc.log("Kodíček: TMDb API key is missing for request.", level=xbmc.LOGERROR)
        return None
    url = f"{TMDB_API_BASE_URL}{endpoint.lstrip('/')}"
    all_params = {'api_key': api_key}
    if params:
        all_params.update(params)
    try:
        if method == 'get':
            response = _session.get(url, params=all_params, timeout=10)
        else:
            xbmc.log(f"Kodíček: Unsupported TMDb API method: {method}", level=xbmc.LOGERROR)
            return None
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        xbmc.log(f"Kodíček: TMDb API call to {url} (params: {all_params}) failed: {e}", level=xbmc.LOGERROR)
        return None
    except json.JSONDecodeError as e:
        xbmc.log(f"Kodíček: Failed to parse TMDb JSON response from {url}: {e}. Response text: {response.text[:500]}", level=xbmc.LOGERROR)
        return None

def _tmdb_get_for_search_module(endpoint, params):
    api_key = get_tmdb_api_key()
    if not api_key:
        return {"results": []} 
    return tmdb_api_request(api_key, endpoint, params)

def get_banner_image_url(tmdb_item, size="w500"):
    if not tmdb_item: return None
    backdrop_path = tmdb_item.get('backdrop_path')
    if backdrop_path: return f"https://image.tmdb.org/t/p/{size}{backdrop_path}"
    poster_path = tmdb_item.get('poster_path')
    if poster_path: return f"https://image.tmdb.org/t/p/{size}{poster_path}"
    return None

def get_tmdb_details(api_key, tmdb_id, media_type='movie', language='cs-CZ'):
    if not tmdb_id:
        xbmc.log("Kodíček: TMDb ID is missing for get_tmdb_details.", level=xbmc.LOGERROR)
        return None
    request_params = {'language': language, 'append_to_response': 'credits,images,videos,external_ids'}
    xbmc.log(f"Kodíček: Fetching TMDb details ({media_type}) for ID: {tmdb_id}, Lang='{language}' using tmdb_api_request", level=xbmc.LOGINFO)
    data = tmdb_api_request(api_key, f"/{media_type}/{tmdb_id}", request_params)
    if data:
        xbmc.log(f"Kodíček: TMDb details fetched successfully for ID: {tmdb_id}", level=xbmc.LOGINFO)
    else:
        xbmc.log(f"Kodíček: Failed to fetch TMDb details for ID: {tmdb_id}", level=xbmc.LOGWARNING)
    return data
# --- End TMDb Functions ---

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    action = params.get("action")

    username, password = get_credentials()
    if not username or not password:
        if action: xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
        return

    token = addon.getSetting('token')
    if not token:
        xbmc.log("Kodíček: No token found, attempting login.", level=xbmc.LOGINFO)
        token = login_webshare(username, password)
        if token:
            addon.setSetting('token', token)
        else:
            xbmc.log("Kodíček: Login failed, cannot proceed.", level=xbmc.LOGERROR)
            if action: xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return

    if action == "search":
        xbmc.log(f"Kodíček: Action 'search' entered. Params: {params}", level=xbmc.LOGINFO)
        what_to_search = params.get("what") 
        ask_for_input = params.get("ask") == "1"

        if ask_for_input:
            search_term_from_dialog = xbmcgui.Dialog().input(f"{plugin_name} – Vyhledat film/seriál", type=xbmcgui.INPUT_ALPHANUM)
            if search_term_from_dialog:
                what_to_search = search_term_from_dialog
                add_to_search_history({"query": what_to_search, "timestamp": int(time.time())})
            else:
                what_to_search = None

        if what_to_search:
            tmdb_api_key = get_tmdb_api_key()
            tmdb_results_to_display = []

            if tmdb_api_key:
                query_text_for_tmdb = strip_year(what_to_search)
                xbmc.log(f"Kodíček: Preparing TMDb multi-search - Query: '{query_text_for_tmdb}'", level=xbmc.LOGINFO)
                tmdb_search_results = new_search_tmdb(query_text_for_tmdb, _tmdb_get_for_search_module)
                if tmdb_search_results:
                    tmdb_results_to_display.extend(tmdb_search_results)
            
            if tmdb_results_to_display:
                xbmcplugin.setPluginCategory(addon_handle, f"TMDb Výsledky pro: {what_to_search}")
                xbmcplugin.setContent(addon_handle, 'videos')
                for item in tmdb_results_to_display:
                    media_type = item.get('media_type')
                    if not media_type or media_type not in ['movie', 'tv']:
                        continue
                    tmdb_id = item.get('id')
                    title = item.get('title') if media_type == 'movie' else item.get('name')
                    overview = item.get('overview', '')
                    release_date = item.get('release_date') if media_type == 'movie' else item.get('first_air_date')
                    year = release_date[:4] if release_date and len(release_date) >= 4 else ""
                    display_title = f"{title} ({year})" if year else title
                    display_title = f"[{media_type.upper()}] {display_title}"
                    
                    li = xbmcgui.ListItem(label=display_title)
                    info_labels = {'title': title, 'plot': overview, 'mediatype': media_type}
                    if year: info_labels['year'] = int(year)
                    
                    art_data = {}
                    thumb_url = get_banner_image_url(item, "w500") 
                    if thumb_url: art_data['thumb'] = art_data['poster'] = art_data['fanart'] = thumb_url
                    
                    li.setArt(art_data)
                    li.setInfo('video', info_labels)
                    li.setProperty('IsPlayable', 'false')

                    action_url = ""
                    if media_type == 'movie':
                        action_url = f"{BASE_URL_PLUGIN}?action=process_tmdb_selection&tmdb_id={tmdb_id}&media_type=movie&title={urllib.parse.quote(title, encoding='utf-8')}&year={year}"
                    elif media_type == 'tv':
                        action_url = f"{BASE_URL_PLUGIN}?action=show_seasons&tmdb_id={tmdb_id}&show_title={urllib.parse.quote(title, encoding='utf-8')}"
                    
                    if action_url:
                        xbmcplugin.addDirectoryItem(handle=addon_handle, url=action_url, listitem=li, isFolder=True)
                xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
                return
            else: 
                xbmc.log("Kodíček: No results from TMDb or no API key, proceeding with Webshare search.", level=xbmc.LOGINFO)
                query_for_webshare = strip_year(what_to_search)
                files = search_webshare(token, query_for_webshare)
                if not files:
                    xbmcgui.Dialog().notification(plugin_name, "Nic nebylo nalezeno na Webshare.", xbmcgui.NOTIFICATION_INFO)
                else:
                    xbmcplugin.setPluginCategory(addon_handle, f"Výsledky pro: {what_to_search}")
                    xbmcplugin.setContent(addon_handle, 'videos')
                    for file_item in files:
                        li = xbmcgui.ListItem(label=file_item["name"])
                        size_bytes = file_item.get("size", 0)
                        size_str = f"{size_bytes/(1024*1024*1024):.2f} GB" if size_bytes > 1024*1024*1024 else f"{size_bytes/(1024*1024):.2f} MB" if size_bytes > 1024*1024 else f"{size_bytes/1024:.0f} KB" if size_bytes > 1024 else f"{size_bytes} B"
                        li.setInfo("video", {"title": file_item["name"], "size": size_bytes, "plot": f"Velikost: {size_str}"})
                        li.setProperty('IsPlayable', 'true')
                        url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'], encoding='utf-8')}"
                        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
                xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

        else: 
            xbmcplugin.setPluginCategory(addon_handle, "Vyhledávání")
            li_new_search = xbmcgui.ListItem(label="Nové vyhledávání...")
            li_new_search.setArt({'icon': 'DefaultAddonsSearch.png'})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=search&ask=1", listitem=li_new_search, isFolder=True)
            search_history_items = load_search_history()
            if search_history_items:
                for item in search_history_items:
                    query_text = item.get("query")
                    if query_text:
                        timestamp_str = time.strftime('%d.%m.%y %H:%M', time.localtime(item['timestamp']))
                        li = xbmcgui.ListItem(label=f"Hledáno: {query_text} ({timestamp_str})")
                        xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=search&what={urllib.parse.quote(query_text, encoding='utf-8')}", listitem=li, isFolder=True)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

    elif action == "play":
        ident = params.get("ident")
        file_name_for_playback = params.get("name", "Přehrávaný soubor")
        if not ident:
            xbmcgui.Dialog().notification(plugin_name, "Chybí ident souboru.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
            return
        stream_url = get_stream_link(token, ident)
        if not stream_url:
            xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se získat odkaz.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.setResolvedUrl(addon_handle, False, xbmcgui.ListItem())
            return
        headers_str = urllib.parse.urlencode({'User-Agent': _session.headers.get('User-Agent', 'Mozilla/5.0'), 'Cookie': f'wst={token}'})
        path_with_headers = f"{stream_url}|{headers_str}"
        li = xbmcgui.ListItem(path=path_with_headers)
        li.setInfo("video", {"title": file_name_for_playback})
        li.setProperty('IsPlayable', 'true')
        li.setMimeType(get_mimetype(file_name_for_playback))
        add_to_history({"ident": ident, "name": file_name_for_playback, "timestamp": int(time.time()), "type": "video"})
        xbmcplugin.setResolvedUrl(addon_handle, True, li)

    elif action == "history":
        history_items = load_history()
        if not history_items:
            xbmcgui.Dialog().notification(plugin_name, "Historie přehrávání je prázdná.", xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
            return
        xbmcplugin.setPluginCategory(addon_handle, "Historie přehrávání")
        xbmcplugin.setContent(addon_handle, 'videos')
        for item in history_items:
            if not item.get("ident") or not item.get("name") or item.get("type") != "video": continue
            li = xbmcgui.ListItem(label=item["name"])
            timestamp_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(item['timestamp']))
            li.setInfo("video", {"title": item["name"], "plot": f"Naposledy přehráno: {timestamp_str}"})
            li.setProperty('IsPlayable', 'true')
            url = f"{BASE_URL_PLUGIN}?action=play&ident={item['ident']}&name={urllib.parse.quote(item['name'], encoding='utf-8')}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle)

    elif action == "show_combined_history":
        display_combined_history()
    
    elif action == "process_tmdb_selection":
        process_tmdb_selection(params, token)

    elif action == "show_seasons":
        tmdb_id = params.get("tmdb_id")
        show_title = params.get("show_title", "Seriál")
        api_key = get_tmdb_api_key()
        if not api_key or not tmdb_id:
            xbmcgui.Dialog().notification(plugin_name, "Chyba: Chybí API klíč nebo ID seriálu.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        tv_details = tmdb_api_request(api_key, f"/tv/{tmdb_id}", {'language': UI_LANG, 'append_to_response': 'images'})
        if not tv_details or not tv_details.get("seasons"):
            xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se načíst informace o sezónách.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        xbmcplugin.setPluginCategory(addon_handle, f"{show_title} - Sezóny")
        xbmcplugin.setContent(addon_handle, 'tvshows')
        for season in tv_details.get("seasons", []):
            season_number = season.get("season_number")
            
            skip_specials = True 
            try:
                skip_specials = addon.getSettingBool("tmdb_skip_specials")
            except TypeError:
                xbmc.log("Kodíček: 'tmdb_skip_specials' setting missing or invalid type, defaulting to True.", level=xbmc.LOGWARNING)

            if season_number == 0 and skip_specials: 
                 continue
            season_name = season.get("name") or f"Sezóna {season_number}"
            episode_count = season.get("episode_count", 0)
            display_label = f"{season_name} ({episode_count} epizod)"
            li = xbmcgui.ListItem(label=display_label)
            art_data = {}
            poster_path = season.get('poster_path') or tv_details.get('poster_path')
            if poster_path: art_data['thumb'] = art_data['poster'] = f"https://image.tmdb.org/t/p/w500{poster_path}"
            fanart_url = get_banner_image_url(tv_details)
            if fanart_url: art_data['fanart'] = fanart_url
            if not art_data.get('thumb') and fanart_url: art_data['thumb'] = fanart_url
            li.setArt(art_data)
            info = {'title': season_name, 'plot': season.get('overview', ''), 'tvshowtitle': show_title, 'season': season_number, 'episode': episode_count, 'mediatype': 'season'}
            if season.get('air_date'): info['premiered'] = season.get('air_date')
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'false')
            url = f"{BASE_URL_PLUGIN}?action=show_episodes&tmdb_id={tmdb_id}&season_number={season_number}&show_title={urllib.parse.quote(show_title, encoding='utf-8')}&show_year={tv_details.get('first_air_date', '')[:4]}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

    elif action == "show_episodes":
        tmdb_id = params.get("tmdb_id")
        season_number = params.get("season_number")
        show_title = params.get("show_title", "Seriál")
        show_year = params.get("show_year", "")
        api_key = get_tmdb_api_key()
        if not api_key or not tmdb_id or season_number is None:
            xbmcgui.Dialog().notification(plugin_name, "Chyba: Chybí API klíč, ID seriálu nebo číslo sezóny.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        season_details = tmdb_api_request(api_key, f"/tv/{tmdb_id}/season/{season_number}", {'language': UI_LANG, 'append_to_response': 'images'})
        if not season_details or not season_details.get("episodes"):
            xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se načíst informace o epizodách.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        xbmcplugin.setPluginCategory(addon_handle, f"{show_title} - Sezóna {season_number} - Epizody")
        xbmcplugin.setContent(addon_handle, 'episodes')
        for episode in season_details.get("episodes", []):
            episode_number = episode.get("episode_number")
            episode_name = episode.get("name") or f"Epizoda {episode_number}"
            display_label = f"E{episode_number:02d}: {episode_name}"
            li = xbmcgui.ListItem(label=display_label)
            art_data = {}
            still_path = episode.get('still_path')
            if still_path: art_data['thumb'] = art_data['icon'] = f"https://image.tmdb.org/t/p/w300{still_path}"
            else: 
                season_poster = season_details.get('poster_path')
                if season_poster: art_data['thumb'] = f"https://image.tmdb.org/t/p/w500{season_poster}"
            li.setArt(art_data)
            info = {'title': episode_name, 'plot': episode.get('overview', ''), 'tvshowtitle': show_title, 'season': int(season_number), 'episode': episode_number, 'mediatype': 'episode', 'premiered': episode.get('air_date','')}
            if episode.get('vote_average'): info['rating'] = episode.get('vote_average')
            li.setInfo('video', info)
            li.setProperty('IsPlayable', 'false')
            url = f"{BASE_URL_PLUGIN}?action=play_episode&tmdb_id={tmdb_id}&season_number={season_number}&episode_number={episode_number}&show_title={urllib.parse.quote(show_title, encoding='utf-8')}&episode_name_cs={urllib.parse.quote(episode.get('name', ''), encoding='utf-8')}&show_year={show_year}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

    elif action == "play_episode":
        tmdb_id = params.get("tmdb_id")
        season_number_str = params.get("season_number")
        episode_number_str = params.get("episode_number")
        show_title = params.get("show_title", "Seriál")
        episode_name_cs = params.get("episode_name_cs", "")
        show_year = params.get("show_year", "")
        if not all([tmdb_id, season_number_str, episode_number_str]):
            xbmcgui.Dialog().notification(plugin_name, "Chybí informace pro přehrání epizody.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        try:
            season_num_int = int(season_number_str)
            episode_num_int = int(episode_number_str)
        except ValueError:
            xbmcgui.Dialog().notification(plugin_name, "Neplatné číslo sezóny nebo epizody.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        
        episode_name_en = ""
        api_key = get_tmdb_api_key()
        if api_key:
            ep_details_en = tmdb_api_request(api_key, f"/tv/{tmdb_id}/season/{season_num_int}/episode/{episode_num_int}", {'language': 'en-US'})
            if ep_details_en and ep_details_en.get('name'):
                episode_name_en = ep_details_en.get('name')
        
        episode_name_for_search = episode_name_cs if episode_name_cs else episode_name_en
        
        queries_to_try = build_episode_queries(show_title, season_num_int, episode_num_int, episode_name_for_search, show_year)
        
        webshare_files = []
        for query in queries_to_try:
            xbmc.log(f"Kodíček: Searching Webshare for episode with query: '{query}'", level=xbmc.LOGINFO)
            current_results = search_webshare(token, query) 
            filtered_results = filter_episode_results(current_results, show_title, season_num_int, episode_num_int)
            xbmc.log(f"Kodíček: Webshare query '{query}' returned {len(current_results)} results, {len(filtered_results)} relevant.", level=xbmc.LOGINFO)
            if filtered_results:
                webshare_files = filtered_results
                break 
        
        if not webshare_files:
            xbmcgui.Dialog().notification(plugin_name, f"Pro '{show_title} S{season_num_int:02d}E{episode_num_int:02d}' nebyly na Webshare nalezeny žádné relevantní soubory.", xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
            return
        
        xbmcplugin.setPluginCategory(addon_handle, f"Webshare zdroje pro: {show_title} S{season_num_int:02d}E{episode_num_int:02d}")
        xbmcplugin.setContent(addon_handle, 'videos')
        for file_item in webshare_files:
            li = xbmcgui.ListItem(label=file_item["name"])
            size_bytes = file_item.get("size", 0)
            size_str = f"{size_bytes/(1024*1024*1024):.2f} GB" if size_bytes > 1024*1024*1024 else f"{size_bytes/(1024*1024):.2f} MB" if size_bytes > 1024*1024 else f"{size_bytes/1024:.0f} KB" if size_bytes > 1024 else f"{size_bytes} B"
            li.setInfo("video", {"title": file_item["name"], "size": size_bytes, "plot": f"Velikost: {size_str}"})
            li.setProperty('IsPlayable', 'true')
            url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'], encoding='utf-8')}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)

    elif action == 'movies':
        movies(params)
    elif action == 'series':
        series(params)
    elif action == "search_test":
        xbmc.log(f"Kodíček: Action 'search_test' entered. Params: {params}", level=xbmc.LOGINFO)
        xbmcgui.Dialog().notification(plugin_name, "Testovací vyhledávání spuštěno!", xbmcgui.NOTIFICATION_INFO, 3000)
        search_term = xbmcgui.Dialog().input(f"{plugin_name} – Testovací vyhledávání", type=xbmcgui.INPUT_ALPHANUM)
        if search_term:
            files = search_webshare(token, search_term)
            if not files:
                xbmcgui.Dialog().notification(plugin_name, f"Test: Nic pro '{search_term}'", xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcplugin.setPluginCategory(addon_handle, f"Testovací výsledky pro: {search_term}")
                xbmcplugin.setContent(addon_handle, 'videos')
                for file_item in files:
                    li = xbmcgui.ListItem(label=f"[TEST] {file_item['name']}")
                    li.setInfo("video", {"title": file_item["name"]})
                    li.setProperty('IsPlayable', 'true')
                    url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'], encoding='utf-8')}"
                    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
    else: # No action or unknown action - show main menu
        display_main_menu()

def build_episode_queries(show_title, season, episode, ep_title=None, year=None):
    """
    Vrátí seznam dotazů od nejpřísnějšího po nejvolnější pro vyhledávání epizod,
    včetně krátkých formátů a různých kombinací.
    """
    ep_title = ep_title or ""
    show_title = " ".join(show_title.split())
    ep_title = " ".join(ep_title.split())

    s_full = f"{season:02d}"
    s_short = str(season)
    e_full = f"{episode:02d}"
    e_short = str(episode)

    # Define all code formats
    code_formats = [
        f"S{s_full}E{e_full}",    # S01E01
        f"S{s_short}E{e_short}",  # S1E1
        f"{s_full}x{e_full}",     # 01x01
        f"{s_short}x{e_short}",   # 1x1
        f"S{s_full} E{e_full}",   # S01 E01 (with space)
        f"S{s_short} E{e_short}", # S1 E1 (with space)
    ]
    # Include less common mixed formats if full and short are different
    if s_full != s_short:
        code_formats.extend([
            f"S{s_short}E{e_full}", # S1E01
            f"S{s_full}E{e_short}", # S01E1
            f"{s_short}x{e_full}",   # 1x01
            f"{s_full}x{e_short}",   # 01x1
        ])

    potential_queries = []

    # Queries with year (most specific, tried first if year is present)
    if year:
        if ep_title:
            for code in [code_formats[0], code_formats[2]]: # S01E01, 01x01 with title and year
                potential_queries.append(f"{show_title} {code} {ep_title} {year}")
        for code in [code_formats[0], code_formats[2]]: # S01E01, 01x01 with year
            potential_queries.append(f"{show_title} {code} {year}")

    # Queries with episode title (without year)
    if ep_title:
        for code in code_formats:
            potential_queries.append(f"{show_title} {code} {ep_title}")

    # Queries without episode title (without year) - most general for episode codes
    for code in code_formats:
        potential_queries.append(f"{show_title} {code}")
        
    # Clean up queries: normalize spaces and remove duplicates while preserving order
    final_queries = []
    seen_queries = set()
    for q_str in potential_queries:
        normalized_q_str = " ".join(q_str.split())
        if normalized_q_str and normalized_q_str not in seen_queries:
            final_queries.append(normalized_q_str)
            seen_queries.add(normalized_q_str)
            
    return final_queries

def filter_episode_results(files, show_title, season, episode):
    norm_show = normalize_text(show_title)
    # Patterns for SxxExx and xxXxx, with and without leading zeros
    patterns = [
        f"s{season:02d}e{episode:02d}", # s01e01
        f"{season:02d}x{episode:02d}",   # 01x01
        f"s{season}e{episode}",          # s1e1
        f"{season}x{episode}",           # 1x1
    ]
    # Regex to match various season/episode patterns more flexibly
    # This regex looks for S<season>E<episode> or <season>x<episode> with optional leading zeros
    # It also allows for a space or dot or no separator between S/E and numbers
    # Example: S01E01, S1E1, 01x01, 1x1, S01.E01, S01 E01
    # The (?:...) is a non-capturing group.
    # The \b ensures word boundaries to avoid partial matches like S1E10 matching S1E1.
    regex_patterns = [
        r'\bs0?%s\s?[e\.]0?%s\b' % (season, episode), # S01E01, S1E1, S01 E01, S01.E01
        r'\b0?%s\s?x\s?0?%s\b' % (season, episode)    # 01x01, 1x1, 01 x 01
    ]
    combined_regex = re.compile('|'.join(regex_patterns), re.IGNORECASE)

    out = []
    for f_item in files:
        fname_normalized = normalize_text(f_item['name'])
        # Check for normalized show title
        if norm_show not in fname_normalized:
            continue
        # Check for any of the episode code patterns using direct string search or regex
        # Using regex for more flexibility with separators and optional leading zeros
        if combined_regex.search(fname_normalized):
            out.append(f_item)
            
    return out

def process_tmdb_selection(params, token):
    tmdb_id = params.get('tmdb_id')
    media_type = params.get('media_type', 'movie') 
    title = params.get('title', '') 
    year = params.get('year', '')
    xbmc.log(f"Kodíček: Processing TMDb MOVIE selection: ID={tmdb_id}, Title='{title}', Year='{year}'", level=xbmc.LOGINFO)

    tmdb_api_key = get_tmdb_api_key()
    detailed_tmdb_item = None
    if tmdb_api_key and tmdb_id:
        detailed_tmdb_item = get_tmdb_details(tmdb_api_key, tmdb_id, 'movie') 
        if detailed_tmdb_item:
            title = detailed_tmdb_item.get('title', title)
            release_date = detailed_tmdb_item.get('release_date')
            if release_date and len(release_date) >= 4: year = release_date[:4]
    
    tmdb_title_cleaned = strip_year(title)
    normalized_tmdb_title = normalize_text(tmdb_title_cleaned)
    tmdb_year_str = str(year) if year else ""
    original_title_cleaned = strip_year(detailed_tmdb_item.get('original_title', '')) if detailed_tmdb_item else ''

    webshare_files = []
    queries_tried = []
    
    def try_ws_search(query):
        if query in queries_tried: return [] 
        queries_tried.append(query)
        xbmc.log(f"Kodíček: Webshare Search for movie: Query='{query}'", level=xbmc.LOGINFO)
        return search_webshare(token, query)

    webshare_files = try_ws_search(tmdb_title_cleaned)
    if not webshare_files and tmdb_year_str:
        webshare_files = try_ws_search(f"{tmdb_title_cleaned} {tmdb_year_str}")
    if not webshare_files and original_title_cleaned and original_title_cleaned.lower() != tmdb_title_cleaned.lower():
        webshare_files = try_ws_search(original_title_cleaned)
    if not webshare_files and original_title_cleaned and original_title_cleaned.lower() != tmdb_title_cleaned.lower() and tmdb_year_str:
        webshare_files = try_ws_search(f"{original_title_cleaned} {tmdb_year_str}")

    if not webshare_files:
        xbmcgui.Dialog().notification(plugin_name, f"Pro '{title}' nebyly na Webshare nalezeny žádné soubory.", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
        return

    scored_files = []
    MIN_SCORE_THRESHOLD = 3.0
    for ws_file in webshare_files:
        fname_normalized = normalize_text(ws_file.get('name', ''))
        score = 0.0
        if normalized_tmdb_title not in fname_normalized:
            score = -100
        else:
            score += 3.0
        if score > -10:
            if tmdb_year_str:
                match = re.search(r'(19|20)\d{2}', fname_normalized)
                if match and abs(int(match.group()) - int(tmdb_year_str)) <= 1: score += 2.0
                else: score -= 1.0
            if any(tag in fname_normalized for tag in ['.cz', '.cze', '.cesky']): score += 2.0
            elif any(tag in fname_normalized for tag in ['.sk', '.svk', '.slovensky']): score += 1.5
            elif any(tag in fname_normalized for tag in ['.en', '.eng', '.english']): score += 0.5
            if '2160p' in fname_normalized or '4k' in fname_normalized: score += 2.0
            elif '1080p' in fname_normalized: score += 1.5
            elif '720p' in fname_normalized: score += 1.0
            if any(bad in fname_normalized for bad in ['.cam.', '.ts.', '.tc.']): score -= 3.0
        if not any(ws_file.get('name', '').lower().endswith(ext) for ext in ['.mkv', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.ts']):
            score = -200
        if score >= MIN_SCORE_THRESHOLD:
            scored_files.append({'file': ws_file, 'score': score, 'normalized_name': fname_normalized})

    scored_files.sort(key=lambda x: x['score'], reverse=True)
    if not scored_files:
        xbmcgui.Dialog().notification(plugin_name, f"Pro '{title} ({year})': žádné relevantní soubory na Webshare.", xbmcgui.NOTIFICATION_INFO)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
        return

    xbmcplugin.setPluginCategory(addon_handle, f"Webshare zdroje pro: {title} ({year})")
    xbmcplugin.setContent(addon_handle, 'videos')
    for scored_item in scored_files:
        file_item = scored_item['file']
        display_label = f"[S: {scored_item['score']:.1f}] {file_item['name']}"
        li = xbmcgui.ListItem(label=display_label)
        size_bytes = file_item.get("size", 0)
        size_str = f"{size_bytes/(1024*1024*1024):.2f} GB" if size_bytes > 1024*1024*1024 else f"{size_bytes/(1024*1024):.2f} MB" if size_bytes > 1024*1024 else f"{size_bytes/1024:.0f} KB" if size_bytes > 1024 else f"{size_bytes} B"
        plot_info = f"Velikost: {size_str}\nNormalizovaný název: {scored_item['normalized_name']}"
        art_data = {}
        if detailed_tmdb_item:
            info_labels = {'title': detailed_tmdb_item.get('title', file_item['name']), 'plot': detailed_tmdb_item.get('overview', plot_info), 'year': int(year) if year and year.isdigit() else None, 'genre': ", ".join([g['name'] for g in detailed_tmdb_item.get('genres', [])]), 'rating': detailed_tmdb_item.get('vote_average'), 'mediatype': 'movie', 'size': size_bytes}
            poster = detailed_tmdb_item.get('poster_path')
            fanart = detailed_tmdb_item.get('backdrop_path')
            if poster: art_data['thumb'] = art_data['poster'] = f"https://image.tmdb.org/t/p/w500{poster}"
            if fanart: art_data['fanart'] = f"https://image.tmdb.org/t/p/original{fanart}"
            li.setArt(art_data)
            li.setInfo('video', info_labels)
        else:
            li.setInfo("video", {"title": file_item["name"], "size": size_bytes, "plot": plot_info})
        li.setProperty('IsPlayable', 'true')
        url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'], encoding='utf-8')}"
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
    li_search_history_folder = xbmcgui.ListItem(label="Historie vyhledávání")
    li_search_history_folder.setArt({'icon': 'DefaultAddonsSearch.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=search", listitem=li_search_history_folder, isFolder=True)
    history_items = load_history()
    if history_items:
        for item in history_items:
            if not item.get("ident") or not item.get("name") or item.get("type") != "video": continue
            li = xbmcgui.ListItem(label=item["name"])
            timestamp_str = time.strftime('%d.%m.%Y %H:%M', time.localtime(item['timestamp']))
            li.setInfo("video", {"title": item["name"], "plot": f"Naposledy přehráno: {timestamp_str}"})
            li.setProperty('IsPlayable', 'true')
            url = f"{BASE_URL_PLUGIN}?action=play&ident={item['ident']}&name={urllib.parse.quote(item['name'], encoding='utf-8')}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
    xbmcplugin.endOfDirectory(addon_handle)

def display_main_menu():
    li_new_search = xbmcgui.ListItem(label="Vyhledat film/seriál")
    li_new_search.setArt({'icon': 'DefaultAddonsSearch.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=search&ask=1", listitem=li_new_search, isFolder=True)
    
    listitem_movies = xbmcgui.ListItem(label="Filmy")
    listitem_movies.setArt({'icon': 'DefaultMovies.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=movies", listitem=listitem_movies, isFolder=True)

    listitem_series = xbmcgui.ListItem(label="Seriály")
    listitem_series.setArt({'icon': 'DefaultTVShows.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=series", listitem=listitem_series, isFolder=True)

    li_history_folder = xbmcgui.ListItem(label="Historie")
    li_history_folder.setArt({'icon': 'DefaultFolder.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=show_combined_history", listitem=li_history_folder, isFolder=True)

    li_search_test = xbmcgui.ListItem(label="Vyhledávání - test")
    li_search_test.setArt({'icon': 'DefaultAddonsSearch.png'})
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=f"{BASE_URL_PLUGIN}?action=search_test", listitem=li_search_test, isFolder=True)
    
    xbmcplugin.endOfDirectory(addon_handle)

def add_dir(label, url, is_folder, icon=None, fanart=None, info=None, properties=None):
    li = xbmcgui.ListItem(label=label)
    art = {}
    if icon: art['icon'] = art['thumb'] = icon
    if fanart: art['fanart'] = fanart
    if art: li.setArt(art)
    if info: li.setInfo('video', info) # Assumes video info
    if properties:
        for key, value in properties.items():
            li.setProperty(key, value)
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=is_folder)

if __name__ == "__main__":
    args = sys.argv[2]
    if args.startswith('?'):
        args = args[1:]
    router(args)
