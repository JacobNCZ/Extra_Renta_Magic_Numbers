"""Textové vysvětlivky pro Streamlit web Extra Renta.

Modul neobsahuje žádnou výpočetní logiku. Slouží pouze jako centrální místo
pro texty, které uživateli vysvětlují pravidla, skóre a pevný režim běhu.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExplanationBlock:
    """Jeden rozbalovací vysvětlovací blok ve webové aplikaci."""

    title: str
    short: str
    detail: str


FIXED_RUN_TITLE = "Kompletní běh + MMR finální výběr"

FIXED_RUN_SUMMARY = (
    "Aplikace má ve webové verzi jeden pevný režim: nejdříve projde kompletní "
    "kombinační prostor všech 7číselných kombinací z rozsahu 1–33, potom aplikuje "
    "tvrdé filtry a scoring, vytvoří omezený kandidátní pool nejlépe skórovaných "
    "kombinací a až na konci použije deterministický MMR / marginal-gain greedy výběr."
)

PROCESS_STEPS: tuple[tuple[str, str], ...] = (
    (
        "1. Kompletní průchod",
        "Program projde celý prostor 4 272 048 možných kombinací bez náhodného zúžení vstupu.",
    ),
    (
        "2. Tvrdé filtry",
        "Každá kombinace musí projít pravidly typu součet, sudá/lichá, rozložení, sousednosti a historický překryv.",
    ),
    (
        "3. Scoring",
        "Přeživší kombinace získají interní skóre podle vyváženosti a shody s nastavenou předvolbou.",
    ),
    (
        "4. Kandidátní pool",
        "Do další fáze postupuje omezený počet nejlépe skórovaných kandidátů podle konfigurace předvolby. Tento limit chrání výkon a přehlednost finální optimalizace.",
    ),
    (
        "5. MMR finální výběr",
        "MMR hodnotí individuální skóre i marginální přínos kandidáta pro rovnoměrnost čísel, pokrytí párů a diverzitu portfolia.",
    ),
    (
        "6. Export a vysvětlení",
        "Výsledek se zobrazí v tabulce, grafech a lze ho stáhnout jako CSV, JSON nebo HTML report.",
    ),
)

SCORE_EXPLANATION = ExplanationBlock(
    title="Co znamená skóre?",
    short="Skóre je interní hodnocení shody s pravidly, ne pravděpodobnost výhry.",
    detail=(
        "Vyšší skóre znamená pouze to, že kombinace lépe odpovídá nastaveným filtrům "
        "a měkkým scoringovým pravidlům. Skóre může zohlednit například součet, poměr "
        "sudých a lichých čísel, rozložení v rozsahu 1–33, mezery mezi čísly, sousednosti, "
        "koncovky a podobnost s historickými tahy. Skóre nikdy neznamená, že kombinace "
        "má vyšší matematickou pravděpodobnost výhry."
    ),
)

RULE_EXPLANATIONS: tuple[ExplanationBlock, ...] = (
    ExplanationBlock(
        title="Součet čísel",
        short="Omezuje extrémně nízké nebo extrémně vysoké součty.",
        detail=(
            "Součet všech sedmi čísel musí být v rozmezí nastaveném předvolbou. "
            "Například kombinace [1, 2, 3, 4, 5, 6, 7] má velmi nízký součet, zatímco "
            "[27, 28, 29, 30, 31, 32, 33] velmi vysoký. Filtr neslibuje vyšší šanci, "
            "pouze omezuje výrazné extrémy."
        ),
    ),
    ExplanationBlock(
        title="Sudá / lichá čísla",
        short="Hlídá poměr sudých a lichých čísel v kombinaci.",
        detail=(
            "Předvolby povolují jen určité počty lichých čísel, například 3 nebo 4. "
            "Cílem je omezit jednostranné kombinace typu 7 sudých / 0 lichých nebo "
            "0 sudých / 7 lichých. Jde o strukturální filtr, ne predikci losování."
        ),
    ),
    ExplanationBlock(
        title="Nízká / vysoká čísla",
        short="Kontroluje, zda kombinace není složená téměř jen z nízkých nebo vysokých čísel.",
        detail=(
            "Rozsah 1–33 je rozdělen na nízkou a vysokou část. Filtr hlídá, kolik čísel "
            "spadá do nízkého rozsahu. Tím omezuje kombinace, které jsou příliš nahromaděné "
            "jen na začátku nebo jen na konci číselného rozsahu."
        ),
    ),
    ExplanationBlock(
        title="Rozložení do pásem",
        short="Sleduje pokrytí nízkého, středního a vysokého pásma.",
        detail=(
            "Čísla se dělí do širších pásem, například 1–11, 12–22 a 23–33. Pravidlo "
            "omezuje kombinace, které leží téměř celé jen v jednom pásmu. Výsledkem je "
            "pestřejší prostor kandidátů."
        ),
    ),
    ExplanationBlock(
        title="Rozložení do jemnějších bucketů",
        short="Hlídá shlukování čísel v užších intervalech.",
        detail=(
            "Vedle širokých pásem se používají i jemnější intervaly, například 1–9, "
            "10–19, 20–29 a 30–33. Pravidlo pomáhá odhalit kombinace, které jsou příliš "
            "nahuštěné v jedné části rozsahu."
        ),
    ),
    ExplanationBlock(
        title="Rozpětí kombinace",
        short="Kontroluje rozdíl mezi nejnižším a nejvyšším číslem.",
        detail=(
            "Rozpětí je rozdíl mezi nejvyšším a nejnižším číslem v kombinaci. Příliš malé "
            "rozpětí značí shluk čísel v úzkém úseku, příliš velké rozpětí může být podle "
            "předvolby také omezené."
        ),
    ),
    ExplanationBlock(
        title="Mezery mezi čísly",
        short="Sleduje vzdálenosti mezi sousedními čísly po seřazení.",
        detail=(
            "Po seřazení kombinace program počítá mezery mezi čísly. Může omezovat extrémně "
            "velkou mezeru nebo penalizovat příliš pravidelné a mechanicky vypadající vzory."
        ),
    ),
    ExplanationBlock(
        title="Sousední čísla a sekvence",
        short="Omezuje příliš mnoho po sobě jdoucích čísel.",
        detail=(
            "Kombinace jako [8, 9, 10, 11, 12, 13, 14] obsahuje mnoho sousedností a dlouhou "
            "souvislou sekvenci. Takové vzory nejsou nemožné, ale předvolby je mohou omezovat "
            "kvůli lepší diverzitě kandidátů."
        ),
    ),
    ExplanationBlock(
        title="Koncovky čísel",
        short="Kontroluje opakování stejné poslední číslice.",
        detail=(
            "Pravidlo sleduje, zda se v kombinaci neopakuje příliš mnoho čísel se stejnou "
            "koncovkou, například 3, 13, 23 a 33. Cílem je omezit jednoduché vizuální vzory."
        ),
    ),
    ExplanationBlock(
        title="Historický překryv",
        short="Porovnává kandidáta s historickými tahy pouze jako kontrolu podobnosti.",
        detail=(
            "Historický překryv není predikce. Program nepředpokládá, že minulá čísla "
            "ovlivňují budoucí losování. Používá se jen k tomu, aby kandidátní kombinace "
            "nebyly příliš podobné dřívějším tahům."
        ),
    ),
    ExplanationBlock(
        title="Kandidátní pool",
        short="Omezený seznam nejlépe skórovaných kombinací pro finální výběr.",
        detail=(
            "Program projde celý kombinační prostor, ale pro závěrečný MMR výběr si neponechává "
            "neomezený seznam všech kombinací, které kdy prošly filtry. Podle předvolby udržuje kandidátní pool "
            "kombinací složený z top-score části a deterministické diverzitní rezervy. Tento limit nemění fakt, "
            "že vstupní prostor byl kompletně posouzen; pouze omezuje velikost seznamu, se kterým pracuje finální optimalizace."
        ),
    ),
    ExplanationBlock(
        title="Diverzifikace finální sady",
        short="Hlídá, aby finální kombinace nebyly příliš podobné jedna druhé.",
        detail=(
            "Dvě kombinace, které se liší jen jedním číslem, jsou pro finální výstup velmi "
            "podobné. Diverzifikace proto omezuje překryv mezi finálními kombinacemi a podle "
            "předvolby může sledovat i opakování párů nebo trojic čísel."
        ),
    ),
    ExplanationBlock(
        title="MMR / marginal-gain greedy",
        short="MMR vybírá každou další kombinaci podle jejího přínosu pro celé portfolio.",
        detail=(
            "MMR kombinuje normalizované individuální skóre s vyvážeností četností čísel, "
            "pokrytím dosud nepoužitých párů a penalizací opakování. Výběr je deterministický "
            "a maximální počet výsledků je pouze horní limit, nikoli povinný cíl."
        ),
    ),
)
