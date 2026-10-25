"""
fpl_api.py - FPL API Integration & Data Engine
Henter og strukturerer all FPL-data: Manager, tropp, miniligaer, terminlister, form og projeksjoner.
"""
import os
import json
import time
import requests
from pathlib import Path
from collections import Counter
import pandas as pd
import numpy as np

BASE_URL = "https://fantasy.premierleague.com/api"
PROJECT_ROOT = Path(__file__).parent
CACHE_DIR = PROJECT_ROOT / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------
# Caching HTTP Client
# ---------------------------------------------------------
def cached_get(endpoint: str, ttl_seconds: int = 300) -> dict:
    sanitized = endpoint.replace("/", "_").replace("?", "_").replace("&", "_").replace("=", "_")
    cache_file = CACHE_DIR / f"{sanitized}.json"
    now = time.time()
    if cache_file.exists():
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                cached = json.load(f)
                if now - cached.get("time", 0) < ttl_seconds:
                    return cached.get("data")
        except Exception:
            pass

    url = endpoint if endpoint.startswith("http") else f"{BASE_URL}/{endpoint}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"time": now, "data": data}, f)
    except Exception:
        pass
    return data

# ---------------------------------------------------------
# FPL API Core Endpoints
# ---------------------------------------------------------
def get_bootstrap_static() -> dict:
    return cached_get("bootstrap-static/", ttl_seconds=600)

def get_fixtures_data() -> list:
    return cached_get("fixtures/", ttl_seconds=600)

def get_manager_entry(manager_id: int = 117526) -> dict:
    return cached_get(f"entry/{manager_id}/", ttl_seconds=120)

def get_manager_history(manager_id: int = 117526) -> dict:
    return cached_get(f"entry/{manager_id}/history/", ttl_seconds=120)

def get_manager_transfers(manager_id: int = 117526) -> list:
    return cached_get(f"entry/{manager_id}/transfers/", ttl_seconds=120)

def get_manager_picks(manager_id: int = 117526, event: int = None) -> dict:
    if event is None:
        static = get_bootstrap_static()
        current_events = [e for e in static["events"] if e["is_current"]]
        event = current_events[0]["id"] if current_events else 1
    return cached_get(f"entry/{manager_id}/event/{event}/picks/", ttl_seconds=120)

def get_league_standings(league_id: int) -> dict:
    return cached_get(f"leagues-classic/{league_id}/standings/", ttl_seconds=180)

def get_live_gameweek(gw: int) -> dict:
    return cached_get(f"event/{gw}/live/", ttl_seconds=60)

def get_element_summary(player_id: int) -> dict:
    """
    Henter full historikk og kommende kamper for en gitt spiller:
    - history: alle spilte runder med poeng, minutter, mål, assists, xG, xA, CS, bonus osv.
    - fixtures: gjenstående kamper i sesongen med FDR
    - history_past: tidligere sesonger
    """
    return cached_get(f"element-summary/{player_id}/", ttl_seconds=300)

# ---------------------------------------------------------
# Premier League Club Metadata (Official Gradients & Badges)
# ---------------------------------------------------------
PL_CLUB_COLORS = {
    "ARS": {"primary": "#EF0107", "secondary": "#063672", "gradient": "linear-gradient(135deg, #EF0107 0%, #9B0004 100%)", "text": "#FFFFFF"},
    "AVL": {"primary": "#670E36", "secondary": "#95BFE5", "gradient": "linear-gradient(135deg, #670E36 0%, #3B061E 100%)", "text": "#FFFFFF"},
    "BOU": {"primary": "#DA291C", "secondary": "#000000", "gradient": "linear-gradient(135deg, #DA291C 0%, #800000 100%)", "text": "#FFFFFF"},
    "BRE": {"primary": "#E30613", "secondary": "#000000", "gradient": "linear-gradient(135deg, #E30613 0%, #8B0000 100%)", "text": "#FFFFFF"},
    "BHA": {"primary": "#0057B8", "secondary": "#FFCD00", "gradient": "linear-gradient(135deg, #0057B8 0%, #002B5C 100%)", "text": "#FFFFFF"},
    "CHE": {"primary": "#034694", "secondary": "#EE242C", "gradient": "linear-gradient(135deg, #034694 0%, #011E42 100%)", "text": "#FFFFFF"},
    "CRY": {"primary": "#1B458F", "secondary": "#C4122E", "gradient": "linear-gradient(135deg, #1B458F 0%, #C4122E 100%)", "text": "#FFFFFF"},
    "EVE": {"primary": "#003399", "secondary": "#FFFFFF", "gradient": "linear-gradient(135deg, #003399 0%, #001A4D 100%)", "text": "#FFFFFF"},
    "FUL": {"primary": "#000000", "secondary": "#CC0000", "gradient": "linear-gradient(135deg, #222222 0%, #000000 100%)", "text": "#FFFFFF"},
    "IPS": {"primary": "#004494", "secondary": "#E4002B", "gradient": "linear-gradient(135deg, #004494 0%, #00224A 100%)", "text": "#FFFFFF"},
    "LEI": {"primary": "#003090", "secondary": "#FDBE11", "gradient": "linear-gradient(135deg, #003090 0%, #001A4E 100%)", "text": "#FFFFFF"},
    "LIV": {"primary": "#C8102E", "secondary": "#00B2A9", "gradient": "linear-gradient(135deg, #C8102E 0%, #78091B 100%)", "text": "#FFFFFF"},
    "MCI": {"primary": "#6CABDD", "secondary": "#1C2C5B", "gradient": "linear-gradient(135deg, #6CABDD 0%, #1C2C5B 100%)", "text": "#FFFFFF"},
    "MUN": {"primary": "#DA291C", "secondary": "#FBE122", "gradient": "linear-gradient(135deg, #DA291C 0%, #850F07 100%)", "text": "#FFFFFF"},
    "NEW": {"primary": "#241F20", "secondary": "#41B6E6", "gradient": "linear-gradient(135deg, #241F20 0%, #000000 100%)", "text": "#FFFFFF"},
    "NFO": {"primary": "#DD0000", "secondary": "#FFFFFF", "gradient": "linear-gradient(135deg, #DD0000 0%, #7A0000 100%)", "text": "#FFFFFF"},
    "SOU": {"primary": "#D71920", "secondary": "#130C0E", "gradient": "linear-gradient(135deg, #D71920 0%, #7E0A0E 100%)", "text": "#FFFFFF"},
    "TOT": {"primary": "#132257", "secondary": "#FFFFFF", "gradient": "linear-gradient(135deg, #132257 0%, #070D22 100%)", "text": "#FFFFFF"},
    "WHU": {"primary": "#7A263A", "secondary": "#1BB1E7", "gradient": "linear-gradient(135deg, #7A263A 0%, #3D0D19 100%)", "text": "#FFFFFF"},
    "WOL": {"primary": "#FDB913", "secondary": "#231F20", "gradient": "linear-gradient(135deg, #FDB913 0%, #B88102 100%)", "text": "#000000"}
}

# Spillere som nylig har skiftet klubb (f.eks. Ndiaye til Man City, Maitland-Niles til Everton)
# der Premier Leagues offisielle 2026/27-studiobilde ennå ikke er publisert på premierleague25 CDN:
PENDING_NEW_PHOTOS = {"154043", "440993"}

