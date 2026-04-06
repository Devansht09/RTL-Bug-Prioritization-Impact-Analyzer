"""
RTL Bug Prioritization & Impact Analyzer — Streamlit Frontend
==============================================================
A premium, hackathon-ready UI with:
  - Tab 1: Dashboard (ranked bug table + severity distribution)
  - Tab 2: Dependency Graph (interactive Plotly network viz)
  - Tab 3: Explanations (expandable cards per bug)
  - Tab 4: ML Insights (feature importance + model stats)

Runs in two modes:
  - Direct mode (default): calls pipeline directly, no FastAPI required
  - API mode: calls FastAPI backend at localhost:8000
"""

import sys
import os

# Add project root to path for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import json
import time
import math
import pathlib
from typing import List, Dict, Optional

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import networkx as nx
import requests

# ===========================================================================
# PAGE CONFIG — must be first Streamlit call
# ===========================================================================
st.set_page_config(
    page_title="RTL Bug Analyzer",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ===========================================================================
# CUSTOM CSS — premium dark-mode EDA tool aesthetic
# ===========================================================================
st.markdown("""
<style>
  /* ---- Google Font ---- */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

  /* ---- Root variables ---- */
  :root {
    --bg-primary:    #0a0e1a;
    --bg-secondary:  #0f1628;
    --bg-card:       #131c32;
    --bg-card-hover: #1a2540;
    --accent-blue:   #3b82f6;
    --accent-cyan:   #06b6d4;
    --accent-purple: #8b5cf6;
    --accent-green:  #10b981;
    --severity-high:   #ef4444;
    --severity-medium: #f59e0b;
    --severity-low:    #10b981;
    --text-primary:  #f1f5f9;
    --text-secondary:#94a3b8;
    --text-muted:    #64748b;
    --border:        #1e2d4a;
    --border-bright: #2d4270;
    --glow-blue:     0 0 20px rgba(59, 130, 246, 0.3);
    --glow-cyan:     0 0 20px rgba(6, 182, 212, 0.2);
  }

  /* ---- Base ---- */
  html, body, .stApp {
    font-family: 'Inter', sans-serif !important;
    background: var(--bg-primary) !important;
    color: var(--text-primary) !important;
  }

  .block-container {
    padding: 1.5rem 2rem !important;
    max-width: 1600px !important;
  }

  /* ---- Sidebar ---- */
  [data-testid="stSidebar"] {
    background: var(--bg-secondary) !important;
    border-right: 1px solid var(--border) !important;
  }
  [data-testid="stSidebar"] .stTextArea textarea,
  [data-testid="stSidebar"] select {
    background: var(--bg-card) !important;
    border: 1px solid var(--border-bright) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
  }

  /* ---- Header Banner ---- */
  .hero-banner {
    background: linear-gradient(135deg, #0f1628 0%, #1a2540 50%, #0f1628 100%);
    border: 1px solid var(--border-bright);
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
  }
  .hero-banner::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(59,130,246,0.08) 0%, transparent 60%),
                radial-gradient(circle at 70% 50%, rgba(139,92,246,0.06) 0%, transparent 60%);
    pointer-events: none;
  }
  .hero-title {
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #60a5fa, #a78bfa, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin: 0 0 0.5rem 0;
    letter-spacing: -0.5px;
  }
  .hero-sub {
    color: var(--text-secondary);
    font-size: 0.92rem;
    font-weight: 400;
    letter-spacing: 0.2px;
  }

  /* ---- Metric Cards ---- */
  .metric-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1rem;
    margin-bottom: 1.5rem;
  }
  .metric-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    text-align: center;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
  }
  .metric-card:hover {
    border-color: var(--border-bright);
    background: var(--bg-card-hover);
    transform: translateY(-2px);
  }
  .metric-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: var(--bar-color, var(--accent-blue));
  }
  .metric-value {
    font-size: 2.5rem;
    font-weight: 800;
    color: var(--val-color, var(--accent-blue));
    line-height: 1;
    margin-bottom: 0.35rem;
  }
  .metric-label {
    font-size: 0.78rem;
    font-weight: 500;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.8px;
  }

  /* ---- Severity Badges ---- */
  .badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .badge-high {
    background: rgba(239,68,68,0.15);
    color: #f87171;
    border: 1px solid rgba(239,68,68,0.3);
  }
  .badge-medium {
    background: rgba(245,158,11,0.15);
    color: #fbbf24;
    border: 1px solid rgba(245,158,11,0.3);
  }
  .badge-low {
    background: rgba(16,185,129,0.15);
    color: #34d399;
    border: 1px solid rgba(16,185,129,0.3);
  }

  /* ---- Score Bar ---- */
  .score-bar-wrap {
    background: var(--bg-primary);
    border-radius: 4px;
    height: 8px;
    overflow: hidden;
    margin-top: 4px;
  }
  .score-bar-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.5s ease;
  }

  /* ---- Bug Cards ---- */
  .bug-card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-left: 3px solid var(--card-accent, var(--accent-blue));
    border-radius: 12px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 0.85rem;
    transition: all 0.2s ease;
  }
  .bug-card:hover {
    background: var(--bg-card-hover);
    border-color: var(--border-bright);
    box-shadow: var(--glow-blue);
  }
  .bug-card-header {
    display: flex;
    align-items: center;
    gap: 0.8rem;
    margin-bottom: 0.6rem;
    flex-wrap: wrap;
  }
  .bug-rank {
    font-size: 0.7rem;
    font-weight: 700;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
    background: var(--bg-primary);
    padding: 0.1rem 0.5rem;
    border-radius: 4px;
  }
  .bug-signal {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.92rem;
    font-weight: 600;
    color: var(--accent-cyan);
  }
  .bug-module {
    font-size: 0.78rem;
    color: var(--text-muted);
    font-family: 'JetBrains Mono', monospace;
  }
  .bug-desc {
    font-size: 0.83rem;
    color: var(--text-secondary);
    margin: 0.4rem 0;
    line-height: 1.5;
  }
  .score-inline {
    font-size: 0.78rem;
    font-family: 'JetBrains Mono', monospace;
    color: var(--text-muted);
  }
  .path-pill {
    display: inline-block;
    background: rgba(59,130,246,0.1);
    border: 1px solid rgba(59,130,246,0.25);
    color: #93c5fd;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    padding: 0.15rem 0.6rem;
    border-radius: 4px;
    margin-top: 0.4rem;
  }

  /* ---- Explanation Card ---- */
  .explain-card {
    background: var(--bg-secondary);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    color: #cbd5e1;
    white-space: pre-wrap;
    line-height: 1.7;
    margin-top: 0.5rem;
  }

  /* ---- Tab Styling ---- */
  .stTabs [data-baseweb="tab-list"] {
    background: var(--bg-secondary) !important;
    border-radius: 10px !important;
    padding: 4px !important;
    gap: 4px !important;
    border: 1px solid var(--border) !important;
    margin-bottom: 1.5rem !important;
  }
  .stTabs [data-baseweb="tab"] {
    background: transparent !important;
    color: var(--text-muted) !important;
    border-radius: 7px !important;
    font-weight: 500 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.2rem !important;
  }
  .stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)) !important;
    color: white !important;
    box-shadow: 0 2px 10px rgba(59,130,246,0.4) !important;
  }

  /* ---- Buttons ---- */
  .stButton > button {
    background: linear-gradient(135deg, var(--accent-blue), var(--accent-purple)) !important;
    color: white !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s ease !important;
    box-shadow: 0 2px 10px rgba(59,130,246,0.35) !important;
  }
  .stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(59,130,246,0.5) !important;
  }

  /* ---- Info boxes ---- */
  .stAlert {
    background: var(--bg-card) !important;
    border-color: var(--border-bright) !important;
    color: var(--text-primary) !important;
    border-radius: 10px !important;
  }

  /* ---- Streamlit overrides ---- */
  .stTextArea textarea {
    background: var(--bg-card) !important;
    border-color: var(--border-bright) !important;
    color: var(--text-primary) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.78rem !important;
  }
  .stSelectbox div[data-baseweb="select"] {
    background: var(--bg-card) !important;
    border-color: var(--border-bright) !important;
  }
  hr { border-color: var(--border) !important; }

  /* ---- Section headers ---- */
  .section-header {
    font-size: 1rem;
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding-bottom: 0.5rem;
    border-bottom: 1px solid var(--border);
  }

  /* ---- Pipeline flow ---- */
  .pipeline-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 20px;
    font-size: 0.7rem;
    color: var(--text-muted);
    padding: 0.15rem 0.6rem;
    margin: 0.1rem;
  }
  .pipeline-pill-active {
    background: rgba(59,130,246,0.15);
    border-color: rgba(59,130,246,0.4);
    color: #93c5fd;
  }

  /* Hide Streamlit header bar entirely (white box killer) */
  header[data-testid="stHeader"] {
    height: 0 !important;
    min-height: 0 !important;
    padding: 0 !important;
    background: transparent !important;
    border: none !important;
    overflow: visible !important;
  }
  #MainMenu, footer { visibility: hidden; }

  /* Pull the sidebar toggle out of the now-zero-height header
     and make it float visibly on the left edge */
  [data-testid="collapsedControl"] {
    display: flex !important;
    visibility: visible !important;
    position: fixed !important;
    top: 50% !important;
    left: 0 !important;
    transform: translateY(-50%) !important;
    background: var(--bg-card) !important;
    border: 1px solid var(--border-bright) !important;
    border-left: none !important;
    border-radius: 0 8px 8px 0 !important;
    color: var(--text-secondary) !important;
    box-shadow: 2px 0 12px rgba(0,0,0,0.5) !important;
    z-index: 9999 !important;
    padding: 8px 4px !important;
  }
  [data-testid="collapsedControl"]:hover {
    background: var(--bg-card-hover) !important;
    border-color: rgba(59,130,246,0.6) !important;
    box-shadow: 3px 0 16px rgba(59,130,246,0.3) !important;
  }
  [data-testid="collapsedControl"] svg {
    fill: var(--text-secondary) !important;
  }

  /* Sidebar's own collapse button stays visible */
  [data-testid="stSidebarCollapseButton"] {
    visibility: visible !important;
  }
</style>
""", unsafe_allow_html=True)


# ===========================================================================
# HELPERS
# ===========================================================================

SEVERITY_COLORS = {
    "High":   "#ef4444",
    "Medium": "#f59e0b",
    "Low":    "#10b981",
}

SEVERITY_ICONS = {
    "High":   "🔴",
    "Medium": "🟡",
    "Low":    "🟢",
}

BUG_TYPE_ICONS = {
    "unused_signal":          "🔇",
    "undriven_signal":        "📡",
    "conflicting_assignment": "⚡",
    "latch_risk":             "🔒",
    "external":               "🔧",
}

BUG_TYPE_LABELS = {
    "unused_signal":          "Unused Signal",
    "undriven_signal":        "Undriven Signal",
    "conflicting_assignment": "Conflicting Assignment",
    "latch_risk":             "Latch Risk",
    "external":               "External Issue",
}


def badge_html(label: str) -> str:
    cls = f"badge badge-{label.lower()}"
    icon = SEVERITY_ICONS.get(label, "⚪")
    return f'<span class="{cls}">{icon} {label}</span>'


def score_bar_html(score: float, color: str) -> str:
    pct = int(score * 100)
    return (
        f'<div class="score-bar-wrap">'
        f'<div class="score-bar-fill" style="width:{pct}%;background:{color};"></div>'
        f'</div>'
    )


def get_card_accent(label: str) -> str:
    return SEVERITY_COLORS.get(label, "#3b82f6")


def load_examples():
    base = pathlib.Path(__file__).parent.parent / "examples"
    files = {f.stem: f.read_text(encoding="utf-8") for f in base.glob("*.v")}
    return files


# ===========================================================================
# PIPELINE RUNNER (direct mode — no FastAPI needed)
# ===========================================================================

@st.cache_resource(show_spinner=False)
def _get_pipeline():
    """Cache the pipeline import so model only trains once."""
    from backend.pipeline import run_pipeline as _rp
    from backend.ml.model import get_model
    model = get_model()  # warm up
    return _rp, model


def run_analysis(rtl_code: str, external_issues: List[Dict]) -> Dict:
    """Run pipeline directly (no FastAPI required)."""
    run_pipeline, _ = _get_pipeline()
    return run_pipeline(rtl_code=rtl_code, external_issues=external_issues)


# ===========================================================================
# GRAPH VISUALIZATION
# ===========================================================================

def build_plotly_graph(graph_data: Dict, results: List[Dict]) -> go.Figure:
    """
    Build an interactive Plotly network graph from the dependency data.
    Bug signals are highlighted. Output nodes glow blue. Propagation paths shine.
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])

    if not nodes:
        fig = go.Figure()
        fig.update_layout(
            paper_bgcolor="#0a0e1a", plot_bgcolor="#0a0e1a",
            annotations=[dict(text="No graph data available.", showarrow=False,
                              font=dict(color="#64748b", size=14),
                              xref="paper", yref="paper", x=0.5, y=0.5)]
        )
        return fig

    # Build nx graph for layout
    G = nx.DiGraph()
    for n in nodes:
        G.add_node(n["id"], **n)
    for e in edges:
        G.add_edge(e["source"], e["target"])

    # Layout
    try:
        pos = nx.spring_layout(G, k=2.5, iterations=60, seed=42)
    except Exception:
        pos = {n: (i % 10, i // 10) for i, n in enumerate(G.nodes())}

    # Gather bug signals
    bug_signals = {r["signal"] for r in results}

    # Gather path signals
    path_signals = set()
    for r in results:
        path_signals.update(r.get("signal_path", []))

    # Gather output signals
    output_signals = {n["id"] for n in nodes if n.get("is_output")}
    input_signals = {n["id"] for n in nodes if n.get("is_input")}

    # Build edge traces
    edge_traces = []
    for src, dst in G.edges():
        x0, y0 = pos[src]
        x1, y1 = pos[dst]
        is_path_edge = src in path_signals and dst in path_signals
        color = "rgba(59,130,246,0.6)" if is_path_edge else "rgba(45,66,112,0.5)"
        width = 2.5 if is_path_edge else 1.0
        edge_traces.append(go.Scatter(
            x=[x0, x1, None], y=[y0, y1, None],
            mode="lines",
            line=dict(width=width, color=color),
            hoverinfo="none",
            showlegend=False,
        ))

    # Build node trace
    nx_list = list(pos.keys())
    node_x = [pos[n][0] for n in nx_list]
    node_y = [pos[n][1] for n in nx_list]

    node_colors, node_sizes, node_symbols, hover_texts = [], [], [], []
    for n in nx_list:
        attrs = G.nodes[n]
        is_bug = n in bug_signals
        is_out = n in output_signals
        is_in  = n in input_signals
        is_path = n in path_signals

        if is_bug and is_out:
            color = "#ef4444"
            size = 22
        elif is_bug:
            color = "#f59e0b"
            size = 18
        elif is_out:
            color = "#06b6d4"
            size = 16
        elif is_in:
            color = "#8b5cf6"
            size = 14
        elif is_path:
            color = "#60a5fa"
            size = 13
        else:
            color = "#1e3a5f"
            size = 10

        node_colors.append(color)
        node_sizes.append(size)

        kind = attrs.get("kind", "wire")
        mod  = attrs.get("module", "")
        tags = []
        if is_bug:  tags.append("⚠️ BUG")
        if is_out:  tags.append("OUTPUT")
        if is_in:   tags.append("INPUT")
        tag_str = " | ".join(tags) if tags else kind.upper()
        hover_texts.append(f"<b>{n}</b><br>{tag_str}<br>Module: {mod}")

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(width=1.5, color="rgba(255,255,255,0.15)"),
        ),
        text=nx_list,
        textposition="top center",
        textfont=dict(size=9, color="#94a3b8", family="JetBrains Mono"),
        hovertext=hover_texts,
        hoverinfo="text",
        showlegend=False,
    )

    fig = go.Figure(data=[*edge_traces, node_trace])
    fig.update_layout(
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0f1628",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showline=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, showline=False),
        height=520,
        hoverlabel=dict(
            bgcolor="#131c32",
            bordercolor="#2d4270",
            font=dict(family="JetBrains Mono", size=11, color="#f1f5f9"),
        ),
    )
    return fig


# ===========================================================================
# FEATURE IMPORTANCE CHART
# ===========================================================================

def build_feature_importance_chart(model) -> go.Figure:
    pairs = model.get_feature_importances()
    if not pairs:
        return go.Figure()

    labels = [p[0].replace("_", " ").title() for p in pairs]
    values = [p[1] for p in pairs]
    colors = px.colors.sequential.Blues[2:]

    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(
            color=values,
            colorscale=[[0, "#1e3a5f"], [0.5, "#3b82f6"], [1.0, "#06b6d4"]],
            line=dict(color="rgba(255,255,255,0.05)", width=1),
        ),
        hovertemplate="<b>%{y}</b><br>Importance: %{x:.4f}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="#0a0e1a",
        plot_bgcolor="#0f1628",
        font=dict(family="Inter", color="#94a3b8"),
        margin=dict(l=10, r=20, t=10, b=10),
        height=300,
        xaxis=dict(
            gridcolor="#1e2d4a",
            zerolinecolor="#1e2d4a",
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            gridcolor="#1e2d4a",
            tickfont=dict(family="JetBrains Mono", size=10),
        ),
    )
    return fig


def build_severity_donut(summary: Dict) -> go.Figure:
    labels = ["High", "Medium", "Low"]
    values = [summary.get("high", 0), summary.get("medium", 0), summary.get("low", 0)]
    colors = ["#ef4444", "#f59e0b", "#10b981"]

    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors, line=dict(color="#0a0e1a", width=2)),
        textinfo="label+percent",
        textfont=dict(family="Inter", size=12, color="white"),
        hovertemplate="<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        margin=dict(l=10, r=10, t=10, b=10),
        height=220,
        annotations=[dict(
            text=f"<b>{summary.get('total', 0)}</b><br><span style='font-size:10px'>Issues</span>",
            x=0.5, y=0.5, showarrow=False,
            font=dict(family="Inter", size=18, color="#f1f5f9"),
        )],
    )
    return fig


def build_bug_type_chart(results: List[Dict]) -> go.Figure:
    from collections import Counter
    counts = Counter(r["bug_type"] for r in results)
    labels = [BUG_TYPE_LABELS.get(k, k) for k in counts.keys()]
    values = list(counts.values())
    colors = ["#3b82f6", "#06b6d4", "#8b5cf6", "#f59e0b", "#10b981"]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(color=colors[:len(labels)], line=dict(color="rgba(255,255,255,0.05)", width=1)),
        hovertemplate="<b>%{x}</b><br>Count: %{y}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", color="#94a3b8"),
        margin=dict(l=5, r=5, t=5, b=40),
        height=200,
        xaxis=dict(gridcolor="#1e2d4a", tickfont=dict(size=10)),
        yaxis=dict(gridcolor="#1e2d4a", tickfont=dict(size=10)),
    )
    return fig


# ===========================================================================
# SIDEBAR
# ===========================================================================

def render_sidebar():
    examples = load_examples()

    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem 0 0.5rem 0;">
          <div style="font-size:1.1rem;font-weight:800;background:linear-gradient(135deg,#60a5fa,#a78bfa);
               -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;">
            🔬 RTL Analyzer
          </div>
          <div style="font-size:0.72rem;color:#64748b;margin-top:0.2rem;">
            Bug Prioritization & Impact Analyzer v1.0
          </div>
        </div>
        <hr style="margin:0.5rem 0 1rem;">
        """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:0.8rem;color:#94a3b8;font-weight:600;margin-bottom:0.4rem;">📂 LOAD EXAMPLE</div>', unsafe_allow_html=True)
        example_choice = st.selectbox(
            "Example Files",
            ["(Paste your own)"] + list(examples.keys()),
            label_visibility="collapsed",
        )

        if example_choice != "(Paste your own)":
            rtl_code_default = examples[example_choice]
        else:
            rtl_code_default = ""

        st.markdown('<div style="font-size:0.8rem;color:#94a3b8;font-weight:600;margin:1rem 0 0.4rem;">📝 RTL SOURCE CODE</div>', unsafe_allow_html=True)
        rtl_input = st.text_area(
            "RTL Code",
            value=rtl_code_default,
            height=320,
            placeholder="Paste your Verilog / VHDL code here...",
            label_visibility="collapsed",
        )

        st.markdown('<div style="font-size:0.8rem;color:#94a3b8;font-weight:600;margin:1rem 0 0.4rem;">🔧 EXTERNAL ISSUES (JSON)</div>', unsafe_allow_html=True)
        ext_input = st.text_area(
            "External Issues",
            height=80,
            placeholder='[{"type":"latch_risk","signal":"q","module":"my_mod","confidence":0.9}]',
            label_visibility="collapsed",
        )

        st.markdown("")
        analyze_btn = st.button("🚀  Analyze RTL", use_container_width=True)

        st.markdown('<hr style="margin:1.5rem 0 1rem;">', unsafe_allow_html=True)
        st.markdown("""
        <div style="font-size:0.7rem;color:#475569;">
          <b style="color:#64748b;">Pipeline Stages</b><br>
          <span style="color:#3b82f6">①</span> RTL Parsing (PyVerilog)<br>
          <span style="color:#3b82f6">②</span> Bug Detection (4 rules)<br>
          <span style="color:#3b82f6">③</span> Dependency Graph (NetworkX)<br>
          <span style="color:#3b82f6">④</span> BFS Impact Analysis<br>
          <span style="color:#3b82f6">⑤</span> Feature Extraction<br>
          <span style="color:#3b82f6">⑥</span> ML Scoring (Random Forest)<br>
          <span style="color:#3b82f6">⑦</span> Hybrid Ranking<br>
          <span style="color:#3b82f6">⑧</span> Explanation Generation
        </div>
        """, unsafe_allow_html=True)

    return rtl_input, ext_input, analyze_btn


# ===========================================================================
# TAB 1: BUG DASHBOARD
# ===========================================================================

def render_dashboard(results: List[Dict], summary: Dict, parse_info: Dict, timing: Dict):

    # ---- Metric Cards ----
    t = summary.get("total", 0)
    h = summary.get("high", 0)
    m = summary.get("medium", 0)
    l = summary.get("low", 0)

    st.markdown(f"""
    <div class="metric-row">
      <div class="metric-card" style="--bar-color:#3b82f6;--val-color:#60a5fa;">
        <div class="metric-value">{t}</div>
        <div class="metric-label">Total Issues</div>
      </div>
      <div class="metric-card" style="--bar-color:#ef4444;--val-color:#f87171;">
        <div class="metric-value">{h}</div>
        <div class="metric-label">🔴 High Priority</div>
      </div>
      <div class="metric-card" style="--bar-color:#f59e0b;--val-color:#fbbf24;">
        <div class="metric-value">{m}</div>
        <div class="metric-label">🟡 Medium Priority</div>
      </div>
      <div class="metric-card" style="--bar-color:#10b981;--val-color:#34d399;">
        <div class="metric-value">{l}</div>
        <div class="metric-label">🟢 Low Priority</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ---- Charts row ----
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown('<div class="section-header">📊 Severity Distribution</div>', unsafe_allow_html=True)
        donut = build_severity_donut(summary)
        st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown('<div class="section-header">🐛 Bug Type Breakdown</div>', unsafe_allow_html=True)
        if results:
            bug_chart = build_bug_type_chart(results)
            st.plotly_chart(bug_chart, use_container_width=True, config={"displayModeBar": False})

    # ---- Parse info row ----
    c3, c4, c5, c6, c7 = st.columns(5)
    info_items = [
        (c3, "Parser", parse_info.get("method", "?").upper()),
        (c4, "Modules", str(len(parse_info.get("modules", [])))),
        (c5, "Signals", str(parse_info.get("signal_count", 0))),
        (c6, "Assignments", str(parse_info.get("assignment_count", 0))),
        (c7, "Analysis Time", f"{timing.get('total', 0):.0f}ms"),
    ]
    for col, lbl, val in info_items:
        with col:
            st.markdown(f"""
            <div style="text-align:center;background:#0f1628;border:1px solid #1e2d4a;
                 border-radius:8px;padding:.6rem .5rem;">
              <div style="font-size:1.1rem;font-weight:700;color:#60a5fa;">{val}</div>
              <div style="font-size:0.67rem;color:#64748b;text-transform:uppercase;letter-spacing:.5px;">{lbl}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---- Ranked Bug Table ----
    if not results:
        st.info("✨ No bugs detected! Your RTL code looks clean.")
        return

    st.markdown('<div class="section-header">🏆 Ranked Bug List</div>', unsafe_allow_html=True)

    for r in results:
        label = r["severity_label"]
        accent = get_card_accent(label)
        icon = BUG_TYPE_ICONS.get(r["bug_type"], "🔧")
        lbl_html = badge_html(label)
        score = r["final_score"]
        path = r.get("signal_path", [])
        path_display = " → ".join(path) if path else ""

        st.markdown(f"""
        <div class="bug-card" style="--card-accent:{accent};">
          <div class="bug-card-header">
            <span class="bug-rank">#{r['rank']}</span>
            <span style="font-size:1.1rem;">{icon}</span>
            <span class="bug-signal">{r['signal']}</span>
            {lbl_html}
            <span class="bug-module">@ {r['module']}</span>
            <span style="margin-left:auto;" class="score-inline">
              Score: <b style="color:{accent};">{score:.3f}</b>
              &nbsp;|&nbsp; Rule: {r['rule_score']:.3f}
              &nbsp;|&nbsp; ML: {r['ml_score']:.3f}
            </span>
          </div>
          <div class="bug-desc">{r['description']}</div>
          {f'<div class="path-pill">📡 {path_display}</div>' if path_display else ''}
          {score_bar_html(score, accent)}
        </div>
        """, unsafe_allow_html=True)


# ===========================================================================
# TAB 2: DEPENDENCY GRAPH
# ===========================================================================

def render_graph_tab(graph_data: Dict, results: List[Dict]):
    st.markdown('<div class="section-header">🔗 Signal Dependency Graph</div>', unsafe_allow_html=True)

    legend_html = """
    <div style="display:flex;gap:1.5rem;margin-bottom:1rem;flex-wrap:wrap;">
      <span style="display:flex;align-items:center;gap:.4rem;font-size:.75rem;color:#94a3b8;">
        <span style="width:10px;height:10px;border-radius:50%;background:#f59e0b;display:inline-block;"></span> Bug Signal
      </span>
      <span style="display:flex;align-items:center;gap:.4rem;font-size:.75rem;color:#94a3b8;">
        <span style="width:10px;height:10px;border-radius:50%;background:#06b6d4;display:inline-block;"></span> Output Port
      </span>
      <span style="display:flex;align-items:center;gap:.4rem;font-size:.75rem;color:#94a3b8;">
        <span style="width:10px;height:10px;border-radius:50%;background:#8b5cf6;display:inline-block;"></span> Input Port
      </span>
      <span style="display:flex;align-items:center;gap:.4rem;font-size:.75rem;color:#94a3b8;">
        <span style="width:10px;height:10px;border-radius:50%;background:#60a5fa;display:inline-block;"></span> Propagation Path
      </span>
      <span style="display:flex;align-items:center;gap:.4rem;font-size:.75rem;color:#94a3b8;">
        <span style="width:10px;height:10px;border-radius:50%;background:#1e3a5f;display:inline-block;"></span> Internal Signal
      </span>
    </div>
    """
    st.markdown(legend_html, unsafe_allow_html=True)

    fig = build_plotly_graph(graph_data, results)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": True, "scrollZoom": True})

    # Graph stats
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    outputs = [n["id"] for n in nodes if n.get("is_output")]
    inputs  = [n["id"] for n in nodes if n.get("is_input")]
    col1, col2, col3, col4 = st.columns(4)
    for col, label, val in [
        (col1, "Total Nodes", len(nodes)),
        (col2, "Total Edges", len(edges)),
        (col3, "Output Ports", len(outputs)),
        (col4, "Input Ports", len(inputs)),
    ]:
        with col:
            st.markdown(f"""
            <div style="text-align:center;background:#0f1628;border:1px solid #1e2d4a;
                 border-radius:8px;padding:.6rem;">
              <div style="font-size:1.3rem;font-weight:700;color:#60a5fa;">{val}</div>
              <div style="font-size:0.68rem;color:#64748b;text-transform:uppercase;">{label}</div>
            </div>
            """, unsafe_allow_html=True)


# ===========================================================================
# TAB 3: EXPLANATIONS
# ===========================================================================

def render_explanations_tab(results: List[Dict]):
    st.markdown('<div class="section-header">🧾 Issue Explanations</div>', unsafe_allow_html=True)

    if not results:
        st.info("Run analysis first to see explanations.")
        return

    # Filter by severity
    severity_filter = st.multiselect(
        "Filter by Severity",
        options=["High", "Medium", "Low"],
        default=["High", "Medium", "Low"],
        key="expl_filter",
    )

    filtered = [r for r in results if r["severity_label"] in severity_filter]

    for r in filtered:
        label = r["severity_label"]
        icon = BUG_TYPE_ICONS.get(r["bug_type"], "🔧")
        accent = get_card_accent(label)

        with st.expander(
            f"{SEVERITY_ICONS[label]} #{r['rank']} — {icon} `{r['signal']}` "
            f"[{BUG_TYPE_LABELS.get(r['bug_type'], r['bug_type'])}] "
            f"  Score: {r['final_score']:.3f}",
            expanded=(label == "High"),
        ):
            cols = st.columns([2, 1])
            with cols[0]:
                st.markdown(
                    f'<div class="explain-card">{r["explanation"]}</div>',
                    unsafe_allow_html=True,
                )
            with cols[1]:
                st.markdown("**Issue Metadata**")
                st.markdown(f"""
                | Field | Value |
                |---|---|
                | Signal | `{r['signal']}` |
                | Module | `{r['module']}` |
                | Bug Type | `{r['bug_type']}` |
                | Location | `{r.get('location', 'N/A')}` |
                | Confidence | `{r['confidence']:.0%}` |
                | Reach Output | `{r['reach_output']}` |
                | Propagation Depth | `{r['propagation_depth']}` |
                | Fanout | `{r['fanout_count']} signals` |
                """)

                if r.get("signal_path"):
                    st.markdown("**Propagation Path**")
                    path = r["signal_path"]
                    path_html = " → ".join(
                        [f'<code style="background:#0f1628;padding:1px 5px;border-radius:3px;color:#60a5fa;">{s}</code>'
                         for s in path]
                    )
                    st.markdown(path_html, unsafe_allow_html=True)


# ===========================================================================
# TAB 4: ML INSIGHTS
# ===========================================================================

def render_ml_tab():
    st.markdown('<div class="section-header">🤖 ML Model Insights</div>', unsafe_allow_html=True)

    try:
        _, model = _get_pipeline()
    except Exception:
        st.warning("Could not load the ML model.")
        return

    c1, c2 = st.columns([1.2, 1])
    with c1:
        st.markdown("**Random Forest Feature Importance**")
        fig = build_feature_importance_chart(model)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    with c2:
        st.markdown("**Model Configuration**")
        st.markdown(f"""
        | Parameter | Value |
        |---|---|
        | Algorithm | Random Forest |
        | Estimators | 150 |
        | Max Depth | 8 |
        | Training Samples | 600 (synthetic) |
        | Features | 7 |
        | Output Classes | Low / Medium / High |
        | Training Accuracy | `{model.train_accuracy:.1%}` |
        """)

        st.markdown("**Scoring Formula**")
        st.markdown("""
        ```
        rule_score =
          0.40 × reach_output
        + 0.25 × (1 / propagation_depth)
        + 0.20 × fanout_norm
        + 0.15 × timing_risk

        final_score =
          0.70 × rule_score
        + 0.30 × ml_score
        ```
        """)

    st.markdown("---")
    st.markdown("**Feature Descriptions**")
    feature_docs = [
        ("bug_type_encoded", "Numeric encoding of bug category (0=unused, 1=undriven, 2=conflict, 3=latch, 4=external)"),
        ("reach_output", "Binary: does the bug signal propagate to any output port? (0 or 1)"),
        ("propagation_depth_norm", "Inverse of shortest BFS path to output. Higher = closer to output."),
        ("fanout_norm", "Normalized fanout count (affected downstream signals / 20, capped at 1)"),
        ("timing_flag", "1 if the bug involves latch risk or clock-related signal"),
        ("module_importance", "Heuristic importance of the module (1.0 = top-level)"),
        ("confidence", "Detector confidence in the reported issue (0.7–0.95)"),
    ]
    for name, desc in feature_docs:
        st.markdown(f"- **`{name}`**: {desc}")


# ===========================================================================
# MAIN APP
# ===========================================================================

def main():
    # Sidebar
    rtl_input, ext_input, analyze_btn = render_sidebar()

    # Hero Banner
    st.markdown("""
    <div class="hero-banner">
      <div class="hero-title">🔬 RTL Bug Prioritization & Impact Analyzer</div>
      <div class="hero-sub">
        Intelligent static analysis · Graph-based propagation · ML-powered severity scoring · Explainable prioritization
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊  Dashboard",
        "🔗  Dependency Graph",
        "🧾  Explanations",
        "🤖  ML Insights",
    ])

    # Session state for results
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None

    if analyze_btn:
        if not rtl_input or len(rtl_input.strip()) < 10:
            st.error("⚠️ Please paste or select Verilog/VHDL code first.")
        else:
            # Parse external issues
            ext_issues = []
            if ext_input.strip():
                try:
                    ext_issues = json.loads(ext_input.strip())
                except json.JSONDecodeError:
                    st.warning("⚠️ External issues JSON is invalid. Ignoring.")

            with st.spinner("🔍 Running full 9-stage analysis pipeline..."):
                t_start = time.time()
                try:
                    result = run_analysis(rtl_input, ext_issues)
                    result["_wall_time"] = round((time.time() - t_start) * 1000, 1)
                    st.session_state.analysis_result = result
                    st.success(
                        f"✅ Analysis complete in {result['_wall_time']:.0f}ms — "
                        f"{result['summary']['total']} issues found."
                    )
                except Exception as e:
                    st.error(f"❌ Analysis failed: {e}")
                    st.exception(e)

    result = st.session_state.analysis_result

    if result is None:
        # Welcome state
        with tab1:
            st.markdown("""
            <div style="text-align:center;padding:4rem 2rem;color:#475569;">
              <div style="font-size:4rem;margin-bottom:1rem;">🔬</div>
              <div style="font-size:1.2rem;font-weight:600;color:#64748b;margin-bottom:.5rem;">
                Ready to analyze your RTL design
              </div>
              <div style="font-size:.85rem;color:#475569;">
                Paste Verilog/VHDL code in the sidebar (or pick an example) and click <b>Analyze RTL</b>
              </div>
            </div>
            """, unsafe_allow_html=True)
        with tab4:
            render_ml_tab()
        return

    results    = result.get("results", [])
    summary    = result.get("summary", {})
    parse_info = result.get("parse_info", {})
    timing     = result.get("timing_ms", {})
    graph_data = result.get("graph_data", {"nodes": [], "edges": []})

    with tab1:
        render_dashboard(results, summary, parse_info, timing)
    with tab2:
        render_graph_tab(graph_data, results)
    with tab3:
        render_explanations_tab(results)
    with tab4:
        render_ml_tab()


if __name__ == "__main__":
    main()
