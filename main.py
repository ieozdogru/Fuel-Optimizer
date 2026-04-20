import re

import matplotlib.colors as mcolors
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from pandas.io.formats.style import Styler

from baselines import crisp_recommend
from diagnostics import (
    compare_inference_modes,
    default_axes,
    grid_statistics,
    score_grid,
)
from engine_configs import ENGINE_CONFIGS
from fuzzy_engine import FuzzyEngine, INFERENCE_MAMDANI, INFERENCE_SUGENO
from trajectory import evaluate_trajectory, synthetic_mixed_cycle, trajectory_summary

# --- Pages (navbar replaces st.tabs) ---
NAV_ITEMS = [
    ("Dashboard", "🎯"),
    ("Diagnostics", "🗺️"),
    ("Compare", "⚖️"),
    ("Trajectory", "📈"),
]

# Dashboard: fixed table height (px) so IF + rule tables fit one viewport with internal scroll.
DASHBOARD_TABLE_HEIGHT = 220


def _theme_dark() -> dict:
    return {
        "mode": "dark",
        "app_bg": "#050508",
        "grid": "rgba(255,255,255,0.04)",
        "glow1": "rgba(99,102,241,0.22)",
        "glow2": "rgba(168,85,247,0.18)",
        "panel": "rgba(12,14,22,0.94)",
        "panel_soft": "rgba(18,21,32,0.88)",
        "border": "rgba(255,255,255,0.09)",
        "text": "#fafafa",
        "muted": "#a1a1aa",
        "accent": "#818cf8",
        "accent2": "#c084fc",
        "neon": "#4ade80",
        "neon_glow": "rgba(74,222,128,0.45)",
        "grad_cta": "linear-gradient(92deg, #2563eb 0%, #7c3aed 55%, #a855f7 100%)",
        "grad_nav_on": "linear-gradient(120deg, rgba(37,99,235,0.45), rgba(124,58,237,0.45))",
        "header_bg": "rgba(5,5,8,0.82)",
        "tab_rail": "rgba(16,18,28,0.92)",
        "metric_bg": "linear-gradient(165deg, rgba(22,25,40,0.98), rgba(12,14,22,0.9))",
        "plot_paper": "rgba(5,5,8,0)",
        "plot_bg": "#0c0e14",
        "plot_grid": "rgba(161,161,170,0.16)",
        "warn": "#fbbf24",
        "danger": "#fb7185",
        "success": "#4ade80",
        "heatmap_lo": "#0a0a0f",
        "heatmap_hi": "#fef9c3",
    }


def _theme_light() -> dict:
    return {
        "mode": "light",
        "app_bg": "#f4f4f5",
        "grid": "rgba(24,24,27,0.06)",
        "glow1": "rgba(79,70,229,0.12)",
        "glow2": "rgba(168,85,247,0.1)",
        "panel": "rgba(255,255,255,0.92)",
        "panel_soft": "#ffffff",
        "border": "rgba(24,24,27,0.08)",
        "text": "#18181b",
        "muted": "#52525b",
        "accent": "#4f46e5",
        "accent2": "#9333ea",
        "neon": "#16a34a",
        "neon_glow": "rgba(22,163,74,0.35)",
        "grad_cta": "linear-gradient(92deg, #4f46e5 0%, #7c3aed 100%)",
        "grad_nav_on": "linear-gradient(120deg, rgba(79,70,229,0.2), rgba(147,51,234,0.2))",
        "header_bg": "rgba(244,244,245,0.88)",
        "tab_rail": "rgba(255,255,255,0.95)",
        "metric_bg": "linear-gradient(165deg, #ffffff, #f4f4f5)",
        "plot_paper": "rgba(255,255,255,0)",
        "plot_bg": "#fafafa",
        "plot_grid": "rgba(82,82,91,0.2)",
        "warn": "#d97706",
        "danger": "#e11d48",
        "success": "#16a34a",
        "heatmap_lo": "#f8fafc",
        "heatmap_hi": "#312e81",
    }


def _tokens() -> dict:
    return _theme_dark() if st.session_state.get("theme", "dark") == "dark" else _theme_light()


def _themed_df(df: pd.DataFrame, t: dict) -> pd.DataFrame | Styler:
    """Light mode: plain frame. Dark mode: Styler so Glide picks up cell/header colors (not from CSS vars)."""
    if t["mode"] != "dark":
        return df
    bg0 = t["plot_bg"]
    bg1 = "#151924"
    fg = t["text"]
    th_bg = "#181c2a"
    th_fg = t["muted"]
    bdr = "rgba(255,255,255,0.1)"

    def _row_style(row: pd.Series) -> list[str]:
        stripe = hash(row.name) % 2
        row_bg = bg0 if stripe == 0 else bg1
        return [f"background-color: {row_bg}; color: {fg}"] * len(row)

    return (
        df.style.set_table_styles(
            [
                {
                    "selector": "thead th",
                    "props": [
                        ("background-color", th_bg),
                        ("color", th_fg),
                        ("font-weight", "600"),
                        ("border-bottom", f"1px solid {bdr}"),
                    ],
                },
            ],
            overwrite=False,
        ).apply(_row_style, axis=1)
    )


