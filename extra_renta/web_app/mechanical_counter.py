"""Světlé minimalistické sedmiválcové počítadlo pro generování kombinací."""

from __future__ import annotations

from html import escape

from extra_renta.web_app.vault_state import CLOSED, ERROR, GENERATING, OPEN

_STATE_LABELS = {
    CLOSED: "PŘIPRAVENO",
    GENERATING: "GENEROVÁNÍ KOMBINACÍ…",
    OPEN: "VÝSLEDEK JE PŘIPRAVEN",
    ERROR: "BĚH PŘERUŠEN",
}


def _normalise_numbers(numbers: tuple[int, ...] | list[int] | None) -> tuple[int | None, ...]:
    if numbers is None or len(numbers) != 7:
        return (None,) * 7
    return tuple(int(number) for number in numbers)


def _static_reel(number: int | None, index: int, *, state: str) -> str:
    if number is None:
        return f"""
        <div class="mc-reel mc-reel-{index} is-empty">
          <div class="mc-static-row mc-muted">—</div>
          <div class="mc-static-row mc-current">—</div>
          <div class="mc-static-row mc-muted">—</div>
        </div>
        """

    previous_number = 33 if number == 1 else number - 1
    next_number = 1 if number == 33 else number + 1
    delay = index * 0.085 if state == OPEN else 0
    return f"""
    <div class="mc-reel mc-reel-{index} is-final" style="--settle-delay:{delay:.3f}s">
      <div class="mc-static-row mc-muted">{previous_number:02d}</div>
      <div class="mc-static-row mc-current">{number:02d}</div>
      <div class="mc-static-row mc-muted">{next_number:02d}</div>
    </div>
    """


def _spinning_reel(index: int) -> str:
    values = list(range(1, 34)) + list(range(1, 34))
    rows = "".join(f'<div class="mc-spin-row">{number:02d}</div>' for number in values)
    duration = 1.65 + index * 0.105
    delay = index * -0.11
    return f"""
    <div class="mc-reel mc-reel-{index} is-spinning" style="--spin-duration:{duration:.3f}s;--spin-delay:{delay:.3f}s">
      <div class="mc-strip">{rows}</div>
    </div>
    """


