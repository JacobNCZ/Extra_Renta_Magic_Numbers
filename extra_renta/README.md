# Extra Renta

Extra Renta je Python projekt a Streamlit aplikace pro tvorbu, filtrování, skórování a diverzifikaci kandidátních kombinací **7 unikátních čísel z rozsahu 1 až 33**.

Projekt negeneruje „výherní čísla“ a netvrdí, že historická data nebo některá kombinace zvyšují matematickou pravděpodobnost výhry. Historická data slouží pouze pro analytiku, filtrování, scoring, porovnání a reporting.

## Aktuální pipeline

```text
konfigurace
→ generování všech kombinací nebo diagnostického vzorku
→ jednorázový výpočet základních metrik
→ strukturální tvrdé filtry
→ doplnění historického překryvu
→ historické filtry
→ scoring
→ kandidátní pool se score částí a diverzitní rezervou
→ deterministický MMR / marginal-gain greedy výběr
→ CSV / JSON / HTML report
```

## Maximální limit výstupu

Konfigurace používá `max_output_count`. Jde o horní mez, nikoliv o garantovaný cílový počet.

Program skončí, když:

- dosáhne maximálního limitu,
- vyčerpá kandidátní pool,
- nezůstane další kandidát splňující tvrdé portfolio limity,
- nebo marginální přínos klesne pod nastavenou mez.

Menší počet výsledků je platný výsledek. Report uvádí skutečný počet i důvod ukončení.

## MMR portfolio výběr

Finální portfolio vybírá deterministická metoda MMR / marginal-gain greedy. Každý kandidát je hodnocen podle:

- normalizovaného individuálního skóre,
- přínosu k vyváženějšímu zastoupení čísel,
- pokrytí dosud nepoužitých párů,
- nižšího opakování párů,
- a dodržení tvrdého limitu překryvu.

Všechny komponenty MMR jsou normalizované do rozsahu 0–1 a jejich váhy jsou uloženy v `MMRConfig`. Při shodě se používá deterministické pořadí, takže stejný vstup a konfigurace vedou ke stejnému výsledku.

## Jednorázový výpočet metrik

Základní metriky kombinace se počítají pouze jednou. Pokud kombinace projde strukturálními filtry, doplní se do stejného objektu pouze historický překryv a spustí se jen historické kontroly. Strukturální filtry se podruhé neopakují.

## Předvolby

Projekt obsahuje tři centrálně definované předvolby:

1. `recommended` – doporučené vyvážené nastavení,
2. `strict` – přísnější filtry a větší důraz na portfolio diverzitu,
3. `experimental_strict` – velmi přísná experimentální varianta.

Každá předvolba mění filtry, scoring, tvrdý překryv, MMR váhy a složení kandidátního poolu. Všechny používají stejnou výpočetní pipeline.

## Spuštění CLI

Kompletní běh:

```bash
python -m extra_renta.main --preset recommended --mode full
```

Diagnostický vzorek:

```bash
python -m extra_renta.main --preset recommended --mode sample --sample-size 20000 --seed 42 --no-export
```

Rychlý dry-run:

```bash
python -m extra_renta.main --preset strict --dry-run --sample-size 5000 --seed 42
```

Kontrola vlastní kombinace:

```bash
python -m extra_renta.main --preset recommended --mode sample --sample-size 10000 --no-export --check-combination "2, 8, 14, 19, 23, 27, 31"
```

Seed ovlivňuje pouze náhodný diagnostický vzorek. Kompletní běh a finální MMR výběr jsou deterministické.

## Spuštění Streamlit aplikace

Nejspolehlivější spuštění, které funguje i při jiném pracovním adresáři PyCharmu:

```bash
python start_streamlit.py
```

Na Windows lze také spustit `run_streamlit.bat`. V PyCharmu otevři kořen projektu, vyber `start_streamlit.py` a použij běžné tlačítko **Run**.

Alternativní příkaz z kořene projektu:

```bash
python -m streamlit run extra_renta/web_app/app.py
```

Webová aplikace používá kompletní průchod a MMR výběr. Uživatel v běžném rozhraní volí pouze předvolbu pravidel; maximální limit výstupu přebírá aplikace přímo z předvolby.

### Uživatelské rozhraní

- světlé industriální téma a animované sedmiválcové mechanické počítadlo,
- během výpočtu se válce otáčejí a po dokončení se zastaví na první vybrané kombinaci,
- výsledky jako loterijní kuličky,
- čitelnější interaktivní grafy,
- HTML report přímo v aplikaci,
- exporty včetně kompletního ZIP balíčku,
- automatická SQLite historie prvního pořadí každého běhu,
- porovnání vlastních i nově nalezených kombinací s pravidly, kandidátním poolem a finálním výběrem,
- disclaimer soustředěný v pravidlech a metodice.

Historie je standardně uložena v `~/.extra_renta/run_history.sqlite3`. Cestu lze změnit proměnnou prostředí `EXTRA_RENTA_HISTORY_DB`.

## Exporty

Projekt vytváří:

- CSV finálních kandidátů včetně MMR komponent,
- JSON kandidátů s individuálním skóre a marginálním přínosem,
- JSON statistik běhu,
- úplný snapshot konfigurace,
- HTML report s průchodem pipeline, filtrováním, výkonem a MMR diagnostikou,
- kompletní ZIP balíček všech exportů.

Konfigurační snapshot obsahuje `max_output_count`, kompletní `MMRConfig`, tvrdé portfolio limity, parametry kandidátního poolu a verzi výběrového algoritmu.

## Testy

```bash
pytest -q
```

Testy kontrolují mimo jiné:

- invarianty kombinací,
- tvrdé filtry a scoring,
- historickou validaci,
- jednorázový výpočet základních metrik,
- determinismus MMR,
- tvrdý limit překryvu,
- maximální limit výstupu,
- CLI, webovou servisní vrstvu a exporty,
- SQLite historii prvních míst,
- mechanické počítadlo, kompaktní snapshot kandidátního poolu a skryté výchozí limity webového běhu.

## Hlavní struktura

```text
extra_renta/
├── core/
│   ├── combination_generator.py
│   ├── statistics.py
│   ├── filters.py
│   ├── scoring.py
│   ├── mmr_selector.py
│   └── config_models.py
├── candidate_pool.py
├── selection_pipeline.py
├── pipeline.py
├── presets.py
├── output/
├── history_update/
├── web_app/
│   ├── assets/
│   ├── run_history.py
│   └── run_history_components.py
└── tests/
```