def _init_session() -> None:
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
    if "page" not in st.session_state:
        st.session_state.page = 0
    if "ui_dark" not in st.session_state:
        st.session_state.ui_dark = st.session_state.theme == "dark"


def _sync_theme_from_toggle() -> None:
    """Align ``theme`` with the navbar toggle each run (no ``on_change`` — callbacks run before ``main()``)."""
    if "ui_dark" in st.session_state:
        st.session_state.theme = "dark" if st.session_state.ui_dark else "light"


def _render_theme_switch() -> None:
    """Toggle in navbar (Streamlit ``toggle`` if available, else checkbox)."""
    if hasattr(st, "toggle"):
        st.toggle(
            "Koyu",
            key="ui_dark",
            help="Koyu / açık arayüz",
        )
    else:
        st.checkbox(
            "Koyu",
            key="ui_dark",
            help="Koyu / açık arayüz",
        )


st.set_page_config(
    page_title="Fuel Optimizer",
    page_icon="🏎️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def inject_custom_css(t: dict) -> None:
    is_dark = t["mode"] == "dark"
    # Toggle label: match primary text in dark mode (nested ``p`` from Streamlit kept config.toml dark textColor).
    switch_label = t["text"] if is_dark else t["muted"]
    dataframe_shell = ""
    if is_dark:
        dataframe_shell = f"""
  color-scheme: dark;
  background-color: {t["plot_bg"]} !important;
"""
    grid_css = (
        f"repeating-linear-gradient(90deg, transparent 0 47px, {t['grid']} 47px 48px), "
        if is_dark
        else f"repeating-linear-gradient(90deg, transparent 0 55px, {t['grid']} 55px 56px), "
    )
    st.markdown(
        f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{
  font-family: "Inter", system-ui, sans-serif;
}}

[data-testid="stAppViewContainer"] {{
  background-color: {t["app_bg"]} !important;
  background-image:
    radial-gradient(1000px 520px at 8% -8%, {t["glow1"]}, transparent 55%),
    radial-gradient(800px 480px at 96% 4%, {t["glow2"]}, transparent 48%),
    {grid_css}
    linear-gradient(180deg, {t["app_bg"]} 0%, {t["app_bg"]} 100%) !important;
}}

[data-testid="stHeader"] {{
  background: {t["header_bg"]} !important;
  backdrop-filter: blur(14px);
  border-bottom: 1px solid {t["border"]};
}}

/* Main scroll area starts under the fixed Streamlit header; extra room for our nav row. */
[data-testid="stMain"] .block-container {{
  padding-top: clamp(4.5rem, 5rem + 2vw, 6.25rem) !important;
  max-width: 1180px !important;
}}

/*
 * config.toml uses base="light" so Streamlit keeps light textColor while we paint a dark shell.
 * Set app + widget chrome to theme tokens so dark mode stays readable.
 */
.stApp {{
  color: {t["text"]};
}}

[data-testid="stCaption"] {{
  color: {t["muted"]};
}}

[data-testid="stMarkdownContainer"] h1,
[data-testid="stMarkdownContainer"] h2,
[data-testid="stMarkdownContainer"] h3 {{
  color: {t["text"]};
}}

[data-testid="stSelectbox"] [data-baseweb="select"] > div,
[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
  color: {t["text"]} !important;
  background-color: {t["panel_soft"]} !important;
  border-color: {t["border"]} !important;
}}

/* Select / multiselect dropdown (BaseWeb menu is often portaled to ``body``). */
div[data-baseweb="popover"],
div[data-baseweb="popover"] > div,
ul[data-baseweb="menu"],
[data-baseweb="menu"] {{
  background-color: {t["panel"]} !important;
  color: {t["text"]} !important;
  {"color-scheme: dark;" if is_dark else "color-scheme: light;"}
}}
div[data-baseweb="popover"] li,
div[data-baseweb="popover"] [role="option"],
ul[data-baseweb="menu"] li,
[data-baseweb="menu"] li,
[data-baseweb="menu"] [role="option"] {{
  color: {t["text"]} !important;
  background-color: transparent !important;
}}
div[data-baseweb="popover"] li[aria-selected="true"],
[data-baseweb="menu"] li[aria-selected="true"],
[data-baseweb="menu"] [aria-selected="true"] {{
  background-color: {t["panel_soft"]} !important;
  color: {t["text"]} !important;
}}
ul[role="listbox"] {{
  background-color: {t["panel"]} !important;
}}
ul[role="listbox"] li {{
  color: {t["text"]} !important;
}}

[data-testid="stRadio"] div[role="radiogroup"] label,
[data-testid="stRadio"] div[role="radiogroup"] label p {{
  color: {t["text"]} !important;
}}