def get_player_photo_urls(photo_raw: str) -> tuple[str, str]:
    """
    Returnerer primær URL (offisielt høyoppløselig 2026/27 500x500 bilde fra premierleague25)
    og sekundær fallback-URL (legacy 250x250 bilde).
    For nysigneringer med ventende fotoshoot brukes det offisielle arkivbildet direkte.
    """
    if not photo_raw:
        return "", ""
    clean_code = str(photo_raw).replace(".jpg", "").replace(".png", "").replace("p", "").strip()
    legacy_url = f"https://resources.premierleague.com/premierleague/photos/players/250x250/p{clean_code}.png"
    
    if clean_code in PENDING_NEW_PHOTOS:
        return legacy_url, legacy_url

    current_season_url = f"https://resources.premierleague.com/premierleague25/photos/players/500x500/{clean_code}.png"
    return current_season_url, legacy_url

def format_player_status(status: str, chance: int | float | None = None) -> str:
    """
    Oversetter interne FPL-statuskoder ('a', 'd', 'i', 's', 'u', 'n') og spillesjanse (%)
    til et intuitivt og tydelig norsk format med fargeindikatorer (f.eks. '🟢 Klar', '🟡 Usikker (75%)').
    """
    s = str(status or "a").lower().strip()
    if s == "a":
        return "🟢 Klar"
    elif s == "d":
        if chance is not None and pd.notna(chance):
            return f"🟡 Usikker ({int(chance)}%)"
        return "🟡 Usikker"
    elif s == "i":
        if chance is not None and pd.notna(chance) and int(chance) > 0:
            return f"🔴 Skadet ({int(chance)}%)"
        return "🔴 Skadet"
    elif s == "s":
        return "🔴 Karantene"
    elif s == "u":
        return "🔴 Utilgjengelig"
    elif s == "n":
        return "⚪ Lånt ut"
    else:
        return f"⚪ {s.upper()}"

# ---------------------------------------------------------
# Helper & Extraction Methods
# ---------------------------------------------------------
def get_current_and_next_gw(static: dict = None) -> tuple[int, int]:
    if static is None:
        static = get_bootstrap_static()
    events = static.get("events", [])
    current_gw = next((e["id"] for e in events if e.get("is_current")), 1)
    next_gw = next((e["id"] for e in events if e.get("is_next")), current_gw + 1)
    return current_gw, next_gw

def get_deadline_info() -> dict:
    static = get_bootstrap_static()
    events = static.get("events", [])
    next_event = next((e for e in events if e.get("is_next")), None)
    if not next_event:
        return {"next_gw": None, "deadline_iso": None, "name": "Ingen kommende GW"}
    return {
        "next_gw": next_event["id"],
        "name": next_event["name"],
        "deadline_iso": next_event["deadline_time"],
    }

def get_manager_summary(manager_id: int = 117526) -> dict:
    entry = get_manager_entry(manager_id)
    history = get_manager_history(manager_id)
    static = get_bootstrap_static()
    current_gw, next_gw = get_current_and_next_gw(static)
    picks_data = get_manager_picks(manager_id, current_gw)

    entry_hist = picks_data.get("entry_history", {})
    bank = entry_hist.get("bank", 0) / 10.0
    team_value = entry_hist.get("value", 0) / 10.0
    total_points = entry.get("summary_overall_points", 0)
    overall_rank = entry.get("summary_overall_rank", 0)
    last_gw_points = entry.get("summary_event_points", 0)

    # Classic minileagues
    classic_leagues = entry.get("leagues", {}).get("classic", [])
    custom_leagues = [lg for lg in classic_leagues if lg.get("league_type") == "x"]
    if not custom_leagues:
        custom_leagues = classic_leagues

    # Used chips
    chips = history.get("chips", [])

    return {
        "manager_id": manager_id,
        "manager_name": f"{entry.get('player_first_name', '')} {entry.get('player_last_name', '')}".strip(),
        "team_name": entry.get("name", ""),
        "total_points": total_points,
        "overall_rank": overall_rank,
        "last_gw_points": last_gw_points,
        "bank": bank,
        "team_value": team_value,
        "current_gw": current_gw,
        "next_gw": next_gw,
        "classic_leagues": custom_leagues,
        "all_classic_leagues": classic_leagues,
        "chips": chips,
    }

def get_detailed_squad(manager_id: int = 117526, event: int = None) -> list[dict]:
    static = get_bootstrap_static()
    fixtures = get_fixtures_data()
    elements = {e["id"]: e for e in static["elements"]}
    teams = {t["id"]: t for t in static["teams"]}
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    
    current_gw, next_gw = get_current_and_next_gw(static)
    target_event = event or current_gw
    picks_resp = get_manager_picks(manager_id, target_event)
    picks = picks_resp.get("picks", [])

    # Lookup upcoming fixtures for next_gw
    next_gw_fixtures = [f for f in fixtures if f.get("event") == next_gw]
    team_fixtures_map = {t_id: [] for t_id in teams.keys()}
    for f in next_gw_fixtures:
        h_id = f["team_h"]
        a_id = f["team_a"]
        team_fixtures_map[h_id].append({"opp": teams[a_id]["short_name"], "venue": "H", "diff": f["team_h_difficulty"]})
        team_fixtures_map[a_id].append({"opp": teams[h_id]["short_name"], "venue": "A", "diff": f["team_a_difficulty"]})

    squad_details = []
    for p in picks:
        elem_id = p["element"]
        elem = elements.get(elem_id, {})
        team_id = elem.get("team")
        team = teams.get(team_id, {})
        
        pos_id = elem.get("element_type", 1)
        pos = pos_map.get(pos_id, "MID")
        
        # Calculate expected points for next round
        ep = float(elem.get("ep_next") or elem.get("form") or 0.0)
        chance = elem.get("chance_of_playing_next_round")
        if chance is not None:
            chance = int(chance)
        else:
            chance = 100 if elem.get("status") == "a" else 0

        news = elem.get("news", "")
        status = elem.get("status", "a")

        # Upcoming fixture info for next_gw
        t_matches = team_fixtures_map.get(team_id, [])
        if len(t_matches) == 0:
            fixture_str = "BGW (Ingen kamp)"
            is_blank = True
            is_double = False
        elif len(t_matches) == 1:
            m = t_matches[0]
            fixture_str = f"{m['opp']} ({m['venue']})"
            is_blank = False
            is_double = False
        else:
            fixture_str = "DGW (" + " + ".join([f"{m['opp']}({m['venue']})" for m in t_matches]) + ")"
            is_blank = False
            is_double = True

        photo_raw = elem.get("photo", "")
        photo_url, legacy_photo_url = get_player_photo_urls(photo_raw)
        team_code = team.get("code", 0)
        badge_url = f"https://resources.premierleague.com/premierleague/badges/70/t{team_code}.png" if team_code else ""
        club_meta = PL_CLUB_COLORS.get(team.get("short_name", ""), {"primary": "#37003c", "secondary": "#00ff87", "gradient": "linear-gradient(135deg, #37003c 0%, #00ff87 100%)", "text": "#FFFFFF"})

        squad_details.append({
            "element_id": elem_id,
            "id": elem_id,
            "name": elem.get("web_name", ""),
            "full_name": f"{elem.get('first_name')} {elem.get('second_name')}",
            "position": pos,
            "position_id": pos_id,
            "team_id": team_id,
            "team_name": team.get("name", ""),
            "team_short": team.get("short_name", ""),
            "cost": elem.get("now_cost", 0) / 10.0,
            "form": float(elem.get("form") or 0.0),
            "ep_next": ep,
            "chance_of_playing": chance,
            "status": status,
            "status_formatted": format_player_status(status, chance),
            "news": news,
            "is_starter": p["position"] <= 11,
            "multiplier": p["multiplier"],
            "is_captain": p["is_captain"],
            "is_vice_captain": p["is_vice_captain"],
            "pitch_order": p["position"],
            "fixture": fixture_str,
            "is_blank": is_blank,
            "is_double": is_double,
            "photo_url": photo_url,
            "legacy_photo_url": legacy_photo_url,
            "badge_url": badge_url,
            "team_code": team_code,
            "club_gradient": club_meta["gradient"],
            "club_primary": club_meta["primary"],
            "club_secondary": club_meta["secondary"],
            "club_text": club_meta["text"]
        })
    return squad_details

