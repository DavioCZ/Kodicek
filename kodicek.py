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
from xml.etree import ElementTree as ET
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
API_BASE_URL = "https://webshare.cz/api/"

# Global session object
_session = requests.Session()
_session.headers.update({'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.138 Safari/537.36"})

def get_credentials():
    username = addon.getSetting("ws_username")
    password = addon.getSetting("ws_password")
    if not username or not password:
        xbmcgui.Dialog().notification(plugin_name, addon.getLocalizedString(30101), xbmcgui.NOTIFICATION_ERROR)
        addon.openSettings()
        return None, None
    return username, password

def api_call(endpoint, data=None, method='post'):
    url = API_BASE_URL + endpoint + "/"
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

    salt_response_content = api_call('salt', {'username_or_email': username})
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
    
    login_response_content = api_call('login', login_data)
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
    search_response_content = api_call('search', search_params, method='post') # Example uses POST for search
    
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
        link_response_content = api_call('file_link', link_params, method='post')
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

    if action == "initiate_search":
        xbmc.log(f"Kodíček: Action 'initiate_search' entered.", level=xbmc.LOGINFO)
        search_query = xbmcgui.Dialog().input(f"{plugin_name} – Vyhledat film/seriál", type=xbmcgui.INPUT_ALPHANUM)
        if search_query:
            url = f"{BASE_URL_PLUGIN}?action=search&query={urllib.parse.quote(search_query)}"
            xbmc.log(f"Kodíček: 'initiate_search' - calling Container.Update with URL: {url}", level=xbmc.LOGINFO)
            xbmc.executebuiltin(f'Container.Update("{url}")')
            # This path is done, Container.Update will trigger the 'search' action.
            # updateListing=False because this path doesn't draw the list.
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True, updateListing=False) 
        else:
            xbmc.log(f"Kodíček: 'initiate_search' - user cancelled input.", level=xbmc.LOGINFO)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False) # User cancelled input

    elif action == "search":
        xbmc.log(f"Kodíček: Action 'search' entered. Params: {params}", level=xbmc.LOGINFO)
        query = params.get("query")
        if not query:
            xbmc.log(f"Kodíček: 'search' action - no query found.", level=xbmc.LOGERROR)
            xbmcgui.Dialog().notification(plugin_name, "Není zadán hledaný výraz.", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
        
        files = search_webshare(token, query)
        if not files:
            xbmcgui.Dialog().notification(plugin_name, "Nic nebylo nalezeno.", xbmcgui.NOTIFICATION_INFO)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True) # Explicitly end directory
            return # Stop further execution in this path
        else:
            xbmcplugin.setPluginCategory(addon_handle, f"Výsledky pro: {query}")
            xbmcplugin.setContent(addon_handle, 'videos') # Inform Kodi about the content type
            for file_item in files: # Renamed to avoid conflict with 'file' module
                li = xbmcgui.ListItem(label=file_item["name"])
                # Format size nicely
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
                # Use BASE_URL_PLUGIN for constructing plugin URLs
                url = f"{BASE_URL_PLUGIN}?action=play&ident={file_item['ident']}&name={urllib.parse.quote(file_item['name'])}"
                xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle)

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

        xbmcplugin.setResolvedUrl(addon_handle, True, li)
        xbmc.log(f"Kodíček: [PLAY] setResolvedUrl called. Should now play.", level=xbmc.LOGINFO)

    else: # No action or unknown action - show main menu
        display_main_menu()


def display_main_menu():
    li = xbmcgui.ListItem(label="Vyhledat")
    # It's good practice to provide an icon, even if default
    # li.setArt({'icon': 'DefaultAddonsSearch.png'}) # Example, if you have icons
    url = f"{BASE_URL_PLUGIN}?action=initiate_search" # Changed to new action
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=True) # isFolder=True, as initiate_search will lead to a list (via search)
    
    # Add other main menu items here if needed in the future
    # e.g., settings, history etc.
    # li_settings = xbmcgui.ListItem(label="Nastavení")
    # url_settings = f"{BASE_URL_PLUGIN}?action=settings" # Assuming you might add a settings action
    # xbmcplugin.addDirectoryItem(handle=addon_handle, url=url_settings, listitem=li_settings, isFolder=False)

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
