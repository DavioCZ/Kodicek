# Kodíček – SPECIFIKACE VÝSLEDNÉHO PRODUKTU

Minimalistický Kodi plugin pro vyhledávání a přehrávání filmů/seriálů z Webshare.cz

## Popis aplikace
Kodíček je chytrý, minimalistický Kodi plugin pro pohodlné vyhledávání a přehrávání filmů i seriálů ze služby Webshare.cz. Důraz je kladen na intuitivní ovládání, vyspělou logiku vyhledávání, čistý uživatelský zážitek, minimum slepých uliček a chytře řízené pokračování sledování. Plugin je kompletně v češtině.

---

## Hlavní funkce pluginu

### 1. Hlavní menu (po spuštění)
- **Vyhledávání** – hlavní cesta, vstup do chytrého vyhledávání filmů/seriálů.
- **Filmy** – možnost v budoucnu prohlížet oblíbené, nové, doporučené filmy.
- **Seriály** – v budoucnu možnost řazení podle žánru, popularity, série.
- **Historie sledování** – přehled naposledy skutečně sledovaných filmů/epizod.
- **Nastavení** – zadání údajů k Webshare a dalších pokročilých voleb.

---

### 2. Vyhledávání (core funkce)
- **Pole pro zadání názvu filmu/seriálu.**
- Vyhledávání tolerantní k překlepům a formátům názvů (např. „spider man 3“, „spider-man 3“, „spiderman 3“ apod.).
- Nejprve využití **TMDB API** pro získání přesného názvu, popisu, banneru, roku, typu (film/seriál) a případně dalších dílů/franšíz.
- Nalezení „podobných“ titulů pomocí TMDB (další díly série, rebooty, filmy z univerza, filmy podle žánru).
- **Výpis výsledků**:
    - Bannery, název, rok, typ.
    - Umožnit rychlé kliknutí na nalezený titul.
- **Po kliknutí na titul**:
    - U filmu: nabídka dostupných zdrojů ke zhlédnutí (filtrováno!).
    - U seriálu: výběr série a epizody (zobrazit jen ty, které skutečně existují na Webshare), pak popup se zdroji.

---

### 3. Filtrování zdrojů (zásadní UX)
- Filtrovat podle shody názvu, roku (případně čísla epizody/série), pouze video soubory (mp4, mkv, avi…), žádné exe, rar, txt, atd.
- (Volitelně později: filtr podle jazyka, kvality, titulků…)
- Nabízet jen funkční, relevantní zdroje.
- Pokud žádný vhodný zdroj neexistuje, zobrazit přátelskou hlášku a nenabízet další prázdné kroky.

---

### 4. Historie sledování
- Ukládat pouze **skutečně sledované tituly/epizody** do lokálního souboru (např. JSON).
- V menu a v sekci historie zobrazovat naposledy sledované filmy/epizody (název, rok, banner, čas přehrání).
- Umožnit opakované přehrání přímo z historie.
- (Volitelně do budoucna: mazání historie, možnost vypnout/zapnout historii.)

---

### 5. Seriály – výběr epizody a automatické přehrání dalšího dílu
- Po kliknutí na seriál:
    - Získat z TMDB seznam sérií a epizod.
    - Zobrazit uživateli pouze ty série/epizody, které mají aspoň jeden zdroj na Webshare.
    - Po výběru epizody nabídnout popup se zdroji.