def get_bgw_dgw_alerts(horizon: int = 5) -> list[dict]:
    """
    Sjekker alle runder i planleggingshorisonten for Blank Gameweeks (0 kamper) og Double Gameweeks (2+ kamper).
    """
    static = get_bootstrap_static()
    fixtures = get_fixtures_data()
    teams = {t["id"]: t["short_name"] for t in static["teams"]}
    current_gw, next_gw = get_current_and_next_gw(static)
    target_gws = list(range(next_gw, min(39, next_gw + horizon)))

    alerts = []
    for gw in target_gws:
        gw_fixes = [f for f in fixtures if f.get("event") == gw]
        counts = {t_id: 0 for t_id in teams.keys()}
        for f in gw_fixes:
            counts[f["team_h"]] += 1
            counts[f["team_a"]] += 1

        blanks = [teams[t_id] for t_id, cnt in counts.items() if cnt == 0]
        doubles = [teams[t_id] for t_id, cnt in counts.items() if cnt >= 2]

        if blanks:
            alerts.append({
                "gw": gw,
                "type": "BGW",
                "teams": blanks,
                "title": f"⚠️ Blank Gameweek (BGW) i GW {gw}",
                "desc": f"Følgende lag har INGEN kamper i GW {gw}: {', '.join(blanks)}. Spillere herfra vil gi 0 poeng! Vurder Free Hit eller benk.",
                "severity": "warning"
            })
        if doubles:
            alerts.append({
                "gw": gw,
                "type": "DGW",
                "teams": doubles,
                "title": f"🔥 Dobbel Gameweek (DGW) i GW {gw}",
                "desc": f"Følgende lag spiller 2 KAMPER i GW {gw}: {', '.join(doubles)}. Spillere herfra får dobbel poengmulighet! Anbefalt for Triple Captain / Bench Boost.",
                "severity": "success"
            })
    return alerts

# ---------------------------------------------------------
# Fixtures & FDR Engine
# ---------------------------------------------------------
def get_fdr_matrix(horizon: int = 5) -> tuple[pd.DataFrame, dict]:
    static = get_bootstrap_static()
    fixtures = get_fixtures_data()
    current_gw, next_gw = get_current_and_next_gw(static)
    target_gws = list(range(next_gw, min(39, next_gw + horizon)))

    teams = {t["id"]: t["short_name"] for t in static["teams"]}
    team_names = sorted(list(teams.values()))

    # Build matrix: rows = team_short, cols = GWs
    # Each cell: {"opponent": "ARS (H)", "fdr": 4, "is_bgw": False, "is_dgw": False}
    matrix = {t: {} for t in team_names}
    meta_info = {t: {} for t in team_names}

    for gw in target_gws:
        gw_fixtures = [f for f in fixtures if f.get("event") == gw]
        team_matches = {t_id: [] for t_id in teams.keys()}
        for f in gw_fixtures:
            h_id = f["team_h"]
            a_id = f["team_a"]
            team_matches[h_id].append({
                "opp_id": a_id,
                "opp_name": teams[a_id],
                "venue": "H",
                "fdr": f["team_h_difficulty"]
            })
            team_matches[a_id].append({
                "opp_id": h_id,
                "opp_name": teams[h_id],
                "venue": "A",
                "fdr": f["team_a_difficulty"]
            })

        for t_id, short in teams.items():
            matches = team_matches[t_id]
            if len(matches) == 0:
                matrix[short][f"GW{gw}"] = "BGW"
                meta_info[short][f"GW{gw}"] = {"fdr": 0, "label": "BLANK", "type": "BGW"}
            elif len(matches) == 1:
                m = matches[0]
                label = f"{m['opp_name']} ({m['venue']})"
                matrix[short][f"GW{gw}"] = label
                meta_info[short][f"GW{gw}"] = {"fdr": m["fdr"], "label": label, "type": "NORMAL"}
            else:
                # DGW
                label = " / ".join([f"{m['opp_name']}({m['venue']})" for m in matches])
                avg_fdr = sum(m["fdr"] for m in matches) / len(matches)
                matrix[short][f"GW{gw}"] = label
                meta_info[short][f"GW{gw}"] = {"fdr": avg_fdr, "label": label, "type": "DGW"}

    df_labels = pd.DataFrame.from_dict(matrix, orient="index")
    return df_labels, meta_info

# ---------------------------------------------------------
# xG vs Goals & Form Analytics
# ---------------------------------------------------------
def get_xg_analytics_df() -> pd.DataFrame:
    static = get_bootstrap_static()
    elements = static.get("elements", [])
    teams = {t["id"]: t["short_name"] for t in static["teams"]}
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

    records = []
    for e in elements:
        try:
            mins = int(e.get("minutes", 0))
            if mins < 90:
                continue
            xg = float(e.get("expected_goals", 0.0) or 0.0)
            xa = float(e.get("expected_assists", 0.0) or 0.0)
            xgi = float(e.get("expected_goal_involvements", 0.0) or 0.0)
            goals = int(e.get("goals_scored", 0))
            assists = int(e.get("assists", 0))
            diff_goals = goals - xg

            records.append({
                "id": e["id"],
                "name": e["web_name"],
                "team": teams.get(e["team"], ""),
                "position": pos_map.get(e["element_type"], "MID"),
                "cost": e["now_cost"] / 10.0,
                "minutes": mins,
                "xg": round(xg, 2),
                "goals": goals,
                "xa": round(xa, 2),
                "assists": assists,
                "xgi": round(xgi, 2),
                "diff_goals": round(diff_goals, 2),
                "form": float(e.get("form") or 0.0),
                "selected_by": float(e.get("selected_by_percent") or 0.0),
                "ep_next": float(e.get("ep_next") or 0.0),
            })
        except Exception:
            continue

    return pd.DataFrame(records)

