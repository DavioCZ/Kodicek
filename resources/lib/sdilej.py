"""KODICEK – resolver pro Sdilej.cz

Tento modul přidává podporu hosteru Sdilej.cz do vašeho Kodi plug‑inu.
Stačí:
1. Přidat objekt `SdilejHoster` do seznamu hosterů (viz main.py).
2. Vyplnit uživatelské jméno a heslo v nastavení add‑onu.

Rozhraní je kompatibilní s třídou `BaseHoster`:
    * search(query) -> list[dict]
    * get_stream(file_id) -> přímé URL k videu (HTTP/HTTPS)

Poznámka: Sdilej.cz API není veřejně dokumentováno. Všechny endpointy
vycházejí z reverzního inženýrství oficiálního Sdilej Manageru 1.42.
Pokud Sdilej.cz změní strukturu, upravte konstanty BASE_URL & API_URL
popř. cesty v methods.
"""
from __future__ import annotations

import logging
import time
from typing import List, Dict

import requests


class SdilejHoster:  # (BaseHoster): dědění od vaší společné třídy
    """Resolver pro Sdilej.cz."""

    BASE_URL = "https://www.sdilej.cz"
    API_URL = f"{BASE_URL}/api"

    def __init__(self, username: str | None = None, password: str | None = None, session: requests.Session | None = None):
        self.username = username
        self.password = password
        self.session = session or requests.Session()
        self._token: str | None = None

        if self.username and self.password:
            self._login()
        else:
            logging.warning("SdilejHoster: není zadáno uživatelské jméno / heslo – dostupná jen pomalá (free) rychlost a limit 1 vlákno.")

    # ------------------------------------------------------------------
    # Veřejné rozhraní
    # ------------------------------------------------------------------
    def search(self, query: str, page: int = 1, per_page: int = 60) -> List[Dict]:
        """Plnotextové hledání videí.
        Vrací list slovníků: {title, size, id, url}.
        """
        params = {
            "term": query,
            "page": page,
            "perPage": per_page,
            "types": "video",  # filtrujeme jen video soubory
        }
        r = self.session.get(f"{self.API_URL}/search", params=params, headers=self._headers(), timeout=10)
        r.raise_for_status()
        data = r.json().get("data", [])
        results: List[Dict] = []
        for item in data:
            results.append({
                "title": item["name"],
                "size": item["size"],
                "id": item["id"],
                "url": f"{self.BASE_URL}/{item['slug']}/{item['id']}",
            })
        return results

    def get_stream(self, file_id: str) -> str | None:
        """Získá přímé (prémiové) URL k videu.
        Pokud je add‑on přihlášen k prémiovému účtu, Sdilej vrátí 302 s Location
        obsahujícím efektivní CDN link. Free účet obvykle vrací JSON s čekací
        dobou; tu by bylo nutné obsloužit (viz _wait_ticket).
        """
        # 1) požádáme o direct URL (download)
        resp = self.session.get(
            f"{self.API_URL}/file/download",
            params={"id": file_id},
            headers=self._headers(),
            allow_redirects=False,
            timeout=10,
        )

        # Prémiový účet => 302 Found s Location
        if resp.status_code in (301, 302):
            return resp.headers["Location"]

        # Free režim => JSON s ticketem a čekací dobou
        if resp.headers.get("Content-Type", "").startswith("application/json"):
            payload = resp.json()
            wait = payload.get("wait", 0)
            ticket = payload.get("ticket")
            if ticket and wait:
                logging.info("SdilejHoster: čekám %s s na ticket…", wait)
                time.sleep(wait + 1)
                return self._redeem_ticket(file_id, ticket)

        resp.raise_for_status()
        return None

    # ------------------------------------------------------------------
    # Interní pomocné funkce
    # ------------------------------------------------------------------
    def _login(self) -> None:
        payload = {"username": self.username, "password": self.password}
        r = self.session.post(f"{self.API_URL}/user/login", json=payload, timeout=10)
        r.raise_for_status()
        data = r.json()
        self._token = data.get("token") or data.get("access_token")
        if not self._token:
            raise RuntimeError("SdilejHoster: nepodařilo se získat token – zkontroluj přihlašovací údaje.")
        logging.info("SdilejHoster: úspěšně přihlášen jako %s", self.username)

    def _headers(self) -> dict:
        hdrs = {
            "User-Agent": "KODICEK/1.0 (Kodi add‑on)",
        }
        if self._token:
            hdrs["Authorization"] = f"Bearer {self._token}"
        return hdrs

    def _redeem_ticket(self, file_id: str, ticket: str) -> str | None:
        """Druhý krok free stahování – smění ticket za přímé URL."""
        r2 = self.session.get(
            f"{self.API_URL}/file/download",
            params={"id": file_id, "ticket": ticket},
            headers=self._headers(),
            allow_redirects=False,
            timeout=10,
        )
        if r2.status_code in (301, 302):
            return r2.headers.get("Location")
        r2.raise_for_status()
        return None


# ----------------------------------------------------------------------
# Krátký test – pustí se jen pokud modul spustíš přímo (python sdilej.py)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    import argparse, sys, os, pprint

    parser = argparse.ArgumentParser(description="Rychlý test Sdilej hosteru")
    parser.add_argument("--user")
    parser.add_argument("--password")
    parser.add_argument("query", help="Hledaný výraz (film)")
    args = parser.parse_args()

    hoster = SdilejHoster(args.user, args.password)
    files = hoster.search(args.query)
    pprint.pprint(files[:5])
    if files:
        first_id = files[0]["id"]
        url = hoster.get_stream(first_id)
        print("Stream URL:", url)
