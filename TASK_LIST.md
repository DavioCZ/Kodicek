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
- [x] Přidat položky "Filmy" a "Seriály" do hlavního menu s placeholder funkcemi

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
- [x] **Získání a uložení TMDB API klíče:**
    - [x] Zaregistrovat se na TMDb a získat API klíč. (User provided)
    - [x] Uložit API klíč bezpečně (např. v Kodi settings).
- [x] **Implementace vyhledávání filmů a seriálů přes TMDb API:** (Movies implemented, TV shows can be added)
    - [x] Funkce pro vyhledávání filmů: `https://api.themoviedb.org/3/search/movie?api_key=TVUJ_KLIC&language=cs&query=NÁZEV&year=ROK` (Vylepšeno o toleranci roku `year_fuzz`, dotaz na TMDB nyní používá název bez roku získaný pomocí `strip_year()`)
    - [ ] Funkce pro vyhledávání seriálů: `https://api.themoviedb.org/3/search/tv?api_key=TVUJ_KLIC&language=cs&query=NÁZEV&first_air_date_year=ROK` (Placeholder for future)
    - [x] Zpracovat uživatelský dotaz (např. "Pán prstenů 2001") a extrahovat název a rok. (Vyhledávání TMDB nyní podporuje `year_fuzz`, dotaz na TMDB nyní používá název bez roku získaný pomocí `strip_year()`)
    - [x] Získat první/více výsledků, umožnit výběr nejrelevantnějšího. (Displayed as a list for user selection)
- [x] **Načítání detailů titulu z TMDb:**
    - [x] Pro vybrané ID titulu stáhnout detaily (např. přes `/movie/{movie_id}` nebo `/tv/{tv_id}`).
    - [x] Získat obrázky (poster, backdrop), žánry, popis, český název, originální název, rok vydání. (Used for enriching ListItems)
- [x] **Získávání a skládání URL obrázků (poster, backdrop):**
    - [x] Poster: `https://image.tmdb.org/t/p/w500/POSTER_PATH.jpg` (možnost volby šířky: w92, w154, w342, w500, w780, original). (w500 used)
    - [x] Backdrop: `https://image.tmdb.org/t/p/original/BACKDROP_PATH.jpg`. (Used for fanart)
- [x] **Zobrazení informací z TMDb ve výsledcích Kodi:**
    - [x] `label`: Název (z TMDb, nebo původní název souboru).
    - [x] `plot`: Popis filmu (z TMDb).
    - [x] `banner/thumb`: Poster/Backdrop z TMDb.
    - [x] `year`: Rok vydání.
    - [x] `genre`: Žánry (volitelně).
    - [x] Příklad implementace: (Implemented in `process_tmdb_selection` and `search` action)
      ```python
      li = xbmcgui.ListItem(label=tmdb_name)
      li.setArt({'thumb': poster_url, 'banner': backdrop_url})
      li.setInfo('video', {
          'title': tmdb_name,
          'plot': tmdb_overview,
          'year': tmdb_year,
          # další info
      })
      li.setProperty('IsPlayable', 'true')
      ```
- [ ] Testovat různé varianty zadání (Spider man/spider-man/…).
- [ ] Přidat zobrazení podobných titulů (rebooty, série, univerza, žánr).
- [ ] **Pokročilé tipy pro TMDb:**
    - [ ] Pokud je víc TMDb výsledků (remaky, seriály vs. filmy), zobrazit uživateli výběr „Myslel jste: ...?“
    - [ ] Možné cachovat TMDb odpovědi (omezení počtu dotazů).

---

## 5.1. Vylepšení TMDB a Navigace Seriálů (Červen 2025)
- [x] **Přepnutí na `/search/multi` pro TMDB:**
    - [x] `resources/lib/tmdb.py` nyní používá `/search/multi` pro současné hledání filmů a seriálů.
- [x] **Podpora více jazyků pro TMDB:**
    - [x] `resources/lib/tmdb.py` vyhledává nejprve v `cs-CZ`, poté jako fallback `en-US`.
- [x] **Fuzzy alias pro vyhledávací dotaz:**
    - [x] `resources/lib/tmdb.py` zkouší nahradit `" a "` za `" and "` pokud původní dotaz nic nenajde.
- [x] **Implementace navigace pro seriály:**
    - [x] Výsledky vyhledávání zobrazují seriály (`media_type="tv"`) jako složky.
    - [x] Kliknutí na seriál vede na `action="show_seasons"`, která zobrazí seznam sezón.
    - [x] Kliknutí na sezónu vede na `action="show_episodes"`, která zobrazí seznam epizod dané sezóny.
    - [x] Metadata a obrázky pro seriály, sezóny a epizody jsou načítány z TMDB.
- [x] **Konstrukce Webshare dotazu pro epizody:**
    - [x] Pro epizodu je Webshare dotaz tvořen jako: `"{Název seriálu} S{číslo série}E{číslo epizody} + {Český/EN název dílu} + {rok seriálu (volitelně)}"`.
    - [x] Vylepšeno v `action="play_episode"`:
        - [x] Funkce `build_episode_queries` byla přepsána pro generování širší škály variant dotazů, včetně krátkých formátů (např. S1E1, 1x1) a různých kombinací s/bez názvu epizody a roku. Pořadí generovaných dotazů bylo upraveno pro lepší úspěšnost.
        - [x] Přidána funkce `filter_episode_results` pro filtrování výsledků z Webshare tak, aby obsahovaly normalizovaný název seriálu a jeden z definovaných vzorů kódu epizody (SxxExx, xxXxx, SxE, xEx).
        - [x] Akce `play_episode` nyní po každém dotazu na Webshare filtruje výsledky pomocí `filter_episode_results` a použije první sadu neprázdných, relevantních výsledků.
        - [x] Rozšířeno logování o počet původních a filtrovaných výsledků.
