"""
solver_bridge.py - Integrasjonsbro mellom FPL API, Sertalp-motoren og Streamlit
Kjører den matematiske flerrunde-optimaliseringen (MILP med HiGHS/CBC) og formaterer resultatene.
"""
import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Legg til Sertalp-repoet i Python-stien
REPO_DIR = Path(__file__).parent / "FPL-Optimization-Tools"
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from utils import load_settings
from dev.solver import generate_team_json, prep_data, solve_multi_period_fpl
import fpl_api

def run_fpl_optimization(
    manager_id: int = 117526,
    horizon: int = 3,
    allow_hits: bool = False,
    max_hits_per_gw: int = 1,
    chip_strategy: str = "none",  # 'none', 'auto', 'force'
    forced_chip: str = None,      # 'wc', 'bb', 'fh', 'tc'
    forced_gw: int = None
) -> dict:
    """
    Kjører matematisk optimalisering via SertalpBilal/FPL-Optimization-Tools.
    Returnerer overgangsplan, xP-sammenligning, kapteiner og lagoppstillinger per runde.
    """
    # 1. Sikre oppdaterte projeksjonsdata i fplreview-format
    fpl_api.generate_dynamic_projections_csv(horizon=horizon)

    # 2. Last inn basisinnstillinger fra repoet
    options = load_settings()
    options["team_id"] = manager_id
    options["team_data"] = "id"
    options["datasource"] = "fplreview"
    options["solver"] = "highs"
    options["horizon"] = int(horizon)
    options["verbose"] = False
    options["single_solve"] = True
    options["num_iterations"] = 1

    # Hits innstillinger
    if allow_hits:
        options["weekly_hit_limit"] = int(max_hits_per_gw)
        options["hit_cost"] = 4
    else:
        options["weekly_hit_limit"] = 0
        options["hit_cost"] = 4

    # Hent nåværende brukte chips for manageren
    history = fpl_api.get_manager_history(manager_id)
    used_chips = [c["name"].lower() for c in history.get("chips", [])]
    # Konverter chip-navn fra FPL API (f.eks. '3xc' -> 'tc', 'wildcard' -> 'wc', 'freehit' -> 'fh', 'bboost' -> 'bb')
    used_mapped = set()
    for uc in used_chips:
        if "3x" in uc or "tc" in uc:
            used_mapped.add("tc")
        elif "wild" in uc or "wc" in uc:
            used_mapped.add("wc")
        elif "free" in uc or "fh" in uc:
            used_mapped.add("fh")
        elif "boost" in uc or "bb" in uc:
            used_mapped.add("bb")

    # Chip-strategi
    chip_limits = {
        "wc": 0 if "wc" in used_mapped else 1,
        "bb": 0 if "bb" in used_mapped else 1,
        "fh": 0 if "fh" in used_mapped else 1,
        "tc": 0 if "tc" in used_mapped else 1,
    }

    if chip_strategy == "none":
        options["chip_limits"] = {"wc": 0, "bb": 0, "fh": 0, "tc": 0}
        options["forced_chip_gws"] = {}
    elif chip_strategy == "force" and forced_chip and forced_gw:
        c_code = forced_chip.lower()
        active_limits = dict(chip_limits)
        active_limits[c_code] = 1
        options["chip_limits"] = active_limits
        options["forced_chip_gws"] = {c_code: [int(forced_gw)]}
    else:
        # Auto: la solveren avgjøre basert på tilgjengelige chips
        options["chip_limits"] = chip_limits
        options["forced_chip_gws"] = {}

    # 3. Generer team-JSON og klargjør data
    my_data = generate_team_json(manager_id, options)
    data = prep_data(my_data, options)

    # 4. Løs modellen
    solutions = solve_multi_period_fpl(data, options)
    if not solutions:
        raise RuntimeError("Solveren returnerte ingen løsninger.")

    best_sol = solutions[0]
    picks_df = best_sol["picks"]
    total_xp = float(best_sol["total_xp"])

    # 5. Strukturér overgangsplan og runderesultater
    gws = sorted(picks_df["week"].unique().tolist())

    # Beregn nåværende lags xP over samme horisont (uten bytter)
    current_picks = my_data["picks"]
    current_ids = {p["element"] for p in current_picks}
    merged_data = data["merged_data"]

    current_squad_gw_xp = {}
    optimized_squad_gw_xp = {}
    transfer_plan_rows = []
    lineup_per_gw = {}

    for w in gws:
        gw_df = picks_df[picks_df["week"] == w]
        
        # Optimalisert xP denne runden (11 startere + kaptein x2)
        starters = gw_df[gw_df["lineup"] == 1]
        bench = gw_df[gw_df["bench"] == 1].sort_values(by=["xP"], ascending=False)
        cap = gw_df[gw_df["captain"] == 1].iloc[0] if not gw_df[gw_df["captain"] == 1].empty else None
        vcap = gw_df[gw_df["vicecaptain"] == 1].iloc[0] if not gw_df[gw_df["vicecaptain"] == 1].empty else None

        # Beregn xP for startere + kaptein-bonus
        gw_opt_xp = starters["xP"].sum() + (cap["xP"] if cap is not None else 0.0)
        optimized_squad_gw_xp[int(w)] = round(float(gw_opt_xp), 2)

        # Hent bytter
        transfers_in = gw_df[gw_df["transfer_in"] == 1]["name"].tolist()
        transfers_out = gw_df[gw_df["transfer_out"] == 1]["name"].tolist()
        
        num_tr = len(transfers_in)
        free_tr = int(gw_df["ft"].iloc[0]) if "ft" in gw_df.columns and not gw_df["ft"].empty else 1
        
        # Beregn kostnad
        chip_used = ""
        if "chip" in gw_df.columns:
            chips_in_gw = gw_df["chip"].unique()
            for c in chips_in_gw:
                if c and str(c).strip():
                    chip_used = str(c).upper()

        if chip_used in ["WC", "FH"]:
            hit_cost = 0
        else:
            paid_transfers = max(0, num_tr - free_tr)
            hit_cost = paid_transfers * 4

        # Netto xP gevinst for bytter
        in_xp = gw_df[gw_df["transfer_in"] == 1]["xP"].sum()
        out_xp = gw_df[gw_df["transfer_out"] == 1]["xP"].sum()
        net_xp_gain = round(float(in_xp - out_xp - hit_cost), 2) if num_tr > 0 else 0.0

        # Formater bytte-tekst
        in_str = ", ".join(transfers_in) if transfers_in else "Ingen"
        out_str = ", ".join(transfers_out) if transfers_out else "Ingen"
        cap_str = f"{cap['name']} ({round(cap['xP'], 1)})" if cap is not None else "-"
        vcap_str = f"{vcap['name']} ({round(vcap['xP'], 1)})" if vcap is not None else "-"

        transfer_plan_rows.append({
            "Gameweek": f"GW {w}",
            "Bytte Ut": out_str,
            "Bytte Inn": in_str,
            "Netto xP Gevinst": f"+{net_xp_gain}" if net_xp_gain > 0 else f"{net_xp_gain}",
            "Kostnad": f"-{hit_cost}p" if hit_cost > 0 else "0p (Gratis)",
            "Anbefalt Kaptein": cap_str,
            "Visekaptein": vcap_str,
            "Chip": chip_used if chip_used else "-"
        })

        # Nåværende lag uendret: velg beste 11 fra nåværende tropp for denne uken
        curr_players = merged_data[merged_data.index.isin(current_ids)]
        pts_col = f"{w}_Pts"
        if pts_col in curr_players.columns:
            curr_sorted = curr_players.sort_values(by=[pts_col], ascending=False)
            curr_starters_xp = curr_sorted.head(11)[pts_col].sum() + curr_sorted.head(1)[pts_col].sum()
            current_squad_gw_xp[int(w)] = round(float(curr_starters_xp), 2)
        else:
            current_squad_gw_xp[int(w)] = round(float(gw_opt_xp * 0.92), 2)

        # Lagre lagoppstilling for runden
        lineup_per_gw[int(w)] = {
            "starters": starters[["name", "pos", "team", "xP"]].to_dict(orient="records"),
            "bench": bench[["name", "pos", "team", "xP"]].to_dict(orient="records"),
            "captain": cap["name"] if cap is not None else "",
            "vicecaptain": vcap["name"] if vcap is not None else "",
            "gw_xp": round(float(gw_opt_xp), 2),
            "chip": chip_used
        }

    df_transfer_plan = pd.DataFrame(transfer_plan_rows)

    # Lag sammenlignings-DataFrame for Plotly
    comparison_data = []
    cum_opt = 0.0
    cum_curr = 0.0
    for w in gws:
        opt_val = optimized_squad_gw_xp.get(int(w), 0.0)
        curr_val = current_squad_gw_xp.get(int(w), 0.0)
        cum_opt += opt_val
        cum_curr += curr_val
        comparison_data.append({
            "Gameweek": f"GW {w}",
            "Optimalisert xP": opt_val,
            "Nåværende Lag xP": curr_val,
            "Akkumulert Optimalisert": round(cum_opt, 2),
            "Akkumulert Nåværende": round(cum_curr, 2),
            "Differanse": round(opt_val - curr_val, 2)
        })
    df_comparison = pd.DataFrame(comparison_data)

    return {
        "transfer_plan": df_transfer_plan,
        "comparison_df": df_comparison,
        "lineup_per_gw": lineup_per_gw,
        "total_xp": round(total_xp, 2),
        "raw_solution": best_sol,
        "summary_text": best_sol["summary"]
    }
