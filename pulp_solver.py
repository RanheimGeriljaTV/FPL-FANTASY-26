"""
pulp_solver.py - Matematisk PuLP MILP-optimeringsmotor for Fantasy Premier League (FPL)
Løser optimal startellever, kapteinsvalg, prioritert reservebenk og 1-2 overganger med hit-evaluering (-4).
"""
import pulp
import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def _create_binary_var(prob, name: str):
    """Oppretter en binær Lp-variabel kompatibel på tvers av PuLP 2.x, 3.x og 4.x."""
    try:
        if hasattr(prob, "add_variable"):
            return prob.add_variable(name, cat="Binary")
    except Exception:
        pass
    try:
        return pulp.LpVariable(name, cat=pulp.LpBinary)
    except Exception:
        try:
            return pulp.LpVariable(name, cat="Binary")
        except Exception:
            return pulp.LpVariable(name, lowBound=0, upBound=1, cat="Integer")

def _solve_problem(prob):
    """Kjører solver med CBC eller standard tilgjengelig motor uten krasj."""
    try:
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
    except Exception:
        try:
            prob.solve()
        except Exception as e:
            logger.warning(f"PuLP solve-feil: {e}")

def _fallback_starting_xi(squad_players: list[dict]) -> dict:
    """
    Robust heuristisk formasjonsvelger hvis MILP-solveren er utilgjengelig.
    Garanterer gyldig FPL-oppstilling: 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD (totalt 11 spillere).
    """
    gks = sorted([p for p in squad_players if p.get("position") in ["GKP", "G"]], key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
    defs = sorted([p for p in squad_players if p.get("position") in ["DEF", "D"]], key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
    mids = sorted([p for p in squad_players if p.get("position") in ["MID", "M"]], key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
    fwds = sorted([p for p in squad_players if p.get("position") in ["FWD", "F"]], key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)

    # Minimumskrav
    starters = []
    if gks:
        starters.append(gks[0])
    starters.extend(defs[:3])
    starters.extend(mids[:2])
    starters.extend(fwds[:1])

    # Samle resterende utespillere
    remaining_outfield = defs[3:] + mids[2:] + fwds[1:]
    remaining_outfield_sorted = sorted(remaining_outfield, key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)

    # Fyll opp til 11 spillere med høyest xP innenfor FPL formasjonsregler
    for p in remaining_outfield_sorted:
        if len(starters) == 11:
            break
        pos = p.get("position")
        if pos in ["DEF", "D"] and len([x for x in starters if x.get("position") in ["DEF", "D"]]) < 5:
            starters.append(p)
        elif pos in ["MID", "M"] and len([x for x in starters if x.get("position") in ["MID", "M"]]) < 5:
            starters.append(p)
        elif pos in ["FWD", "F"] and len([x for x in starters if x.get("position") in ["FWD", "F"]]) < 3:
            starters.append(p)

    starter_ids = set(p.get("element_id") or p.get("id") for p in starters)
    bench_raw = [p for p in squad_players if (p.get("element_id") or p.get("id")) not in starter_ids]
    bench_gk = [p for p in bench_raw if p.get("position") in ["GKP", "G"]]
    bench_outfield = sorted([p for p in bench_raw if p.get("position") not in ["GKP", "G"]], key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
    bench = bench_gk + bench_outfield

    starters_sorted = sorted(starters, key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
    captain = starters_sorted[0] if starters_sorted else None
    vice_captain = starters_sorted[1] if len(starters_sorted) > 1 else None

    cap_id = captain.get("element_id") or captain.get("id") if captain else None
    vc_id = vice_captain.get("element_id") or vice_captain.get("id") if vice_captain else None

    for p in starters:
        p["is_starter"] = True
        pid = p.get("element_id") or p.get("id")
        p["is_captain"] = (pid == cap_id)
        p["is_vice_captain"] = (pid == vc_id)

    for p in bench:
        p["is_starter"] = False
        p["is_captain"] = False
        p["is_vice_captain"] = False

    n_def = len([p for p in starters if p.get("position") in ["DEF", "D"]])
    n_mid = len([p for p in starters if p.get("position") in ["MID", "M"]])
    n_fwd = len([p for p in starters if p.get("position") in ["FWD", "F"]])
    formation = f"{n_def}-{n_mid}-{n_fwd}"

    sum_starters_xp = sum(float(p.get("ep_next", 0.0)) for p in starters)
    cap_xp = float(captain.get("ep_next", 0.0)) if captain else 0.0
    total_xp = round(sum_starters_xp + cap_xp, 1)

    return {
        "starters": starters,
        "bench": bench,
        "formation": formation,
        "captain": captain,
        "vice_captain": vice_captain,
        "total_xp": total_xp,
        "raw_starters_xp": round(sum_starters_xp, 1)
    }

# ---------------------------------------------------------
# 1. Optimal Startellever & Benk (solve_optimal_starting_xi)
# ---------------------------------------------------------
def solve_optimal_starting_xi(squad_players: list[dict]) -> dict:
    """
    Løser Mixed-Integer Linear Programming (MILP) via PuLP for å finne optimal
    startellever (11 spillere) og reservebenk (4 spillere) som maksimerer forventede poeng (xP).
    
    Harde FPL-krav:
    - Nøyaktig 11 spillere i startoppstillingen.
    - Formasjonskrav: Nøyaktig 1 Keeper, 3–5 Forsvar, 2–5 Midtbane, 1–3 Angrep.
    - Kaptein (2x xP) og Visekaptein tildeles automatisk til de to spillerne med høyest xP.
    - Benken rangeres matematisk: Reservekeeper først, deretter utespillere i fallende xP-rekkefølge.
    """
    try:
        prob = pulp.LpProblem("FPL_Optimal_Starting_XI", pulp.LpMaximize)
        
        player_vars = {}
        for i, p in enumerate(squad_players):
            player_vars[i] = _create_binary_var(prob, f"starter_{i}")
        
        # 1. Nøyaktig 11 spillere i startoppstillingen
        prob += pulp.lpSum(player_vars[i] for i in range(len(squad_players))) == 11, "Total_Starters"
        
        # 2. Formasjonskrav
        gk_indices = [i for i, p in enumerate(squad_players) if p.get("position") in ["GKP", "G"]]
        def_indices = [i for i, p in enumerate(squad_players) if p.get("position") in ["DEF", "D"]]
        mid_indices = [i for i, p in enumerate(squad_players) if p.get("position") in ["MID", "M"]]
        fwd_indices = [i for i, p in enumerate(squad_players) if p.get("position") in ["FWD", "F"]]
        
        prob += pulp.lpSum(player_vars[i] for i in gk_indices) == 1, "Exactly_1_GK"
        prob += pulp.lpSum(player_vars[i] for i in def_indices) >= 3, "Min_3_DEF"
        prob += pulp.lpSum(player_vars[i] for i in def_indices) <= 5, "Max_5_DEF"
        prob += pulp.lpSum(player_vars[i] for i in mid_indices) >= 2, "Min_2_MID"
        prob += pulp.lpSum(player_vars[i] for i in mid_indices) <= 5, "Max_5_MID"
        prob += pulp.lpSum(player_vars[i] for i in fwd_indices) >= 1, "Min_1_FWD"
        prob += pulp.lpSum(player_vars[i] for i in fwd_indices) <= 3, "Max_3_FWD"
        
        # 3. Objektiv: Maksimer sum xP
        prob += pulp.lpSum(player_vars[i] * float(squad_players[i].get("ep_next", 0.0)) for i in range(len(squad_players))), "Maximize_xP"
        
        _solve_problem(prob)
        
        starter_indices = [i for i in range(len(squad_players)) if player_vars[i].varValue and player_vars[i].varValue > 0.5]
        if len(starter_indices) != 11:
            return _fallback_starting_xi(squad_players)

        bench_indices = [i for i in range(len(squad_players)) if i not in starter_indices]
        
        starters = [dict(squad_players[i]) for i in starter_indices]
        bench_raw = [dict(squad_players[i]) for i in bench_indices]
        
        # Sorter benk: Reservekeeper først, deretter utespillere i fallende xP-rekkefølge
        bench_gk = [p for p in bench_raw if p.get("position") in ["GKP", "G"]]
        bench_outfield = sorted([p for p in bench_raw if p.get("position") not in ["GKP", "G"]], 
                                key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
        bench = bench_gk + bench_outfield
        
        # Kaptein og Visekaptein
        starters_sorted_by_xp = sorted(starters, key=lambda x: float(x.get("ep_next", 0.0)), reverse=True)
        captain = starters_sorted_by_xp[0] if starters_sorted_by_xp else None
        vice_captain = starters_sorted_by_xp[1] if len(starters_sorted_by_xp) > 1 else None
        
        cap_id = captain.get("element_id") or captain.get("id") if captain else None
        vc_id = vice_captain.get("element_id") or vice_captain.get("id") if vice_captain else None
        
        for p in starters:
            p["is_starter"] = True
            pid = p.get("element_id") or p.get("id")
            p["is_captain"] = (pid == cap_id)
            p["is_vice_captain"] = (pid == vc_id)
            
        for p in bench:
            p["is_starter"] = False
            p["is_captain"] = False
            p["is_vice_captain"] = False
            
        n_def = len([p for p in starters if p.get("position") in ["DEF", "D"]])
        n_mid = len([p for p in starters if p.get("position") in ["MID", "M"]])
        n_fwd = len([p for p in starters if p.get("position") in ["FWD", "F"]])
        formation = f"{n_def}-{n_mid}-{n_fwd}"
        
        sum_starters_xp = sum(float(p.get("ep_next", 0.0)) for p in starters)
        cap_xp = float(captain.get("ep_next", 0.0)) if captain else 0.0
        total_xp = round(sum_starters_xp + cap_xp, 1)
        
        return {
            "starters": starters,
            "bench": bench,
            "formation": formation,
            "captain": captain,
            "vice_captain": vice_captain,
            "total_xp": total_xp,
            "raw_starters_xp": round(sum_starters_xp, 1)
        }
    except Exception as e:
        logger.warning(f"Feil i solve_optimal_starting_xi, bruker fallback: {e}")
        return _fallback_starting_xi(squad_players)

# ---------------------------------------------------------
# 2. Transfer Optimizer & Hit-Evaluator (solve_transfers_pulp)
# ---------------------------------------------------------
def solve_transfers_pulp(
    squad_players: list[dict],
    bank: float,
    all_players_df: pd.DataFrame,
    max_transfers: int = 1,
    horizon: int = 3,
    allow_hits: bool = False
) -> dict:
    """
    Løser optimal 1-overgang (gratisbytte) og 2-overganger (-4 hit) via PuLP MILP over en rullerende horisont.
    
    - Respekterer budsjett: Salgssum + bank >= Kjøpesum.
    - Respekterer kvoter: Maks 3 spillere per Premier League-klubb.
    - Hit-evaluator: Flagger '🟢 ANBEFALT HIT' hvis netto forventet gevinst over horisonten overstiger 4 poeng.
    """
    xp_col = f"xp_{horizon}gw" if f"xp_{horizon}gw" in all_players_df.columns else "ep_next"
    
    squad_ids = set(p.get("element_id") or p.get("id") for p in squad_players)
    selling_budget = sum(float(p.get("cost", 5.0)) for p in squad_players) + bank
    
    baseline_opt = solve_optimal_starting_xi(squad_players)
    baseline_xp = baseline_opt["total_xp"]
    
    # Begrens kandidatpoolen til relevante spillere for lynrask løsning (< 2 sekunder)
    top_candidates_per_pos = []
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        sub = all_players_df[
            (all_players_df["position"] == pos) & 
            (all_players_df["status"] == "a")
        ].sort_values(by=xp_col, ascending=False).head(20)
        top_candidates_per_pos.append(sub)
    
    pool_df = pd.concat(top_candidates_per_pos).drop_duplicates(subset=["id"]).reset_index(drop=True)
    current_in_db = all_players_df[all_players_df["id"].isin(squad_ids)]
    pool_df = pd.concat([pool_df, current_in_db]).drop_duplicates(subset=["id"]).reset_index(drop=True)
    
    eval_transfers = [1]
    if allow_hits or max_transfers >= 2:
        eval_transfers.append(2)
        
    best_overall_transfer = None
    best_overall_net_gain = -999.0
    all_evaluated = []
    
    for T in eval_transfers:
        try:
            prob = pulp.LpProblem(f"FPL_Transfers_T{T}", pulp.LpMaximize)
            n = len(pool_df)
            x = {i: _create_binary_var(prob, f"x_{i}") for i in range(n)}
            
            # 1. Nøyaktig 15 spillere
            prob += pulp.lpSum(x[i] for i in range(n)) == 15, "Total_Squad_15"
            
            # 2. Posisjoner: 2 GKP, 5 DEF, 5 MID, 3 FWD
            prob += pulp.lpSum(x[i] for i in range(n) if pool_df.iloc[i]["position"] == "GKP") == 2, "2_GKP"
            prob += pulp.lpSum(x[i] for i in range(n) if pool_df.iloc[i]["position"] == "DEF") == 5, "5_DEF"
            prob += pulp.lpSum(x[i] for i in range(n) if pool_df.iloc[i]["position"] == "MID") == 5, "5_MID"
            prob += pulp.lpSum(x[i] for i in range(n) if pool_df.iloc[i]["position"] == "FWD") == 3, "3_FWD"
            
            # 3. Budsjett
            prob += pulp.lpSum(x[i] * float(pool_df.iloc[i]["cost"]) for i in range(n)) <= selling_budget + 0.01, "Budget"
            
            # 4. Klubbkvote (maks 3 spillere per lag)
            for team_name in pool_df["team"].unique():
                prob += pulp.lpSum(x[i] for i in range(n) if pool_df.iloc[i]["team"] == team_name) <= 3, f"Club_Quota_{team_name}"
                
            # 5. Antall overganger = T (nøyaktig 15 - T beholdes)
            retained_indices = [i for i in range(n) if pool_df.iloc[i]["id"] in squad_ids]
            prob += pulp.lpSum(x[i] for i in retained_indices) == 15 - T, f"Exact_{T}_Transfers"
            
            # 6. Objektiv: Maksimer sum horisont-xP
            prob += pulp.lpSum(x[i] * float(pool_df.iloc[i][xp_col]) for i in range(n)), "Objective_xP"
            
            _solve_problem(prob)
            
            chosen_indices = [i for i in range(n) if x[i].varValue and x[i].varValue > 0.5]
            if len(chosen_indices) == 15:
                chosen_players = pool_df.iloc[chosen_indices].to_dict(orient="records")
                
                chosen_ids = set(p["id"] for p in chosen_players)
                transfers_out = [p for p in squad_players if (p.get("element_id") or p.get("id")) not in chosen_ids]
                transfers_in = [p for p in chosen_players if p["id"] not in squad_ids]
                
                squad_formatted = []
                for p in chosen_players:
                    squad_formatted.append({
                        "element_id": p["id"],
                        "id": p["id"],
                        "name": p["name"],
                        "full_name": p.get("full_name", p["name"]),
                        "position": p["position"],
                        "team": p["team"],
                        "team_short": p["team"],
                        "cost": p["cost"],
                        "ep_next": p.get("ep_next", 0.0),
                        "xp_3gw": p.get("xp_3gw", 0.0),
                        "fixture": p.get("next_fixture", ""),
                        "is_blank": p.get("is_blank_next", False),
                        "is_double": p.get("is_double_next", False),
                        "chance_of_playing": p.get("chance_of_playing", 100),
                        "status": p.get("status", "a"),
                        "photo_url": p.get("photo_url", ""),
                        "badge_url": p.get("badge_url", ""),
                        "club_gradient": p.get("club_gradient", "")
                    })
                    
                new_opt = solve_optimal_starting_xi(squad_formatted)
                new_xp_next = new_opt["total_xp"]
                
                hit_penalty = 4 if T == 2 else 0
                gross_gain = round(new_xp_next - baseline_xp, 1)
                net_gain = round(gross_gain - hit_penalty, 1)
                
                squad_xp_map = {row["id"]: float(row.get(xp_col, row.get("ep_next", 0.0))) for _, row in all_players_df.iterrows()}
                new_horizon_xp = sum(float(p.get(xp_col, squad_xp_map.get(p.get("id"), 0.0))) for p in chosen_players)
                old_horizon_xp = sum(float(p.get(xp_col, squad_xp_map.get(p.get("element_id") or p.get("id"), p.get("ep_next", 0.0)))) for p in squad_players)
                horizon_gross_gain = round(new_horizon_xp - old_horizon_xp, 1)
                horizon_net_gain = round(horizon_gross_gain - hit_penalty, 1)
                
                hit_recommended = (T == 2) and (horizon_net_gain >= 4.0 or net_gain >= 1.0)
                
                plan_entry = {
                    "num_transfers": T,
                    "transfers_out": transfers_out,
                    "transfers_in": transfers_in,
                    "hit_penalty": hit_penalty,
                    "gross_gain": gross_gain,
                    "net_gain": net_gain,
                    "horizon_gross_gain": horizon_gross_gain,
                    "horizon_net_gain": horizon_net_gain,
                    "hit_recommended": hit_recommended,
                    "new_squad": squad_formatted,
                    "new_optimal_xi": new_opt,
                    "remaining_bank": round(selling_budget - sum(p["cost"] for p in chosen_players), 1)
                }
                all_evaluated.append(plan_entry)
                
                if net_gain > best_overall_net_gain:
                    best_overall_net_gain = net_gain
                    best_overall_transfer = plan_entry
        except Exception as e:
            logger.warning(f"Feil ved evaluering av overganger T={T}: {e}")
                
    sell_candidates = sorted(squad_players, key=lambda p: (float(p.get("ep_next", 0.0)) / max(0.1, float(p.get("cost", 5.0)))), reverse=False)[:5]
    buy_candidates = all_players_df[
        (~all_players_df["id"].isin(squad_ids)) &
        (all_players_df["status"] == "a")
    ].sort_values(by=xp_col, ascending=False).head(5).to_dict(orient="records")
    
    return {
        "best_plan": best_overall_transfer,
        "all_plans": all_evaluated,
        "baseline_xp": baseline_xp,
        "top_sells": sell_candidates,
        "top_buys": buy_candidates
    }