hr {{
  border-color: {t["border"]} !important;
  opacity: 1;
}}

/* --- Top nav (segmented control): Streamlit buttons no longer expose kind= in DOM --- */
[data-testid="stButtonGroup"] [role="radiogroup"] {{
  background: {t["tab_rail"]};
  border: 1px solid {t["border"]};
  border-radius: 999px;
  padding: 0.3rem 0.4rem;
  gap: 0.25rem;
  box-shadow: 0 8px 28px rgba(0,0,0,{"0.35" if is_dark else "0.08"});
}}
[data-testid="stButtonGroup"] [role="radiogroup"] button {{
  border-radius: 999px !important;
  font-weight: 600 !important;
  font-size: 0.82rem !important;
  background: transparent !important;
  background-image: none !important;
  color: {t["muted"]} !important;
  border: 1px solid transparent !important;
  box-shadow: none !important;
  opacity: {"0.82" if is_dark else "0.88"};
}}
[data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] {{
  background-image: {t["grad_nav_on"]} !important;
  background-color: {"rgba(30,27,75,0.55)" if is_dark else "rgba(238,242,255,0.95)"} !important;
  color: {t["text"]} !important;
  border: {"1px solid rgba(165,180,252,0.75)" if is_dark else "1px solid rgba(79,70,229,0.45)"} !important;
  box-shadow:
    0 0 0 2px {"rgba(129,140,248,0.45)" if is_dark else "rgba(79,70,229,0.22)"},
    0 4px 18px {"rgba(99,102,241,0.35)" if is_dark else "rgba(79,70,229,0.18)"} !important;
  font-weight: 800 !important;
  opacity: 1 !important;
  z-index: 1;
}}
[data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] p,
[data-testid="stButtonGroup"] [role="radiogroup"] button[aria-checked="true"] span {{
  color: {t["text"]} !important;
}}

/* --- Theme toggle (switch or checkbox in navbar) --- */
[data-testid="stSwitch"] label,
[data-testid="stSwitch"] label p,
[data-testid="stSwitch"] label span,
[data-testid="stCheckbox"] label,
[data-testid="stCheckbox"] label p,
[data-testid="stCheckbox"] label span {{
  color: {switch_label} !important;
  font-size: 0.78rem !important;
  font-weight: 600 !important;
}}
[data-testid="stSwitch"],
[data-testid="stCheckbox"] {{
  margin-top: 4px;
}}

/* --- Section tabs (if any nested) --- */
div[data-testid="stTabs"] [data-baseweb="tab-list"] {{
  gap: 0.35rem;
  background: {t["tab_rail"]};
  border: 1px solid {t["border"]};
  border-radius: 999px;
  padding: 0.35rem 0.45rem;
  box-shadow: 0 8px 28px rgba(0,0,0,{"0.35" if is_dark else "0.08"});
}}
div[data-testid="stTabs"] [data-baseweb="tab"] {{
  border-radius: 999px !important;
  padding: 0.5rem 1rem !important;
  font-weight: 600 !important;
  font-size: 0.88rem !important;
  color: {t["muted"]} !important;
  border: 1px solid transparent !important;
  opacity: {"0.82" if is_dark else "0.88"};
}}
div[data-testid="stTabs"] [aria-selected="true"] {{
  background: {t["grad_nav_on"]} !important;
  background-color: {"rgba(30,27,75,0.55)" if is_dark else "rgba(238,242,255,0.95)"} !important;
  color: {t["text"]} !important;
  border: {"1px solid rgba(165,180,252,0.75)" if is_dark else "1px solid rgba(79,70,229,0.45)"} !important;
  box-shadow:
    0 0 0 2px {"rgba(129,140,248,0.45)" if is_dark else "rgba(79,70,229,0.22)"},
    0 4px 18px {"rgba(99,102,241,0.35)" if is_dark else "rgba(79,70,229,0.18)"} !important;
  font-weight: 800 !important;
  opacity: 1 !important;
}}
div[data-testid="stTabs"] [aria-selected="true"] p,
div[data-testid="stTabs"] [aria-selected="true"] span {{
  color: {t["text"]} !important;
}}

/* Metrics */
[data-testid="stMetric"] {{
  background: {t["metric_bg"]};
  border: 1px solid {t["border"]};
  border-radius: 16px;
  padding: 0.85rem 1rem !important;
}}
[data-testid="stMetric"] label {{ color: {t["muted"]} !important; }}
[data-testid="stMetric"] [data-testid="stMetricValue"] {{
  color: {t["text"]} !important;
  font-family: "JetBrains Mono", monospace !important;
}}

.stSlider label, .stSelectbox label, .stRadio label {{
  color: {t["muted"]} !important;
  font-weight: 500 !important;
}}

[data-testid="stDataFrame"] {{
  border-radius: 14px !important;
  overflow: hidden !important;
  border: 1px solid {t["border"]} !important;
{dataframe_shell}
}}

.streamlit-expanderHeader {{
  font-weight: 600 !important;
  border-radius: 12px !important;
  color: {t["text"]} !important;
}}

