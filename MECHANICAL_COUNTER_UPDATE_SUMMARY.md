# Extra Renta – mechanické počítadlo a zjednodušení UI

## Hlavní změny

- Trezor byl v hlavní záložce nahrazen sedmiválcovým mechanickým počítadlem.
- Během výpočtu se všech sedm válců plynule otáčí a zobrazuje měnící se čísla 1–33.
- Po dokončení se válce postupně zastaví na skutečné kombinaci z prvního pořadí.
- Výpočetní logika, filtry, scoring ani MMR se animací nemění.
- Z levého panelu byly odstraněny:
  - maximální počet výsledků,
  - rozšířená nastavení,
  - potvrzení délky kompletního běhu.
- Maximální limit výstupu se nyní používá automaticky podle vybrané předvolby.
- V aplikaci zůstává jediné hlavní tlačítko `SPUSTIT GENEROVÁNÍ`.
- Hlavní tlačítko má tmavý vysoce kontrastní podklad, bílý text a výraznější typografii.
- Nadpisy používají elegantnější serifové písmo, běžné UI čistý systémový sans-serif.
- Aktualizace historie zobrazuje pouze název zdrojové stránky, nikoli URL nebo technické chyby jednotlivých zdrojů.
- Nově nalezené historické tahy lze porovnat s posledním dokončeným během:
  - průchod tvrdými pravidly,
  - skóre,
  - členství v kandidátním poolu,
  - členství ve finálním MMR výběru,
  - případné pořadí.
- V záložce Výsledky je doplněna samostatná kontrola vlastních kombinací.
- Pro kontrolu členství v poolu se ukládá pouze kompaktní množina čísel kombinací, nikoli celý kandidátní pool.

## Technické poznámky

- Aktivní komponenta: `extra_renta/web_app/mechanical_counter.py`
- Stavový model zůstává zpětně kompatibilní se staršími názvy session klíčů.
- Staré trezorové obrázky a nepoužívaná trezorová komponenta byly z projektu odstraněny.

## Ověření

- `73 passed`
- kompilace všech Python modulů proběhla úspěšně
- mechanické počítadlo bylo vizuálně ověřeno v Chromium pro stav generování i dokončený výsledek
