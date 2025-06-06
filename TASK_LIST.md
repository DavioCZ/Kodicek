# Kodíček – TASK LIST PRO VÝVOJ

## 0. Příprava a plánování
- [x] **Vytvořit repozitář** pro projekt ([GitHub/GitLab/Bitbucket](https://github.com/DavioCZ/Kodicek))
- [x] Přidat README.md se specifikací
- [x] Vytvořit základní složkovou strukturu pro Kodi plugin (`plugin.video.kodicek`)
- [x] Založit `CHANGELOG.md` pro sledování vývoje
- [x] Připravit kanál pro poznámky/chyby (Trello, GitHub Issues…)

---

## 1. Základní funkční skeleton pluginu
- [x] Vytvořit základní `addon.xml` (název, id, metadata)
- [x] Přidat prázdný hlavní skript `default.py`
- [x] Připravit `resources/settings.xml` s nastavením pro Webshare login/heslo (čeština)
- [x] Otestovat instalaci pluginu do Kodi („Doplňky > Instalovat ze ZIP“)
- [x] Otestovat zobrazení pluginu v menu Kodi

---

## 2. Přihlášení a komunikace s Webshare
- [x] Implementovat načítání login/hesla z Kodi settings
- [x] Naprogramovat login funkci (přihlášení na Webshare API, získání tokenu)
- [ ] Otestovat přihlášení (správné i špatné údaje → ověřit chybové hlášky)
- [ ] Zajistit bezpečné zacházení s citlivými údaji

---

## 3. První verze vyhledávání filmů/seriálů
- [x] Vytvořit jednoduché vyhledávací pole (dialog v češtině)
- [x] Implementovat vyhledávání přes Webshare API
- [x] Výpis základních výsledků (název souboru, velikost, typ)
- [x] Opravit navigaci zpět po vyhledávání (aby se vracelo do hlavního menu)
- [ ] Otestovat různé vyhledávací dotazy (správně/špatně/bez výsledků)
- [x] Přidat přehrávání vybraného výsledku v Kodi
- [ ] Otestovat přehrávání různých typů souborů

---

## 4. Implementace základní historie sledování
- [x] Ukládat název, čas, typ přehrávaného titulu/epizody do lokálního souboru (JSON) (`history.json`)
  - [x] Refaktoring pro použití xbmcvfs a translatePath v history.py
  - [x] Zajistit, aby se do `history.json` ukládaly pouze skutečně přehrávané položky (typ "video").
- [x] Zobrazit historii přehrávání v hlavním menu (název, poslední čas sledování)
  - [x] Upřesnit název menu na "Historie přehrávání".
  - [x] Zajistit, aby se zobrazovaly pouze položky z `history.json` (přehrávané).
- [ ] Otestovat opakované přehrávání z historie
- [x] Ošetřit edge-cases (duplicitní položky, full historie)
- [x] Implementovat oddělenou historii vyhledávání (`search_history.json`)
  - [x] Vytvořit funkce v `history.py` pro načítání, ukládání a přidávání do `search_history.json`.
  - [x] Ukládat vyhledané dotazy (text + timestamp) do `search_history.json` při akci vyhledávání.
  - [x] Zobrazovat historii vyhledaných dotazů v menu "Vyhledávání", pokud není aktivní vyhledávací dotaz.

---

## X. Oprava UX Bugu Vyhledávání
- [x] Opravit UX bug s vyhledávacím dialogem (popsáno v zadání)
  - [x] Zajistit, aby se vyhledávací dialog zobrazil POUZE pokud je explicitně vyvolán (např. `ask=1`)
  - [x] Upravit položku menu "Vyhledat" tak, aby volala `action=search` s parametrem `ask=1`
  - [x] Pokud `ask=1` není přítomen, zobrazit historii vyhledávání a další relevantní položky, NE klávesnici.
  - [x] Odebrat/refaktorovat `action=initiate_search` a sloučit logiku do `action=search`.

---

## 5. Chytré vyhledávání pomocí TMDB API
- [ ] Získat TMDB API klíč (uložit do `.env` nebo Kodi settings)
- [ ] Implementovat funkci na vyhledávání v TMDB podle uživatelského dotazu (fuzzy search)
- [ ] Načítat bannery, popisy, typ, rok z TMDB a zobrazovat u výsledků
- [ ] Testovat různé varianty zadání (Spider man/spider-man/…)
- [ ] Přidat zobrazení podobných titulů (rebooty, série, univerza, žánr)

---

## 6. Filtrování a výběr správných zdrojů
- [ ] Propojovat vyhledaný titul z TMDB s výsledky z Webshare (název, rok, číslo série/epizody)
- [ ] Filtrovat výsledky podle:
    - správného roku
    - typu souboru (jen video)
    - (volitelně) jazyk, titulky, kvalita
- [ ] Otestovat, že nikdy nenabídnu prázdnou volbu zdrojů
- [ ] Přidat uživatelsky přívětivou hlášku při nenalezení zdroje

---

## 7. Seriály – výběr epizody a zobrazení pouze dostupných
- [ ] Po kliknutí na seriál načíst z TMDB seznam sérií a epizod
- [ ] Ověřit dostupnost zdrojů na Webshare pro každou epizodu
- [ ] Zobrazit uživateli pouze ty epizody, které lze opravdu přehrát
- [ ] Otestovat různé případy (chybějící díly, různé formáty označení, speciální epizody…)

---

## 8. Autoplay dalšího dílu (seriály) – vestavěné i přes Up Next
- [ ] Implementovat funkci „automaticky přehrát další díl“ (možnost zap/vyp v nastavení)
- [ ] Zachytit konec přehrávání (nebo závěrečné titulky)
- [ ] Zobrazit popup s odpočtem (ANO/NE, přehrát nyní/zrušit)
- [ ] Předat metadata (název seriálu, série, epizoda, atd.) pro kompatibilitu s Up Next
- [ ] Otestovat s pluginem [Up Next](https://kodi.wiki/view/Add-on:Up_Next)
- [ ] Otestovat všechny edge-case (poslední díl, chybějící další díl, změna preferencí uživatele)

---

## 9. Filmy – doporučené po skončení
- [ ] Po skončení filmu získat přes TMDB seznam doporučených/podobných/ze stejné kolekce filmů
- [ ] Zobrazit uživateli jednoduché menu s doporučenými filmy (banner, název, rok)
- [ ] Při výběru rovnou navázat vyhledáváním a nabídkou zdrojů (automatický přechod)
- [ ] Otestovat různé kolekce, univerza, žánry

---

## 10. Inteligentní převzetí preferencí zdroje
- [ ] Při sledování filmu/epizody uložit vlastnosti zdroje (jazyk, titulky, kvalita)
- [ ] Při přehrání dalšího dílu nebo doporučeného filmu automaticky předvybrat nejpodobnější zdroj
- [ ] Pokud není k dispozici identická varianta, nabídnout další nejlepší možnost
- [ ] Umožnit ruční změnu zdroje (popup)
- [ ] Otestovat různé kombinace jazyků/titulků/kvality

---

## 11. Vylepšování UX a stabilita
- [ ] Lokalizovat všechny popisky, hlášky a dialogy do češtiny
- [ ] Ošetřit chybové scénáře (špatné přihlášení, chyba sítě, nedostupné API…)
- [ ] Pravidelně testovat na různých verzích Kodi a různých OS
- [ ] Vyčistit a komentovat kód
- [ ] Pravidelně průběžně zálohovat a commitovat

---

## 12. Dokumentace a finální příprava
- [ ] Doplnit komentáře do kódu
- [ ] Aktualizovat README.md (návod na instalaci, používání, screenshoty)
- [ ] Přidat poznámky k integraci s Up Next
- [ ] Připravit instalační ZIP
- [ ] Ověřit čistotu a bezpečnost repozitáře (žádné citlivé údaje!)
- [ ] Finální testování: projít všechny user flows, otestovat chyby, edge-case, UX

---

## 13. Release, údržba, sběr zpětné vazby
- [ ] Publikovat první veřejnou verzi (např. GitHub release)
- [ ] Požádat testery o zpětnou vazbu
- [ ] Sledovat a opravovat bugy (issue tracker)
- [ ] Plánovat nové featury, údržbu a další rozvoj

---