# ---------------------------------------------------------
# Price Changes Radar
# ---------------------------------------------------------
def get_price_change_radar(manager_id: int = 117526) -> tuple[pd.DataFrame, pd.DataFrame]:
    static = get_bootstrap_static()
    elements = static.get("elements", [])
    teams = {t["id"]: t["short_name"] for t in static["teams"]}
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

    squad = get_detailed_squad(manager_id)
    my_ids = {p["element_id"] for p in squad}

    all_players = []
    for e in elements:
        in_ev = int(e.get("transfers_in_event", 0))
        out_ev = int(e.get("transfers_out_event", 0))
        net = in_ev - out_ev
        cost = e["now_cost"] / 10.0
        all_players.append({
            "id": e["id"],
            "name": e["web_name"],
            "team": teams.get(e["team"], ""),
            "position": pos_map.get(e["element_type"], "MID"),
            "cost": cost,
            "transfers_in": in_ev,
            "transfers_out": out_ev,
            "net_transfers": net,
            "form": float(e.get("form") or 0.0),
            "selected_by": float(e.get("selected_by_percent") or 0.0),
            "in_squad": e["id"] in my_ids
        })

    df = pd.DataFrame(all_players)

    # Squad players with price fall danger (negative net transfers)
    squad_danger = df[df["in_squad"]].sort_values(by=["net_transfers"], ascending=True)

    # Market players approaching price rise (highest net transfers in)
    market_risers = df[~df["in_squad"]].sort_values(by=["net_transfers"], ascending=False).head(15)

    return squad_danger, market_risers

# ---------------------------------------------------------
# Mini-league Effective Ownership (EO) & Rival Tracking
# ---------------------------------------------------------
# Mini-league Effective Ownership (EO), Chips & Rival Tracking
# ---------------------------------------------------------
def get_league_rival_analysis(league_id: int, manager_id: int = 117526, max_rivals: int = 25) -> dict:
    league_data = get_league_standings(league_id)
    raw_standings = league_data.get("standings", {}).get("results", [])
    league_name = league_data.get("league", {}).get("name", "Miniliga")
    
    if not raw_standings:
        return {
            "league_name": league_name,
            "standings": pd.DataFrame(),
            "eo_df": pd.DataFrame(),
            "differentials": pd.DataFrame(),
            "chips_matrix": pd.DataFrame(),
            "captain_distribution": pd.DataFrame(),
            "overlap_df": pd.DataFrame(),
            "template_team": pd.DataFrame(),
            "chase_stats": {}
        }

    static = get_bootstrap_static()
    elements = {e["id"]: e for e in static["elements"]}
    teams = {t["id"]: t["short_name"] for t in static["teams"]}
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}
    current_gw, next_gw = get_current_and_next_gw(static)

    my_squad = get_detailed_squad(manager_id, current_gw)
    my_ids = {p["element_id"] for p in my_squad}
    my_starter_ids = {p["element_id"] for p in my_squad if p["is_starter"]}

    # Inspect rivals up to max_rivals
    standings_rows = []
    chips_rows = []
    overlap_rows = []
    rival_picks_count = Counter()
    rival_captain_count = Counter()
    total_rivals_inspected = 0

    target_entries = raw_standings[:max_rivals]

    for s in target_entries:
        r_id = s["entry"]
        is_me = (r_id == manager_id)
        r_name = s.get("player_name", "")
        e_name = s.get("entry_name", "")
        rank = s.get("rank", 0)
        total = s.get("total", 0)
        event_total = s.get("event_total", 0)

        # Defaults
        captain_name = "-"
        transfers_count = 0
        hit_cost = 0
        bank = 0.0
        val = 0.0
        rival_squad_ids = set()
        chips_used_list = []

        try:
            picks_resp = get_manager_picks(r_id, current_gw)
            eh = picks_resp.get("entry_history", {})
            bank = eh.get("bank", 0) / 10.0
            val = eh.get("value", 0) / 10.0
            transfers_count = eh.get("event_transfers", 0)
            hit_cost = eh.get("event_transfers_cost", 0)
            picks = picks_resp.get("picks", [])

            for p in picks:
                elem_id = p["element"]
                rival_squad_ids.add(elem_id)
                is_starter = p["position"] <= 11
                if is_starter and not is_me:
                    rival_picks_count[elem_id] += 1
                if p.get("is_captain"):
                    c_elem = elements.get(elem_id, {})
                    captain_name = c_elem.get("web_name", "-")
                    if not is_me:
                        rival_captain_count[captain_name] += 1

            if not is_me and picks:
                total_rivals_inspected += 1

            # Fetch chips history
            hist_resp = get_manager_history(r_id)
            chips_used_list = [c["name"].lower() for c in hist_resp.get("chips", [])]

        except Exception:
            pass

        # Chip status mapping
        def format_chip(code):
            for c in chips_used_list:
                if code in c or (code == "tc" and "3x" in c) or (code == "bb" and "boost" in c):
                    return "Brukt ❌"
            return "Tilgjengelig 🟢"

        chips_rows.append({
            "Plassering": rank,
            "Manager": r_name,
            "Lag": e_name,
            "Wildcard": format_chip("wildcard") if "wildcard" in chips_used_list else ("Brukt ❌" if "wc" in chips_used_list else "Tilgjengelig 🟢"),
            "Free Hit": format_chip("freehit") if "freehit" in chips_used_list else ("Brukt ❌" if "fh" in chips_used_list else "Tilgjengelig 🟢"),
            "Bench Boost": format_chip("bboost") if "bboost" in chips_used_list else ("Brukt ❌" if "bb" in chips_used_list else "Tilgjengelig 🟢"),
            "Triple Captain": format_chip("3xc") if "3xc" in chips_used_list else ("Brukt ❌" if "tc" in chips_used_list else "Tilgjengelig 🟢"),
            "is_me": is_me
        })

        standings_rows.append({
            "rank": rank,
            "last_rank": s.get("last_rank", rank),
            "entry_name": e_name,
            "player_name": r_name,
            "total": total,
            "event_total": event_total,
            "captain": captain_name,
            "transfers": transfers_count,
            "hit_cost": hit_cost,
            "bank": bank,
            "value": val,
            "entry_id": r_id,
            "is_me": is_me
        })

        if not is_me and rival_squad_ids:
            common_count = len(rival_squad_ids.intersection(my_ids))
            sim_pct = round((common_count / 15.0) * 100, 1)
            they_have_not_me = [elements[pid]["web_name"] for pid in (rival_squad_ids - my_ids) if pid in elements]
            i_have_not_them = [elements[pid]["web_name"] for pid in (my_ids - rival_squad_ids) if pid in elements]
            overlap_rows.append({
                "Plassering": rank,
                "Manager": r_name,
                "Lag": e_name,
                "Like Spillere": f"{common_count}/15",
                "Likhet (%)": sim_pct,
                "De har (du mangler)": ", ".join(they_have_not_me[:4]) + ("..." if len(they_have_not_me) > 4 else ""),
                "Du har (de mangler)": ", ".join(i_have_not_them[:4]) + ("..." if len(i_have_not_them) > 4 else "")
            })

    df_standings = pd.DataFrame(standings_rows)
    df_chips = pd.DataFrame(chips_rows)
    df_overlap = pd.DataFrame(overlap_rows).sort_values(by=["Plassering"], ascending=True)

    denom = max(1, total_rivals_inspected)

    # Effective Ownership & Differentials
    eo_list = []
    template_list = []
    for elem_id, count in rival_picks_count.items():
        elem = elements.get(elem_id, {})
        cap_name = elem.get("web_name", "")
        captains = rival_captain_count.get(cap_name, 0)
        eo_pct = round(((count + captains) / denom) * 100, 1)
        ownership_pct = round((count / denom) * 100, 1)

        item = {
            "id": elem_id,
            "name": elem.get("web_name", ""),
            "team": teams.get(elem.get("team"), ""),
            "position": pos_map.get(elem.get("element_type", 1), "MID"),
            "cost": elem.get("now_cost", 0) / 10.0,
            "form": float(elem.get("form") or 0.0),
            "ep_next": float(elem.get("ep_next") or 0.0),
            "ownership_pct": ownership_pct,
            "eo_pct": eo_pct,
            "owned_by_me": elem_id in my_ids,
            "danger_rating": "HØY RISIKO" if (eo_pct >= 40 and elem_id not in my_ids) else ("MODERAT" if (eo_pct >= 20 and elem_id not in my_ids) else "TRYGG")
        }
        eo_list.append(item)
        template_list.append({
            "Spiller": elem.get("web_name", ""),
            "Klubb": teams.get(elem.get("team"), ""),
            "Posisjon": pos_map.get(elem.get("element_type", 1), "MID"),
            "Pris": elem.get("now_cost", 0) / 10.0,
            "Liga Eierandel (%)": ownership_pct,
            "Status i ditt lag": "✅ På ditt lag" if elem_id in my_ids else "❌ Mangler"
        })

    df_eo = pd.DataFrame(eo_list).sort_values(by=["eo_pct"], ascending=False)
    df_diff = df_eo[~df_eo["owned_by_me"]].sort_values(by=["eo_pct"], ascending=False)
    df_template = pd.DataFrame(template_list).sort_values(by=["Liga Eierandel (%)"], ascending=False).head(15)

    # Captain distribution
    cap_rows = [{"Kaptein": k, "Antall Valg": v, "Andel (%)": round((v / denom) * 100, 1)} for k, v in rival_captain_count.items()]
    df_captains = pd.DataFrame(cap_rows).sort_values(by=["Antall Valg"], ascending=False)

    # Chase & Gap analysis
    leader_row = df_standings.iloc[0] if not df_standings.empty else {}
    my_row_list = [r for _, r in df_standings.iterrows() if r["is_me"]]
    my_row = my_row_list[0] if my_row_list else {}

    leader_pts = leader_row.get("total", 0)
    my_pts = my_row.get("total", 0)
    gap_to_leader = max(0, leader_pts - my_pts)
    gws_remaining = max(1, 38 - current_gw)
    pts_per_gw_needed = round(gap_to_leader / gws_remaining, 2)

    third_row = df_standings.iloc[2] if len(df_standings) >= 3 else leader_row
    third_pts = third_row.get("total", 0)
    gap_to_third = max(0, third_pts - my_pts)
    pts_per_gw_to_third = round(gap_to_third / gws_remaining, 2)

    chase_stats = {
        "leader_name": f"{leader_row.get('player_name', '')} ({leader_row.get('entry_name', '')})",
        "leader_pts": leader_pts,
        "third_name": f"{third_row.get('player_name', '')} ({third_row.get('entry_name', '')})",
        "third_pts": third_pts,
        "my_pts": my_pts,
        "my_rank": my_row.get("rank", 1),
        "gap_to_leader": gap_to_leader,
        "gap_to_third": gap_to_third,
        "gws_remaining": gws_remaining,
        "pts_per_gw_needed": pts_per_gw_needed,
        "pts_per_gw_to_third": pts_per_gw_to_third,
        "league_avg_total": round(df_standings["total"].mean(), 1) if not df_standings.empty else 0,
        "league_avg_gw": round(df_standings["event_total"].mean(), 1) if not df_standings.empty else 0
    }

    return {
        "league_name": league_name,
        "standings": df_standings,
        "eo_df": df_eo,
        "differentials": df_diff,
        "chips_matrix": df_chips,
        "captain_distribution": df_captains,
        "overlap_df": df_overlap,
        "template_team": df_template,
        "chase_stats": chase_stats,
        "rivals_count": total_rivals_inspected
    }