div[data-testid="stSpinner"] {{ color: {t["accent"]} !important; }}
</style>
""",
        unsafe_allow_html=True,
    )


def render_navbar(t: dict) -> None:
    """Brand + segmented nav + status + theme toggle."""
    st.markdown(
        f'<div style="border-bottom:1px solid {t["border"]}; margin-bottom:0.85rem; padding-bottom:0.45rem;"></div>',
        unsafe_allow_html=True,
    )

    c_brand, c_nav, c_util = st.columns([1.35, 4.05, 1.6])
    with c_brand:
        st.markdown(
            f"""<div style="margin-top:4px;">
<span style="font-weight:800;font-size:1.12rem;letter-spacing:-0.03em;color:{t["text"]};">Fuel</span>
<span style="font-weight:600;font-size:1.02rem;color:{t["muted"]};"> Optimizer</span>
</div>""",
            unsafe_allow_html=True,
        )
        st.caption("FUZZY · MAMDANI · STREAMLIT")
    with c_nav:
        nav_options = list(range(len(NAV_ITEMS)))
        sel = st.segmented_control(
            "Sayfa",
            nav_options,
            selection_mode="single",
            default=st.session_state.page,
            format_func=lambda i: f"{NAV_ITEMS[i][1]} {NAV_ITEMS[i][0]}",
            key="fo_nav",
            label_visibility="collapsed",
            width="stretch",
            required=True,
        )
        if sel is not None:
            st.session_state.page = int(sel)
    with c_util:
        u1, u2 = st.columns([1.1, 1])
        with u1:
            st.markdown(
                f'<div style="text-align:center; margin-top:6px; padding:6px 10px; border-radius:999px; border:1px solid {t["border"]}; font-size:0.68rem; font-weight:600; letter-spacing:0.06em; color:{t["muted"]};">FUZZY • LIVE</div>',
                unsafe_allow_html=True,
            )
        with u2:
            _render_theme_switch()


def hero_banner(t: dict) -> None:
    st.markdown(
        f"""
<div class="fo-hero" style="
  text-align:center;
  padding: 2rem 1.5rem 1.75rem;
  margin: 0.35rem 0 1.25rem;
  border-radius: 28px;
  background: linear-gradient(180deg, {t["panel"]} 0%, {t["panel_soft"]} 100%);
  border: 1px solid {t["border"]};
  box-shadow:
    0 24px 80px rgba(0,0,0,{"0.5" if t["mode"]=="dark" else "0.12"}),
    inset 0 1px 0 rgba(255,255,255,{"0.06" if t["mode"]=="dark" else "0.9"});
