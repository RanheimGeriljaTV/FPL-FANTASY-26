"""
app.py - FPL Super Optimizer & Analytics Dashboard
Fantasy Premier League (Manager ID: 117526)
Drevet av PuLP MILP-optimeringsmotor, live FPL API og FUT/Panini sports-UI.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import altair as alt
from datetime import datetime, timezone
import dateutil.parser
from collections import Counter

import fpl_api
import pulp_solver
import transfer_tracker

# ---------------------------------------------------------
# Page Configuration & Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="FPL Super Optimizer | Manager 117526",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS: FUT/Panini Sports-UI, Pitch & DarkReader Protection
custom_css = """
<meta name="darkreader-lock">
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800;900&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Top Header */
    .fpl-header {
        background: linear-gradient(135deg, #37003c 0%, #15001a 60%, #00ff87 100%) !important;
        padding: 20px 26px;
        border-radius: 16px;
        margin-bottom: 20px;
        color: #ffffff !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.4);
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #4a154b;
    }
    .fpl-title {
        font-size: 26px;
        font-weight: 800;
        margin: 0;
        color: #ffffff !important;
    }
    .fpl-subtitle {
        font-size: 14px;
        color: #e0d0eb !important;
        margin: 4px 0 0 0;
    }
    
    /* Metric Cards */
    .metric-card {
        background-color: #1a1e2e !important;
        border: 1px solid #333d59 !important;
        border-radius: 14px;
        padding: 14px 16px;
        text-align: center;
        box-shadow: 0 4px 14px rgba(0,0,0,0.3);
    }
    .metric-label {
        font-size: 11px;
        font-weight: 700;
        color: #a5b4fc !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 4px;
    }
    .metric-value {
        font-size: 26px;
        font-weight: 900;
        color: #ffffff !important;
    }
    .metric-sub {
        font-size: 11px;
        color: #00ff87 !important;
        font-weight: 600;
        margin-top: 2px;
    }

    /* Plotly Containers */
    [data-testid="stPlotlyChart"] {
        background-color: #161926 !important;
        border: 1px solid #2d3550 !important;
        border-radius: 14px;
        padding: 8px;
    }
    
    /* Football Pitch (FUT Style, min-height: 1150px) */
    .pitch-container {
        background: radial-gradient(circle at center, #1b5e20 0%, #0d3813 85%, #07220b 100%) !important;
        border: 4px solid #4caf50;
        border-radius: 24px;
        padding: 30px 15px;
        position: relative;
        overflow: hidden;
        min-height: 1150px;
        box-shadow: inset 0 0 60px rgba(0,0,0,0.8), 0 12px 35px rgba(0,0,0,0.6);
        margin: 10px 0 25px 0;
    }
    .pitch-center-circle {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        width: 170px;
        height: 170px;
        border: 2px dashed rgba(255,255,255,0.35);
        border-radius: 50%;
        pointer-events: none;
    }
    .pitch-half-line {
        position: absolute;
        top: 50%;
        left: 0;
        right: 0;
        height: 2px;
        background: rgba(255,255,255,0.35);
        pointer-events: none;
    }
    .pitch-row {
        display: flex;
        justify-content: space-around;
        align-items: center;
        margin-bottom: 26px;
        position: relative;
        z-index: 2;
    }

    /* =========================================================
       AUTHENTIC 90s FOOTBALL CARD IN GLOSSY PROTECTIVE SLEEVE
       ========================================================= */
    .fut-card {
        width: 200px;
        background: radial-gradient(circle at 50% 25%, #182236 0%, #0b0f19 100%) !important;
        border-radius: 14px;
        /* Subtle glossy plastic top-loader sleeve seam & 3D bevel */
        border: 2px solid rgba(255, 255, 255, 0.35) !important;
        box-shadow: 
            0 0 0 1px rgba(255, 255, 255, 0.12),
            0 14px 34px rgba(0, 0, 0, 0.9),
            inset 0 2px 4px rgba(255, 255, 255, 0.35),
            inset 0 -2px 5px rgba(0, 0, 0, 0.6) !important;
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        text-align: center;
        transition: transform 0.35s cubic-bezier(0.2, 0.8, 0.2, 1), box-shadow 0.35s ease, filter 0.3s ease, opacity 0.3s ease;
        margin: 0 4px;
        cursor: pointer;
    }
    
    /* 3D tilt & elevated plastic hover */
    .fut-card:hover {
        transform: translateY(-8px) scale(1.04) rotateX(3deg);
        box-shadow: 
            0 0 0 2px rgba(0, 255, 135, 0.75),
            0 24px 48px rgba(0, 0, 0, 0.96),
            inset 0 3px 6px rgba(255, 255, 255, 0.5) !important;
    }

    /* Plastic top-loader sleeve lip / notch */
    .plastic-sleeve-notch {
        position: absolute;
        top: 0;
        left: 50%;
        transform: translateX(-50%);
        width: 48px;
        height: 4px;
        background: rgba(255, 255, 255, 0.3);
        border-bottom-left-radius: 4px;
        border-bottom-right-radius: 4px;
        box-shadow: 0 1px 2px rgba(0,0,0,0.5);
        z-index: 15;
        pointer-events: none;
    }

    /* Cellophane / Glossy Plastic Light Reflection - Toned down & realistic */
    .plastic-glare-overlay {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            128deg,
            rgba(255, 255, 255, 0.14) 0%,
            rgba(255, 255, 255, 0.04) 18%,
            transparent 35%,
            transparent 65%,
            rgba(255, 255, 255, 0.03) 80%,
            rgba(255, 255, 255, 0.10) 100%
        );
        pointer-events: none;
        z-index: 10;
        mix-blend-mode: screen;
    }

    /* Subtle 90s Holographic Rainbow Prism / Refractor Foil */
    .retro-prism-foil {
        position: absolute;
        inset: 0;
        background: linear-gradient(
            135deg,
            rgba(255, 0, 128, 0.06) 0%,
            rgba(255, 180, 0, 0.07) 25%,
            rgba(0, 255, 200, 0.07) 50%,
            rgba(0, 140, 255, 0.07) 75%,
            rgba(255, 0, 255, 0.06) 100%
        );
        background-size: 250% 250%;
        pointer-events: none;
        z-index: 9;
        mix-blend-mode: screen;
        opacity: 0.25;
        transition: opacity 0.3s ease;
    }
    .fut-card:hover .retro-prism-foil {
        opacity: 0.55;
    }

    /* Moving Plastic Specular Light Beam on Hover */
    .fut-card::after {
        content: '';
        position: absolute;
        top: -60%;
        left: -80%;
        width: 250%;
        height: 220%;
        background: linear-gradient(
            110deg,
            transparent 35%,
            rgba(255, 255, 255, 0.04) 44%,
            rgba(255, 255, 255, 0.32) 48%,
            rgba(255, 255, 255, 0.08) 53%,
            transparent 65%
        );
        transform: rotate(26deg);
        transition: left 0.65s cubic-bezier(0.1, 0.9, 0.2, 1);
        pointer-events: none;
        z-index: 11;
        opacity: 0.45;
    }
    .fut-card:hover::after {
        left: 120%;
        opacity: 0.85;
    }

    /* Clean Card Top Bar in Official Club Colors */
    .fut-card-top-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 5px 8px;
        border-top-left-radius: 12px;
        border-top-right-radius: 12px;
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.6);
        position: relative;
        z-index: 5;
    }
    .fut-top-badge-wrap {
        display: flex;
        align-items: center;
        flex-shrink: 0;
    }
    .fut-club-badge {
        width: 24px;
        height: 24px;
        object-fit: contain;
        filter: drop-shadow(0 2px 4px rgba(0, 0, 0, 0.8));
    }
    .fut-top-team-name {
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-size: 11px;
        font-weight: 900;
        letter-spacing: 0.6px;
        text-transform: uppercase;
        color: #ffffff !important;
        text-shadow: 0 1px 3px rgba(0, 0, 0, 0.9), 1px 1px 0 #000;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding: 0 6px;
        flex-grow: 1;
        text-align: center;
    }
    .fut-pos-badge {
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-size: 11px;
        letter-spacing: 0.5px;
        color: #111827 !important;
        background: linear-gradient(135deg, #fef08a 0%, #eab308 100%) !important;
        padding: 2px 6px;
        border-radius: 5px;
        border: 1px solid #ffffff;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.6);
        flex-shrink: 0;
    }

    /* Captain / VC Badges */
    .card-badge-cap-gold {
        position: absolute;
        top: 36px;
        right: 8px;
        background: linear-gradient(135deg, #ffe066 0%, #d4af37 50%, #997a15 100%) !important;
        color: #1a1200 !important;
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-weight: 900;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.7);
        z-index: 12;
    }
    .card-badge-cap-silver {
        position: absolute;
        top: 36px;
        right: 8px;
        background: linear-gradient(135deg, #ffffff 0%, #cbd5e1 50%, #64748b 100%) !important;
        color: #0f172a !important;
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-weight: 900;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 2px 8px;
        border-radius: 6px;
        border: 1px solid #ffffff;
        box-shadow: 0 2px 8px rgba(0,0,0,0.8), inset 0 1px 0 rgba(255,255,255,0.7);
        z-index: 12;
    }

    /* Prominent Photo Window - Fills Out The Player Cutout */
    .fut-photo-wrap {
        height: 152px;
        width: calc(100% - 12px);
        margin: 4px auto 0 auto;
        position: relative;
        overflow: hidden;
        display: flex;
        justify-content: center;
        align-items: center;
        border-radius: 8px;
        border: 1.5px solid rgba(255, 215, 0, 0.4);
        background: radial-gradient(circle at 50% 25%, rgba(255,255,255,0.14) 0%, rgba(0,0,0,0.78) 100%);
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.8), 0 2px 6px rgba(0,0,0,0.5);
    }
    .spotlight-halo {
        position: absolute;
        width: 130px;
        height: 130px;
        border-radius: 50%;
        top: 8px;
        left: 50%;
        transform: translateX(-50%);
        background: radial-gradient(circle, rgba(255,255,255,0.28) 0%, rgba(255,255,255,0.0) 70%);
        pointer-events: none;
    }
    .fut-player-img {
        width: 100%;
        height: 100%;
        object-fit: cover;
        object-position: center 8%;
        transform: scale(1.22);
        transform-origin: center 22%;
        position: relative;
        z-index: 4;
        filter: drop-shadow(0 6px 14px rgba(0,0,0,0.85));
    }

    /* 90s Angled Name Ribbon */
    .fut-name {
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-size: 15px;
        font-weight: 900;
        letter-spacing: 0.8px;
        text-transform: uppercase;
        color: #ffffff !important;
        text-shadow: 1px 1px 0 #000, -1px -1px 0 #000, 1px -1px 0 #000, -1px 1px 0 #000, 0 3px 6px rgba(0,0,0,0.9);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        padding: 2px 6px;
        margin: 4px 6px 0 6px;
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.95) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(255, 215, 0, 0.5);
        border-radius: 5px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.6);
        position: relative;
        z-index: 5;
    }
    .fut-team-cost {
        font-size: 11px;
        font-weight: 700;
        color: #cbd5e1 !important;
        margin: 2px 0 3px 0;
        text-shadow: 0 1px 2px #000;
        position: relative;
        z-index: 5;
    }

    /* 90s Collectible Stat Box (Power Rating / xP) */
    .fut-hero-box {
        background: linear-gradient(180deg, rgba(15, 23, 42, 0.95) 0%, rgba(2, 6, 23, 0.98) 100%) !important;
        border-top: 1.5px solid rgba(255, 215, 0, 0.5);
        padding: 5px 4px 6px 4px;
        margin-top: auto;
        box-shadow: inset 0 2px 6px rgba(0,0,0,0.7);
        position: relative;
        z-index: 5;
    }
    .fut-hero-val {
        font-family: 'Impact', 'Arial Black', sans-serif;
        font-size: 24px;
        font-weight: 900;
        letter-spacing: 0.5px;
        color: #00ff87 !important;
        line-height: 1.05;
        text-shadow: 0 0 10px rgba(0, 255, 135, 0.6), 1px 1px 2px #000;
    }
    .fut-hero-label {
        font-family: 'Arial Black', sans-serif;
        font-size: 9px;
        font-weight: 900;
        color: #facc15 !important;
        text-transform: uppercase;
        letter-spacing: 0.8px;
        text-shadow: 0 1px 2px #000;
    }

    /* Live Glow Animation - Green/Red for Playing Now */
    @keyframes liveGlow {
        0% { box-shadow: 0 0 10px rgba(34, 197, 94, 0.7); border-color: #22c55e !important; }
        50% { box-shadow: 0 0 24px rgba(34, 197, 94, 1); border-color: #4ade80 !important; }
        100% { box-shadow: 0 0 10px rgba(34, 197, 94, 0.7); border-color: #22c55e !important; }
    }
    .card-live {
        animation: liveGlow 1.8s infinite;
        border: 2px solid #22c55e !important;
    }
    .card-finished {
        border: 2px solid rgba(255, 215, 0, 0.6) !important;
    }

    /* Unplayed / Yet to Play: Striking visual contrast */
    .card-unplayed {
        opacity: 0.52 !important;
        filter: grayscale(80%) contrast(85%) brightness(0.7) !important;
        border: 2px dashed rgba(148, 163, 184, 0.45) !important;
        background: radial-gradient(circle at 50% 25%, #111624 0%, #060910 100%) !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.6) !important;
    }
    .card-unplayed .fut-hero-val {
        color: #64748b !important;
        text-shadow: none !important;
    }
    .card-unplayed .fut-card-top-bar {
        filter: grayscale(60%) brightness(0.7) !important;
    }
    .card-unplayed:hover {
        opacity: 1 !important;
        filter: grayscale(0%) contrast(100%) brightness(1) !important;
        transform: translateY(-8px) scale(1.04) rotateX(3deg);
        border: 2px solid rgba(255, 255, 255, 0.65) !important;
        box-shadow: 0 18px 40px rgba(0, 0, 0, 0.9) !important;
    }

    /* English Badges */
    .pill-live {
        font-size: 11px;
        font-weight: 800;
        color: #ffffff !important;
        background: #dc2626 !important;
        border: 1px solid #f87171 !important;
        padding: 2px 7px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
        box-shadow: 0 2px 6px rgba(220, 38, 38, 0.6);
    }
    .pill-ft {
        font-size: 11px;
        font-weight: 800;
        color: #00ff87 !important;
        background: #0f172a !important;
        border: 1px solid #10b981 !important;
        padding: 2px 7px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
    }
    .pill-unplayed {
        font-size: 10px;
        font-weight: 800;
        color: #cbd5e1 !important;
        background: #1e293b !important;
        border: 1px dashed #64748b !important;
        padding: 2px 7px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
        letter-spacing: 0.5px;
    }

    /* Badges */
    .player-fixture {
        font-size: 11px;
        font-weight: 700;
        color: #f8fafc !important;
        background: #1e293b !important;
        border: 1px solid #475569 !important;
        padding: 2px 7px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
    }
    .bgw-pill {
        background-color: #dc2626 !important;
        border: 1px solid #f87171 !important;
        color: #ffffff !important;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
    }
    .dgw-pill {
        background-color: #16a34a !important;
        border: 1px solid #86efac !important;
        color: #ffffff !important;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
    }
    .manual-badge {
        background-color: #2563eb !important;
        border: 1px solid #93c5fd !important;
        color: #ffffff !important;
        font-size: 10px;
        font-weight: 800;
        padding: 2px 6px;
        border-radius: 6px;
        margin: 2px auto;
        display: inline-block;
    }
    .injury-pill {
        background-color: rgba(239, 68, 68, 0.25) !important;
        border: 1px solid #ef4444 !important;
        color: #fca5a5 !important;
        font-size: 10px;
        font-weight: 700;
        padding: 1px 6px;
        border-radius: 8px;
        margin: 2px auto;
        display: inline-block;
    }
    
    /* Bench Bar */
    .bench-container {
        background-color: #121624 !important;
        border: 1px solid #2d3748 !important;
        border-radius: 18px;
        padding: 20px 15px;
        margin-bottom: 25px;
    }
    .bench-title {
        font-size: 13px;
        font-weight: 800;
        color: #a5b4fc !important;
        text-transform: uppercase;
        margin-bottom: 14px;
        letter-spacing: 0.5px;
    }

    /* Hide off-screen Streamlit trigger buttons */
    div[class*="st-key-btn_trigger_tab"] {
        display: none !important;
    }
</style>
"""
st.html(custom_css)

def get_pitch_card_script() -> str:
    """
    Returnerer en klientskript-lytter som fanger opp klikk på spillerkort (bane & benk)
    og trigger modal-dialogen umiddelbart.
    """
    return """
    <script>
    (function() {
        window.triggerCardInspect = function(pid, tab) {
            if (!pid) return false;
            var selList = [
                '.st-key-btn_trigger_tab' + tab + '_' + pid + ' button',
                '.st-key-btn_trigger_tab0_' + pid + ' button',
                '.st-key-btn_trigger_tab1_' + pid + ' button'
            ];
            for (var i = 0; i < selList.length; i++) {
                var btn = (window.parent && window.parent.document) ? 
                          (window.parent.document.querySelector(selList[i]) || document.querySelector(selList[i])) : 
                          document.querySelector(selList[i]);
                if (btn) {
                    btn.click();
                    return true;
                }
            }
            return false;
        };

        function onCardClick(e) {
            var card = e.target.closest('[data-player-id]');
            if (!card) return;
            e.preventDefault();
            e.stopPropagation();
            var pid = card.getAttribute('data-player-id');
            var tab = card.getAttribute('data-tab') || '0';
            window.triggerCardInspect(pid, tab);
        }

        var doc = (window.parent && window.parent.document) ? window.parent.document : document;
        if (!window._pitchCardClickListenerActive) {
            window._pitchCardClickListenerActive = true;
            doc.addEventListener('click', onCardClick, true);
            doc.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    var card = e.target.closest('[data-player-id]');
                    if (card) {
                        onCardClick(e);
                    }
                }
            }, true);
        }
    })();
    </script>
    """

st.html(get_pitch_card_script())

# ---------------------------------------------------------
# Plotly High-Contrast Helper
# ---------------------------------------------------------
def apply_hc_theme(fig, title: str = "", height: int = 450):
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=16, color="#ffffff", family="Inter, Segoe UI, sans-serif")
        ),
        template="plotly_dark",
        paper_bgcolor="#161926",
        plot_bgcolor="#1f2438",
        font=dict(color="#ffffff", size=12, family="Inter, Segoe UI, sans-serif"),
        height=height,
        margin=dict(l=45, r=30, t=55, b=45),
        xaxis=dict(
            gridcolor="#2d3550",
            zerolinecolor="#455178",
            tickfont=dict(color="#ffffff", size=11),
            title_font=dict(color="#ffffff", size=13)
        ),
        yaxis=dict(
            gridcolor="#2d3550",
            zerolinecolor="#455178",
            tickfont=dict(color="#ffffff", size=11),
            title_font=dict(color="#ffffff", size=13)
        ),
        legend=dict(
            font=dict(color="#ffffff", size=12),
            bgcolor="#1a1e2e",
            bordercolor="#3d4666",
            borderwidth=1
        )
    )
    return fig

# ---------------------------------------------------------
# Sidebar Controls
# ---------------------------------------------------------
st.sidebar.image("https://fantasy.premierleague.com/static/libs/fpl-ui/images/badge-100.png", width=70)
st.sidebar.markdown("### ⚙️ Kontrollpanel")

# ---------------------------------------------------------
# Dynamic Manager ID via Query Parameters (?id=... or ?manager_id=...)
# ---------------------------------------------------------
query_id_val = None
if "id" in st.query_params:
    try:
        query_id_val = int(st.query_params["id"])
    except (ValueError, TypeError):
        pass
elif "manager_id" in st.query_params:
    try:
        query_id_val = int(st.query_params["manager_id"])
    except (ValueError, TypeError):
        pass

if "current_manager_id" not in st.session_state:
    st.session_state.current_manager_id = query_id_val if query_id_val else 117526
elif query_id_val and query_id_val != st.session_state.current_manager_id:
    st.session_state.current_manager_id = query_id_val

manager_id = st.sidebar.number_input(
    "Manager ID",
    value=int(st.session_state.current_manager_id),
    step=1,
    help="Ditt FPL Manager ID. Skriv inn ditt ID for å hente ditt lag og dine ligaer."
)

if int(manager_id) != st.session_state.current_manager_id:
    st.session_state.current_manager_id = int(manager_id)
    st.query_params["id"] = str(manager_id)
    if "manual_transfers" in st.session_state:
        del st.session_state["manual_transfers"]
    st.rerun()
elif str(st.query_params.get("id")) != str(manager_id):
    st.query_params["id"] = str(manager_id)

deadline_info = fpl_api.get_deadline_info()
if deadline_info.get("deadline_iso"):
    deadline_dt = dateutil.parser.isoparse(deadline_info["deadline_iso"])
    now_dt = datetime.now(timezone.utc)
    diff = deadline_dt - now_dt
    
    if diff.total_seconds() > 0:
        days = diff.days
        hours = int(diff.seconds // 3600)
        minutes = int((diff.seconds % 3600) // 60)
        time_str = f"{days}d {hours}t {minutes}m"
    else:
        time_str = "Frist passert"

    deadline_html = f"""<div style="background:#241638; border:1px solid #9333ea; padding:8px 12px; border-radius:10px; font-size:12px; color:#e9d5ff; font-weight:600; margin-bottom:15px;">⏳ <b>{deadline_info['name']} Frist:</b><br>{time_str} ({deadline_dt.strftime('%d.%m kl. %H:%M')})</div>"""
    st.sidebar.html(deadline_html)

st.sidebar.markdown("---")
st.sidebar.markdown("#### 🎯 PuLP MILP-Parametre")

horizon = st.sidebar.slider(
    "Planleggingshorisont (Gameweeks)",
    min_value=1,
    max_value=5,
    value=3,
    help="Hvor mange runder fremover i tid solveren skal optimalisere overganger for."
)

allow_hits = st.sidebar.toggle("Evaluer Minuspoeng (-4 Hits)", value=False)

# ---------------------------------------------------------
# Data Fetching & Session State
# ---------------------------------------------------------
try:
    mgr_summary = fpl_api.get_manager_summary(manager_id)
except Exception as e:
    st.error(f"Feil ved henting av FPL-data for Manager ID {manager_id}: {e}")
    st.stop()

if "modal_player_id" not in st.session_state:
    st.session_state.modal_player_id = None

static_data = fpl_api.get_bootstrap_static()
base_squad = fpl_api.get_detailed_squad(manager_id)
all_players_df = fpl_api.get_all_players_database(horizon=5)

if "manual_transfers" not in st.session_state:
    next_gw_val = mgr_summary.get("next_gw", mgr_summary.get("current_gw", 1) + 1)
    st.session_state.manual_transfers = transfer_tracker.get_active_simulated_transfers(
        base_squad=base_squad,
        all_players_df=all_players_df,
        next_gw=next_gw_val,
        manager_id=manager_id
    )

# Bygg aktiv tropp basert på eventuelle manuelle bytter
active_squad = [dict(p) for p in base_squad]
current_bank = mgr_summary["bank"]

for tr in st.session_state.manual_transfers:
    out_id = tr["out"].get("element_id") or tr["out"].get("id")
    in_p = tr["in"]
    current_bank += (tr["out"]["cost"] - in_p["cost"])
    for idx, p in enumerate(active_squad):
        pid = p.get("element_id") or p.get("id")
        if pid == out_id:
            active_squad[idx] = {
                "element_id": in_p["id"],
                "id": in_p["id"],
                "name": in_p["name"],
                "full_name": in_p.get("full_name", in_p["name"]),
                "position": in_p["position"],
                "position_id": p.get("position_id", 1),
                "team_id": in_p.get("team_id", 1),
                "team_name": in_p.get("team", ""),
                "team_short": in_p.get("team", ""),
                "cost": in_p["cost"],
                "form": in_p.get("form", 0.0),
                "ep_next": in_p.get("ep_next", 0.0),
                "xp_3gw": in_p.get("xp_3gw", 0.0),
                "chance_of_playing": in_p.get("chance_of_playing", 100),
                "status": in_p.get("status", "a"),
                "news": "",
                "is_starter": p.get("is_starter", True),
                "multiplier": p.get("multiplier", 1),
                "is_captain": p.get("is_captain", False),
                "is_vice_captain": p.get("is_vice_captain", False),
                "pitch_order": p.get("pitch_order", 1),
                "fixture": in_p.get("next_fixture", ""),
                "is_blank": in_p.get("is_blank_next", False),
                "is_double": in_p.get("is_double_next", False),
                "photo_url": in_p.get("photo_url", ""),
                "legacy_photo_url": in_p.get("legacy_photo_url", ""),
                "badge_url": in_p.get("badge_url", ""),
                "club_gradient": in_p.get("club_gradient", ""),
                "is_manual_transfer": True
            }
            break
current_bank = round(current_bank, 1)

# Main Header
header_html = f"""
<div class="fpl-header">
    <div>
        <h1 class="fpl-title">{mgr_summary['team_name']}</h1>
        <p class="fpl-subtitle">Manager: <b>{mgr_summary['manager_name']}</b> | ID: <b>{manager_id}</b> | Sesong 2026/27</p>
    </div>
    <div style="text-align: right;">
        <span style="background: rgba(255,255,255,0.2); padding: 8px 16px; border-radius: 20px; font-weight: 800; font-size: 14px; border: 1px solid #00ff87; color: #ffffff;">
            Gameweek {mgr_summary['current_gw']} 🟢
        </span>
    </div>
</div>
"""
st.html(header_html)

# KPI Cards
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.html(f"""<div class="metric-card"><div class="metric-label">Sammenlagtpoeng</div><div class="metric-value">{mgr_summary['total_points']}</div><div class="metric-sub">Siste GW: +{mgr_summary['last_gw_points']} pts</div></div>""")

with col2:
    st.html(f"""<div class="metric-card"><div class="metric-label">Overall Rank (OR)</div><div class="metric-value">{mgr_summary['overall_rank']:,}</div><div class="metric-sub">Topp {round((mgr_summary['overall_rank']/10400000)*100, 1)}% globalt</div></div>""")

with col3:
    st.html(f"""<div class="metric-card"><div class="metric-label">Lagverdi</div><div class="metric-value">£{mgr_summary['team_value']:.1f}m</div><div class="metric-sub">Troppens markedsverdi</div></div>""")

with col4:
    bank_sub = f"Opprinnelig: £{mgr_summary['bank']:.1f}m" if st.session_state.manual_transfers else "ITB (Tilgjengelig kapital)"
    st.html(f"""<div class="metric-card"><div class="metric-label">Penger i Banken</div><div class="metric-value" style="color: #00ff87 !important;">£{current_bank:.1f}m</div><div class="metric-sub">{bank_sub}</div></div>""")

# ---------------------------------------------------------
# Card HTML Builder (FUT / Panini Style)
# ---------------------------------------------------------
def build_fut_card_html(p, mode="xp", tab_index="1"):
    cap_badge = ""
    p_id = p.get("element_id") or p.get("id") or ""
    p_name = p.get("name", "")
    p_team = p.get("team_short", p.get("team", ""))
    if p.get("is_captain"):
        cap_badge = '<div class="card-badge-cap-gold">👑 C (2x)</div>'
    elif p.get("is_vice_captain"):
        cap_badge = '<div class="card-badge-cap-silver">🥈 VC</div>'

    # Status / Fixture Pill (English standard terms)
    if mode == "live":
        m_finished = p.get("match_finished", False)
        m_live = p.get("match_live", False)
        m_started = p.get("match_started", False)
        has_played = p.get("played", False) or p.get("minutes", 0) > 0
        mins = p.get("minutes", 0)
        pts = p.get("effective_points", 0)

        if m_finished or mins >= 90:
            card_extra_class = "card-finished"
            if has_played:
                status_pill = f'<div class="pill-ft">⏱️ FT ({mins}\')</div>'
                hero_label_str = "FINAL POINTS (FULL TIME)"
                hero_val_str = f"{pts}"
            else:
                status_pill = '<div class="pill-unplayed">⛔ DID NOT PLAY</div>'
                hero_label_str = "DID NOT PLAY (0')"
                hero_val_str = "0"
        elif m_live:
            card_extra_class = "card-live"
            m_mins = p.get("match_minutes") or mins
            status_pill = f'<div class="pill-live">🔴 LIVE {m_mins}\'</div>'
            hero_label_str = "LIVE POINTS (IN PLAY)"
            hero_val_str = f"{pts}"
        else:
            card_extra_class = "card-unplayed"
            status_pill = '<div class="pill-unplayed">⏳ YET TO PLAY</div>'
            hero_label_str = "YET TO PLAY"
            hero_val_str = "-"
    else:
        card_extra_class = ""
        if p.get("is_blank"):
            status_pill = '<div class="bgw-pill">❌ BLANK GW</div>'
            card_extra_class = "card-blank"
        elif p.get("is_double"):
            status_pill = f'<div class="dgw-pill">🔥 DGW ({p.get("fixture", "")})</div>'
            card_extra_class = "card-double"
        else:
            status_pill = f'<div class="player-fixture">⚔️ {p.get("fixture", "")}</div>'
        hero_val_str = f"{p.get('ep_next', 0):.1f}"
        hero_label_str = "PROJECTED xP"

    manual_badge = '<div class="manual-badge">🆕 SIMULATED TRANSFER</div>' if p.get("is_manual_transfer") else ''
    
    injury_badge = ""
    if p.get("chance_of_playing") is not None and p["chance_of_playing"] < 100:
        injury_badge = f'<div class="injury-pill">⚠️ {p["chance_of_playing"]}% DOUBT</div>'
    elif p.get("status") not in ["a", None]:
        injury_badge = '<div class="injury-pill">🏥 OUT</div>'

    # Gradient & Badge
    club_grad = p.get("club_gradient") or "linear-gradient(135deg, #37003c 0%, #00ff87 100%)"
    badge_img = f'<img src="{p.get("badge_url")}" class="fut-club-badge"/>' if p.get("badge_url") else ''
    photo_src = p.get("photo_url") or "https://fantasy.premierleague.com/static/libs/fpl-ui/images/badge-100.png"
    legacy_src = p.get("legacy_photo_url") or ""
    if not legacy_src and "premierleague25" in photo_src:
        code_part = photo_src.split("/")[-1].replace(".png", "")
        legacy_src = f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{code_part}.png"

    # Mini Live Events Pill
    live_events_html = ""
    if mode == "live" and p.get("played"):
        ev_items = []
        if p.get("goals", 0) > 0:
            ev_items.append(f"⚽ {p['goals']}")
        if p.get("assists", 0) > 0:
            ev_items.append(f"👟 {p['assists']}")
        if p.get("clean_sheets", 0) > 0:
            ev_items.append("🧤 CS")
        if p.get("bonus", 0) > 0:
            ev_items.append(f"⭐ {p['bonus']}")
        if p.get("yellow_cards", 0) > 0:
            ev_items.append("🟨")
        if p.get("red_cards", 0) > 0:
            ev_items.append("🟥")
        if ev_items:
            live_events_html = f'<div style="font-size: 11px; font-weight: 800; color: #facc15; margin-bottom: 2px;">{" ".join(ev_items)}</div>'

    t_code = p.get("team_code", 1)
    team_display_name = p.get("team_name") or p.get("team_short") or p.get("team", "")

    return f"""
    <div class="fut-card {card_extra_class} pitch-card-link" role="button" tabindex="0" data-player-id="{p_id}" data-tab="{tab_index}" data-player-name="{p_name}" data-player-team="{p_team}">
        <div class="plastic-sleeve-notch"></div>
        <div class="plastic-glare-overlay"></div>
        <div class="retro-prism-foil"></div>
        <div class="fut-card-top-bar" style="background: {club_grad};">
            <div class="fut-top-badge-wrap">{badge_img}</div>
            <div class="fut-top-team-name">{team_display_name}</div>
            <span class="fut-pos-badge">{p.get('position')}</span>
        </div>
        {cap_badge}
        <div class="fut-photo-wrap">
            <div class="spotlight-halo"></div>
            <img src="{photo_src}" class="fut-player-img" onerror="if ('{legacy_src}' && this.src !== '{legacy_src}') {{ this.src = '{legacy_src}'; }} else {{ this.onerror = null; this.src = 'https://fantasy.premierleague.com/dist/img/shirts/standard/shirt_{t_code}-66.webp'; }}"/>
        </div>
        <div class="fut-name">{p.get('name')}</div>
        <div class="fut-team-cost">{p.get('team_short', p.get('team', ''))} | £{p.get('cost', 0):.1f}m</div>
        {status_pill}
        {manual_badge}
        {injury_badge}
        {live_events_html}
        <div class="fut-hero-box">
            <div class="fut-hero-val">{hero_val_str}</div>
            <div class="fut-hero-label">⚡ {hero_label_str}</div>
        </div>
    </div>
    """

# =========================================================
# SPILLERPROFIL & DYBDEANALYSE-MODAL (@st.dialog)
# =========================================================
@st.dialog("⚽ Spillerprofil & Dybdeanalyse", width="large")
def render_player_dialog(player_id: int, df_players: pd.DataFrame, bootstrap: dict, manager_id: int = 117526):
    matching = df_players[df_players["id"] == player_id]
    if matching.empty:
        elem_match = [e for e in bootstrap.get("elements", []) if e["id"] == player_id]
        if not elem_match:
            st.warning(f"Fant ikke spillerdata for ID {player_id}.")
            return
        elem = elem_match[0]
        teams_map = {t["id"]: t for t in bootstrap.get("teams", [])}
        team_obj = teams_map.get(elem.get("team"), {})
        p = {
            "id": elem["id"],
            "name": elem.get("web_name", ""),
            "full_name": f"{elem.get('first_name', '')} {elem.get('second_name', '')}".strip(),
            "team_short": team_obj.get("short_name", ""),
            "team_name": team_obj.get("name", ""),
            "position": {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}.get(elem.get("element_type"), "MID"),
            "cost": elem.get("now_cost", 0) / 10.0,
            "cost_change_start": elem.get("cost_change_start", 0) / 10.0,
            "total_points": elem.get("total_points", 0),
            "selected_by_percent": float(elem.get("selected_by_percent", 0.0)),
            "form": float(elem.get("form", 0.0)),
            "ep_next": float(elem.get("ep_next", 0.0)),
            "status": elem.get("status", "a"),
            "news": elem.get("news", ""),
            "chance_of_playing": elem.get("chance_of_playing_next_round"),
            "dreamteam_count": elem.get("dreamteam_count", 0),
            "transfers_in_event": elem.get("transfers_in_event", 0),
            "transfers_out_event": elem.get("transfers_out_event", 0),
            "next_fixture": "-",
            "next_fdr": 3,
            "photo_url": f"https://resources.premierleague.com/premierleague25/photos/players/500x500/{elem.get('code')}.png",
            "legacy_photo_url": f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{elem.get('code')}.png"
        }
    else:
        p = matching.iloc[0].to_dict()

    # Hent kjøps- og salgshistorikk for denne spilleren
    tx_history = transfer_tracker.get_player_transfer_history(player_id, manager_id)
    bought_gws = tx_history.get("bought", [])
    sold_gws = tx_history.get("sold", [])

    with st.spinner("Henter spillerhistorikk fra FPL..."):
        summary = fpl_api.get_element_summary(player_id) or {}
    history = summary.get("history", [])
    upcoming_fixtures = summary.get("fixtures", [])
    past_seasons = summary.get("history_past", [])

    # Klubb-stil
    t_short = p.get("team_short", "")
    club = fpl_api.PL_CLUB_COLORS.get(t_short, {
        "primary": "#37003c", "secondary": "#00ff87", "gradient": "linear-gradient(135deg, #37003c 0%, #00ff87 100%)", "text": "#ffffff"
    })

    fdr_labels = {1: "1/5 (Svært lett)", 2: "2/5 (Lett)", 3: "3/5 (Middels)", 4: "4/5 (Vanskelig)", 5: "5/5 (Svært tøff)"}
    fdr_val = int(p.get("next_fdr", 3))
    fdr_desc = fdr_labels.get(fdr_val, f"{fdr_val}/5")

    full_name = p.get("full_name") or f"{p.get('name', '')}"
    photo_url = p.get("photo_url", "")
    legacy_url = p.get("legacy_photo_url", "")
    photo_tag = f'<img src="{photo_url}" onerror="this.onerror=null; this.src=\'{legacy_url}\';" style="width:100%; height:100%; object-fit:cover; object-position:center 8%;" />' if photo_url else ''

    # Header badges: Status, Dream Team, Kjøpt/Solgt
    status = p.get("status", "a")
    cop = p.get("chance_of_playing")
    status_badge = ""
    if status in ["i", "s", "u"]:
        status_badge = f'<span style="background:#fee2e2; color:#991b1b; font-size:11px; font-weight:800; border-radius:6px; padding:2px 7px; border:1px solid #f87171;" title="{p.get("news", "")}">🔴 Ute: {p.get("news", "")}</span>'
    elif status == "d" or (cop is not None and cop < 100):
        cop_str = f"{cop}% " if cop is not None else ""
        status_badge = f'<span style="background:#fef3c7; color:#92400e; font-size:11px; font-weight:800; border-radius:6px; padding:2px 7px; border:1px solid #fcd34d;" title="{p.get("news", "")}">🟡 Usikker ({cop_str}): {p.get("news", "")}</span>'

    dt_count = int(p.get("dreamteam_count", 0))
    dt_badge = f'<span style="background:linear-gradient(135deg,#f59e0b,#d97706); color:white; font-size:11px; font-weight:800; border-radius:6px; padding:2px 7px;">⭐ Ukens Lag ({dt_count}x)</span>' if dt_count > 0 else ""

    tx_badges = []
    for g in bought_gws:
        tx_badges.append(f'<span style="background:#dcfce7; color:#15803d; font-size:11px; font-weight:800; border-radius:6px; padding:2px 7px; border:1px solid #86efac;" title="Kjøpt i Runde {g}">🟢 Kjøpt i GW {g}</span>')
    for g in sold_gws:
        tx_badges.append(f'<span style="background:#fee2e2; color:#b91c1c; font-size:11px; font-weight:800; border-radius:6px; padding:2px 7px; border:1px solid #fca5a5;" title="Solgt i Runde {g}">🔴 Solgt i GW {g}</span>')
    tx_badge_str = " ".join(tx_badges)

    header_html = (
        f'<div style="background: #1e293b; border: 1px solid #334155; border-radius: 14px; padding: 12px 16px; margin-bottom: 12px; box-shadow: 0 4px 14px rgba(0,0,0,0.25);">'
        f'<div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;">'
        f'<div style="display: flex; align-items: center; gap: 14px;">'
        f'<div style="width: 64px; height: 64px; border-radius: 50%; overflow: hidden; border: 2px solid {club["primary"]}; background: #0b0f19; flex-shrink: 0; box-shadow: 0 2px 8px rgba(0,0,0,0.4);">{photo_tag}</div>'
        f'<div>'
        f'<div style="display: flex; align-items: center; gap: 8px; flex-wrap: wrap;">'
        f'<span style="font-size: 20px; font-weight: 800; color: #ffffff;">{p.get("name", "")}</span>'
        f'<span style="background: {club["primary"]}; color: {club["text"]}; font-size: 11px; font-weight: 800; border-radius: 4px; padding: 2px 7px;">{p.get("team_short", "")}</span>'
        f'<span style="background: rgba(255,255,255,0.12); color: #f8fafc; font-size: 11px; font-weight: 700; border-radius: 4px; padding: 2px 7px;">{p.get("position", "")}</span>'
        f'</div>'
        f'<div style="font-size: 13px; color: #94a3b8; margin-top: 2px;">{full_name} • {p.get("team_name", p.get("team_short", ""))}</div>'
        f'<div style="display: flex; gap: 6px; margin-top: 5px; flex-wrap: wrap;">{status_badge} {dt_badge} {tx_badge_str}</div>'
        f'</div></div>'
        f'<div style="text-align: right;">'
        f'<div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; font-weight: 700;">Neste Kamp</div>'
        f'<div style="font-size: 14px; font-weight: 800; color: #f8fafc;">{p.get("next_fixture", "-")} • <span style="font-size: 12px; color: #facc15;">FDR {fdr_val}/5</span></div>'
        f'</div></div></div>'
    )
    st.html(header_html)

    # 4 Nøkkelmetrikker
    m1, m2, m3, m4 = st.columns(4)
    cost_chg = p.get('cost_change_start', 0)
    cost_chg_str = f"+£{cost_chg:.1f}m" if cost_chg > 0 else (f"-£{abs(cost_chg):.1f}m" if cost_chg < 0 else "£0.0m")
    with m1:
        st.metric("Pris", f"£{p.get('cost', 0):.1f}m", cost_chg_str)
    with m2:
        ppg = p.get('total_points', 0) / max(1, len(history)) if history else 0.0
        st.metric("Totalpoeng", f"{p.get('total_points', 0)} pts", f"{ppg:.1f} PPG")
    with m3:
        st.metric("Eierandel", f"{p.get('selected_by_percent', 0):.1f}%", f"Form: {p.get('form', '-')}")
    with m4:
        st.metric("xP Neste GW", f"{p.get('ep_next', 0):.1f}", f"Motstand: {fdr_desc}")

    # Bygg historikk-dataframe
    teams_dict = {t["id"]: t["short_name"] for t in bootstrap.get("teams", [])}
    rows = []
    for h in history:
        pts = h.get("total_points", 0)
        cat = 'Topp (≥8)' if pts >= 8 else ('God (5-7)' if pts >= 5 else ('Middels (2-4)' if pts >= 2 else 'Blank (0-1)'))
        opp_id = h.get("opponent_team")
        opp_short = teams_dict.get(opp_id, f"Lag {opp_id}")
        venue = "H" if h.get("was_home") else "B"
        score = f"{h.get('team_h_score', 0)}-{h.get('team_a_score', 0)}" if h.get('was_home') else f"{h.get('team_a_score', 0)}-{h.get('team_h_score', 0)}"
        gw_num = int(h.get("round", 0))
        
        tx_tag = "-"
        if gw_num in bought_gws and gw_num in sold_gws:
            tx_tag = "🟢 Kjøpt / 🔴 Solgt"
        elif gw_num in bought_gws:
            tx_tag = "🟢 Kjøpt"
        elif gw_num in sold_gws:
            tx_tag = "🔴 Solgt"

        rows.append({
            "GW": f"GW {gw_num}",
            "gw_num": gw_num,
            "Status": tx_tag,
            "Kamp": f"vs {opp_short} ({venue}) [{score}]",
            "Motstander": f"{opp_short} ({venue})",
            "Poeng": pts,
            "Pts": pts,
            "Min": h.get("minutes", 0),
            "Mål ⚽": h.get("goals_scored", 0),
            "Ass 👟": h.get("assists", 0),
            "CS 🧤": "Ja" if h.get("clean_sheets", 0) > 0 else "Nei",
            "Bonus ⭐": h.get("bonus", 0),
            "xG": round(float(h.get("expected_goals", 0.0) or 0.0), 2),
            "xA": round(float(h.get("expected_assists", 0.0) or 0.0), 2),
            "BPS": h.get("bps", 0),
            "🟨": h.get("yellow_cards", 0),
            "🟥": h.get("red_cards", 0),
            "Pris": round(h.get("value", 0) / 10.0, 1),
            "Eiere": h.get("selected", 0),
            "Kategori": cat,
            "was_home": h.get("was_home", True)
        })
    df_hist = pd.DataFrame(rows)

    sub_tab_graphs, sub_tab_split, sub_tab_hist, sub_tab_fix, sub_tab_past = st.tabs([
        "📈 Sesonggrafer",
        "⚔️ Hjemme vs Borte & Nøkkeltall",
        "📋 Kamp-for-Kamp Historikk",
        "📅 Kommende Kamper (FDR)",
        "📜 Tidligere Sesonger"
    ])

    with sub_tab_graphs:
        if not df_hist.empty:
            st.markdown("##### 📊 Poeng per Gameweek")
            bar_chart = alt.Chart(df_hist).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                x=alt.X('GW:O', sort=alt.SortField('gw_num', order='ascending'), title='Gameweek (Runde)'),
                y=alt.Y('Pts:Q', title='Poeng i Runden'),
                color=alt.Color('Kategori:N', scale=alt.Scale(
                    domain=['Topp (≥8)', 'God (5-7)', 'Middels (2-4)', 'Blank (0-1)'],
                    range=['#10b981', '#3b82f6', '#f59e0b', '#ef4444']
                ), legend=alt.Legend(title="Kategori", orient="top")),
                tooltip=[
                    alt.Tooltip('GW:N', title='Runde'),
                    alt.Tooltip('Status:N', title='Overgangsstatus'),
                    alt.Tooltip('Kamp:N', title='Kamp'),
                    alt.Tooltip('Pts:Q', title='Poeng'),
                    alt.Tooltip('Min:Q', title='Minutter spilt'),
                    alt.Tooltip('Mål ⚽:Q', title='Mål'),
                    alt.Tooltip('Ass 👟:Q', title='Målgivende'),
                    alt.Tooltip('CS 🧤:N', title='Clean Sheet'),
                    alt.Tooltip('xG:Q', title='xG'),
                    alt.Tooltip('xA:Q', title='xA'),
                    alt.Tooltip('Bonus ⭐:Q', title='Bonuspoeng')
                ]
            ).properties(height=260)

            ppg_val = float(ppg)
            if ppg_val > 0:
                rule = alt.Chart(pd.DataFrame({'ppg': [ppg_val]})).mark_rule(
                    color='#f97316', strokeDash=[5, 5], size=2
                ).encode(
                    y='ppg:Q',
                    tooltip=[alt.Tooltip('ppg:Q', title='Sesongsnitt (PPG)')]
                )
                bar_chart = bar_chart + rule

            st.altair_chart(bar_chart, width="stretch")
            st.caption(f"💡 Oransje stiplet linje viser spillerens sesongsnitt på **{ppg_val:.1f} poeng per kamp**.")

            st.markdown("---")
            st.markdown("##### 📈 Prisutvikling & Eierandel over Sesongen")
            c_p1, c_p2 = st.columns(2)
            with c_p1:
                price_base = alt.Chart(df_hist).encode(
                    x=alt.X('GW:O', sort=alt.SortField('gw_num', order='ascending'), title='Runde')
                )
                price_line = price_base.mark_line(color='#3b82f6', strokeWidth=3).encode(
                    y=alt.Y('Pris:Q', scale=alt.Scale(zero=False), title='Pris (£m)')
                )
                price_points = price_base.mark_circle(size=55, color='#1d4ed8').encode(
                    y=alt.Y('Pris:Q', scale=alt.Scale(zero=False)),
                    tooltip=[
                        alt.Tooltip('GW:N', title='Runde'),
                        alt.Tooltip('Status:N', title='Status / Overgang'),
                        alt.Tooltip('Pris:Q', title='Pris (£m)'),
                        alt.Tooltip('Kamp:N', title='Kamp')
                    ]
                )

                df_tx_dots = df_hist[df_hist['Status'] != "-"].copy()
                if not df_tx_dots.empty:
                    df_tx_dots['DotColor'] = df_tx_dots['Status'].apply(
                        lambda s: '#10b981' if 'Kjøpt' in s and 'Solgt' not in s else ('#ef4444' if 'Solgt' in s and 'Kjøpt' not in s else '#f59e0b')
                    )
                    df_tx_dots['DotLabel'] = df_tx_dots['Status'].apply(
                        lambda s: '🟢 Kjøpt' if 'Kjøpt' in s and 'Solgt' not in s else ('🔴 Solgt' if 'Solgt' in s and 'Kjøpt' not in s else '🟢🔴')
                    )
                    tx_dots_chart = alt.Chart(df_tx_dots).mark_circle(
                        size=160, stroke='#ffffff', strokeWidth=2.5, opacity=1
                    ).encode(
                        x=alt.X('GW:O', sort=alt.SortField('gw_num', order='ascending')),
                        y=alt.Y('Pris:Q', scale=alt.Scale(zero=False)),
                        color=alt.Color('DotColor:N', scale=None),
                        tooltip=[
                            alt.Tooltip('GW:N', title='Runde'),
                            alt.Tooltip('Status:N', title='Overgang'),
                            alt.Tooltip('Pris:Q', title='Pris ved overgang (£m)'),
                            alt.Tooltip('Kamp:N', title='Kamp')
                        ]
                    )
                    tx_text_chart = alt.Chart(df_tx_dots).mark_text(
                        dy=-14, fontSize=11, fontWeight='bold'
                    ).encode(
                        x=alt.X('GW:O', sort=alt.SortField('gw_num', order='ascending')),
                        y=alt.Y('Pris:Q', scale=alt.Scale(zero=False)),
                        text='DotLabel:N',
                        color=alt.Color('DotColor:N', scale=None)
                    )
                    price_chart = (price_line + price_points + tx_dots_chart + tx_text_chart).properties(height=220)
                else:
                    price_chart = (price_line + price_points).properties(height=220)

                st.altair_chart(price_chart, width="stretch")
                if not df_tx_dots.empty:
                    st.caption("💡 🟢 Grønn markør viser runden spilleren ble kjøpt, 🔴 rød viser runden spilleren ble solgt.")
            with c_p2:
                sel_chart = alt.Chart(df_hist).mark_area(
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[alt.GradientStop(color='#10b981', offset=0), alt.GradientStop(color='rgba(16, 185, 129, 0.05)', offset=1)],
                        x1=1, x2=1, y1=1, y2=0
                    ),
                    line={'color': '#10b981', 'strokeWidth': 2}
                ).encode(
                    x=alt.X('GW:O', sort=alt.SortField('gw_num', order='ascending'), title='Runde'),
                    y=alt.Y('Eiere:Q', title='Antall Eiere'),
                    tooltip=[alt.Tooltip('GW:N', title='Runde'), alt.Tooltip('Eiere:Q', title='Managere', format=',')]
                ).properties(height=220)
                st.altair_chart(sel_chart, width="stretch")
        else:
            st.info("Ingen spilte kamper registrert ennå denne sesongen.")

    with sub_tab_split:
        st.markdown("##### 🏠 Hjemmebane vs. ✈️ Bortebane Sammenligning")
        home_rows = [r for r in rows if r["was_home"]]
        away_rows = [r for r in rows if not r["was_home"]]
        h_pts = sum(r["Poeng"] for r in home_rows)
        a_pts = sum(r["Poeng"] for r in away_rows)
        h_count = len(home_rows)
        a_count = len(away_rows)
        h_avg = (h_pts / h_count) if h_count else 0.0
        a_avg = (a_pts / a_count) if a_count else 0.0
        h_g = sum(r["Mål ⚽"] for r in home_rows)
        a_g = sum(r["Mål ⚽"] for r in away_rows)
        h_a = sum(r["Ass 👟"] for r in home_rows)
        a_a = sum(r["Ass 👟"] for r in away_rows)
        h_cs = sum(1 for r in home_rows if r["CS 🧤"] == "Ja")
        a_cs = sum(1 for r in away_rows if r["CS 🧤"] == "Ja")
        h_bon = sum(r["Bonus ⭐"] for r in home_rows)
        a_bon = sum(r["Bonus ⭐"] for r in away_rows)

        split_df = pd.DataFrame([
            {"Arena": "🏠 Hjemmebane", "Kamper": h_count, "Poeng": h_pts, "Snitt PPG": f"{h_avg:.2f}", "Mål ⚽": h_g, "Assists 👟": h_a, "Clean Sheets 🧤": h_cs, "Bonus ⭐": h_bon},
            {"Arena": "✈️ Bortebane", "Kamper": a_count, "Poeng": a_pts, "Snitt PPG": f"{a_avg:.2f}", "Mål ⚽": a_g, "Assists 👟": a_a, "Clean Sheets 🧤": a_cs, "Bonus ⭐": a_bon}
        ])
        st.dataframe(split_df, hide_index=True, width="stretch")

        st.markdown("---")
        st.markdown("##### ⚡ Effektivitetsstatistikk & Nøkkeltall")
        tot_mins = int(sum(h["Min"] for h in rows)) if rows else 0
        tot_goals = int(sum(h["Mål ⚽"] for h in rows)) if rows else 0
        tot_assists = int(sum(h["Ass 👟"] for h in rows)) if rows else 0
        ga_total = tot_goals + tot_assists
        min_per_ga = (tot_mins / ga_total) if ga_total > 0 else 0.0
        min_per_pt = (tot_mins / p.get("total_points", 1)) if p.get("total_points", 0) > 0 else 0.0
        tot_cs = sum(1 for h in rows if h["CS 🧤"] == "Ja")
        tot_bonus = sum(h["Bonus ⭐"] for h in rows)
        tot_xg = sum(h["xG"] for h in rows) if rows else 0.0
        tot_xa = sum(h["xA"] for h in rows) if rows else 0.0
        tot_yc = sum(h["🟨"] for h in rows) if rows else 0
        tot_rc = sum(h["🟥"] for h in rows) if rows else 0

        e1, e2, e3, e4 = st.columns(4)
        with e1:
            st.metric("Målpoeng (Mål + Assist)", f"{ga_total}", f"{tot_goals} mål • {tot_assists} ass")
            st.metric("Spilte Minutter", f"{tot_mins}'")
        with e2:
            st.metric("Minutter per Målpoeng", f"{min_per_ga:.1f} min" if min_per_ga > 0 else "-", "G+A frekvens")
            st.metric("Minutter per Poeng", f"{min_per_pt:.1f} min" if min_per_pt > 0 else "-", "Poeng frekvens")
        with e3:
            st.metric("Clean Sheets 🧤", f"{tot_cs}", f"{tot_bonus} Bonuspoeng ⭐")
            st.metric("xG / xA", f"{tot_xg:.2f} / {tot_xa:.2f}", "Forventet produksjon")
        with e4:
            in_ev = int(p.get("transfers_in_event", 0))
            out_ev = int(p.get("transfers_out_event", 0))
            net_tr = in_ev - out_ev
            st.metric("Kjøpt/Solgt denne runden", f"{net_tr:+d}", f"+{in_ev} inn / -{out_ev} ut")
            st.metric("Kort", f"🟨 {tot_yc}  🟥 {tot_rc}")

    with sub_tab_hist:
        if not df_hist.empty:
            st.markdown("##### 📋 Full Kamphistorikk per Gameweek")
            table_cols = ["GW", "Status", "Kamp", "Min", "Mål ⚽", "Ass 👟", "CS 🧤", "Bonus ⭐", "xG", "xA", "BPS", "🟨", "🟥", "Pris", "Pts"]
            st.dataframe(
                df_hist[table_cols],
                column_config={
                    "GW": st.column_config.TextColumn("GW", width=60),
                    "Status": st.column_config.TextColumn("Status", width=90),
                    "Kamp": st.column_config.TextColumn("Kamp", width=140),
                    "Min": st.column_config.NumberColumn("Min", width=45),
                    "Mål ⚽": st.column_config.NumberColumn("Mål ⚽", width=50),
                    "Ass 👟": st.column_config.NumberColumn("Ass 👟", width=50),
                    "CS 🧤": st.column_config.TextColumn("CS 🧤", width=50),
                    "Bonus ⭐": st.column_config.NumberColumn("Bonus ⭐", width=55),
                    "xG": st.column_config.NumberColumn("xG", format="%.2f", width=50),
                    "xA": st.column_config.NumberColumn("xA", format="%.2f", width=50),
                    "BPS": st.column_config.NumberColumn("BPS", width=50),
                    "🟨": st.column_config.NumberColumn("🟨", width=40),
                    "🟥": st.column_config.NumberColumn("🟥", width=40),
                    "Pris": st.column_config.NumberColumn("Pris", format="£%.1fm", width=65),
                    "Pts": st.column_config.NumberColumn("Pts", width=45)
                },
                width="stretch",
                hide_index=True
            )
        else:
            st.info("Ingen kamphistorikk tilgjengelig.")

    with sub_tab_fix:
        if upcoming_fixtures:
            st.markdown("##### 📅 Kommende Kamper & Motstandere")
            fix_rows = []
            for f in upcoming_fixtures[:8]:
                opp_id = f.get('team_a') if f.get('is_home') else f.get('team_h')
                opp_short = teams_dict.get(opp_id, f"Lag {opp_id}")
                venue = "H" if f.get('is_home') else "B"
                k_time_raw = f.get('kickoff_time') or ''
                k_date = k_time_raw[:10] if len(k_time_raw) >= 10 else '-'
                k_time = k_time_raw[11:16] if len(k_time_raw) >= 16 else '-'
                diff = f.get('difficulty', 3)
                ev_id = f.get('event')
                status_tx = "-"
                if ev_id in bought_gws and ev_id in sold_gws:
                    status_tx = "🟢 Kjøpt / 🔴 Solgt"
                elif ev_id in bought_gws:
                    status_tx = "🟢 Kjøpt"
                elif ev_id in sold_gws:
                    status_tx = "🔴 Solgt"
                fix_rows.append({
                    "Runde": f"GW {ev_id}" if ev_id else "-",
                    "Status": status_tx,
                    "Motstander": f"{opp_short} ({venue})",
                    "Dato": k_date,
                    "Tid": k_time,
                    "FDR": diff
                })
            st.dataframe(
                pd.DataFrame(fix_rows),
                column_config={
                    "FDR": st.column_config.NumberColumn("FDR (1-5)", width=60)
                },
                hide_index=True,
                width="stretch"
            )
        else:
            st.info("Ingen kommende kamper registrert.")

    with sub_tab_past:
        if past_seasons:
            st.markdown("##### 📜 Tidligere Sesonger i Premier League")
            past_rows = []
            for ps in past_seasons:
                past_rows.append({
                    "Sesong": ps.get("season_name", "?"),
                    "Totalpoeng": ps.get("total_points", 0),
                    "Minutter": ps.get("minutes", 0),
                    "Mål": ps.get("goals_scored", 0),
                    "Assists": ps.get("assists", 0),
                    "Clean Sheets": ps.get("clean_sheets", 0)
                })
            st.dataframe(pd.DataFrame(past_rows), hide_index=True, width="stretch")
        else:
            st.info("Ingen tidligere sesongstatistikk tilgjengelig for denne spilleren i FPL.")

def render_instant_pill_selector(players_list: list[dict], key_prefix: str = "starters", label: str = "🔍 Klikk på en spiller for umiddelbar profil & grafer:"):
    """Lar brukeren klikke på en spiller for umiddelbar åpning av modal uten sidelasting."""
    if not players_list:
        return
    options = [p.get("element_id") or p.get("id") for p in players_list]
    name_map = {
        (p.get("element_id") or p.get("id")): f"{p.get('name', p.get('web_name', ''))} ({p.get('team_short', p.get('team', ''))})"
        for p in players_list
    }
    pill_key = f"pills_{key_prefix}"
    def _on_pill_change():
        chosen = st.session_state.get(pill_key)
        if chosen:
            st.session_state["modal_player_id"] = chosen
            st.session_state[pill_key] = None

    st.pills(
        label,
        options=options,
        format_func=lambda pid: name_map.get(pid, str(pid)),
        key=pill_key,
        on_change=_on_pill_change
    )

# Sjekk om modal-åpning er trigget fra pill-klikk (kjører kun én gang per klikk)
if st.session_state.get("modal_player_id"):
    pid_to_render = st.session_state["modal_player_id"]
    st.session_state["modal_player_id"] = None
    render_player_dialog(pid_to_render, all_players_df, static_data, manager_id=manager_id)

# ---------------------------------------------------------
# SYSTEMSTRUKTUR: 6 KOMPLETTE FANER
# ---------------------------------------------------------
tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⚡ Live Gameweek Tracker",
    "📋 Mitt Lag & Neste Runde",
    "🔄 Transfer Hub (Overganger)",
    "📊 Komplett Spillerdatabase",
    "🏆 Mine Ligaer",
    "📈 Grafer & Avansert Statistikk"
])

# =========================================================
# FANE 0: LIVE GAMEWEEK TRACKER
# =========================================================
with tab0:
    st.markdown("### ⚡ Live Gameweek Tracker")
    st.caption("Sanntidsoppdatering av poeng, hendelser og ligasnitt for pågående eller nylig spilte runder.")

    col_lv_sel, col_lv_ref = st.columns([2, 1])
    with col_lv_sel:
        gw_options = list(range(1, mgr_summary["current_gw"] + 1))
        selected_live_gw = st.selectbox("Velg Gameweek for Live Tracker:", gw_options, index=len(gw_options) - 1)
    with col_lv_ref:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Oppdater Live Data Nå", width="stretch"):
            st.cache_data.clear()
            st.rerun()

    with st.spinner("Henter live hendelsesdata fra FPL..."):
        live_data = fpl_api.get_live_tracker_data(manager_id=manager_id, event=selected_live_gw)

    # Live KPI Cards
    k_l1, k_l2, k_l3, k_l4 = st.columns(4)
    with k_l1:
        st.html(f"""<div class="metric-card"><div class="metric-label">Din Live Poengsum</div><div class="metric-value" style="color: #00ff87 !important;">{live_data['total_live_points']}</div><div class="metric-sub">Start 11 Brutto</div></div>""")
    with k_l2:
        st.html(f"""<div class="metric-card"><div class="metric-label">Ligasnitt (GW {selected_live_gw})</div><div class="metric-value">{live_data['average_score']}</div><div class="metric-sub">Offisielt FPL-snitt</div></div>""")
    with k_l3:
        diff_avg = live_data['vs_average']
        diff_color = "#00ff87" if diff_avg >= 0 else "#ef4444"
        diff_sign = "+" if diff_avg >= 0 else ""
        st.html(f"""<div class="metric-card"><div class="metric-label">Differanse mot Snitt</div><div class="metric-value" style="color: {diff_color} !important;">{diff_sign}{diff_avg}</div><div class="metric-sub">Poeng foran/bak</div></div>""")
    with k_l4:
        st.html(f"""<div class="metric-card"><div class="metric-label">Høyeste Score i Verden</div><div class="metric-value">{live_data['highest_score']}</div><div class="metric-sub">Toppscorer GW {selected_live_gw}</div></div>""")

    st.markdown("---")

    # Starters split by position
    live_starters = live_data["starters"]
    live_bench = live_data["bench"]

    l_gks = [p for p in live_starters if p["position"] == "GKP"]
    l_defs = [p for p in live_starters if p["position"] == "DEF"]
    l_mids = [p for p in live_starters if p["position"] == "MID"]
    l_fwds = [p for p in live_starters if p["position"] == "FWD"]

    st.markdown("#### 🏟️ Startellever (Live Kampstatus & Poeng)")
    render_instant_pill_selector(live_starters, key_prefix="f0_starters", label="🔍 Klikk på en spiller for profil, form & historikk:")

    # Usynlige trigger-knapper for umiddelbar modal-åpning ved klikk på kortene
    for p_obj in live_starters + live_bench:
        p_obj_id = p_obj.get("element_id") or p_obj.get("id")
        if st.button("inspect", key=f"btn_trigger_tab0_{p_obj_id}"):
            st.session_state["modal_player_id"] = p_obj_id
            st.rerun()

    live_pitch = (
        '<div class="pitch-container">'
        '<div class="pitch-half-line"></div>'
        '<div class="pitch-center-circle"></div>'
        f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="live", tab_index="0") for p in l_fwds)}</div>'
        f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="live", tab_index="0") for p in l_mids)}</div>'
        f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="live", tab_index="0") for p in l_defs)}</div>'
        f'<div class="pitch-row" style="margin-bottom: 0;">{"".join(build_fut_card_html(p, mode="live", tab_index="0") for p in l_gks)}</div>'
        '</div>'
    )
    st.html(live_pitch)

    # Live Bench
    st.markdown("#### 🪑 Reservebenk (Live)")
    render_instant_pill_selector(live_bench, key_prefix="f0_bench", label="🔍 Klikk på en benkespiller for profil:")
    live_bench_content = (
        '<div class="bench-container">'
        f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="live", tab_index="0") for p in live_bench)}</div>'
        '</div>'
    )
    st.html(live_bench_content)

    # Detailed Live Table
    with st.expander("📋 Detaljert Live Hendelsestabell", expanded=False):
        all_live_players = live_starters + live_bench
        df_live = pd.DataFrame(all_live_players)[[
            "name", "team", "position", "played", "minutes", "goals", "assists", "clean_sheets", "bonus", "yellow_cards", "red_cards", "raw_points", "multiplier", "effective_points"
        ]].rename(columns={
            "name": "Spiller", "team": "Klubb", "position": "Pos", "played": "Spilt", "minutes": "Min", "goals": "Mål ⚽", "assists": "Assist 👟", "clean_sheets": "CS 🧤", "bonus": "Bonus ⭐", "yellow_cards": "Gult 🟨", "red_cards": "Rødt 🟥", "raw_points": "Basis Poeng", "multiplier": "Mult", "effective_points": "Totalt"
        })
        st.dataframe(df_live, width="stretch", hide_index=True)

# =========================================================
# FANE 1: MITT LAG & NESTE RUNDE (SQUAD PLANNER)
# =========================================================
with tab1:
    st.markdown("### 📋 Mitt Lag & Squad Planner")
    st.caption("Matematisk optimal startellever, kapteinsvalg og formasjon på stor fotballbane (FUT-stil).")

    # Manuell byttesimulator kontroller
    with st.container(border=True):
        st.markdown("##### 🛠️ Manuell Byttesimulator (Før Fristen)")
        st.caption("Gjort overganger på FPL-nettsiden? Siden FPL API-et skjuler overganger inntil fristen, kan du registrere dem her for å oppdatere banen og best lagoppstilling.")

        if st.session_state.manual_transfers:
            tr_summary_list = [f"**{tr['out']['name']}** ➡️ **{tr['in']['name']}**" for tr in st.session_state.manual_transfers]
            st.info(f"💾 **Aktive overganger på banen (lagres automatisk og overlever omstart av .bat-filen):** {', '.join(tr_summary_list)}. Trykk **«🗑️ Nullstill»** for å gå tilbake til din opprinnelige FPL-tropp.")

        col_mt1, col_mt2 = st.columns(2)
        with col_mt1:
            out_options = {
                f"{p['name']} ({p.get('team_short', p.get('team', ''))}) - {p['position']} | £{p['cost']:.1f}m | xP: {p.get('ep_next', 0):.1f}": p
                for p in active_squad
            }
            selected_out_label = st.selectbox("1. Selg spiller (UT):", list(out_options.keys()), key="f1_sim_out")
            p_out = out_options[selected_out_label]

        with col_mt2:
            max_buy_budget = round(p_out["cost"] + current_bank, 1)
            squad_elem_ids = [p.get("element_id") or p.get("id") for p in active_squad]
            eligible_in = all_players_df[
                (all_players_df["position"] == p_out["position"]) &
                (all_players_df["cost"] <= max_buy_budget + 0.01) &
                (~all_players_df["id"].isin(squad_elem_ids)) &
                (all_players_df["status"] != "u")
            ].sort_values(by="ep_next", ascending=False)

            in_options = {
                f"{row['name']} ({row['team']}) - £{row['cost']:.1f}m | xP: {row['ep_next']:.1f} | Neste: {row['next_fixture']}": row.to_dict()
                for _, row in eligible_in.iterrows()
            }
            if in_options:
                selected_in_label = st.selectbox(
                    f"2. Kjøp spiller (INN) [Maks: £{max_buy_budget:.1f}m]:",
                    list(in_options.keys()),
                    key="f1_sim_in"
                )
                p_in = in_options[selected_in_label]
            else:
                st.warning(f"Ingen spillere i posisjon {p_out['position']} innen budsjett.")
                p_in = None

        col_b_act1, col_b_act2 = st.columns([2, 1])
        with col_b_act1:
            if p_in:
                diff_money = p_out["cost"] - p_in["cost"]
                diff_xp = p_in["ep_next"] - p_out.get("ep_next", 0)
                m_txt = f"+£{diff_money:.1f}m i banken" if diff_money >= 0 else f"£{abs(diff_money):.1f}m fra banken"
                st.info(f"🔄 **Bytte:** {p_out['name']} ➡️ {p_in['name']} | **Budsjett:** {m_txt} (Ny bank: £{current_bank + diff_money:.1f}m) | **xP-gevinst:** {diff_xp:+.1f} pts")
        with col_b_act2:
            st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                if p_in and st.button("➕ Bekreft", type="primary", width="stretch", key="f1_add_tr"):
                    st.session_state.manual_transfers.append({"out": p_out, "in": p_in})
                    transfer_tracker.save_simulated_transfers(st.session_state.manual_transfers, manager_id=manager_id)
                    out_pid = p_out.get("element_id") or p_out.get("id")
                    in_pid = p_in.get("element_id") or p_in.get("id")
                    diff_xp = float(p_in.get("ep_next", 0)) - float(p_out.get("ep_next", 0))
                    transfer_tracker.add_tracked_transfer(
                        gw=mgr_summary.get("next_gw", mgr_summary["current_gw"] + 1),
                        out_id=out_pid,
                        out_name=p_out["name"],
                        out_team=p_out.get("team_short", p_out.get("team", "")),
                        in_id=in_pid,
                        in_name=p_in["name"],
                        in_team=p_in.get("team", p_in.get("team_short", "")),
                        exp_gain=diff_xp,
                        hit_cost=0,
                        manager_id=manager_id
                    )
                    st.rerun()
            with c_btn2:
                if st.session_state.manual_transfers and st.button("🗑️ Nullstill", width="stretch", key="f1_rst_tr"):
                    st.session_state.manual_transfers = []
                    transfer_tracker.clear_simulated_transfers(manager_id=manager_id)
                    st.rerun()

    # Formasjon og PuLP-løser for start 11
    with st.container(border=True):
        col_lineup_ctrl, col_lineup_stat = st.columns([1, 2])
        with col_lineup_ctrl:
            lineup_opt_choice = st.radio(
                "Optimaliseringsmodus:",
                ["⚡ PuLP Matematisk Optimal 11 & Kaptein", "📋 Nåværende FPL-oppstilling"],
                index=0
            )

    if "PuLP" in lineup_opt_choice:
        pulp_xi = pulp_solver.solve_optimal_starting_xi(active_squad)
        starters = pulp_xi["starters"]
        bench = pulp_xi["bench"]
        active_formation = pulp_xi["formation"]
        c_player = pulp_xi["captain"]
        vc_player = pulp_xi["vice_captain"]
        total_starting_xp = pulp_xi["total_xp"]
    else:
        starters = [p for p in active_squad if p.get("is_starter", True)]
        bench = [p for p in active_squad if not p.get("is_starter", False)]
        bench_gk = [p for p in bench if p["position"] == "GKP"]
        bench_outfield = sorted([p for p in bench if p["position"] != "GKP"], key=lambda x: float(x.get("ep_next", 0)), reverse=True)
        bench = bench_gk + bench_outfield
        active_formation = f"{len([p for p in starters if p['position'] == 'DEF'])}-{len([p for p in starters if p['position'] == 'MID'])}-{len([p for p in starters if p['position'] == 'FWD'])}"
        c_player = next((p for p in starters if p.get("is_captain")), starters[0] if starters else None)
        vc_player = next((p for p in starters if p.get("is_vice_captain")), starters[1] if len(starters) > 1 else None)
        total_starting_xp = round(sum(float(p.get("ep_next", 0)) for p in starters) + float(c_player.get("ep_next", 0) if c_player else 0), 1)

    # Blank / Double Gameweek Banners
    next_gw_num = mgr_summary.get("next_gw", mgr_summary["current_gw"] + 1)
    blank_starters = [p for p in starters if p.get("is_blank")]
    double_starters = [p for p in starters if p.get("is_double")]

    if blank_starters:
        names_str = ", ".join(f"**{p['name']}** ({p.get('team_short', p.get('team', ''))})" for p in blank_starters)
        st.error(f"🚨 **KRITISK ADVARSEL - BLANK GAMEWEEK (0 KAMPER):** Følgende spillere i din startellever har **INGEN kamp** i GW {next_gw_num}: {names_str}. Disse vil gi **0 poeng**! Du bør bytte dem ut eller flytte dem til reservebenken før fristen.")
    if double_starters:
        names_str = ", ".join(f"**{p['name']}** ({p.get('team_short', p.get('team', ''))})" for p in double_starters)
        st.success(f"🔥 **DOBBEL GAMEWEEK (DGW) ALERT:** {names_str} spiller **2 kamper** i GW {next_gw_num}! Stor oppside for kapteinsbind eller Triple Captain!")

    # Summary Info Card
    st.info(f"""
    **Aktiv Formasjon:** {active_formation} | 
    **Kaptein:** {c_player['name'] if c_player else '-'} (2x poeng) | 
    **Visekaptein:** {vc_player['name'] if vc_player else '-'} | 
    **Forventet Poengsum Neste Runde (Start 11):** **{total_starting_xp:.1f} xP**
    """)

    # View Mode Toggle
    view_type = st.radio("Visningsmodus:", ["⚽ Grafisk Fotballbane (Pitch View)", "📋 Tabelloversikt"], horizontal=True, key="f1_view_type")

    if "Pitch" in view_type:
        s_gks = [p for p in starters if p["position"] in ["GKP", "G"]]
        s_defs = [p for p in starters if p["position"] in ["DEF", "D"]]
        s_mids = [p for p in starters if p["position"] in ["MID", "M"]]
        s_fwds = [p for p in starters if p["position"] in ["FWD", "F"]]

        render_instant_pill_selector(starters, key_prefix="f1_starters", label="🔍 Klikk på en spiller for profil, formkurve & sesonggrafer:")

        # Usynlige trigger-knapper for umiddelbar modal-åpning ved klikk på kortene
        for p_obj in starters + bench:
            p_obj_id = p_obj.get("element_id") or p_obj.get("id")
            if st.button("inspect", key=f"btn_trigger_tab1_{p_obj_id}"):
                st.session_state["modal_player_id"] = p_obj_id
                st.rerun()

        pitch_content = (
            '<div class="pitch-container">'
            '<div class="pitch-half-line"></div>'
            '<div class="pitch-center-circle"></div>'
            f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="xp", tab_index="1") for p in s_fwds)}</div>'
            f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="xp", tab_index="1") for p in s_mids)}</div>'
            f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="xp", tab_index="1") for p in s_defs)}</div>'
            f'<div class="pitch-row" style="margin-bottom: 0;">{"".join(build_fut_card_html(p, mode="xp", tab_index="1") for p in s_gks)}</div>'
            '</div>'
        )
        st.html(pitch_content)

        # Bench View
        render_instant_pill_selector(bench, key_prefix="f1_bench", label="🔍 Klikk på en benkespiller for analyse:")
        bench_content = (
            '<div class="bench-container">'
            '<div class="bench-title">🪑 Reservebenk (Matematisk prioritert rekkefølge for innbytte)</div>'
            f'<div class="pitch-row">{"".join(build_fut_card_html(p, mode="xp", tab_index="1") for p in bench)}</div>'
            '</div>'
        )
        st.html(bench_content)
    else:
        st.markdown("#### Startellever")
        for p in starters:
            if "status_formatted" not in p:
                p["status_formatted"] = fpl_api.format_player_status(p.get("status"), p.get("chance_of_playing"))
        df_starters = pd.DataFrame(starters)[["name", "position", "team_short", "fixture", "cost", "ep_next", "form", "is_captain", "is_vice_captain", "status_formatted"]].rename(columns={
            "name": "Spiller", "position": "Pos", "team_short": "Klubb", "fixture": "Neste Kamp", "cost": "Pris (£m)", "ep_next": "xP Neste", "form": "Form", "is_captain": "C", "is_vice_captain": "VC", "status_formatted": "Status"
        })
        st.dataframe(df_starters, width="stretch", hide_index=True)

        st.markdown("#### Reservebenk")
        for p in bench:
            if "status_formatted" not in p:
                p["status_formatted"] = fpl_api.format_player_status(p.get("status"), p.get("chance_of_playing"))
        df_bench = pd.DataFrame(bench)[["name", "position", "team_short", "fixture", "cost", "ep_next", "form", "status_formatted"]].rename(columns={
            "name": "Spiller", "position": "Pos", "team_short": "Klubb", "fixture": "Neste Kamp", "cost": "Pris (£m)", "ep_next": "xP Neste", "form": "Form", "status_formatted": "Status"
        })
        st.dataframe(df_bench, width="stretch", hide_index=True)

# =========================================================
# FANE 2: TRANSFER HUB (OVERGANGER & HIT-EVALUATOR)
# =========================================================
with tab2:
    st.markdown("### 🔄 Transfer Hub & PuLP Overgangsoptimalisator")
    st.caption("Matematisk optimering av 1- og 2-overganger med minuspoengevaluering (-4 hits) over 1–5 runder, pluss Skreddersydd Byttekalkulator.")

    # 1. PuLP MILP Transfer Solver
    with st.container(border=True):
        st.markdown("#### ⚡ PuLP Flerrunders Overgangsoptimalisator")
        col_ps1, col_ps2 = st.columns([3, 1])
        with col_ps1:
            st.markdown(f"Solveren evaluerer hele spillerbasen innenfor budsjettet (£{sum(p['cost'] for p in active_squad) + current_bank:.1f}m), FPL-klubbkvoter (maks 3) og horisonten på **{horizon} runder**.")
        with col_ps2:
            run_pulp_tr_btn = st.button("🚀 Løs Overganger (PuLP)", type="primary", width="stretch")

    with st.spinner("Løser Mixed-Integer Linear Programming for overganger..."):
        pulp_tr_res = pulp_solver.solve_transfers_pulp(
            squad_players=active_squad,
            bank=current_bank,
            all_players_df=all_players_df,
            max_transfers=2 if allow_hits else 1,
            horizon=horizon,
            allow_hits=allow_hits
        )

    best_plan = pulp_tr_res.get("best_plan")
    if best_plan:
        num_tr = best_plan["num_transfers"]
        hit_cost = best_plan["hit_penalty"]
        net_g = best_plan["net_gain"]
        hor_net = best_plan["horizon_net_gain"]

        if best_plan["hit_recommended"]:
            st.success(f"🟢 **ANBEFALT HIT (-4):** 2 overganger gir en forventet nettogevinst på **+{hor_net:.1f} poeng** over de neste {horizon} rundene (etter fratrekk av -4 straffepoeng)!")
        elif num_tr == 1:
            st.success(f"✅ **ANBEFALT GRATISBYTTE (1 FT):** Gir en nettogevinst på **+{net_g:.1f} xP** i neste runde uten minuspoeng.")
        else:
            st.warning(f"ℹ️ 2 overganger er vurdert, men hit (-4) anbefales kun dersom du ønsker å ta kortsiktig risiko.")

        col_tp1, col_tp2 = st.columns(2)
        with col_tp1:
            st.markdown("##### 📤 Anbefalt Ut (Salg):")
            for p in best_plan["transfers_out"]:
                st.error(f"❌ **{p['name']}** ({p.get('team_short', p.get('team', ''))}) | £{p['cost']:.1f}m | xP: {p.get('ep_next', 0):.1f}")
        with col_tp2:
            st.markdown("##### 📥 Anbefalt Inn (Kjøp):")
            for p in best_plan["transfers_in"]:
                st.success(f"✅ **{p['name']}** ({p.get('team', '')}) | £{p['cost']:.1f}m | xP: {p.get('ep_next', 0):.1f}")

        st.caption(f"💰 Restbeløp i banken etter byttene: **£{best_plan['remaining_bank']:.1f}m**")

        col_pact1, col_pact2 = st.columns([1.5, 1])
        with col_pact1:
            if st.button("🚀 Gjennomfør i simulatoren nå!", type="primary", width="stretch", key="btn_apply_pulp_tr", help="Legger overgangene til i simulatoren og logger dem automatisk i Track Record."):
                for p_out, p_in in zip(best_plan["transfers_out"], best_plan["transfers_in"]):
                    st.session_state.manual_transfers.append({"out": p_out, "in": p_in})
                    out_pid = p_out.get("element_id") or p_out.get("id")
                    in_pid = p_in.get("element_id") or p_in.get("id")
                    exp_gain_val = float(p_in.get("ep_next", 0)) - float(p_out.get("ep_next", 0))
                    hit_val = hit_cost if num_tr > 1 else 0
                    transfer_tracker.add_tracked_transfer(
                        gw=mgr_summary.get("next_gw", mgr_summary["current_gw"] + 1),
                        out_id=out_pid,
                        out_name=p_out["name"],
                        out_team=p_out.get("team_short", p_out.get("team", "")),
                        in_id=in_pid,
                        in_name=p_in["name"],
                        in_team=p_in.get("team", p_in.get("team_short", "")),
                        exp_gain=exp_gain_val,
                        hit_cost=hit_val,
                        manager_id=manager_id
                    )
                transfer_tracker.save_simulated_transfers(st.session_state.manual_transfers, manager_id=manager_id)
                st.success("✅ Overgangene ble lagt til i simulatoren, lagret på disk og automatisk logget i Track Record! Gå til Fane 1 for å se den oppdaterte startelleveren.")
                st.rerun()
        with col_pact2:
            if st.button("📝 Logg separat i Track Record", width="stretch", key="btn_log_pulp_tr"):
                for p_out, p_in in zip(best_plan["transfers_out"], best_plan["transfers_in"]):
                    out_pid = p_out.get("element_id") or p_out.get("id")
                    in_pid = p_in.get("element_id") or p_in.get("id")
                    exp_gain_val = float(p_in.get("ep_next", 0)) - float(p_out.get("ep_next", 0))
                    hit_val = hit_cost if num_tr > 1 else 0
                    transfer_tracker.add_tracked_transfer(
                        gw=mgr_summary.get("next_gw", mgr_summary["current_gw"] + 1),
                        out_id=out_pid,
                        out_name=p_out["name"],
                        out_team=p_out.get("team_short", p_out.get("team", "")),
                        in_id=in_pid,
                        in_name=p_in["name"],
                        in_team=p_in.get("team", p_in.get("team_short", "")),
                        exp_gain=exp_gain_val,
                        hit_cost=hit_val,
                        manager_id=manager_id
                    )
                st.success("✅ Overgangene er logget i Track Record! Poenggevinsten evalueres automatisk etter at runden er ferdigspilt.")
                st.rerun()

    st.markdown("---")

    # 2. Topp 5 Salgsforslag & Kjøpsmål
    col_s_box, col_b_box = st.columns(2)
    with col_s_box:
        with st.container(border=True):
            st.markdown("#### 🔻 Topp 5 Salgskandidater (Eget Lag)")
            st.caption("Spillere i troppen med lavest xP i forhold til markedsverdi.")
            top_sells_data = pulp_tr_res.get("top_sells", [])
            if top_sells_data:
                df_sells_raw = pd.DataFrame(top_sells_data)
                cols_to_use = [c for c in ["name", "team_short", "position", "cost", "ep_next", "form"] if c in df_sells_raw.columns]
                rename_map = {
                    "name": "Spiller", "team_short": "Klubb", "position": "Pos", "cost": "Pris", "ep_next": "xP Neste", "form": "Form"
                }
                df_sells = df_sells_raw[cols_to_use].rename(columns=rename_map)
                st.dataframe(df_sells, width="stretch", hide_index=True)
            else:
                st.info("Ingen salgskandidater funnet.")

    with col_b_box:
        with st.container(border=True):
            st.markdown("#### 🔺 Topp 5 Kjøpsmål (Hele Premier League)")
            st.caption(f"Spillere i markedet med høyest forventet poengsum over {horizon} runder.")
            top_buys_data = pulp_tr_res.get("top_buys", [])
            if top_buys_data:
                df_buys_raw = pd.DataFrame(top_buys_data)
                xp_disp_col = f"xp_{horizon}gw" if f"xp_{horizon}gw" in df_buys_raw.columns else ("xp_3gw" if "xp_3gw" in df_buys_raw.columns else "ep_next")
                cols_to_use = [c for c in ["name", "team", "position", "cost", "ep_next", xp_disp_col, "form"] if c in df_buys_raw.columns]
                rename_map = {
                    "name": "Spiller", "team": "Klubb", "position": "Pos", "cost": "Pris", "ep_next": "xP Neste", xp_disp_col: f"xP {horizon}GW", "form": "Form"
                }
                df_buys = df_buys_raw[cols_to_use].rename(columns=rename_map)
                st.dataframe(df_buys, width="stretch", hide_index=True)
            else:
                st.info("Ingen kjøpskandidater funnet.")

    st.markdown("---")

    # 3. Skreddersydd Byttekalkulator
    with st.container(border=True):
        st.markdown("#### 🎯 Skreddersydd Byttekalkulator")
        st.caption("Velg en spesifikk spiller du vurderer å selge, og få umiddelbart opp de beste erstatningskjøpene innen nøyaktig ditt budsjett.")

        col_calc_p1, col_calc_p2 = st.columns([2, 1])
        with col_calc_p1:
            sell_opts = {
                f"{p['name']} ({p.get('team_short', p.get('team', ''))}) - {p['position']} | £{p['cost']:.1f}m | xP: {p.get('ep_next', 0):.1f}": p
                for p in active_squad
            }
            sel_sold_lbl = st.selectbox("Velg spiller du vurderer å selge:", list(sell_opts.keys()), key="calc_tab_sell")
            c_sold_p = sell_opts[sel_sold_lbl]

        calc_max_budget = round(c_sold_p["cost"] + current_bank, 1)

        with col_calc_p2:
            st.html(f"""
            <div class="metric-card" style="padding: 10px 14px;">
                <div class="metric-label">Tilgjengelig Budsjett</div>
                <div class="metric-value" style="font-size: 22px; color: #00ff87 !important;">£{calc_max_budget:.1f}m</div>
                <div class="metric-sub">Pris (£{c_sold_p['cost']:.1f}m) + Bank (£{current_bank:.1f}m)</div>
            </div>
            """)

        col_fl1, col_fl2, col_fl3 = st.columns(3)
        with col_fl1:
            calc_slider_max = st.slider("Maks pris på ny spiller (£m):", min_value=3.8, max_value=max(3.9, calc_max_budget), value=calc_max_budget, step=0.1, key="calc_tab_slider")
        with col_fl2:
            calc_fit_only = st.checkbox("Kun skadefrie spillere", value=True, key="calc_tab_fit")
        with col_fl3:
            calc_min_mins = st.slider("Min. spilte minutter:", min_value=0, max_value=360, value=90, step=15, key="calc_tab_mins")

        squad_ids_list = [p.get("element_id") or p.get("id") for p in active_squad]
        team_counts = Counter([p.get("team_short") or p.get("team") for p in active_squad])

        rec_table = fpl_api.get_replacement_recommendations(
            sold_player=c_sold_p,
            max_budget=calc_slider_max,
            all_players_df=all_players_df,
            exclude_ids=squad_ids_list,
            squad_team_counts=team_counts
        )

        if calc_fit_only and not rec_table.empty:
            rec_table = rec_table[rec_table["status"] == "a"]
        if calc_min_mins > 0 and not rec_table.empty:
            rec_table = rec_table[rec_table["minutes"] >= calc_min_mins]

        if not rec_table.empty:
            # Top 4 KPI Picks
            top_xp = rec_table.iloc[0]
            budget_buys = rec_table[rec_table["budget_saved"] > 0]
            top_budget = budget_buys.sort_values(by="xp_per_cost", ascending=False).iloc[0] if not budget_buys.empty else rec_table.iloc[0]
            top_fdr = rec_table.sort_values(by="fdr_3gw", ascending=True).iloc[0]
            top_form = rec_table.sort_values(by="form", ascending=False).iloc[0]

            ck1, ck2, ck3, ck4 = st.columns(4)
            with ck1:
                st.html(f"""<div class="metric-card"><div class="metric-label">🌟 Beste xP</div><div class="metric-value" style="font-size: 16px;">{top_xp['name']} ({top_xp['team']})</div><div class="metric-sub">£{top_xp['cost']}m | {top_xp['ep_next']} xP ({top_xp['xp_gain_next']:+.1f})</div></div>""")
            with ck2:
                st.html(f"""<div class="metric-card"><div class="metric-label">💎 Budsjett-kupp</div><div class="metric-value" style="font-size: 16px;">{top_budget['name']} ({top_budget['team']})</div><div class="metric-sub">£{top_budget['cost']}m | Spar £{top_budget['budget_saved']}m</div></div>""")
            with ck3:
                st.html(f"""<div class="metric-card"><div class="metric-label">🗓️ Lett Terminliste</div><div class="metric-value" style="font-size: 16px;">{top_fdr['name']} ({top_fdr['team']})</div><div class="metric-sub">Snitt FDR: {top_fdr['fdr_3gw']} (3GW)</div></div>""")
            with ck4:
                st.html(f"""<div class="metric-card"><div class="metric-label">🔥 Formsterkest</div><div class="metric-value" style="font-size: 16px;">{top_form['name']} ({top_form['team']})</div><div class="metric-sub">Form: {top_form['form']} | {top_form['total_points']} pts</div></div>""")

            st.markdown("##### Anbefalte Erstatningsspillere:")
            st.dataframe(rec_table.head(20)[[
                "name", "team", "cost", "category", "ep_next", "xp_gain_next", "xp_3gw", "next_fixture", "fdr_3gw", "budget_saved", "form", "selected_by_percent"
            ]].rename(columns={
                "name": "Spiller", "team": "Klubb", "cost": "Pris (£m)", "category": "Kategori / Styrker", "ep_next": "xP Neste", "xp_gain_next": "xP Gevinst", "xp_3gw": "xP 3GW", "next_fixture": "Neste Kamp", "fdr_3gw": "FDR (3GW)", "budget_saved": "Spart (£m)", "form": "Form", "selected_by_percent": "Eie %"
            }), width="stretch", hide_index=True)

            col_ex1, col_ex2 = st.columns([3, 1.2])
            with col_ex1:
                cand_map = {
                    f"{r['name']} ({r['team']}) - £{r['cost']}m | xP: {r['ep_next']} ({r['category']})": r.to_dict()
                    for _, r in rec_table.head(15).iterrows()
                }
                chosen_cand_lbl = st.selectbox("Velg erstatning for direkte gjennomføring:", list(cand_map.keys()), key="sel_calc_cand")
                chosen_cand = cand_map[chosen_cand_lbl]
            with col_ex2:
                st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                if st.button("🚀 Gjennomfør bytte", type="primary", width="stretch", key="btn_exec_calc_tab", help="Gjennomfører byttet i simulatoren og logger det automatisk i Track Record."):
                    st.session_state.manual_transfers.append({"out": c_sold_p, "in": chosen_cand})
                    out_pid = c_sold_p.get("element_id") or c_sold_p.get("id")
                    in_pid = chosen_cand.get("element_id") or chosen_cand.get("id")
                    exp_gain_val = float(chosen_cand.get("ep_next", 0)) - float(c_sold_p.get("ep_next", 0))
                    transfer_tracker.add_tracked_transfer(
                        gw=mgr_summary.get("next_gw", mgr_summary["current_gw"] + 1),
                        out_id=out_pid,
                        out_name=c_sold_p["name"],
                        out_team=c_sold_p.get("team_short", c_sold_p.get("team", "")),
                        in_id=in_pid,
                        in_name=chosen_cand["name"],
                        in_team=chosen_cand.get("team", chosen_cand.get("team_short", "")),
                        exp_gain=exp_gain_val,
                        hit_cost=0,
                        manager_id=manager_id
                    )
                    transfer_tracker.save_simulated_transfers(st.session_state.manual_transfers, manager_id=manager_id)
                    st.success(f"✅ Byttet {c_sold_p['name']} ➡️ {chosen_cand['name']} er gjennomført, lagret på disk og automatisk logget i Track Record!")
                    st.rerun()

    st.markdown("---")

    # 4. Overgangslogg & Optimizer Resultater (Track Record)
    with st.container(border=True):
        st.markdown("### 📈 Overgangslogg & Optimizer Resultater (Track Record)")
        st.caption("Følger opp faktiske poeng etter runden (INN − UT − Hit) og regner ut netto poenggevinst samt suksessrate for optimizeren.")

        raw_tracked = transfer_tracker.load_tracked_transfers(manager_id=manager_id)
        if not raw_tracked:
            st.info("Ingen overganger er logget ennå. Bytter du gjennomfører med PuLP-optimalisatoren eller Skreddersydd Byttekalkulator kan lagres automatisk her.")
        else:
            with st.spinner("Evaluerer faktiske poeng for overgangene..."):
                evaluated = [transfer_tracker.evaluate_transfer_record(t, static_data) for t in raw_tracked]
            
            card_stats = transfer_tracker.get_tracker_scorecard(evaluated)
            tot_log = card_stats["total_logged"]
            fin_cnt = card_stats["finished_count"]
            tot_gain = card_stats["total_net_gain"]
            avg_gain = card_stats["avg_gain"]
            win_rate = card_stats["win_rate"]
            wins = card_stats["wins"]
            draws = card_stats["draws"]
            losses = card_stats["losses"]
            avg_exp = card_stats["avg_exp"]

            # 4 Scorecard-kort
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.html(f'''<div class="metric-card"><div class="metric-label">Bytter Logget</div><div class="metric-value">{tot_log} stk</div><div class="metric-sub">{fin_cnt} runder ferdigspilt</div></div>''')
            with sc2:
                sign = "+" if tot_gain > 0 else ""
                color_gain = "#00ff87" if tot_gain > 0 else ("#ef4444" if tot_gain < 0 else "#ffffff")
                st.html(f'''<div class="metric-card"><div class="metric-label">Netto Poenggevinst</div><div class="metric-value" style="color: {color_gain} !important;">{sign}{tot_gain} pts</div><div class="metric-sub">Snitt: {sign}{avg_gain:.1f} pts per bytte</div></div>''')
            with sc3:
                st.html(f'''<div class="metric-card"><div class="metric-label">Suksessrate</div><div class="metric-value" style="color: #facc15 !important;">{win_rate:.0f}%</div><div class="metric-sub">{wins} vinn • {draws} uavgjort • {losses} tap</div></div>''')
            with sc4:
                st.html(f'''<div class="metric-card"><div class="metric-label">Forventet vs. Faktisk</div><div class="metric-value">{sign}{avg_gain:.1f} pts</div><div class="metric-sub">Forventet xP-snitt: +{avg_exp:.1f} pts</div></div>''')

            st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

            # Tabellvisning
            rows_tr = []
            for t in evaluated:
                in_pts_str = f"{t['in_pts']} pts" if t['in_pts'] is not None else "⏳"
                out_pts_str = f"{t['out_pts']} pts" if t['out_pts'] is not None else "⏳"
                gain_str = f"{t['actual_gain']:+d} pts" if t['actual_gain'] is not None else "⏳ Venter"
                rows_tr.append({
                    "Runde": f"GW {t['gw']}",
                    "Dato": t.get("date", "-"),
                    "UT (Solgt)": f"❌ {t['out_name']} ({t['out_team']}) [{out_pts_str}]",
                    "INN (Kjøpt)": f"✅ {t['in_name']} ({t['in_team']}) [{in_pts_str}]",
                    "Hit": f"-{t['hit_cost']}" if t['hit_cost'] > 0 else "0",
                    "xP Forventet": f"+{t.get('exp_gain', 0.0):.1f}",
                    "Faktisk Gevinst": gain_str,
                    "Status": t["status"]
                })
            df_track = pd.DataFrame(rows_tr)
            st.dataframe(df_track, width="stretch", hide_index=True)

            with st.expander("⚙️ Administrer / Slett loggførte overganger", expanded=False):
                c_del_sel, c_del_btn = st.columns([3, 1])
                with c_del_sel:
                    del_opts = [t['id'] for t in evaluated]
                    chosen_del_id = st.selectbox(
                        "Velg overgang som skal slettes:",
                        options=del_opts,
                        format_func=lambda x: next(f"GW {t['gw']}: ❌ {t['out_name']} ➔ ✅ {t['in_name']} ({t['status']})" for t in evaluated if t['id'] == x),
                        key="sel_del_transfer"
                    )
                with c_del_btn:
                    st.write("")
                    st.write("")
                    if st.button("🗑️ Slett overgang", key="btn_del_transfer", width="stretch"):
                        transfer_tracker.delete_tracked_transfer(chosen_del_id)
                        st.success("Overgang slettet fra loggen!")
                        st.rerun()

                st.markdown("---")
                if st.button("🗑️ Tøm hele overgangsloggen (Nullstill)", key="btn_clear_track_log"):
                    transfer_tracker.save_tracked_transfers([])
                    transfer_tracker.clear_simulated_transfers()
                    st.session_state.manual_transfers = []
                    st.success("Overgangsloggen og simulerte bytter er nullstilt.")
                    st.rerun()

        with st.expander("➕ Loggfør en overgang manuelt (f.eks. fra tidligere runder)", expanded=False):
            c_man1, c_man2, c_man3 = st.columns(3)
            with c_man1:
                next_gw_default = int(mgr_summary.get("next_gw", mgr_summary["current_gw"] + 1))
                man_gw = st.number_input("Gameweek / Runde:", min_value=1, max_value=38, value=next_gw_default, step=1, key="man_tx_gw")
            with c_man2:
                sorted_all_p = all_players_df.sort_values(by="name")
                man_out_id = st.selectbox(
                    "Spiller UT (Solgt):",
                    options=sorted_all_p["id"].tolist(),
                    format_func=lambda x: f"{all_players_df.loc[all_players_df['id']==x, 'name'].values[0]} ({all_players_df.loc[all_players_df['id']==x, 'team'].values[0]}) - £{all_players_df.loc[all_players_df['id']==x, 'cost'].values[0]:.1f}m",
                    key="man_tx_out"
                )
            with c_man3:
                man_in_id = st.selectbox(
                    "Spiller INN (Kjøpt):",
                    options=sorted_all_p["id"].tolist(),
                    format_func=lambda x: f"{all_players_df.loc[all_players_df['id']==x, 'name'].values[0]} ({all_players_df.loc[all_players_df['id']==x, 'team'].values[0]}) - £{all_players_df.loc[all_players_df['id']==x, 'cost'].values[0]:.1f}m",
                    key="man_tx_in"
                )
            c_man_hit, c_man_btn = st.columns([1, 2])
            with c_man_hit:
                man_hit = st.selectbox("Minuspoeng:", [0, 4, 8], format_func=lambda x: f"-{x} hit" if x > 0 else "0 (Gratis)", key="man_tx_hit")
            with c_man_btn:
                st.write("")
                st.write("")
                if st.button("➕ Legg til i overgangslogg", key="btn_add_manual_tx", width="stretch"):
                    out_row = all_players_df[all_players_df["id"] == man_out_id].iloc[0]
                    in_row = all_players_df[all_players_df["id"] == man_in_id].iloc[0]
                    exp_diff = round(float(in_row.get("ep_next", 0)) - float(out_row.get("ep_next", 0)) - man_hit, 2)
                    transfer_tracker.add_tracked_transfer(
                        gw=man_gw,
                        out_id=int(out_row["id"]),
                        out_name=str(out_row["name"]),
                        out_team=str(out_row["team"]),
                        in_id=int(in_row["id"]),
                        in_name=str(in_row["name"]),
                        in_team=str(in_row["team"]),
                        exp_gain=exp_diff,
                        hit_cost=man_hit
                    )
                    st.success(f"Overgang logget for GW {man_gw}: {out_row['name']} ➔ {in_row['name']}!")
                    st.rerun()

# =========================================================
# FANE 3: KOMPLETT SPILLERDATABASE
# =========================================================
with tab3:
    st.markdown("### 📊 Komplett Spillerdatabase")
    st.caption("Søk og filtrer blant alle 650+ Premier League-spillere for å planlegge fremover.")

    with st.container(border=True):
        c_db1, c_db2, c_db3 = st.columns([2, 1, 1])
        with c_db1:
            search_query = st.text_input("🔍 Søk etter spillernavn (f.eks. Saka, Palmer, Isak, Gabriel)...", "").strip().lower()
        with c_db2:
            pos_filter = st.multiselect("Posisjon", ["GKP", "DEF", "MID", "FWD"], default=["GKP", "DEF", "MID", "FWD"], key="f3_pos")
        with c_db3:
            sort_by = st.selectbox("Sorter etter:", [
                "xP Neste Runde (ep_next)",
                "xP 3 Runder (Sum)",
                "xP 5 Runder (Sum)",
                "Gunstig Terminliste (Lavest FDR 3GW)",
                "Form",
                "Totale Poeng",
                "Pris (£m)",
                "Expected Goals (xG)",
                "Expected Assists (xA)",
                "Eierandel (%)"
            ], index=0, key="f3_sort")

        col_f3_1, col_f3_2, col_f3_3 = st.columns(3)
        with col_f3_1:
            price_range = st.slider("Prisområde (£m):", min_value=3.8, max_value=15.5, value=(3.8, 15.5), step=0.1, key="f3_price")
        with col_f3_2:
            min_minutes = st.slider("Minimum spilte minutter:", min_value=0, max_value=360, value=0, step=15, key="f3_mins")
        with col_f3_3:
            only_fit_db = st.checkbox("Kun spilleklare spillere (Status = Klar)", value=False, key="f3_fit")

    filtered_db = all_players_df[
        (all_players_df["position"].isin(pos_filter)) &
        (all_players_df["cost"] >= price_range[0]) &
        (all_players_df["cost"] <= price_range[1]) &
        (all_players_df["minutes"] >= min_minutes)
    ].copy()

    if search_query:
        filtered_db = filtered_db[
            filtered_db["name"].str.lower().str.contains(search_query) |
            filtered_db["full_name"].str.lower().str.contains(search_query) |
            filtered_db["team"].str.lower().str.contains(search_query)
        ]

    if only_fit_db:
        filtered_db = filtered_db[filtered_db["status"] == "a"]

    sort_map = {
        "xP Neste Runde (ep_next)": ("ep_next", False),
        "xP 3 Runder (Sum)": ("xp_3gw", False),
        "xP 5 Runder (Sum)": ("xp_5gw", False),
        "Gunstig Terminliste (Lavest FDR 3GW)": ("fdr_3gw", True),
        "Form": ("form", False),
        "Totale Poeng": ("total_points", False),
        "Pris (£m)": ("cost", False),
        "Expected Goals (xG)": ("xg", False),
        "Expected Assists (xA)": ("xa", False),
        "Eierandel (%)": ("selected_by_percent", False)
    }
    col_s_name, asc = sort_map.get(sort_by, ("ep_next", False))
    filtered_db = filtered_db.sort_values(by=col_s_name, ascending=asc)

    # Metrics overview
    k_f3_1, k_f3_2, k_f3_3 = st.columns(3)
    with k_f3_1:
        st.metric("Spillere funnet", f"{len(filtered_db)}")
    with k_f3_2:
        top_name = filtered_db.iloc[0]["name"] if not filtered_db.empty else "-"
        top_xp_val = filtered_db.iloc[0]["ep_next"] if not filtered_db.empty else 0
        st.metric("Høyest xP", f"{top_name} ({top_xp_val} xP)")
    with k_f3_3:
        avg_c = filtered_db["cost"].mean() if not filtered_db.empty else 0
    # Hurtigvelger for spillerprofil modal
    with st.container(border=True):
        col_pop1, col_pop2 = st.columns([3, 1])
        with col_pop1:
            db_opts = {
                f"{row['name']} ({row['team']}) - {row['position']} | £{row['cost']:.1f}m | xP: {row['ep_next']:.1f} | Totalt: {row['total_points']} pts": row['id']
                for _, row in filtered_db.head(100).iterrows()
            } if not filtered_db.empty else {}
            chosen_label = st.selectbox("🔍 Åpne Spillerprofil & Dybdeanalyse for:", list(db_opts.keys()) if db_opts else ["Ingen spillere funnet"], key="f3_quick_prof_sel")
            chosen_pid = db_opts.get(chosen_label)
        with col_pop2:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if chosen_pid and st.button("🚀 Åpne Spillerprofil", type="primary", width="stretch", key="f3_btn_open_modal"):
                render_player_dialog(chosen_pid, all_players_df, static_data)

    if "status_formatted" not in filtered_db.columns:
        filtered_db["status_formatted"] = filtered_db.apply(
            lambda r: fpl_api.format_player_status(r.get("status"), r.get("chance_of_playing")), axis=1
        )

    display_cols = [
        "name", "team", "position", "cost", "next_fixture", "next_fdr",
        "ep_next", "xp_3gw", "fdr_3gw", "form", "total_points", "xg", "xa",
        "minutes", "selected_by_percent", "status_formatted"
    ]
    renamed_cols = {
        "name": "Spiller", "team": "Klubb", "position": "Pos", "cost": "Pris (£m)", "next_fixture": "Neste Kamp", "next_fdr": "FDR Neste", "ep_next": "xP Neste", "xp_3gw": "xP 3GW", "fdr_3gw": "Snitt FDR 3GW", "form": "Form", "total_points": "Poeng", "xg": "xG", "xa": "xA", "minutes": "Min", "selected_by_percent": "Eie %", "status_formatted": "Status"
    }
    st.dataframe(filtered_db[display_cols].rename(columns=renamed_cols), width="stretch", hide_index=True)

    csv_data = filtered_db[display_cols].rename(columns=renamed_cols).to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Last ned filtrert spillerdatabase som CSV",
        data=csv_data,
        file_name="fpl_spillerdatabase.csv",
        mime="text/csv",
        key="f3_csv_dl"
    )

# =========================================================
# FANE 4: MINE LIGAER
# =========================================================
with tab4:
    st.markdown("### 🏆 Mine Ligaer & Dyp Konkurrentanalyse")
    st.caption("Få full oversikt over private venneligaer (f.eks. Forza Ranheim) og globale ligaer med rank, bevegelsespiler og poenggap til toppen og pallplass.")

    classic_leagues = mgr_summary.get("all_classic_leagues", []) or mgr_summary.get("classic_leagues", [])
    if classic_leagues:
        league_summary_rows = []
        for l in classic_leagues:
            is_private = (l.get('league_type') == 'x')
            type_label = "🔒 Privat Venneliga" if is_private else "🌐 Offisiell Liga"
            cur_rank = l.get('entry_rank', 0)
            last_rank = l.get('entry_last_rank', cur_rank)
            total_entries = l.get('rank_count', 0)
            # Trendberegning
            if not last_rank or cur_rank == last_rank:
                trend = "➖ Uendret"
            elif cur_rank < last_rank:
                trend = f"🟢 +{last_rank - cur_rank:,}".replace(",", " ")
            else:
                trend = f"🔴 -{cur_rank - last_rank:,}".replace(",", " ")
            pct = l.get('entry_percentile_rank')
            pct_str = f"Topp {pct}%" if pct is not None else "-"
            league_summary_rows.append({
                'id': l['id'],
                'Liganavn': l.get('name', 'Ukjent'),
                'Type': type_label,
                'Plassering': f"#{cur_rank:,}".replace(",", " ") if cur_rank else "-",
                'Totalt Lag': f"{total_entries:,}".replace(",", " ") if total_entries else "-",
                'Endring': trend,
                'Toppsjikt': pct_str,
                'is_private': is_private
            })
        df_l_summary = pd.DataFrame(league_summary_rows)

        st.markdown("##### 📋 Samlet Ligaoversikt (Private & Offisielle)")
        st.dataframe(df_l_summary[['Liganavn', 'Type', 'Plassering', 'Totalt Lag', 'Endring', 'Toppsjikt']], width="stretch", hide_index=True)

        st.markdown("---")
        st.markdown("##### 🔍 Velg Miniliga for Dybdeanalyse & Avstandsberegning")

        # Sorter med private venneligaer øverst
        sorted_opts = sorted(league_summary_rows, key=lambda x: (not x['is_private'], x['Liganavn']))
        league_options = {f"{r['Liganavn']} ({r['Type']}) — {r['Plassering']}": r['id'] for r in sorted_opts}
        chosen_league_label = st.selectbox("Velg liga for å åpne tabell og konkurrentanalyse:", list(league_options.keys()), key="f4_lg_select")
        chosen_league_id = league_options[chosen_league_label]

        with st.spinner(f"Henter dybdedata for rivaler i {chosen_league_label}..."):
            rival_data = fpl_api.get_league_rival_analysis(chosen_league_id, manager_id=manager_id, max_rivals=25)

        cs = rival_data.get("chase_stats", {})
        if cs:
            st.markdown("#### 🏁 Jakt-analyse mot Ligatoppen & Pallplass")
            c_gap1, c_gap2, c_gap3, c_gap4 = st.columns(4)
            with c_gap1:
                st.html(f"""<div class="metric-card"><div class="metric-label">Ligaleder</div><div class="metric-value" style="font-size: 18px;">{cs.get('leader_name')}</div><div class="metric-sub">{cs.get('leader_pts')} poeng totalt</div></div>""")
            with c_gap2:
                gap_val = cs.get('gap_to_leader', 0)
                leader_txt = f"-{gap_val} pts" if gap_val > 0 else "Du leder! 🏆"
                gap_3rd = cs.get('gap_to_third', 0)
                pod_txt = f"-{gap_3rd} pts" if gap_3rd > 0 else "På pallen! 🥉"
                st.html(f"""<div class="metric-card"><div class="metric-label">Avstand til Leder</div><div class="metric-value" style="color: {'#ef4444' if gap_val > 0 else '#00ff87'} !important;">{leader_txt}</div><div class="metric-sub">Pallen (3. plass): {pod_txt}</div></div>""")
            with c_gap3:
                st.html(f"""<div class="metric-card"><div class="metric-label">Avstand til Pallen (3. plass)</div><div class="metric-value" style="color: {'#f59e0b' if gap_3rd > 0 else '#00ff87'} !important;">{pod_txt}</div><div class="metric-sub">Du er #{cs.get('my_rank')} i ligaen</div></div>""")
            with c_gap4:
                st.html(f"""<div class="metric-card"><div class="metric-label">Ligasnitt</div><div class="metric-value">{cs.get('league_avg_total')} pts</div><div class="metric-sub">Forrige runde snitt: {cs.get('league_avg_gw')} pts</div></div>""")

        st.markdown("---")

        l_sub1, l_sub2, l_sub3, l_sub4 = st.tabs([
            "🏆 Tabell & Kapteinsvalg",
            "💣 Chip-arsenal (Hvem har hva igjen?)",
            "🧬 Tropp-likhet & Differensialer",
            "📊 Eierandeler & Konsensuslag"
        ])

        with l_sub1:
            st.markdown("##### 🏆 Ligatabell med Bevegelsespiler & Kapteinsvalg")
            df_st = rival_data["standings"]
            if not df_st.empty:
                # Legg til bevegelsespil (⬆️, ⬇️, ➖)
                def get_arrow(row):
                    last_r = row.get("last_rank", row.get("rank"))
                    cur_r = row.get("rank")
                    if last_r > cur_r:
                        return f"⬆️ +{last_r - cur_r}"
                    elif last_r < cur_r:
                        return f"⬇️ -{cur_r - last_r}"
                    return "➖ 0"

                df_st["Endring"] = df_st.apply(get_arrow, axis=1) if "last_rank" in df_st.columns else "➖"

                display_st = df_st.drop(columns=["entry_id", "is_me", "last_rank"], errors="ignore").rename(columns={
                    "rank": "Plass", "entry_name": "Lag", "player_name": "Manager", "total": "Totalpoeng", "event_total": "Siste GW", "captain": "Kaptein", "transfers": "Bytter", "hit_cost": "Minuspoeng", "bank": "Bank", "value": "Verdi"
                })
                st.dataframe(display_st, width="stretch", hide_index=True)

            df_caps = rival_data.get("captain_distribution", pd.DataFrame())
            if not df_caps.empty:
                fig_caps = px.bar(
                    df_caps, x="Kaptein", y="Antall Valg", color="Antall Valg", text="Andel (%)", color_continuous_scale="Viridis"
                )
                fig_caps.update_traces(texttemplate='%{text}%', textposition='outside')
                apply_hc_theme(fig_caps, "Mest populære kapteinsvalg i miniligaen", height=350)
                st.plotly_chart(fig_caps, width="stretch")

        with l_sub2:
            st.markdown("##### 💣 Chip-status for alle managere i ligaen")
            df_chips = rival_data.get("chips_matrix", pd.DataFrame())
            if not df_chips.empty:
                st.dataframe(df_chips.drop(columns=["is_me"], errors="ignore"), width="stretch", hide_index=True)

        with l_sub3:
            st.markdown("##### 🧬 Tropp-likhet & Hode-til-hode Differensialer")
            df_ov = rival_data.get("overlap_df", pd.DataFrame())
            if not df_ov.empty:
                st.dataframe(df_ov, width="stretch", hide_index=True)

        with l_sub4:
            st.markdown("##### 🚨 Farlige Differensialer & Konsensuslag")
            c_d1, c_d2 = st.columns(2)
            with c_d1:
                st.markdown("**Høyeste eierandel blant rivaler som du MANGLER:**")
                df_diff = rival_data.get("differentials", pd.DataFrame())
                if not df_diff.empty:
                    fig_eo = px.bar(
                        df_diff.head(10), x="eo_pct", y="name", orientation="h", color="eo_pct",
                        color_continuous_scale=["#00ff87", "#ffd600", "#ff3366"], text="eo_pct"
                    )
                    fig_eo.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                    fig_eo.update_layout(yaxis=dict(autorange="reversed"))
                    apply_hc_theme(fig_eo, "Høyeste trusler (Rival EO)", height=420)
                    st.plotly_chart(fig_eo, width="stretch")
            with c_d2:
                st.markdown("**Ligaens Konsensuslag (Mest eide spillere totalt):**")
                df_tpl = rival_data.get("template_team", pd.DataFrame())
                if not df_tpl.empty:
                    st.dataframe(df_tpl, width="stretch", hide_index=True)

# =========================================================
# FANE 5: GRAFER & AVANSERT STATISTIKK
# =========================================================
with tab5:
    st.markdown("### 📈 Avansert Statistikk & Grafisk Analyse")
    st.caption("Visuelle analyser av din sesongutvikling mot ligasnitt, 20-lags terminliste-ticker med FDR-snitt, verdimatrise og troppens budsjettfordeling.")

    # ------------------------------------------------------------------
    # SEKSJON 1: SESONGSTATISTIKK & INTERAKTIVE GRAFER (MANAGER HISTORY)
    # ------------------------------------------------------------------
    with st.spinner("Henter sesonghistorikk og genererer analyser..."):
        history_data = fpl_api.get_manager_history(manager_id)

    history_current = history_data.get('current', []) if history_data else []

    if not history_current:
        st.info("Ingen historiske data tilgjengelig for dette laget ennå (f.eks. før første runde er ferdigspilt).")
    else:
        events_data = static_data.get('events', [])
        event_avgs = {ev['id']: ev.get('average_entry_score', 0) for ev in events_data}

        h_rows = []
        cum_diff = 0
        for h in history_current:
            gw_idx = h['event']
            avg_s = event_avgs.get(gw_idx, 0)
            pts = h['points']
            diff = pts - avg_s
            cum_diff += diff
            h_rows.append({
                'gw': gw_idx,
                'Runde': f"GW {gw_idx}",
                'Dine Poeng': pts,
                'Snittpoeng': avg_s,
                'Diff Snitt': diff,
                'Akkumulert Forsprang': cum_diff,
                'Totalpoeng': h['total_points'],
                'Overall Rangering': h['overall_rank'],
                'Lagverdi (£m)': h['value'] / 10.0,
                'Benkepoeng': h['points_on_bench'],
                'Minuspoeng': h.get('event_transfers_cost', 0)
            })
        df_hist = pd.DataFrame(h_rows)

        best_round = df_hist.loc[df_hist['Dine Poeng'].idxmax()]
        worst_round = df_hist.loc[df_hist['Dine Poeng'].idxmin()]
        tot_diff_pts = df_hist['Diff Snitt'].sum()
        tot_hit_pts = df_hist['Minuspoeng'].sum()
        tot_bench_pts = df_hist['Benkepoeng'].sum()
        avg_my_pts = df_hist['Dine Poeng'].mean()
        avg_league_pts = df_hist['Snittpoeng'].mean()

        # Nøkkeltall-kort
        st.markdown("#### 🏆 Sesongstatistikk i Tall")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
        with kpi_col1:
            st.metric("Beste Runde", f"{best_round['Dine Poeng']} pts", f"GW {best_round['gw']} 🚀")
        with kpi_col2:
            st.metric("Laveste Runde", f"{worst_round['Dine Poeng']} pts", f"GW {worst_round['gw']}")
        with kpi_col3:
            diff_sign = "+" if tot_diff_pts >= 0 else ""
            st.metric("Forsprang vs. Snitt", f"{diff_sign}{tot_diff_pts} pts", f"Snitt {avg_my_pts:.1f} vs {avg_league_pts:.1f}")
        with kpi_col4:
            hits_taken = int(tot_hit_pts / 4) if tot_hit_pts > 0 else 0
            st.metric("Tapt på Hits (-4)", f"-{tot_hit_pts} pts", f"{hits_taken} ekstrabytter")
        with kpi_col5:
            st.metric("Poeng på Benken", f"{tot_bench_pts} pts", f"Snitt {(tot_bench_pts / len(df_hist)):.1f} / runde")

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("##### 📊 Velg visualisering for sesongutvikling")
            graph_choice = st.radio(
                "Visningsmodus:",
                [
                    "📊 Dine Poeng vs. Gjennomsnitt per Runde",
                    "📈 Sammenlagtrangering over Tid (Overall Rank)",
                    "🏔️ Akkumulert Poengforsprang til Snittet"
                ],
                horizontal=True,
                key="f5_graph_choice"
            )

            if graph_choice == "📊 Dine Poeng vs. Gjennomsnitt per Runde":
                df_melt = df_hist.melt(
                    id_vars=['gw', 'Runde', 'Diff Snitt'],
                    value_vars=['Dine Poeng', 'Snittpoeng'],
                    var_name='Kategori',
                    value_name='Poeng'
                )
                chart_bars = alt.Chart(df_melt).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(
                    x=alt.X('gw:O', title='Gameweek (Runde)'),
                    y=alt.Y('Poeng:Q', title='Poeng i Runden'),
                    color=alt.Color(
                        'Kategori:N',
                        scale=alt.Scale(domain=['Dine Poeng', 'Snittpoeng'], range=['#00ff87', '#64748b']),
                        legend=alt.Legend(title="Kategori", orient="top")
                    ),
                    xOffset='Kategori:N',
                    tooltip=[
                        alt.Tooltip('Runde:N', title='Runde'),
                        alt.Tooltip('Kategori:N', title='Kategori'),
                        alt.Tooltip('Poeng:Q', title='Poeng'),
                        alt.Tooltip('Diff Snitt:Q', title='Differanse mot Snitt')
                    ]
                ).properties(height=340)
                st.altair_chart(chart_bars, width="stretch")

            elif graph_choice == "📈 Sammenlagtrangering over Tid (Overall Rank)":
                chart_rank = alt.Chart(df_hist).mark_line(
                    point=alt.OverlayMarkDef(filled=True, size=60, color='#10b981'),
                    color='#10b981',
                    strokeWidth=3
                ).encode(
                    x=alt.X('gw:O', title='Gameweek (Runde)'),
                    y=alt.Y('Overall Rangering:Q', scale=alt.Scale(reverse=True), title='Sammenlagtplassering (høyere på grafen = bedre rank)'),
                    tooltip=[
                        alt.Tooltip('Runde:N', title='Runde'),
                        alt.Tooltip('Overall Rangering:Q', title='Plassering', format=','),
                        alt.Tooltip('Totalpoeng:Q', title='Totalpoeng'),
                        alt.Tooltip('Lagverdi (£m):Q', title='Lagverdi (£m)')
                    ]
                ).properties(height=340)
                st.altair_chart(chart_rank, width="stretch")

            else:
                chart_cum = alt.Chart(df_hist).mark_area(
                    line={'color': '#6366f1', 'strokeWidth': 2.5},
                    color=alt.Gradient(
                        gradient='linear',
                        stops=[
                            alt.GradientStop(color='#6366f1', offset=0),
                            alt.GradientStop(color='rgba(99, 102, 241, 0.05)', offset=1)
                        ],
                        x1=1, x2=1, y1=1, y2=0
                    )
                ).encode(
                    x=alt.X('gw:O', title='Gameweek (Runde)'),
                    y=alt.Y('Akkumulert Forsprang:Q', title='Akkumulerte Poeng Foran/Bak Ligasnitt'),
                    tooltip=[
                        alt.Tooltip('Runde:N', title='Runde'),
                        alt.Tooltip('Akkumulert Forsprang:Q', title='Netto forsprang'),
                        alt.Tooltip('Totalpoeng:Q', title='Totalpoeng')
                    ]
                ).properties(height=340)
                st.altair_chart(chart_cum, width="stretch")

        with st.expander("🔎 Vis komplett sesongtabell runde for runde", expanded=False):
            st.dataframe(
                df_hist[['Runde', 'Dine Poeng', 'Snittpoeng', 'Diff Snitt', 'Akkumulert Forsprang', 'Totalpoeng', 'Overall Rangering', 'Minuspoeng', 'Benkepoeng', 'Lagverdi (£m)']],
                width="stretch",
                hide_index=True
            )

    # ------------------------------------------------------------------
    # SEKSJON 2: TERMINLISTE-TICKER & KAMPSTYRKE (NESTE 5 RUNDER)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 🗓️ Terminliste-Ticker & Kampstyrke (Neste 5 Runder)")
    st.caption("FDR (Fixture Difficulty Rating 1-5): 🟢 1-2 (Lett) | ⚪ 3 (Middels) | 🟠 4 (Tøff) | 🔴 5 (Veldig tøff). Sortert etter enklest gjennomsnittlig kampprogram.")

    fdr_df, fdr_meta = fpl_api.get_fdr_matrix(horizon=5)
    teams_list = static_data.get('teams', [])
    teams_dict_all = {t['short_name']: t for t in teams_list}

    ticker_rows = []
    for short_name, t in teams_dict_all.items():
        code = t['code']
        logo_url = f"https://resources.premierleague.com/premierleague/badges/50/t{code}.png"
        row_t = {
            'Logo': logo_url,
            'Klubb': t['name'],
            'Kortnavn': short_name,
            'team_id': t['id']
        }
        team_fdrs = []
        for gw_col in fdr_df.columns:
            info = fdr_meta[short_name].get(gw_col, {})
            row_t[gw_col] = info.get('label', 'Blank ❌')
            team_fdrs.append(info.get('fdr', 3.0))
        row_t['Snitt FDR'] = round(sum(team_fdrs) / len(team_fdrs), 2) if team_fdrs else 3.0
        ticker_rows.append(row_t)

    df_full_ticker = pd.DataFrame(ticker_rows).sort_values(by='Snitt FDR')

    # Filter for egne klubber
    squad_team_shorts = set(p.get('team_short', p.get('team', '')) for p in active_squad)
    c_tick1, c_tick2 = st.columns([2, 1])
    with c_tick1:
        filter_my_clubs = st.checkbox("Vis kun klubber representert i min tropp", value=False, key="f5_filter_clubs")

    display_ticker = df_full_ticker[df_full_ticker['Kortnavn'].isin(squad_team_shorts)] if filter_my_clubs else df_full_ticker

    # Callouts for beste og tøffeste kampprogram
    best_3_teams = df_full_ticker.iloc[:3]['Klubb'].tolist()
    worst_3_teams = df_full_ticker.iloc[-3:]['Klubb'].tolist()

    c_call1, c_call2 = st.columns(2)
    with c_call1:
        st.success(f"🟢 **Beste kampprogram neste 5 runder (Kjøpsanbefaling):**  \n**{', '.join(best_3_teams)}**")
    with c_call2:
        st.error(f"🔴 **Tøffeste kampprogram neste 5 runder (Styr unna/selg):**  \n**{', '.join(worst_3_teams)}**")

    ticker_cols = ['Logo', 'Klubb', 'Snitt FDR'] + list(fdr_df.columns)
    st.dataframe(
        display_ticker[ticker_cols],
        column_config={
            "Logo": st.column_config.ImageColumn("Logo", width="small")
        },
        width="stretch",
        hide_index=True
    )

    # Blank & Double GW Radar Callout
    bgw_dgw_alerts = fpl_api.get_bgw_dgw_alerts(horizon=5)
    if bgw_dgw_alerts:
        for alert in bgw_dgw_alerts:
            if alert["type"] == "BGW":
                st.error(f"🚨 **{alert['title']}**\n\n{alert['desc']}")
            else:
                st.success(f"🔥 **{alert['title']}**\n\n{alert['desc']}")

    with st.expander("🗺️ Vis grafisk FDR Varmekart (Heatmap)", expanded=False):
        num_matrix = []
        text_matrix = []
        y_teams = list(fdr_df.index)
        x_gws = list(fdr_df.columns)

        for team in y_teams:
            row_num = []
            row_text = []
            for gw in x_gws:
                info = fdr_meta[team].get(gw, {})
                row_num.append(info.get("fdr", 3))
                row_text.append(info.get("label", ""))
            num_matrix.append(row_num)
            text_matrix.append(row_text)

        fig_fdr = go.Figure(data=go.Heatmap(
            z=num_matrix, x=x_gws, y=y_teams, text=text_matrix,
            texttemplate="<b>%{text}</b>", textfont=dict(size=12, color="#000000"),
            colorscale=[
                [0.0, "#e2e8f0"], [0.4, "#4ade80"], [0.6, "#facc15"], [0.8, "#fb923c"], [1.0, "#f87171"]
            ],
            showscale=True, colorbar=dict(title=dict(text="FDR", font=dict(color="#ffffff")), tickfont=dict(color="#ffffff"))
        ))
        apply_hc_theme(fig_fdr, "Terminliste-varmekart (FDR)", height=680)
        fig_fdr.update_layout(yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_fdr, width="stretch")

    # ------------------------------------------------------------------
    # SEKSJON 3: VERDI VS. FORVENTEDE POENG (xP MATRISE)
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### 💎 Verdi vs. Forventede Poeng (xP Matrise)")
    st.caption("Sammenlign spillerpris mot forventede poeng (xP). Se hvilke spillere som gir mest valuta for pengene, og hvor dine spillere plasserer seg!")

    squad_elem_ids = set(p.get('element_id') or p.get('id') for p in active_squad)
    df_scatter_all = all_players_df[all_players_df['status'] != 'u'].copy()
    df_scatter_all['Eierskap'] = df_scatter_all['id'].apply(lambda x: "Ditt Lag ⭐" if x in squad_elem_ids else "Andre Spillere")

    with st.container(border=True):
        st.markdown("##### 💎 Filter for verdimatrise")
        c_scat_f1, c_scat_f2 = st.columns([1, 1])
        with c_scat_f1:
            pos_filter_scat = st.selectbox(
                "Filtrer posisjon:",
                ["Alle Posisjoner", "Keepere (GKP)", "Forsvar (DEF)", "Midtbane (MID)", "Angrep (FWD)"],
                key="f5_pos_scat"
            )
        with c_scat_f2:
            min_xp_scat = st.slider("Minste forventede poeng (xP neste runde):", min_value=0.0, max_value=12.0, value=3.0, step=0.5, key="f5_min_xp")

    filtered_scatter = df_scatter_all[df_scatter_all['ep_next'] >= min_xp_scat].copy()
    if pos_filter_scat == "Keepere (GKP)":
        filtered_scatter = filtered_scatter[filtered_scatter['position'] == 'GKP']
    elif pos_filter_scat == "Forsvar (DEF)":
        filtered_scatter = filtered_scatter[filtered_scatter['position'] == 'DEF']
    elif pos_filter_scat == "Midtbane (MID)":
        filtered_scatter = filtered_scatter[filtered_scatter['position'] == 'MID']
    elif pos_filter_scat == "Angrep (FWD)":
        filtered_scatter = filtered_scatter[filtered_scatter['position'] == 'FWD']

    scatter_chart = alt.Chart(filtered_scatter).mark_circle().encode(
        x=alt.X('cost:Q', title='Pris (£m)', scale=alt.Scale(zero=False)),
        y=alt.Y('ep_next:Q', title='Forventede Poeng (xP Neste Runde)'),
        color=alt.Color(
            'position:N',
            title='Posisjon',
            scale=alt.Scale(domain=['GKP', 'DEF', 'MID', 'FWD'], range=['#f59e0b', '#3b82f6', '#10b981', '#ec4899'])
        ),
        size=alt.Size(
            'Eierskap:N',
            scale=alt.Scale(domain=['Andre Spillere', 'Ditt Lag ⭐'], range=[70, 260]),
            legend=alt.Legend(title="Dine Spillere", orient="top")
        ),
        tooltip=[
            alt.Tooltip('name:N', title='Spiller'),
            alt.Tooltip('team:N', title='Klubb'),
            alt.Tooltip('position:N', title='Posisjon'),
            alt.Tooltip('cost:Q', title='Pris (£m)'),
            alt.Tooltip('ep_next:Q', title='xP Neste GW'),
            alt.Tooltip('next_fixture:N', title='Neste Kamp'),
            alt.Tooltip('Eierskap:N', title='Eierskap')
        ]
    ).properties(height=420)

    st.altair_chart(scatter_chart, width="stretch")

    # Topp 5 Verdispillere i utvalget
    filtered_scatter['xp_per_m'] = (filtered_scatter['ep_next'] / filtered_scatter['cost']).round(2)
    top_value_picks = filtered_scatter.sort_values(by='xp_per_m', ascending=False).head(5)
    st.markdown("##### 💡 Topp 5 'Mest xP per million' i dette utvalget:")
    st.dataframe(
        top_value_picks[['name', 'team', 'position', 'cost', 'ep_next', 'xp_per_m', 'next_fixture', 'Eierskap']].rename(
            columns={'name': 'Spiller', 'team': 'Klubb', 'position': 'Pos', 'cost': 'Pris (£m)', 'ep_next': 'xP Neste', 'xp_per_m': 'xP / £m', 'next_fixture': 'Neste Kamp'}
        ),
        width="stretch",
        hide_index=True
    )

    # ------------------------------------------------------------------
    # SEKSJON 4: TROPPENS BUDSJETTFORDELING & ROI PER POSISJON
    # ------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### ⚖️ Troppens Budsjettfordeling & Posisjonseffektivitet")
    st.caption("Hvordan fordeler lagverdien din seg over de ulike lagdelene, og hvilken posisjon leverer høyest avkastning (xP per million)?")

    pos_summary = []
    for p_pos in ["GKP", "DEF", "MID", "FWD"]:
        s_pos = [p for p in active_squad if p["position"] == p_pos]
        cost_sum = sum(p["cost"] for p in s_pos)
        xp_sum = sum(float(p.get("ep_next", 0)) for p in s_pos)
        roi = round(xp_sum / max(0.1, cost_sum), 2)
        pos_summary.append({
            "Posisjon": p_pos,
            "Antall": len(s_pos),
            "Total_Pris": round(cost_sum, 1),
            "Total_xP": round(xp_sum, 1),
            "xP_per_Mill": roi
        })
    df_pos = pd.DataFrame(pos_summary)

    c_roi1, c_roi2 = st.columns([1, 1])
    with c_roi1:
        st.markdown("##### 💰 Investert Kapital per Lagdel (£m)")
        chart_cost = alt.Chart(df_pos).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color='#3b82f6').encode(
            x=alt.X('Posisjon:N', title='Posisjon', sort=['GKP', 'DEF', 'MID', 'FWD']),
            y=alt.Y('Total_Pris:Q', title='Investert Kapital (£m)'),
            tooltip=['Posisjon:N', 'Antall:Q', 'Total_Pris:Q']
        ).properties(height=260)
        st.altair_chart(chart_cost, width="stretch")

    with c_roi2:
        st.markdown("##### ⚡ Forventet Avkastning (xP per Investert Million)")
        chart_roi = alt.Chart(df_pos).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color='#10b981').encode(
            x=alt.X('Posisjon:N', title='Posisjon', sort=['GKP', 'DEF', 'MID', 'FWD']),
            y=alt.Y('xP_per_Mill:Q', title='xP per Million (ROI)'),
            tooltip=['Posisjon:N', 'Total_xP:Q', 'xP_per_Mill:Q']
        ).properties(height=260)
        st.altair_chart(chart_roi, width="stretch")

    st.dataframe(
        df_pos.rename(columns={'Total_Pris': 'Totalverdi (£m)', 'Total_xP': 'Total xP', 'xP_per_Mill': 'xP per £m (ROI)'}),
        width="stretch",
        hide_index=True
    )

    # ------------------------------------------------------------------
    # SEKSJON 5: xG VS FAKTISKE MÅL (FINN SKJULTE VERDIFUNN)
    # ------------------------------------------------------------------
    st.markdown("---")
    with st.container(border=True):
        col_hdr, col_theme = st.columns([3, 1])
        with col_hdr:
            st.markdown("#### 🎯 xG vs. Faktiske Mål (Finn Skjulte Verdivalg)")
            st.caption("Spillere under den stiplede linjen (Høy xG, lav uttelling) underpresterer og har høy sannsynlighet for ketchup-effekt før markedet oppdager dem.")
        with col_theme:
            graph_theme = st.radio(
                "Graf-tema (Dark Reader):",
                ["☀️ Lys modus (Svart skrift)", "🌙 Mørk modus"],
                horizontal=True,
                index=0,
                key="f5_xg_theme"
            )

        xg_df = fpl_api.get_xg_analytics_df()
        if not xg_df.empty:
            col_xg1, col_xg2 = st.columns(2)
            with col_xg1:
                pos_xg_filter = st.multiselect("Filtrer posisjon:", ["DEF", "MID", "FWD"], default=["MID", "FWD"], key="xg_pos_f")
            with col_xg2:
                min_mins_xg = st.slider("Minimum spilte minutter:", min_value=90, max_value=360, value=180, key="xg_mins_f")

            filtered_xg = xg_df[
                (xg_df["position"].isin(pos_xg_filter)) &
                (xg_df["minutes"] >= min_mins_xg)
            ].copy()
            filtered_xg["name_bold"] = "<b>" + filtered_xg["name"] + "</b>"

            max_val = max(filtered_xg["xg"].max(), filtered_xg["goals"].max(), 5.0) + 0.5

            if "Lys" in graph_theme:
                fig_xg = px.scatter(
                    filtered_xg, x="xg", y="goals", text="name_bold", color="diff_goals",
                    color_continuous_scale=[[0.0, "#dc2626"], [0.5, "#d97706"], [1.0, "#16a34a"]],
                    labels={"xg": "Expected Goals (xG)", "goals": "Faktiske Mål", "diff_goals": "Mål - xG"}
                )
                fig_xg.update_traces(
                    textposition="top center",
                    textfont=dict(color="#000000", size=14, family="Arial, Helvetica, sans-serif"),
                    marker=dict(size=16, line=dict(width=2, color="#000000"))
                )
                fig_xg.update_layout(
                    title=dict(text="<b>xG vs Faktiske Mål per Spiller (Høy Kontrast - Svart Skrift)</b>", font=dict(size=17, color="#000000")),
                    paper_bgcolor="#ffffff", plot_bgcolor="#f8fafc",
                    font=dict(color="#000000", size=13), height=560,
                    margin=dict(l=55, r=35, t=60, b=55),
                    xaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#94a3b8", linecolor="#000000", linewidth=2, tickfont=dict(color="#000000", size=13), title_font=dict(color="#000000", size=15)),
                    yaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#94a3b8", linecolor="#000000", linewidth=2, tickfont=dict(color="#000000", size=13), title_font=dict(color="#000000", size=15))
                )
                fig_xg.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="#2563eb", width=2.5, dash="dash"))
                fig_xg.add_annotation(x=max_val * 0.8, y=max_val * 0.82, text="<b>Balanse (xG = Mål)</b>", showarrow=False, font=dict(color="#1d4ed8", size=13))
            else:
                fig_xg = px.scatter(
                    filtered_xg, x="xg", y="goals", text="name_bold", color="diff_goals",
                    color_continuous_scale=[[0.0, "#ff3366"], [0.5, "#ffd600"], [1.0, "#00ff87"]],
                    labels={"xg": "Expected Goals (xG)", "goals": "Faktiske Mål", "diff_goals": "Mål - xG"}
                )
                fig_xg.update_traces(
                    textposition="top center", textfont=dict(color="#ffffff", size=14),
                    marker=dict(size=16, line=dict(width=1.5, color="#ffffff"))
                )
                apply_hc_theme(fig_xg, "xG vs Faktiske Mål per Spiller", height=540)
                fig_xg.add_shape(type="line", x0=0, y0=0, x1=max_val, y1=max_val, line=dict(color="#00e5ff", width=2.5, dash="dash"))
                fig_xg.add_annotation(x=max_val * 0.8, y=max_val * 0.82, text="Balanse (xG = Mål)", showarrow=False, font=dict(color="#00e5ff", size=12, weight="bold"))

            st.plotly_chart(fig_xg, width="stretch")

# Footer
st.markdown("---")
st.caption("FPL Super Optimizer & Dashboard | Drevet av PuLP MILP Lineærprogrammering, FPL Live API & Premier League CDN | Manager ID: 117526")