def build_counter_html(
    state: str,
    message: str,
    *,
    final_numbers: tuple[int, ...] | list[int] | None = None,
    result_count: int | None = None,
) -> str:
    """Vrátí samostatný HTML dokument počítadla pro Streamlit iframe."""
    safe_state = state if state in _STATE_LABELS else CLOSED
    numbers = _normalise_numbers(final_numbers)
    if safe_state == GENERATING:
        reels = "".join(_spinning_reel(index) for index in range(7))
    else:
        reels = "".join(
            _static_reel(number, index, state=safe_state)
            for index, number in enumerate(numbers)
        )

    count_text = ""
    if safe_state == OPEN and result_count is not None:
        count_text = f" · {int(result_count):,} vybraných kombinací".replace(",", " ")

    aria_numbers = ", ".join(str(number) for number in numbers if number is not None)
    aria = (
        f"Mechanické počítadlo, stav {_STATE_LABELS[safe_state]}. "
        + (f"První kombinace: {aria_numbers}." if aria_numbers else escape(message))
    )
    progress_width = {
        CLOSED: 0,
        GENERATING: 74,
        OPEN: 100,
        ERROR: 100,
    }.get(safe_state, 0)

    return f"""
<!doctype html>
<html lang="cs">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root {{
  --surface:#f8fafc;
  --surface-soft:#eef2f7;
  --surface-deep:#e5eaf1;
  --frame:#d0d7e1;
  --frame-dark:#b9c2ce;
  --ink:#202630;
  --muted:#9ca6b3;
  --blue:#347ff2;
  --blue-soft:#e8f1ff;
  --shadow:0 14px 32px rgba(35,49,75,.11);
}}
* {{box-sizing:border-box}}
html,body {{margin:0;background:transparent;font-family:"Aptos","Inter","Segoe UI",system-ui,sans-serif;}}
body {{padding:0;}}
.mc-shell {{
  width:100%;
  padding:12px;
  border:1px solid var(--frame);
  border-radius:18px;
  background:linear-gradient(180deg,#ffffff 0%,#f2f5f9 100%);
  box-shadow:var(--shadow), inset 0 1px 0 rgba(255,255,255,.96);
}}
.mc-window {{
  position:relative;
  padding:8px;
  border:1px solid var(--frame-dark);
  border-radius:15px;
  overflow:hidden;
  background:linear-gradient(180deg,#e9edf3 0%,#f4f6f9 49%,#e7ebf1 100%);
  box-shadow:inset 0 3px 9px rgba(54,69,94,.11), inset 0 -1px 0 rgba(255,255,255,.92);
}}
.mc-window::after {{
  content:"";
  position:absolute;
  left:8px; right:8px; top:50%;
  height:54px;
  transform:translateY(-50%);
  border-top:1px solid rgba(163,174,188,.48);
  border-bottom:1px solid rgba(163,174,188,.48);
  pointer-events:none;
  z-index:5;
  box-shadow:inset 0 1px 0 rgba(255,255,255,.85);
}}
.mc-machine {{display:grid;grid-template-columns:repeat(7,minmax(0,1fr));gap:5px;}}
.mc-reel {{
  position:relative;
  height:162px;
  overflow:hidden;
  border:1px solid #c8d0da;
  border-radius:11px;
  background:linear-gradient(90deg,#e5e9ef 0%,#f7f9fb 16%,#ffffff 50%,#f5f7fa 84%,#e1e6ed 100%);
  box-shadow:inset 2px 0 5px rgba(52,65,86,.07), inset -2px 0 5px rgba(52,65,86,.07);
}}
.mc-reel::before,.mc-reel::after {{
  content:"";
  position:absolute;
  left:0;right:0;
  height:43px;
  z-index:4;
  pointer-events:none;
}}
.mc-reel::before {{top:0;background:linear-gradient(#e9edf2 4%,rgba(233,237,242,.62),transparent);}}
.mc-reel::after {{bottom:0;background:linear-gradient(transparent,rgba(226,231,237,.62),#e2e7ed 96%);}}
.mc-static-row,.mc-spin-row {{
  height:54px;
  display:grid;
  place-items:center;
  font-family:"Aptos Display","Arial Narrow","Segoe UI",sans-serif;
  font-variant-numeric:tabular-nums;
  font-weight:750;
  letter-spacing:-.045em;
}}
.mc-current {{
  color:var(--ink);
  font-size:clamp(38px,4vw,56px);
  background:linear-gradient(90deg,#edf0f4,#ffffff 22%,#ffffff 78%,#edf0f4);
  text-shadow:0 1px 0 rgba(255,255,255,.92);
}}
.mc-muted {{color:var(--muted);font-size:clamp(22px,2.45vw,31px);font-weight:620;}}
.mc-strip {{
  animation:mcSpin var(--spin-duration) linear infinite;
  animation-delay:var(--spin-delay);
  will-change:transform;
  filter:blur(.22px);
}}
.mc-spin-row {{
  color:#677282;
  font-size:clamp(34px,3.65vw,51px);
  background:linear-gradient(90deg,#e9edf2,#f9fafc 22%,#ffffff 50%,#f8fafc 78%,#e8ecf2);
  border-bottom:1px solid rgba(203,211,221,.58);
}}
.is-final {{animation:mcSettle .52s cubic-bezier(.2,.76,.25,1) both;animation-delay:var(--settle-delay);}}
.is-final .mc-current {{animation:mcFocus .95s ease-out both;animation-delay:calc(var(--settle-delay) + .12s);}}
.mc-status {{
  display:grid;
  grid-template-columns:auto minmax(0,1fr);
  gap:11px;
  align-items:center;
  margin-top:9px;
  padding:8px 10px 2px;
}}
.mc-loader {{
  width:27px;height:27px;border-radius:50%;
  border:3px dotted #75a8f9;
  animation:mcRotate 1.1s linear infinite;
}}
.state-closed .mc-loader,.state-open .mc-loader,.state-error .mc-loader {{
  animation:none;
  border-style:solid;
  border-color:#d2d9e3;
  opacity:.78;
}}
.mc-status-copy {{min-width:0;}}
.mc-status-title {{
  color:var(--ink);
  font-size:13px;
  line-height:1.2;
  font-weight:820;
  letter-spacing:.035em;
  text-transform:uppercase;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}}
.mc-status-message {{
  margin-top:2px;
  color:#737e8d;
  font-size:11px;
  line-height:1.25;
  white-space:nowrap;
  overflow:hidden;
  text-overflow:ellipsis;
}}
.mc-progress {{
  grid-column:1/-1;
  height:7px;
  margin-top:3px;
  overflow:hidden;
  border-radius:999px;
  background:#e1e6ed;
}}
.mc-progress-fill {{
  height:100%;width:{progress_width}%;border-radius:inherit;
  background:linear-gradient(90deg,#79aefb,#347ff2);
  transition:width .4s ease;
  box-shadow:0 0 10px rgba(52,127,242,.22);
}}
.state-generating .mc-progress-fill {{animation:mcPulse 1.25s ease-in-out infinite;}}
.state-error .mc-progress-fill {{background:linear-gradient(90deg,#ef9a93,#d9534f);box-shadow:none;}}
.state-error .mc-status-title {{color:#9e4440;}}
@keyframes mcSpin {{from{{transform:translateY(-108px)}}to{{transform:translateY(-1890px)}}}}
@keyframes mcSettle {{0%{{transform:translateY(-9px);opacity:.45;filter:blur(1.3px)}}100%{{transform:translateY(0);opacity:1;filter:blur(0)}}}}
@keyframes mcFocus {{0%{{background:#fff}}45%{{background:var(--blue-soft)}}100%{{background:linear-gradient(90deg,#edf0f4,#fff 22%,#fff 78%,#edf0f4)}}}}
@keyframes mcRotate {{to{{transform:rotate(360deg)}}}}
@keyframes mcPulse {{50%{{opacity:.68}}}}
@media(max-width:760px){{
  .mc-shell{{padding:8px;border-radius:15px;}}
  .mc-window{{padding:5px;border-radius:12px;}}
  .mc-machine{{gap:3px;}}
  .mc-reel{{height:135px;border-radius:8px;}}
  .mc-static-row,.mc-spin-row{{height:45px;}}
  .mc-current{{font-size:clamp(29px,7vw,42px);}}
  .mc-muted{{font-size:clamp(18px,4.6vw,25px);}}
  .mc-spin-row{{font-size:clamp(27px,6.5vw,38px);}}
  .mc-window::after{{height:45px;left:5px;right:5px;}}
  .mc-status{{gap:8px;margin-top:6px;padding:7px 7px 1px;}}
  .mc-loader{{width:23px;height:23px;}}
  .mc-status-title{{font-size:11px;}}
  .mc-status-message{{font-size:10px;}}
}}
@media(prefers-reduced-motion:reduce){{
  .mc-strip{{animation-duration:4s}}
  .is-final,.is-final .mc-current,.mc-loader,.mc-progress-fill{{animation:none!important}}
}}
</style>
</head>
<body>
<div class="mc-shell state-{safe_state}" role="img" aria-label="{escape(aria)}">
  <div class="mc-window">
    <div class="mc-machine">{reels}</div>
  </div>
  <div class="mc-status">
    <div class="mc-loader" aria-hidden="true"></div>
    <div class="mc-status-copy">
      <div class="mc-status-title">{_STATE_LABELS[safe_state]}{count_text}</div>
      <div class="mc-status-message">{escape(message)}</div>
    </div>
    <div class="mc-progress"><div class="mc-progress-fill"></div></div>
  </div>
</div>
</body>
</html>
"""


def render_mechanical_counter(
    state: str,
    message: str,
    *,
    final_numbers: tuple[int, ...] | list[int] | None = None,
    result_count: int | None = None,
) -> None:
    """Vykreslí mechanické počítadlo jako lokální HTML komponentu."""
    import streamlit.components.v1 as components

    components.html(
        build_counter_html(
            state,
            message,
            final_numbers=final_numbers,
            result_count=result_count,
        ),
        height=275,
        scrolling=False,
    )