">
  <div style="
    display:inline-block;
    font-size:0.72rem;
    font-weight:700;
    letter-spacing:0.28em;
    text-transform:uppercase;
    color:{t["muted"]};
    margin-bottom:0.65rem;
  ">RPM · GAZ · EĞİM · SKOR</div>
  <h1 style="
    margin:0;
    font-size:clamp(1.65rem, 4vw, 2.55rem);
    font-weight:800;
    line-height:1.12;
    letter-spacing:-0.04em;
    color:{t["text"]};
  ">Çoklu araç telemetrisi ve bulanık yakıt optimizasyonu</h1>
  <p style="
    margin:1rem auto 0;
    max-width:640px;
    font-size:1.02rem;
    color:{t["muted"]};
    line-height:1.65;
  ">Mamdani ve sıfırıncı derece Sugeno, ızgara teşhisi, kural ateşleme açıklaması ve sentetik rota — tek panelde.</p>
  <div style="display:flex; justify-content:center; gap:12px; flex-wrap:wrap; margin-top:1.35rem;">
    <span style="display:inline-block; padding:12px 26px; border-radius:999px; background:{t["grad_cta"]}; color:#fafafa; font-weight:700; font-size:0.92rem; box-shadow:0 8px 32px rgba(99,102,241,0.45);">Canlı kontrol paneli</span>
    <span style="display:inline-block; padding:12px 22px; border-radius:999px; border:1px solid {t["border"]}; color:{t["text"]}; font-weight:600; font-size:0.9rem; background:transparent;">Dokümantasyon</span>
  </div>
  <div style="display:flex; justify-content:center; gap:10px; flex-wrap:wrap; margin-top:1rem;">
    {''.join(f'<span style="font-size:0.78rem; padding:6px 12px; border-radius:999px; border:1px solid {t["border"]}; color:{t["muted"]};">{tag}</span>' for tag in ("Policy gates", "Auto rollbacks", "Izgara analiz", "Trajectory"))}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def pipeline_strip(t: dict) -> None:
    """Decorative 'live pipeline' row inspired by the reference dashboard."""
    cards = [
        ("FUZZIFY", "Girdi üyelikleri", 78, True),
        ("RULE FIRE", "Kural birleşimi", 62, False),
        ("AGGREGATE", "Maks birleştirme", 55, False),
        ("DEFUZZ", "Centroid / WA", 71, False),
    ]
    parts = []
    for title, sub, pct, pulse in cards:
        dot = (
            f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{t["neon"]};box-shadow:0 0 12px {t["neon_glow"]};margin-right:8px;vertical-align:middle;{"animation: fo-pulse 1.4s ease-in-out infinite" if pulse else ""}"></span>'
            if pulse
            else f'<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{t["muted"]};opacity:0.35;margin-right:8px;vertical-align:middle;"></span>'
        )
        parts.append(
            f"""
<div style="
  background: {t["panel_soft"]};
  border: 1px solid {t["border"]};
  border-radius: 16px;
  padding: 12px 14px 14px;
  min-height: 92px;
">
  <div style="font-size:0.65rem; font-weight:800; letter-spacing:0.14em; color:{t["muted"]};">{title}</div>
  <div style="margin-top:6px; font-size:0.82rem; font-weight:600; color:{t["text"]};">{dot}{sub}</div>
  <div style="margin-top:12px; height:4px; border-radius:999px; background: rgba(161,161,170,0.15); overflow:hidden;">
    <div style="width:{pct}%; height:100%; border-radius:999px; background: linear-gradient(90deg, #22d3ee, #6366f1, #a855f7);"></div>
  </div>
</div>
"""
        )
    st.markdown(
        f"""
<style>
@keyframes fo-pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: 0.55; transform: scale(0.92); }}
}}
</style>
<div style="margin: 0 0 1.5rem;">
  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
    <span style="font-size:0.68rem; font-weight:800; letter-spacing:0.2em; color:{t["muted"]};">LIVE CONTROL PREVIEW</span>
    <span style="font-size:0.72rem; font-weight:600; color:{t["neon"]}; font-family: 'JetBrains Mono', monospace;">
      <span style="color:{t["neon"]};">●</span> Streaming
    </span>
  </div>
  <div style="display:grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 12px;">
    {''.join(parts)}
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


_CSS_RGB = re.compile(
    r"^rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*(?:,\s*([0-9.]+))?\s*\)\s*$",
    re.I,
)


def _mpl_color(css: str) -> tuple[float, float, float, float]:
    """Matplotlib does not accept CSS rgba(...) strings via to_rgba; parse to floats."""
    raw = css.strip()
    m = _CSS_RGB.match(raw)
    if m:
        r, g, b = (int(m.group(i)) / 255.0 for i in (1, 2, 3))
        a = float(m.group(4)) if m.group(4) is not None else 1.0
        return (r, g, b, a)
    return mcolors.to_rgba(raw)


def section_title(text: str, icon: str, t: dict, *, compact: bool = False) -> None:
    prefix = f"{icon} " if icon else ""
    mt, mb = ("0.35rem", "0.2rem") if compact else ("1.35rem", "0.65rem")
    fs = "0.88rem" if compact else "1.02rem"
    st.markdown(
        f'<p style="margin:{mt} 0 {mb}; font-size:{fs}; font-weight:700; color:{t["text"]}; letter-spacing:-0.02em;">{prefix}{text}</p>',
        unsafe_allow_html=True,
    )


def style_matplotlib_figure(fig, t: dict) -> None:
    """Match Agg figures to the in-app theme (native Streamlit stays light in config.toml)."""
    if t["mode"] != "dark":
        return
    bg = t["plot_bg"]
    fg = t["text"]
    muted = t["muted"]
    border = _mpl_color(t["border"])
    panel_soft = _mpl_color(t["panel_soft"])
    fig.patch.set_facecolor(bg)
    for ax in fig.axes:
        ax.set_facecolor(bg)
        ax.tick_params(colors=muted)
        ax.xaxis.label.set_color(fg)
        ax.yaxis.label.set_color(fg)
        ax.title.set_color(fg)
        for s in ax.spines.values():
            s.set_color(border)
        leg = ax.get_legend()
        if leg is not None:
            leg.get_frame().set_facecolor(panel_soft)
            leg.get_frame().set_edgecolor(border)
            for tx in leg.get_texts():
                tx.set_color(fg)


def style_plotly(fig: go.Figure, title: str | None, height: int, t: dict) -> go.Figure:
    dark = t["mode"] == "dark"
    tpl = "plotly_dark" if dark else "plotly_white"
    fig.update_layout(
        template=tpl,
        title=dict(text=title or "", font=dict(size=15, color=t["text"])),
        paper_bgcolor=t["plot_paper"],
        plot_bgcolor=t["plot_bg"],
        font=dict(color=t["muted"], family="Inter, sans-serif"),
        height=height,
        margin=dict(l=52, r=20, t=52 if title else 36, b=44),
        xaxis=dict(gridcolor=t["plot_grid"], zerolinecolor=t["plot_grid"]),
        yaxis=dict(gridcolor=t["plot_grid"], zerolinecolor=t["plot_grid"]),
        legend=dict(
            bgcolor=("rgba(12,14,22,0.8)" if dark else "rgba(255,255,255,0.9)"),
            bordercolor=t["border"],
            borderwidth=1,
        ),
    )
    return fig


@st.cache_resource
def get_engine(car_name: str, inference_mode: str) -> FuzzyEngine:
    return FuzzyEngine(ENGINE_CONFIGS[car_name], inference_mode=inference_mode)


def render_advice(result: dict, t: dict, *, compact: bool = False) -> None:
    pad = "0.55rem 0.7rem" if compact else "1rem 1.1rem"
    if not result["success"]:
        if result.get("hata") == "KeyError":
            st.markdown(
                f"""<div style="border-left:4px solid {t["warn"]};background:rgba(251,191,36,0.12);padding:{pad};border-radius:12px;color:{t["text"]};border:1px solid {t["border"]};">
                <strong>Güvenlik</strong> — Bu noktada kural çıktısı üretilemedi (seyrek uzay). Mevcut sürüş durumunu koruyun.
                </div>""",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""<div style="border-left:4px solid {t["danger"]};background:rgba(251,113,133,0.12);padding:{pad};border-radius:12px;color:{t["text"]};border:1px solid {t["border"]};">
                <strong>Hesaplama</strong> — Girdi aralığı veya durulaştırma başarısız.
                </div>""",
                unsafe_allow_html=True,
            )
        return

    tavsiye = result["tavsiye"]
    styles = {
        "VİTES BÜYÜT": (t["success"], "rgba(74,222,128,0.12)", "⬆️", "Yüksek devir / yeterli tork marjı — üst vites ekonomik banda yaklaştırır."),
        "VİTES KÜÇÜLT": (t["danger"], "rgba(251,113,133,0.12)", "⬇️", "Düşük devir veya yüksek yokuş — alt vitesle motoru çalışma bandına çekin."),
        "GAZDAN ÇEK": (t["warn"], "rgba(251,191,36,0.12)", "🦶", "İniş veya fazla ivme — gazdan çekerek yakıt kesimi / motor freni."),
        "DURUMU KORU": (t["accent"], "rgba(129,140,248,0.12)", "➖", "Vites–gaz dengesi kabul edilebilir; sürüşü sabit tutun."),
    }
    border, bg, icon, body = styles.get(
        tavsiye,
        (t["accent"], "rgba(129,140,248,0.12)", "➖", "Durum değerlendirildi."),
    )
    pad = "0.55rem 0.65rem" if compact else "1.1rem 1.2rem"
    rad = "12px" if compact else "16px"
    title_fs = "1.05rem" if compact else "1.42rem"
    body_fs = "0.78rem" if compact else "0.96rem"
    body_mt = "0.3rem" if compact else "0.5rem"
    body_lh = "1.35" if compact else "1.55"
    shadow = "0 4px 16px rgba(0,0,0,0.2)" if compact else f"0 10px 36px rgba(0,0,0,{'0.28' if t['mode']=='dark' else '0.08'})"
    st.markdown(
        f"""<div style="border-left:4px solid {border};background:{bg};padding:{pad};border-radius:{rad};margin-top:0.15rem;border:1px solid {t["border"]};box-shadow:{shadow};">
        <div style="font-size:{title_fs};font-weight:800;color:{t["text"]};letter-spacing:-0.03em;">{icon} {tavsiye}</div>
        <div style="margin-top:{body_mt};color:{t["muted"]};font-size:{body_fs};line-height:{body_lh};">{body}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def tab_dashboard(t: dict) -> None:
    section_title("Canlı telemetri ve bulanık karar", "🎯", t, compact=True)

    col_left, col_right = st.columns([1, 1.05], gap="small")

    with col_left:
        st.markdown(
            f'<div style="padding:0.15rem 0 0.2rem;font-size:0.65rem;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:{t["muted"]};">Kontrol</div>',
            unsafe_allow_html=True,
        )
        _car_options = list(ENGINE_CONFIGS.keys())
        _rpm_by_profile = ", ".join(
            f"{name}: {ENGINE_CONFIGS[name]['rpm_max']}" for name in _car_options
        )
        car = st.selectbox(
            "Araç profili",
            _car_options,
            help=f"Profil başına RPM üst sınırı (redline): {_rpm_by_profile}",
        )
        cfg = ENGINE_CONFIGS[car]
        inference = st.radio(
            "Çıkarım mimarisi",
            (INFERENCE_MAMDANI, INFERENCE_SUGENO),
            format_func=lambda x: "Mamdani (centroid)"
            if x == INFERENCE_MAMDANI
            else "Sugeno (sıfırıncı derece, WA)",
            horizontal=True,
        )
        engine = get_engine(car, inference)

        st.markdown(
            f'<div style="padding:0.35rem 0 0.1rem;font-size:0.65rem;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:{t["muted"]};">Sensörler</div>',
            unsafe_allow_html=True,
        )
        rpm = st.slider(
            "Motor devri (RPM)",
            0,
            engine.rpm_max,
            int(cfg["ideal_range"][0]),
            step=10,
        )
        throttle = st.slider("Gaz (%)", 0, 100, 40, step=1)
        grade = st.slider("Yol eğimi (°)", -20, 20, 0, step=1)

    result = engine.evaluate(rpm, throttle, grade)

    with col_right:
        st.markdown(
            f'<div style="padding:0.05rem 0 0.2rem;font-size:0.65rem;font-weight:800;letter-spacing:0.18em;text-transform:uppercase;color:{t["muted"]};">Anlık</div>',
            unsafe_allow_html=True,
        )
        m1, m2, m3 = st.columns(3)
        m1.metric("RPM", f"{rpm}")
        m2.metric("Gaz", f"{throttle} %")
        m3.metric("Eğim", f"{grade} °")

        section_title("Öneri", "🤖", t, compact=True)
        render_advice(result, t, compact=True)

    if result["success"]:
        dt1, dt2 = st.columns(2, gap="small")
        with dt1:
            section_title("Girdi üyelikleri (IF)", "📊", t, compact=True)
            st.dataframe(
                _themed_df(pd.DataFrame(result["antecedent_mu"]), t),
                use_container_width=True,
                hide_index=True,
                height=DASHBOARD_TABLE_HEIGHT,
            )
        with dt2:
            section_title("Kural ateşleme güçleri", "⚡", t, compact=True)
            rf = pd.DataFrame(result["rule_firings"])
            if len(rf):
                st.dataframe(
                    _themed_df(rf, t),
                    use_container_width=True,
                    hide_index=True,
                    height=DASHBOARD_TABLE_HEIGHT,
                )
            else:
                st.caption("Kural ateşleme listesi boş.")

    st.divider()
    with st.expander("📐 Matematiksel özet ve çıkış üyelikleri", expanded=False):
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("### Durulaştırılmış skor")
            st.metric("Skor", f"{result['skor']:.2f}" if result["success"] else "—")
            st.caption(
                f"Çıkarım: **{result['inference']}** · "
                f"Durulaştırma: **{result['defuzz_method']}**"
            )
        with c2:
            if result["success"]:
                _fig = engine.plot_result(result["skor"])
                style_matplotlib_figure(_fig, t)
                st.pyplot(_fig)
            else:
                st.caption("Grafik için geçerli birleşik çıkış üyeliği yok.")


def tab_diagnostics(t: dict) -> None:
    section_title("Hassasiyet · RPM × gaz ızgara taraması", "🗺️", t)
    st.caption(
        "Sabit eğimde tüm hücrelerde skor; başarısız hücre oranı ölü bölge göstergesidir."
    )
    car = st.selectbox("Araç (diagnostics)", list(ENGINE_CONFIGS.keys()), key="diag_car")
    inference = st.radio(
        "Çıkarım",
        (INFERENCE_MAMDANI, INFERENCE_SUGENO),
        horizontal=True,
        key="diag_inf",
    )
    cfg = ENGINE_CONFIGS[car]
    rpm_step = st.slider("RPM adımı", 50, 500, 200, step=50, key="diag_rpm_step")
    thr_step = st.slider("Gaz adımı", 5, 25, 10, step=5, key="diag_thr_step")
    egim = st.slider("Sabit eğim (°)", -20, 20, 0, key="diag_egim")

    engine = get_engine(car, inference)
    rpm_axis, thr_axis = default_axes(cfg["rpm_max"], rpm_step, thr_step)
    scores, mask = score_grid(engine, rpm_axis, thr_axis, float(egim))
    stats = grid_statistics(mask)

    c1, c2, c3 = st.columns(3)
    c1.metric("Başarılı hücre", f"{stats['cells_success']} / {stats['cells_total']}")
    c2.metric("Başarı oranı", f"{100 * stats['success_rate']:.1f} %")
    c3.metric("Ölü bölge oranı", f"{100 * stats['dead_zone_rate']:.1f} %")

    fig = go.Figure(
        data=go.Heatmap(
            z=np.ma.masked_invalid(scores),
            x=thr_axis,
            y=rpm_axis,
            colorscale=[
                [0.0, t["heatmap_lo"]],
                [0.35, "#155e75"],
                [0.55, "#22d3ee"],
                [0.78, t["accent2"]],
                [1.0, t["heatmap_hi"]],
            ],
            colorbar=dict(title=dict(text="Skor", font=dict(color=t["muted"]))),
        )
    )
    style_plotly(fig, f"Karar yüzeyi · {car} · {inference}", 520, t)
    st.plotly_chart(fig, use_container_width=True)


def tab_compare(t: dict) -> None:
    section_title("Mamdani vs Sugeno (aynı kural tabanı)", "⚖️", t)
    st.caption(
        "Mamdani (bulanık çıkış + centroid) ile singleton’lı zero-order Sugeno (ağırlıklı ortalama)."
    )
    car = st.selectbox("Araç (karşılaştırma)", list(ENGINE_CONFIGS.keys()), key="cmp_car")
    cfg = ENGINE_CONFIGS[car]
    rpm_step = st.slider("RPM adımı", 100, 500, 250, step=50, key="cmp_rpm")
    thr_step = st.slider("Gaz adımı", 10, 25, 15, step=5, key="cmp_thr")
    egim = st.slider("Eğim (°)", -20, 20, 0, key="cmp_egim")

    rpm_axis, thr_axis = default_axes(cfg["rpm_max"], rpm_step, thr_step)
    with st.spinner("Izgara hesaplanıyor…"):
        df, summary = compare_inference_modes(cfg, rpm_axis, thr_axis, float(egim))

    if summary["mean_abs_diff"] is not None:
        k1, k2, k3 = st.columns(3)
        k1.metric("Ort. |fark|", f"{summary['mean_abs_diff']:.2f}")
        k2.metric("Maks |fark|", f"{summary['max_abs_diff']:.2f}")
        k3.metric("Karşılaştırılabilir hücre", str(summary["n_comparable"]))
    else:
        st.warning("Karşılaştırma için yeterli başarılı hücre yok.")

    if len(df):
        fig = go.Figure(
            data=go.Scatter(
                x=df["mamdani"],
                y=df["sugeno"],
                mode="markers",
                marker=dict(
                    size=9,
                    opacity=0.55,
                    color=df["mamdani"],
                    colorscale=[[0, "#22d3ee"], [1, t["accent2"]]],
                    line=dict(width=0.5, color="rgba(255,255,255,0.25)"),
                ),
                name="hücreler",
            )
        )
        lim = [0, 100]
        fig.add_trace(
            go.Scatter(
                x=lim,
                y=lim,
                mode="lines",
                name="y = x",
                line=dict(dash="dash", color=t["muted"], width=2),
            )
        )
        style_plotly(fig, "Dağılım: Mamdani vs Sugeno", 480, t)
        st.plotly_chart(fig, use_container_width=True)


def tab_trajectory(t: dict) -> None:
    section_title("Sentetik sürüş döngüsü", "📈", t)
    st.caption(
        "Bulanık (Mamdani) ve crisp baseline; raporda kıyaslama metriği olarak kullanılabilir."
    )
    car = st.selectbox("Araç (trajectory)", list(ENGINE_CONFIGS.keys()), key="tr_car")
    n = st.slider("Adım sayısı", 30, 150, 80, step=10)
    cfg = ENGINE_CONFIGS[car]
    rpm_max = cfg["rpm_max"]

    df = synthetic_mixed_cycle(n=n, rpm_max=rpm_max)
    fuzzy_engine = get_engine(car, INFERENCE_MAMDANI)
    ev = evaluate_trajectory(fuzzy_engine, df)

    crisp_rows = []
    for _, row in df.iterrows():
        crisp_rows.append(
            crisp_recommend(
                int(row["rpm"]),
                int(row["throttle"]),
                int(row["grade_deg"]),
                ideal_min=cfg["ideal_range"][0],
                ideal_max=cfg["ideal_range"][1],
                high_rev=cfg["high_rev"],
            )
        )
    ev["crisp_tavsiye"] = [r["tavsiye"] for r in crisp_rows]
    ev["crisp_skor"] = [r["skor"] for r in crisp_rows]
    ev["agree"] = ev["tavsiye"] == ev["crisp_tavsiye"]

    summ = trajectory_summary(ev)
    a1, a2, a3 = st.columns(3)
    a1.metric("Başarı (fuzzy)", f"{100 * summ['success_rate']:.0f} %")
    a2.metric("Ort. skor (fuzzy)", f"{summ['mean_skor']:.1f}" if summ["mean_skor"] else "—")
    a3.metric("Crisp ile uyum", f"{100 * float(ev['agree'].mean()):.0f} %")

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=ev["step"],
            y=ev["skor"],
            name="Mamdani skor",
            mode="lines+markers",
            line=dict(width=2.5, color="#22d3ee"),
            marker=dict(size=5, color="#22d3ee"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=ev["step"],
            y=ev["crisp_skor"],
            name="Crisp skor",
            mode="lines",
            line=dict(width=2, dash="dot", color=t["accent2"]),
        )
    )
    style_plotly(fig, "Skor zaman serisi", 420, t)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Ham tablo", expanded=False):
        st.dataframe(_themed_df(ev, t), use_container_width=True, hide_index=True)


def main() -> None:
    _init_session()
    _sync_theme_from_toggle()
    t = _tokens()
    inject_custom_css(t)
    render_navbar(t)
    hero_banner(t)
    pipeline_strip(t)

    pages = (tab_dashboard, tab_diagnostics, tab_compare, tab_trajectory)
    pages[st.session_state.page](t)

    st.markdown(
        f'<div style="text-align:center;padding:2rem 0 1rem;font-size:0.78rem;color:{t["muted"]};font-family:JetBrains Mono,monospace;">FUEL_OPTIMIZER / fuzzy_control_demo</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