# ---------------------------------------------------------
# Dynamic xP Projection Engine (Generates solver projection CSV)
# ---------------------------------------------------------
def generate_dynamic_projections_csv(horizon: int = 5, output_filename: str = "fplreview.csv") -> Path:
    """
    Generates a full projection dataset compatible with Sertalp's solver:
    Columns: ID, Name, Pos, Team, Value + {gw}_Pts + {gw}_xMins for gw in horizon
    """
    static = get_bootstrap_static()
    fixtures = get_fixtures_data()
    current_gw, next_gw = get_current_and_next_gw(static)
    target_gws = list(range(next_gw, min(39, next_gw + horizon)))

    teams_map = {t["id"]: t["short_name"] for t in static["teams"]}
    pos_map = {1: "G", 2: "D", 3: "M", 4: "F"}

    # Build fixtures lookup per team and gw
    # team_fixtures[team_id][gw] = list of {is_home, diff, opp_id}
    team_fixtures = {t_id: {gw: [] for gw in target_gws} for t_id in teams_map.keys()}
    for f in fixtures:
        gw = f.get("event")
        if gw in target_gws:
            h_id = f["team_h"]
            a_id = f["team_a"]
            team_fixtures[h_id][gw].append({"is_home": True, "diff": f["team_h_difficulty"], "opp": a_id})
            team_fixtures[a_id][gw].append({"is_home": False, "diff": f["team_a_difficulty"], "opp": h_id})

    rows = []
    for e in static["elements"]:
        elem_id = e["id"]
        team_id = e["team"]
        pos = pos_map.get(e["element_type"], "M")
        name = e["web_name"]
        team_short = teams_map.get(team_id, "")
        value = round(e["now_cost"] / 10.0, 1)

        # Baseline expected points
        form = float(e.get("form") or 0.0)
        ppg = float(e.get("points_per_game") or 0.0)
        ep_next = float(e.get("ep_next") or 0.0)
        
        # Blended baseline
        base_xp = max(0.5, (ep_next * 0.5) + (form * 0.3) + (ppg * 0.2)) if (ep_next > 0 or form > 0) else max(0.5, ppg)
        
        # Minutes factor based on fitness / status
        chance = e.get("chance_of_playing_next_round")
        status = e.get("status", "a")
        total_mins = int(e.get("minutes", 0))

        if status != "a" and chance is not None and int(chance) == 0:
            default_mins = 0
        elif chance is not None and int(chance) <= 25:
            default_mins = 20
        elif chance is not None and int(chance) <= 50:
            default_mins = 40
        elif chance is not None and int(chance) <= 75:
            default_mins = 60
        else:
            default_mins = 85 if total_mins > 150 else (45 if total_mins > 45 else 15)

        row = {
            "ID": elem_id,
            "Name": name,
            "Pos": pos,
            "Team": team_short,
            "Value": value
        }

        # Calculate for each GW
        for gw in target_gws:
            matches = team_fixtures[team_id].get(gw, [])
            if len(matches) == 0:
                # BGW
                row[f"{gw}_Pts"] = 0.0
                row[f"{gw}_xMins"] = 0.0
            else:
                gw_pts = 0.0
                gw_mins = 0.0
                for m in matches:
                    diff = m["diff"]
                    # Difficulty multiplier: 2 -> 1.15, 3 -> 1.0, 4 -> 0.85, 5 -> 0.70
                    diff_factor = 1.0 - (diff - 3) * 0.15
                    # Home advantage: +8% if home, -8% if away
                    venue_factor = 1.08 if m["is_home"] else 0.92
                    
                    match_xp = base_xp * diff_factor * venue_factor * (default_mins / 90.0)
                    gw_pts += max(0.0, match_xp)
                    gw_mins += default_mins

                row[f"{gw}_Pts"] = round(gw_pts, 2)
                row[f"{gw}_xMins"] = round(min(180, gw_mins), 1)

        rows.append(row)

    df = pd.DataFrame(rows)

    # Save to FPL-Optimization-Tools/data/
    target_dir = PROJECT_ROOT / "FPL-Optimization-Tools" / "data"
    target_dir.mkdir(exist_ok=True, parents=True)
    out_path = target_dir / output_filename
    df.to_csv(out_path, index=False, encoding="utf-8")

    # Also save to root data/
    root_data = PROJECT_ROOT / "data"
    root_data.mkdir(exist_ok=True)
    df.to_csv(root_data / output_filename, index=False, encoding="utf-8")

    return out_path