- **Autoplay dalšího dílu:**  
    - Po přehrání (nebo už v závěrečných titulcích) nabídnout automatické přehrání další epizody (popup: „Chcete přehrát další díl?“ s odpočtem nebo bez).
    - Výběr zdroje pro další díl proběhne **co nejpodobněji** právě přehrávanému (jazyk, titulky, kvalita…).
    - Pokud není další díl dostupný, zobrazit hlášku „Další díl není k dispozici.“
    - **Integrace s Up Next:**  
      - Kodíček bude podporovat plugin [Up Next](https://kodi.wiki/view/Add-on:Up_Next), který automaticky nabídne další díl v popupu podle správně nastavených metadat.
      - Při přehrávání budou vyplněny všechny důležité metadata (`season`, `episode`, `tvshowtitle` atd.), aby Up Next poznal, že jde o seriál.

---

### 6. Filmy – doporučení po skončení
- Po přehrání filmu (nebo už v závěrečných titulcích) se nabídne **menu s doporučenými filmy**:
    - Nejprve filmy ze stejné „kolekce“ (franchise/universe) podle TMDB.
    - Dále filmy podobného žánru/tématu (TMDB „similar movies“).
    - (Volitelně: napojení na uživatelské preference, historii…)
- Uživatel si může rovnou vybrat a pustit další film bez nutnosti znovu vyhledávat.
- **Při přehrání doporučeného filmu se automaticky předvybere zdroj s vlastnostmi co nejvíce podobnými právě sledovanému filmu** (viz další sekce).

---

### 7. Inteligentní převzetí preferencí zdroje
- Při přehrávání dalšího dílu seriálu nebo doporučeného filmu plugin automaticky vyhledá a předvybere ten zdroj, který se co nejvíce shoduje s vlastnostmi naposledy přehrávaného titulu:
    - jazyk zvuku (primární kritérium),
    - titulky (pokud byly použity),
    - kvalita videa (rozlišení, bitrate).
- Pokud není přesně stejný zdroj dostupný, plugin nabídne další nejbližší variantu (např. nižší kvalita, stejný jazyk apod.).
- Uživatel může v případě potřeby zdroj ručně změnit.
- Toto chování může být volitelné (nastavitelné v preferencích pluginu).

---

### 8. Uživatelský zážitek
- Vše v češtině (UI, hlášky, nastavení).
- Žádné prázdné výsledky, slepé uličky nebo zmatené menu.
- Upozornění na chyby (špatné přihlášení, žádné zdroje, chyba sítě…).
- Hlavní funkce mají co nejkratší cestu k cíli (minimum kliknutí k přehrání).

---

### 9. Bezpečnost a správa údajů
- Přihlašovací údaje k Webshare se zadávají pouze v nastavení pluginu.
- Žádné citlivé údaje v kódu.
- Volitelné API klíče (např. TMDB) načítat z `.env` nebo nastavení pluginu.

---

## Budoucí rozšíření (Nice-to-have)
- Uživatelské filtry (jazyk, titulky, rozlišení…)
- Zobrazení oblíbených/doporučených titulů
- Napojení na další databáze (IMDB, ČSFD)
- Oznámení o nových dílech, pokročilá práce s historií
- Multijazyčné prostředí

---

## Priorita vývoje a ladění
1. **Vyhledávání a zobrazování relevantních výsledků** (spolehlivost!)
2. **Filtrování správných zdrojů**
3. **Historie sledování**
4. **Seriály – výběr epizody a autoplay**
5. **Filmy – doporučené po skončení**
6. **Inteligentní převzetí preferencí zdroje**
7. Vylepšování UX a pokročilé funkce

---

## Uživatelská cesta (user flow)

### Filmy:
1. Spustím Kodíček → „Vyhledávání“ → zadám film (např. „Spider man 3“)
2. Zobrazí se výsledky s bannery (název, rok, popis)
3. Kliknu na „Spider-Man 3 (2007)“ → popup se zdroji (jen relevantní)
4. Vyberu zdroj, spustí se přehrávání
5. Po skončení filmu se zobrazí menu s doporučenými filmy (stejná kolekce/universe, žánr, podobné filmy podle TMDB)
6. Kliknutím na doporučený titul mohu rovnou spustit další film (automaticky se vybere podobný zdroj dle posledně přehrávaného)

### Seriály:
1. Spustím Kodíček → „Vyhledávání“ → zadám název seriálu
2. Vyberu seriál → zobrazí se série a epizody (jen ty s dostupným zdrojem)
3. Vyberu epizodu → popup se zdroji
4. Spustí se přehrávání
5. Po skončení (nebo v titulcích) – nabídka přehrát další díl (Up Next popup, nebo vestavěné okno Kodíčku)
6. Pokud souhlasím, automaticky se spustí další díl (s co nejpodobnějším zdrojem jako předchozí díl)

---

## Poznámky pro vývoj
- Každou funkci vyvíjet samostatně a testovat
- Priorita: vždy správné výsledky a žádná „mrtvá místa“ v aplikaci
- Ošetřit i chybové scénáře (např. chybějící zdroje, přerušené připojení, špatné přihlášení…)

---

## Podpora pluginu Up Next
- Kodíček je plně kompatibilní s [Up Next](https://kodi.wiki/view/Add-on:Up_Next) – při správném nastavení metadat funguje automatické/polautomatické přehrávání další epizody se všemi možnostmi Up Next (odpočet, popup, nastavení chování).
- Uživatelům může být doporučeno plugin Up Next nainstalovat, pokud chtějí „next episode experience“ (nebo použít vestavěné řešení Kodíčku).

---

## Sledování chyb a návrhů
Pro hlášení chyb, návrhy na vylepšení nebo diskuzi k funkcím využijte, prosím, [Issues na GitHubu](https://github.com/UZIVATEL/REPOZITAR/issues) (nahraďte odkazem na skutečný repozitář).

---

## Autor
Tvoje jméno / tým
