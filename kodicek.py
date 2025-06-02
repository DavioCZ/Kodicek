# -*- coding: utf-8 -*-
import sys
import os
import urllib.parse
import xbmc
import xbmcplugin
import xbmcgui
import xbmcaddon
import requests

addon = xbmcaddon.Addon()
addon_handle = int(sys.argv[1])
BASE_URL = sys.argv[0]
plugin_name = "Kodíček"

def get_credentials():
    username = addon.getSetting("ws_username")
    password = addon.getSetting("ws_password")
    return username, password

def login_webshare(username, password):
    url = "https://webshare.cz/api/login/"
    data = {"username": username, "password": password}
    r = requests.post(url, data=data)
    r.raise_for_status()
    resp = r.json()
    if resp.get("status") != "OK":
        xbmcgui.Dialog().notification(plugin_name, "Přihlášení k Webshare selhalo!", xbmcgui.NOTIFICATION_ERROR)
        return None
    return resp.get("token")

def search_webshare(token, query):
    url = "https://webshare.cz/api/file_search/"
    params = {
        "search": query,
        "limit": 30
    }
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json().get("files", [])

def get_stream_link(token, ident):
    url = "https://webshare.cz/api/file_link/"
    params = {"ident": ident}
    headers = {"Authorization": f"Bearer {token}"}
    r = requests.get(url, params=params, headers=headers)
    r.raise_for_status()
    return r.json().get("url")

def router(paramstring):
    params = dict(urllib.parse.parse_qsl(paramstring))
    if params.get("action") == "search":
        query = params.get("query")
        if not query:
            xbmcgui.Dialog().notification(plugin_name, "Není zadán hledaný výraz.", xbmcgui.NOTIFICATION_ERROR)
            return
        username, password = get_credentials()
        token = login_webshare(username, password)
        if not token:
            return
        files = search_webshare(token, query)
        if not files:
            xbmcgui.Dialog().notification(plugin_name, "Nic nebylo nalezeno.", xbmcgui.NOTIFICATION_INFO)
            return
        for file in files:
            li = xbmcgui.ListItem(label=file["name"])
            li.setInfo("video", {"title": file["name"], "size": file["size"]})
            url = f"{BASE_URL}?action=play&ident={file['ident']}&name={urllib.parse.quote(file['name'])}"
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url, listitem=li, isFolder=False)
        xbmcplugin.endOfDirectory(addon_handle)
    elif params.get("action") == "play":
        ident = params.get("ident")
        username, password = get_credentials()
        token = login_webshare(username, password)
        if not token:
            return
        stream_url = get_stream_link(token, ident)
        if not stream_url:
            xbmcgui.Dialog().notification(plugin_name, "Nepodařilo se získat odkaz ke stažení.", xbmcgui.NOTIFICATION_ERROR)
            return
        li = xbmcgui.ListItem(path=stream_url)
        xbmcplugin.setResolvedUrl(addon_handle, True, li)
    else:
        # Úvodní obrazovka – zadání hledání
        search_query = xbmcgui.Dialog().input("Kodíček – Vyhledat film/seriál", type=xbmcgui.INPUT_ALPHANUM)
        if search_query:
            url = f"{BASE_URL}?action=search&query={urllib.parse.quote(search_query)}"
            xbmc.executebuiltin(f'RunPlugin("{url}")')

if __name__ == "__main__":
    router(sys.argv[2][1:])