# ---------------------------------------------------------
# Comprehensive Player Database Engine (All ~650 Players)
# ---------------------------------------------------------
def get_all_players_database(horizon: int = 5) -> pd.DataFrame:
    """
    Henter og strukturerer en komplett spillerdatabase for alle aktive spillere i Premier League
    med xP for neste runde, sum xP over horisont, form, terminliste (FDR), xG, xA, spilletid og verdi.
    """
    static = get_bootstrap_static()
    fixtures = get_fixtures_data()
    current_gw, next_gw = get_current_and_next_gw(static)
    target_gws = list(range(next_gw, min(39, next_gw + horizon)))

    teams_map = {t["id"]: t["short_name"] for t in static["teams"]}
    pos_map = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

    # Team fixtures per GW
    team_fixtures = {t_id: {gw: [] for gw in target_gws} for t_id in teams_map.keys()}
    for f in fixtures:
        gw = f.get("event")
        if gw in target_gws:
            h_id = f["team_h"]
            a_id = f["team_a"]
            team_fixtures[h_id][gw].append({"is_home": True, "diff": f["team_h_difficulty"], "opp": teams_map[a_id], "venue": "H"})
            team_fixtures[a_id][gw].append({"is_home": False, "diff": f["team_a_difficulty"], "opp": teams_map[h_id], "venue": "A"})

    rows = []
    for e in static["elements"]:
        elem_id = e["id"]
        team_id = e["team"]
        pos = pos_map.get(e["element_type"], "MID")
        name = e["web_name"]
        full_name = f"{e.get('first_name', '')} {e.get('second_name', '')}".strip()
        team_short = teams_map.get(team_id, "")
        cost = round(e["now_cost"] / 10.0, 1)

        form = float(e.get("form") or 0.0)
        ppg = float(e.get("points_per_game") or 0.0)
        ep_next = float(e.get("ep_next") or 0.0)
        total_pts = int(e.get("total_points") or 0)
        mins = int(e.get("minutes") or 0)
        selected_pct = float(e.get("selected_by_percent") or 0.0)
        goals = int(e.get("goals_scored") or 0)
        assists = int(e.get("assists") or 0)
        clean_sheets = int(e.get("clean_sheets") or 0)
        xg = float(e.get("expected_goals") or 0.0)
        xa = float(e.get("expected_assists") or 0.0)
        ict = float(e.get("ict_index") or 0.0)
        status = e.get("status", "a")
        chance = e.get("chance_of_playing_next_round")

        # Baseline expected points
        base_xp = max(0.5, (ep_next * 0.5) + (form * 0.3) + (ppg * 0.2)) if (ep_next > 0 or form > 0) else max(0.5, ppg)
        
        # Spilletidsfaktor
        if status != "a" and chance is not None and int(chance) == 0:
            default_mins = 0
        elif chance is not None and int(chance) <= 25:
            default_mins = 20
        elif chance is not None and int(chance) <= 50:
            default_mins = 40
        elif chance is not None and int(chance) <= 75:
            default_mins = 60
        else:
            default_mins = 85 if mins > 150 else (45 if mins > 45 else 15)

        # Neste kamp detaljer
        next_matches = team_fixtures[team_id].get(next_gw, [])
        if len(next_matches) == 0:
            next_fix_str = "BGW (Ingen kamp)"
            next_fdr = 0
            is_blank_next = True
            is_double_next = False
        elif len(next_matches) == 1:
            m = next_matches[0]
            next_fix_str = f"{m['opp']} ({m['venue']})"
            next_fdr = m["diff"]
            is_blank_next = False
            is_double_next = False
        else:
            next_fix_str = "DGW: " + " + ".join(f"{m['opp']}({m['venue']})" for m in next_matches)
            next_fdr = round(sum(m["diff"] for m in next_matches) / len(next_matches), 1)
            is_blank_next = False
            is_double_next = True

        # Beregn xP og FDR over runder
        gw_pts_list = []
        gw_fdr_list = []
        for gw in target_gws:
            matches = team_fixtures[team_id].get(gw, [])
            if len(matches) == 0:
                gw_pts_list.append(0.0)
                gw_fdr_list.append(3.0)
            else:
                gw_pts = 0.0
                for m in matches:
                    diff = m["diff"]
                    gw_fdr_list.append(diff)
                    diff_factor = 1.0 - (diff - 3) * 0.15
                    venue_factor = 1.08 if m["is_home"] else 0.92
                    match_xp = base_xp * diff_factor * venue_factor * (default_mins / 90.0)
                    gw_pts += max(0.0, match_xp)
                gw_pts_list.append(gw_pts)

        xp_next = round(gw_pts_list[0] if gw_pts_list else base_xp, 1)
        xp_1gw = xp_next
        xp_2gw = round(sum(gw_pts_list[:2]), 1) if len(gw_pts_list) >= 2 else xp_next
        xp_3gw = round(sum(gw_pts_list[:3]), 1) if len(gw_pts_list) >= 3 else xp_2gw
        xp_4gw = round(sum(gw_pts_list[:4]), 1) if len(gw_pts_list) >= 4 else xp_3gw
        xp_5gw = round(sum(gw_pts_list[:5]), 1) if len(gw_pts_list) >= 5 else xp_4gw

        fdr_1gw = round(gw_fdr_list[0], 1) if gw_fdr_list else 3.0
        fdr_2gw = round(sum(gw_fdr_list[:2]) / max(1, len(gw_fdr_list[:2])), 1) if len(gw_fdr_list) >= 2 else fdr_1gw
        fdr_3gw = round(sum(gw_fdr_list[:3]) / max(1, len(gw_fdr_list[:3])), 1) if len(gw_fdr_list) >= 3 else fdr_2gw
        fdr_4gw = round(sum(gw_fdr_list[:4]) / max(1, len(gw_fdr_list[:4])), 1) if len(gw_fdr_list) >= 4 else fdr_3gw
        fdr_5gw = round(sum(gw_fdr_list[:5]) / max(1, len(gw_fdr_list[:5])), 1) if len(gw_fdr_list) >= 5 else fdr_4gw
        photo_raw = e.get("photo", "")
        photo_url, legacy_photo_url = get_player_photo_urls(photo_raw)
        t_code = static["teams"][team_id - 1].get("code", 0) if (team_id - 1 < len(static["teams"])) else 0
        badge_url = f"https://resources.premierleague.com/premierleague/badges/70/t{t_code}.png" if t_code else ""
        c_meta = PL_CLUB_COLORS.get(team_short, {"primary": "#37003c", "secondary": "#00ff87", "gradient": "linear-gradient(135deg, #37003c 0%, #00ff87 100%)", "text": "#FFFFFF"})

        rows.append({
            "id": elem_id,
            "name": name,
            "full_name": full_name,
            "team": team_short,
            "team_short": team_short,
            "team_name": static["teams"][team_id - 1].get("name", team_short) if (team_id - 1 < len(static["teams"])) else team_short,
            "team_id": team_id,
            "position": pos,
            "cost": cost,
            "next_fixture": next_fix_str,
            "next_fdr": next_fdr,
            "fdr_1gw": fdr_1gw,
            "fdr_2gw": fdr_2gw,
            "fdr_3gw": fdr_3gw,
            "fdr_4gw": fdr_4gw,
            "fdr_5gw": fdr_5gw,
            "ep_next": xp_next,
            "xp_1gw": xp_1gw,
            "xp_2gw": xp_2gw,
            "xp_3gw": xp_3gw,
            "xp_4gw": xp_4gw,
            "xp_5gw": xp_5gw,
            "form": form,
            "total_points": total_pts,
            "minutes": mins,
            "selected_by_percent": selected_pct,
            "goals": goals,
            "assists": assists,
            "clean_sheets": clean_sheets,
            "xg": xg,
            "xa": xa,
            "ict_index": ict,
            "status": status,
            "chance_of_playing": chance,
            "status_formatted": format_player_status(status, chance),
            "is_blank_next": is_blank_next,
            "is_double_next": is_double_next,
            "photo_url": photo_url,
            "legacy_photo_url": legacy_photo_url,
            "badge_url": badge_url,
            "team_code": t_code,
            "club_gradient": c_meta["gradient"]
        })

    return pd.DataFrame(rows)