- [x] **Oprava chyby "Invalid setting type" pro `tmdb_skip_specials`:**
    - [x] Přidána definice `tmdb_skip_specials` do `resources/settings.xml`.
    - [x] Ošetřeno volání `addon.getSettingBool("tmdb_skip_specials")` pomocí `try-except` v `kodicek.py`.

---

## 6. Filtrování a výběr správných zdrojů (Matching s Webshare)
- [x] **Propojení TMDb titulu s výsledky z Webshare:**
    - [x] Porovnávat název souboru z Webshare s originálním/českým názvem z TMDb (název z TMDb je před porovnáním také očištěn pomocí `strip_year()`).
        - [x] Normalizovat názvy (malá písmena, odstranit diakritiku, speciální znaky, nahradit mezery `_` nebo `.`).
    - [x] Porovnávat rok vydání (pokud je v názvu/metadata souboru). (Nyní s tolerancí ±1 rok)
    - [x] Vylepšena logika vyhledávání na Webshare v `process_tmdb_selection`:
        - [x] Primární vyhledávání: název z TMDb (očištěný pomocí `strip_year()`) BEZ roku.
        - [x] Fallback 1: název z TMDb (očištěný) + rok z TMDb.
        - [x] Fallback 2: originální název z TMDb (očištěný) BEZ roku.
        - [x] Fallback 3: originální název z TMDb (očištěný) + rok z TMDb.
    - [x] Dotazy na Webshare v `action=search` (při fallbacku z TMDb) také používají název očištěný pomocí `strip_year()`.
- [x] **Implementace algoritmu pro filtrování a skórování souborů z Webshare:**
    - [x] Vytvořit funkci `normalize(text)` pro úpravu názvů.
    - [x] Vytvořit funkci `strip_year(title)` pro odstranění roku z názvu.
    - [x] Pro každý soubor z Webshare:
        - [x] Zkontrolovat shodu normalizovaného názvu (očištěného pomocí `strip_year()`) a roku s TMDb.
        - [x] Přidělovat skóre na základě kritérií:
            - [x] Shoda názvu (očištěného pomocí `strip_year()`) a roku (základní skóre). (Shoda roku nyní s tolerancí ±1)
            - [x] Přítomnost jazykové stopy (CZ, CZE, český, SK, EN, ENG – preferovat CZ).
            - [x] Kvalita (1080p, 720p, BluRay, WEBRip). (Rozšířeno o 4K a penalizaci za CAM/TS)
            - [x] Další relevantní pravidla. (File type check implemented, přidán MIN_SCORE_THRESHOLD)
    - [x] Seřadit výsledky podle skóre (nejlepší nahoře).
    - [x] Vybrat soubor s nejvyšším skóre; pokud žádný nevyhovuje, vzít první dostupný z Webshare jako fallback. (User selects from sorted list; fallback if no scored files meeting threshold, plus fallback search query)
    - [x] Příklad algoritmu (pseudo): (Implemented and enhanced in `process_tmdb_selection`)
      ```python
      # Po získání výsledků z TMDb a Webshare:
      tmdb_name = 'Forrest Gump' # normalizovaný
      tmdb_year = 1994
      files = [ ... ] # seznam z Webshare

      def normalize(text):
          # Převod na malá písmena, odstranění diakritiky a speciálních znaků, nahradit mezery
          text = text.lower()
          # ... (implementace odstranění diakritiky a speciálních znaků)
          text = text.replace(' ', '.').replace('_', '.') # Příklad náhrady mezer
          return text

      results = []
      normalized_tmdb_name = normalize(tmdb_name)
      for f in files:
          fname_normalized = normalize(f['name'])
          score = 0
          if normalized_tmdb_name in fname_normalized and str(tmdb_year) in fname_normalized:
              score += 2 # Základní shoda
              if 'cz' in fname_normalized or 'cze' in fname_normalized or 'česky' in fname_normalized:
                  score += 2 # Český jazyk
              if '1080p' in fname_normalized:
                  score += 1 # HD kvalita
              # ... další pravidla pro kvalitu, typ souboru atd.
              if score > 0:
                  results.append((score, f))
      
      results.sort(key=lambda x: x[0], reverse=True) # Nejlepší nahoře
      vybrany_soubor = results[0][1] if results else (files[0] if files else None) # Pokud nic, vezmi první, pokud existuje
      ```
- [x] **Filtrovat výsledky podle:**
    - [x] Správného roku.
    - [x] Typu souboru (jen video: .mp4, .mkv, .avi…).
    - [x] (Volitelně) Jazyk, titulky, kvalita – již částečně řešeno skórováním.
- [ ] Otestovat, že nikdy nenabídnu prázdnou volbu zdrojů (pokud Webshare něco vrátí).
- [ ] Přidat uživatelsky přívětivou hlášku při nenalezení vhodného zdroje na Webshare. (Basic notification exists)
- [ ] **Pokročilé tipy pro filtrování:**
    - [ ] Pokud nenajdeš přesnou shodu, nabídnout víc verzí (uživatel si vybere). (User selects from sorted list)

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

## 14. Integrace dalších služeb
- [x] **Streamuj.tv Resolver:**
    - [x] Přidat `StreamujHoster` do `kodicek.py`.
    - [x] Přidat nastavení pro Streamuj.tv (`st_user`, `st_pass`, `st_loc`) do `resources/settings.xml`.
    - [x] Opravit regulární výraz pro extrakci zdrojové URL v `streamuj.py`.

---
