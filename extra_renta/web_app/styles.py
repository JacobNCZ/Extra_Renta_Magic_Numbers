"""Světlý, čistý a sjednocený vzhled Streamlit aplikace Extra Renta."""

from __future__ import annotations

import streamlit as st

APP_CSS = r"""
<style>
:root {
  --er-bg: #f4f6f9;
  --er-bg-soft: #fafbfc;
  --er-card: #ffffff;
  --er-card-soft: #f7f9fb;
  --er-ink: #202630;
  --er-muted: #6f7886;
  --er-line: #d9dfe7;
  --er-line-strong: #c7d0dc;
  --er-strong: #273142;
  --er-blue: #347ff2;
  --er-blue-soft: #eaf2ff;
  --er-good: #2f8f60;
  --er-good-soft: #eaf7ef;
  --er-warn: #a96d18;
  --er-warn-soft: #fff5e8;
  --er-danger: #bf4d4d;
  --er-danger-soft: #fdeeee;
  --er-radius: 16px;
  --er-shadow: 0 9px 26px rgba(27, 40, 66, .065);
}

html, body, [class*="css"] {
  font-family: "Aptos", "Inter", "Segoe UI", ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
  font-feature-settings: "tnum" 1, "ss01" 1;
  text-rendering: optimizeLegibility;
}
.stApp {
  background:
    radial-gradient(circle at 9% -4%, rgba(52,127,242,.075), transparent 24%),
    linear-gradient(180deg, #fafbfd 0%, var(--er-bg) 100%);
  color: var(--er-ink);
}
.block-container {
  max-width: 1480px;
  padding-top: .8rem;
  padding-bottom: 3.2rem;
}
.main h1, .main h2, .main h3 {
  color: var(--er-strong);
  letter-spacing: -.025em;
  line-height: 1.2;
}
.main h1 {font-size: clamp(2rem, 3.7vw, 2.8rem); font-weight: 820;}
.main h2 {font-size: clamp(1.38rem, 2.1vw, 1.65rem); margin-top: 1.2rem; margin-bottom: .65rem;}
.main h3 {font-size: 1.15rem; margin-top: 1rem; margin-bottom: .55rem;}
p, li, label, [data-testid="stCaptionContainer"] {color: var(--er-ink); line-height: 1.5;}
[data-testid="stCaptionContainer"] {opacity: .76; font-size: .88rem;}

/* Odstranění kotev, technických toolbarů a ikon vpravo od nadpisů/tabulek. */
[data-testid="stHeaderActionElements"],
[data-testid="stElementToolbar"],
[data-testid="stDataFrameToolbar"],
button[title="Copy link to heading"],
button[title="View fullscreen"],
a[data-testid="stAnchorLink"],
.stMarkdown h1 > a,
.stMarkdown h2 > a,
.stMarkdown h3 > a,
.stMarkdown h4 > a {display: none !important; visibility: hidden !important;}

[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #fcfdfe 0%, #f2f5f8 100%);
  border-right: 1px solid var(--er-line);
  box-shadow: 5px 0 20px rgba(27,40,66,.035);
}
[data-testid="stSidebar"] .block-container {padding-top: .95rem;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {line-height:1.42;}

[data-testid="stMetric"] {
  min-height: 104px;
  background: linear-gradient(180deg, #ffffff, #f8fafc);
  border: 1px solid var(--er-line);
  border-radius: var(--er-radius);
  padding: 14px 15px;
  box-shadow: var(--er-shadow);
}
[data-testid="stMetricLabel"] {color: var(--er-muted); font-weight: 700; font-size: .88rem;}
[data-testid="stMetricValue"] {color: var(--er-strong); font-weight: 820; letter-spacing: -.02em;}

.stButton > button,
.stDownloadButton > button {
  border: 1px solid var(--er-line-strong);
  border-radius: 12px;
  color: var(--er-strong);
  background: linear-gradient(180deg, #ffffff, #f2f5f9);
  font-weight: 720;
  box-shadow: 0 4px 12px rgba(27,40,66,.055);
  transition: transform .15s ease, box-shadow .15s ease, border-color .15s ease, background .15s ease;
}
.stButton > button:hover,
.stDownloadButton > button:hover {
  border-color: #aebbd0;
  color: var(--er-strong);
  transform: translateY(-1px);
  box-shadow: 0 7px 16px rgba(27,40,66,.075);
}
.stButton > button[kind="primary"],
[data-testid="stButton"] button[kind="primary"] {
  min-height: 3.25rem;
  border: 1px solid #bfd4f8 !important;
  color: #17376f !important;
  background: linear-gradient(180deg, #ffffff 0%, #eaf2ff 100%) !important;
  box-shadow: 0 8px 20px rgba(52,127,242,.105), inset 0 1px 0 rgba(255,255,255,.95);
  font-size: 1rem;
  font-weight: 850;
  letter-spacing: .015em;
}
.stButton > button[kind="primary"]:hover,
[data-testid="stButton"] button[kind="primary"]:hover {
  border-color: #91b9f6 !important;
  color: #103477 !important;
  background: linear-gradient(180deg,#fafdff 0%,#dceaff 100%) !important;
  box-shadow: 0 10px 22px rgba(52,127,242,.145);
}
.stButton > button[kind="primary"]:disabled,
[data-testid="stButton"] button[kind="primary"]:disabled {
  background:#f0f3f7 !important;
  color:#778297 !important;
  border-color:#d5dce6 !important;
  opacity:.92;
}

/* Počítadlo a hlavní tlačítko tvoří jeden kompaktní blok. */
[data-testid="stElementContainer"]:has(iframe[title="streamlit_components.v1.html"]) {margin-bottom: -.35rem;}
iframe[title="streamlit_components.v1.html"] {display:block; border-radius: var(--er-radius);}

[data-baseweb="tab-list"] {
  gap: .38rem;
  flex-wrap: wrap;
  background: rgba(255,255,255,.72);
  padding: .4rem;
  border: 1px solid var(--er-line);
  border-radius: var(--er-radius);
  box-shadow: 0 4px 14px rgba(27,40,66,.045);
}
[data-baseweb="tab"] {
  min-height: 42px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: 11px;
  color: var(--er-muted);
  padding: .48rem .78rem;
  font-weight: 700;
}
[data-baseweb="tab"][aria-selected="true"] {
  background: #fff;
  border-color: #d8e4f7;
  color: #17376f;
  box-shadow: 0 3px 9px rgba(52,127,242,.065);
}

[data-testid="stExpander"] {
  background: rgba(255,255,255,.84);
  border: 1px solid var(--er-line);
  border-radius: var(--er-radius);
  box-shadow: 0 4px 13px rgba(27,40,66,.035);
}
[data-testid="stDataFrame"] {
  border: 1px solid var(--er-line);
  border-radius: var(--er-radius);
  overflow: hidden;
  background: #fff;
  box-shadow: 0 5px 16px rgba(27,40,66,.045);
}
[data-testid="stAlert"] {
  border-radius: var(--er-radius);
  border: 1px solid var(--er-line);
  box-shadow: 0 4px 13px rgba(27,40,66,.035);
}
[data-testid="stHorizontalBlock"] {gap: .85rem;}
hr {border-color: var(--er-line) !important; margin: 1.25rem 0 !important;}

.er-hero {
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:1rem;
  padding: .85rem 1.05rem;
  border: 1px solid var(--er-line);
  border-radius: var(--er-radius);
  background: linear-gradient(120deg,rgba(255,255,255,.99),rgba(245,248,252,.96));
  box-shadow: var(--er-shadow);
  margin: .05rem 0 .9rem;
}
.er-hero-main {display:flex; align-items:baseline; gap:.65rem; flex-wrap:wrap;}
.er-hero-title {font-size: clamp(1.55rem, 2.5vw, 2.05rem); font-weight: 850; color: var(--er-strong); letter-spacing:-.035em;}
.er-hero-subtitle {color: var(--er-muted); font-size:.94rem; font-weight:650;}
.er-hero-badge {
  border:1px solid #d6e3f7;
  border-radius:999px;
  padding:.42rem .72rem;
  color:#244d89;
  background:#f5f9ff;
  font-size:.74rem;
  font-weight:800;
  letter-spacing:.035em;
  text-transform:uppercase;
  white-space:nowrap;
}
.er-section-label {font-size:.72rem; letter-spacing:.105em; text-transform:uppercase; color:#587fb8; font-weight:800;}
.er-card,
.er-subtle-card,
.er-preview-card,
.er-quick-card,
.er-result-card,
.er-game-card,
.er-sidebar-status,
.er-report-frame,
.er-inline-report {border-radius:var(--er-radius);}
.er-card {
  background: var(--er-card);
  border:1px solid var(--er-line);
  padding:1rem 1.05rem;
  box-shadow:var(--er-shadow);
}
.er-subtle-card {
  background:rgba(255,255,255,.82);
  border:1px solid var(--er-line);
  padding:.85rem .95rem;
}
.er-inline-grid {display:grid; grid-template-columns: repeat(auto-fit,minmax(220px,1fr)); gap:.75rem; margin:.7rem 0 .9rem;}
.er-sidebar-brand {font-size:1.45rem;font-weight:850;color:var(--er-strong);letter-spacing:-.03em;margin:.1rem 0 .05rem;}
.er-sidebar-status {
  border:1px solid var(--er-line);
  background:#fff;
  padding:.68rem .76rem;
  margin:.32rem 0 .72rem;
}
.er-sidebar-status strong {color:var(--er-strong);}
.er-sidebar-status small {color:var(--er-muted);}

.er-preview-card {
  background: linear-gradient(180deg, rgba(255,255,255,.99), rgba(248,250,253,.97));
  border: 1px solid var(--er-line);
  padding: 1rem 1.05rem;
  box-shadow: var(--er-shadow);
  min-height: 230px;
}
.er-preview-card h3 {margin: .3rem 0 .65rem; font-size: 1.22rem;}
.er-preview-card p {color: var(--er-muted); margin: .25rem 0 .65rem;}
.er-preview-empty {
  display:grid; place-items:center; min-height: 118px;
  border: 1px dashed var(--er-line-strong); border-radius: 14px;
  color: var(--er-muted); background: rgba(255,255,255,.58);
}
.er-balls-large .er-ball {width: 52px; height: 52px; font-size: 1.16rem;}
.er-preview-stats {
  display:grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap: .65rem; margin-top: .82rem;
}
.er-preview-stats > div {
  padding: .68rem .75rem; border:1px solid var(--er-line); border-radius: 14px; background: #fff;
}
.er-preview-stats span {display:block; color: var(--er-muted); font-size: .78rem; margin-bottom: .15rem;}
.er-preview-stats strong {font-size: 1rem; color: var(--er-strong);}

.er-quick-grid {display:grid; grid-template-columns: repeat(3,minmax(0,1fr)); gap:.65rem; margin-top:.72rem;}
.er-quick-card {
  background: rgba(255,255,255,.94);
  border: 1px solid var(--er-line);
  padding: .78rem .85rem;
  box-shadow: 0 5px 14px rgba(27,40,66,.04);
}
.er-quick-card strong {display:block; margin:.2rem 0 .1rem; color: var(--er-strong); font-size: 1.02rem;}
.er-quick-card small {display:block; color: var(--er-muted); font-size:.76rem;}
.er-quick-title {display:block; color:#5a7fae; font-size:.7rem; text-transform:uppercase; letter-spacing:.07em; font-weight:800;}

.er-results-grid {display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:.78rem;margin:.55rem 0 .9rem;}
.er-result-card {
  position:relative;
  background:linear-gradient(180deg,#fff,#f8f9fb);
  border:1px solid var(--er-line);
  padding:.9rem;
  box-shadow:0 6px 17px rgba(27,40,66,.05);
}
.er-result-card.is-first {
  border-color:#cfe0fa;
  box-shadow:0 8px 22px rgba(52,127,242,.095);
  background:linear-gradient(180deg,#fff,#f5f8ff);
}
.er-result-head {display:flex;justify-content:space-between;gap:.65rem;align-items:center;margin-bottom:.7rem;}
.er-rank {font-size:.74rem;font-weight:850;letter-spacing:.07em;color:var(--er-muted);text-transform:uppercase;}
.er-score-pill {border:1px solid var(--er-line);background:#fff;border-radius:999px;padding:.3rem .52rem;font-size:.75rem;font-weight:800;color:var(--er-strong);}
.er-balls {display:flex;flex-wrap:wrap;gap:.4rem;align-items:center;}
.er-ball {
  width:42px;height:42px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;
  font-size:.98rem;font-weight:900;color:#202630;border:1px solid #ced8e6;
  background:radial-gradient(circle at 32% 27%,#fff 0 15%,#f8fbff 34%,#dce9fc 70%,#b9d0f3 100%);
  box-shadow:inset 0 2px 4px rgba(255,255,255,.9),inset 0 -3px 6px rgba(27,40,66,.09),0 3px 7px rgba(27,40,66,.1);
}
.er-result-meta {display:flex;flex-wrap:wrap;gap:.45rem .85rem;margin-top:.65rem;color:var(--er-muted);font-size:.78rem;}
.er-result-meta b {color:var(--er-strong);}

.er-report-frame,
.er-inline-report {
  border:1px solid var(--er-line);
  padding:.45rem;
  background:#fff;
  box-shadow:var(--er-shadow);
  overflow:visible;
}
.er-inline-report .page {max-width:100% !important;padding:12px !important;}
.er-inline-report .card {border-radius:var(--er-radius) !important;}

@media (max-width:1100px) {.er-quick-grid{grid-template-columns:1fr;}}
@media (max-width:900px) {
  .er-hero{align-items:flex-start;}
  .er-preview-stats{grid-template-columns:1fr 1fr;}
}
@media (max-width:700px) {
  .block-container{padding:.65rem .68rem 2.6rem;}
  .er-hero{flex-direction:column;align-items:flex-start;}
  .er-results-grid{grid-template-columns:1fr;}
  .er-ball{width:39px;height:39px;font-size:.92rem;}
  .er-balls-large .er-ball{width:46px;height:46px;font-size:1.05rem;}
  .er-preview-stats{grid-template-columns:1fr;}
  [data-testid="stMetric"]{min-height:92px;}
}
@media (prefers-reduced-motion:reduce) {
  *,*::before,*::after{animation-duration:.001ms!important;animation-iteration-count:1!important;transition-duration:.001ms!important;}
}
</style>
"""


def apply_global_styles() -> None:
    st.markdown(APP_CSS, unsafe_allow_html=True)


def render_hero() -> None:
    st.markdown(
        """
        <section class="er-hero">
          <div class="er-hero-main">
            <div class="er-hero-title">Extra Renta</div>
            <div class="er-hero-subtitle">Analytický dashboard</div>
          </div>
          <div class="er-hero-badge">7 čísel z 33</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