# ---------------------------------------------------------
# Live Gameweek Tracker Engine
# ---------------------------------------------------------
def get_live_tracker_data(manager_id: int = 117526, event: int = None) -> dict:
    """
    Henter sanntidsstatistikk for gjeldende eller valgt Gameweek:
    - Live poengsum for startende 11
    - Spilte minutter, mål ⚽, målgivende 👟, clean sheet 🧤, bonus ⭐, gule/røde kort
    - Kapteinsmultiplikator (2x)
    - Ligasnitt for runden og sammenligning (+/- poeng)
    """
    static = get_bootstrap_static()
    current_gw, next_gw = get_current_and_next_gw(static)
    if event is None:
        event = current_gw

    picks_data = get_manager_picks(manager_id, event)
    live_data = get_live_gameweek(event)
    fixtures_data = get_fixtures_data()

    # Match-status per lag for valgt runde
    gw_fixtures = [f for f in fixtures_data if f.get("event") == event]
    team_fixture_status = {}
    for f in gw_fixtures:
        th = f.get("team_h")
        ta = f.get("team_a")
        f_min = f.get("minutes", 0)
        f_started = f.get("started", False)
        f_finished = f.get("finished", False) or (f_started and f_min >= 90)
        f_live = f_started and not f_finished
        stat = {
            "match_started": f_started,
            "match_finished": f_finished,
            "match_live": f_live,
            "match_minutes": f_min
        }
        team_fixture_status[th] = stat
        team_fixture_status[ta] = stat

    elements_map = {e["id"]: e for e in static["elements"]}
    teams_map = {t["id"]: t for t in static["teams"]}
    live_stats = {el["id"]: el["stats"] for el in live_data.get("elements", [])}

    event_info = next((e for e in static["events"] if e["id"] == event), {})
    avg_score = event_info.get("average_entry_score", 0)
    highest_score = event_info.get("highest_score", 0)

    picks = picks_data.get("picks", [])
    starters_live = []
    bench_live = []
    total_live_points = 0

    for p in picks:
        elem_id = p["element"]
        elem = elements_map.get(elem_id, {})
        team = teams_map.get(elem.get("team"), {})
        stats = live_stats.get(elem_id, {})
        
        pts_raw = stats.get("total_points", 0)
        mult = p.get("multiplier", 1)
        effective_pts = pts_raw * mult
        
        is_starter = p.get("position", 1) <= 11
        if is_starter:
            total_live_points += effective_pts

        photo_raw = elem.get("photo", "")
        photo_url, legacy_photo_url = get_player_photo_urls(photo_raw)
        team_code = team.get("code", 0)
        badge_url = f"https://resources.premierleague.com/premierleague/badges/70/t{team_code}.png" if team_code else ""
        club_meta = PL_CLUB_COLORS.get(team.get("short_name", ""), {"primary": "#37003c", "secondary": "#00ff87", "gradient": "linear-gradient(135deg, #37003c 0%, #00ff87 100%)", "text": "#FFFFFF"})

        t_id = elem.get("team")
        f_stat = team_fixture_status.get(t_id, {
            "match_started": stats.get("played", False),
            "match_finished": stats.get("minutes", 0) >= 90,
            "match_live": False,
            "match_minutes": stats.get("minutes", 0)
        })
        m_played = stats.get("played", False)
        m_mins = stats.get("minutes", 0)
        if m_played or m_mins > 0:
            m_started = True
            m_finished = f_stat.get("match_finished", False) or m_mins >= 90
            m_live = not m_finished
        else:
            m_started = f_stat.get("match_started", False)
            m_finished = f_stat.get("match_finished", False)
            m_live = f_stat.get("match_live", False)

        item = {
            "element_id": elem_id,
            "id": elem_id,
            "name": elem.get("web_name", ""),
            "full_name": f"{elem.get('first_name')} {elem.get('second_name')}",
            "position": {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}.get(elem.get("element_type"), "MID"),
            "team": team.get("short_name", ""),
            "team_short": team.get("short_name", ""),
            "team_name": team.get("name", team.get("short_name", "")),
            "cost": elem.get("now_cost", 0) / 10.0,
            "multiplier": mult,
            "is_captain": p.get("is_captain", False),
            "is_vice_captain": p.get("is_vice_captain", False),
            "is_starter": is_starter,
            "played": m_played,
            "minutes": m_mins,
            "match_started": m_started,
            "match_finished": m_finished,
            "match_live": m_live,
            "match_minutes": f_stat.get("match_minutes", 0),
            "goals": stats.get("goals_scored", 0),
            "assists": stats.get("assists", 0),
            "clean_sheets": stats.get("clean_sheets", 0),
            "bonus": stats.get("bonus", 0),
            "bps": stats.get("bps", 0),
            "yellow_cards": stats.get("yellow_cards", 0),
            "red_cards": stats.get("red_cards", 0),
            "raw_points": pts_raw,
            "effective_points": effective_pts,
            "photo_url": photo_url,
            "legacy_photo_url": legacy_photo_url,
            "badge_url": badge_url,
            "team_code": team_code,
            "club_gradient": club_meta["gradient"]
        }

        if is_starter:
            starters_live.append(item)
        else:
            bench_live.append(item)

    entry_history = picks_data.get("entry_history", {})
    event_transfers_cost = entry_history.get("event_transfers_cost", 0)
    net_live_points = total_live_points - event_transfers_cost

    return {
        "event": event,
        "starters": starters_live,
        "bench": bench_live,
        "total_live_points": total_live_points,
        "net_live_points": net_live_points,
        "event_transfers_cost": event_transfers_cost,
        "average_score": avg_score,
        "highest_score": highest_score,
        "vs_average": net_live_points - avg_score
    }

