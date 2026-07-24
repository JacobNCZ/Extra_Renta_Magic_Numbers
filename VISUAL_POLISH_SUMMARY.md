# Extra Renta – finální vizuální polishing

## Provedené úpravy

- z první stránky byl odstraněn blok se základními informacemi o hře a čase losování,
- hlavní stránka byla zjednodušena na počítadlo, tlačítko, náhled výsledku a hlavní metriky,
- mechanické počítadlo bylo graficky přepracováno:
  - jemnější světlý rám,
  - realističtější válce,
  - výraznější prostřední pozice,
  - decentní stíny a přechody,
  - kompaktní stavový řádek a progress bar,
  - nižší výška komponenty,
- tlačítko `Spustit generování` bylo posunuto blíže k počítadlu,
- výsledkové karty již nemají pravostranný technický štítek; skóre je součástí spodního přehledu,
- z výchozího zobrazení výsledků byl odstraněn rozsáhlý technický detail kombinací,
- byly skryty kotevní ikony nadpisů a technické toolbary tabulek,
- byla sjednocena typografie, velikosti nadpisů, spacing, stíny a zaoblení,
- HTML report má při vložení do stránky vlastní scoped CSS a neovlivňuje zbytek Streamlit rozhraní.

## Ověření

- `73 passed`
- všechny upravené Python moduly se úspěšně zkompilovaly