# ---------------------------------------------------------
# Optimal Starting XI & Captain Solver for Any 15-Man Squad
# ---------------------------------------------------------
def optimize_squad_lineup(squad_players: list[dict]) -> dict:
    """
    Finner matematisk optimal startellever (11 spillere) og reservebenk (4 spillere)
    for en gitt 15-manns tropp som maksimerer forventet poengsum (xP) i en gyldig FPL-formasjon.
    """
    gkps = sorted([p for p in squad_players if p["position"] in ["GKP", "G"]], key=lambda x: x.get("ep_next", 0), reverse=True)
    defs = sorted([p for p in squad_players if p["position"] in ["DEF", "D"]], key=lambda x: x.get("ep_next", 0), reverse=True)
    mids = sorted([p for p in squad_players if p["position"] in ["MID", "M"]], key=lambda x: x.get("ep_next", 0), reverse=True)
    fwds = sorted([p for p in squad_players if p["position"] in ["FWD", "F"]], key=lambda x: x.get("ep_next", 0), reverse=True)

    # Gyldige FPL-formasjoner: (D, M, F) der D in [3,5], M in [2,5], F in [1,3], sum = 10
    valid_formations = [
        (3, 4, 3),
        (3, 5, 2),
        (4, 4, 2),
        (4, 3, 3),
        (4, 5, 1),
        (5, 3, 2),
        (5, 4, 1),
        (5, 2, 3),
    ]

    best_total_xp = -1.0
    best_starters = []
    best_bench = []
    best_formation_str = "3-4-3"

    for d_count, m_count, f_count in valid_formations:
        if len(defs) < d_count or len(mids) < m_count or len(fwds) < f_count or len(gkps) < 1:
            continue
        
        cur_starters = [gkps[0]] + defs[:d_count] + mids[:m_count] + fwds[:f_count]
        cur_bench = [gkps[1]] if len(gkps) > 1 else []
        cur_bench += defs[d_count:] + mids[m_count:] + fwds[f_count:]
        cur_bench_outfield = sorted([p for p in cur_bench if p["position"] not in ["GKP", "G"]], key=lambda x: x.get("ep_next", 0), reverse=True)
        cur_bench_sorted = ([gkps[1]] if len(gkps) > 1 else []) + cur_bench_outfield

        cap_candidate = max(cur_starters, key=lambda x: x.get("ep_next", 0))
        tot_xp = sum(p.get("ep_next", 0) for p in cur_starters) + cap_candidate.get("ep_next", 0)

        if tot_xp > best_total_xp:
            best_total_xp = tot_xp
            best_starters = cur_starters
            best_bench = cur_bench_sorted
            best_formation_str = f"{d_count}-{m_count}-{f_count}"

    starters_sorted_by_xp = sorted(best_starters, key=lambda x: x.get("ep_next", 0), reverse=True)
    captain_id = starters_sorted_by_xp[0]["element_id"] if starters_sorted_by_xp else None
    vice_captain_id = starters_sorted_by_xp[1]["element_id"] if len(starters_sorted_by_xp) > 1 else None

    final_starters = []
    for p in best_starters:
        p_copy = dict(p)
        p_copy["is_starter"] = True
        p_copy["is_captain"] = (p_copy["element_id"] == captain_id)
        p_copy["is_vice_captain"] = (p_copy["element_id"] == vice_captain_id)
        final_starters.append(p_copy)

    final_bench = []
    for p in best_bench:
        p_copy = dict(p)
        p_copy["is_starter"] = False
        p_copy["is_captain"] = False
        p_copy["is_vice_captain"] = False
        final_bench.append(p_copy)

    return {
        "starters": final_starters,
        "bench": final_bench,
        "formation": best_formation_str,
        "captain": starters_sorted_by_xp[0] if starters_sorted_by_xp else None,
        "vice_captain": starters_sorted_by_xp[1] if len(starters_sorted_by_xp) > 1 else None,
        "total_starting_xp": round(best_total_xp, 1)
    }

# ---------------------------------------------------------
# Transfer Replacement Recommendations Engine
# ---------------------------------------------------------
def get_replacement_recommendations(
    sold_player: dict,
    max_budget: float,
    all_players_df: pd.DataFrame = None,
    exclude_ids: list[int] = None,
    squad_team_counts: dict = None
) -> pd.DataFrame:
    """
    Genererer anbefalte erstatningskjøp for en solgt spiller innenfor tilgjengelig budsjett.
    Beregner differanse i xP neste runde, sum xP over 3 runder, budsjetteffekt og kategoriserer valgene.
    """
    if all_players_df is None:
        all_players_df = get_all_players_database(horizon=5)

    pos = sold_player.get("position", "MID")
    sold_cost = sold_player.get("cost", 5.0)
    sold_ep_next = sold_player.get("ep_next", 3.0)
    sold_id = sold_player.get("element_id") or sold_player.get("id")

    if exclude_ids is None:
        exclude_ids = [sold_id]
    else:
        exclude_ids = list(exclude_ids) + [sold_id]

    candidates = all_players_df[
        (all_players_df["position"] == pos) &
        (all_players_df["cost"] <= max_budget + 0.01) &
        (~all_players_df["id"].isin(exclude_ids)) &
        (all_players_df["status"] != "u")
    ].copy()

    if squad_team_counts:
        sold_team = sold_player.get("team_short") or sold_player.get("team")
        invalid_teams = [t for t, cnt in squad_team_counts.items() if cnt >= 3 and t != sold_team]
        if invalid_teams:
            candidates = candidates[~candidates["team"].isin(invalid_teams)]

    if candidates.empty:
        return pd.DataFrame()

    candidates["xp_gain_next"] = (candidates["ep_next"] - sold_ep_next).round(1)
    candidates["budget_saved"] = (sold_cost - candidates["cost"]).round(1)
    candidates["xp_per_cost"] = (candidates["ep_next"] / candidates["cost"]).round(2)

    def assign_category(row):
        badges = []
        if row["ep_next"] >= candidates["ep_next"].quantile(0.85):
            badges.append("🌟 Topp xP")
        if row["fdr_3gw"] <= 2.5:
            badges.append("🗓️ Gunstig Terminliste")
        if row["budget_saved"] > 0 and row["xp_per_cost"] >= candidates["xp_per_cost"].quantile(0.70):
            badges.append("💎 Budsjett-kupp")
        if row["form"] >= 5.5:
            badges.append("🔥 Formsterk")
        if row["selected_by_percent"] < 10.0 and row["ep_next"] >= 4.0:
            badges.append("🎯 Differensial")
        return " | ".join(badges) if badges else "Solid Valg"

    candidates["category"] = candidates.apply(assign_category, axis=1)
    candidates = candidates.sort_values(by=["ep_next", "xp_3gw"], ascending=[False, False])
    return candidates

