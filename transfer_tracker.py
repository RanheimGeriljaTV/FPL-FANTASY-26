"""
transfer_tracker.py
Håndterer lokal persistens og automatisk poengevaluering av gjennomførte overganger (Track Record).
Følger opp faktiske poeng etter runden (INN - UT - Hit) og beregner suksessrate.
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
import fpl_api

TRACKER_FILE = Path(__file__).parent / "transfer_tracker.json"
SIMULATED_TRANSFERS_FILE = Path(__file__).parent / "simulated_transfers.json"

def sanitize_for_json(obj: Any) -> Any:
    """Konverterer numpy/pandas datatyper til standard Python-typer for trygg JSON-serialisering."""
    if isinstance(obj, dict):
        return {str(k): sanitize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_for_json(v) for v in obj]
    elif hasattr(obj, "item"):
        try:
            return obj.item()
        except Exception:
            return str(obj)
    elif isinstance(obj, (int, float, str, bool)) or obj is None:
        return obj
    return str(obj)

def load_simulated_transfers(manager_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Laster lagrede simulerte bytter fra disk (støtter per-manager lagring)."""
    try:
        if SIMULATED_TRANSFERS_FILE.exists():
            with open(SIMULATED_TRANSFERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    key = str(manager_id) if manager_id else "117526"
                    return data.get(key, [])
                elif isinstance(data, list):
                    return data
    except Exception:
        pass
    return []

def save_simulated_transfers(transfers: List[Dict[str, Any]], manager_id: Optional[int] = None) -> None:
    """Lagrer simulerte bytter til disk per manager slik at de overlever omstart av appen/bat-filen."""
    try:
        sanitized = sanitize_for_json(transfers)
        existing_data = {}
        if SIMULATED_TRANSFERS_FILE.exists():
            try:
                with open(SIMULATED_TRANSFERS_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    if isinstance(raw, dict):
                        existing_data = raw
                    elif isinstance(raw, list):
                        existing_data = {"117526": raw}
            except Exception:
                existing_data = {}
        
        key = str(manager_id) if manager_id else "117526"
        existing_data[key] = sanitized
        with open(SIMULATED_TRANSFERS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def clear_simulated_transfers(manager_id: Optional[int] = None) -> None:
    """Tømmer lagrede simulerte bytter fra disk for en manager."""
    try:
        if SIMULATED_TRANSFERS_FILE.exists():
            if manager_id:
                try:
                    with open(SIMULATED_TRANSFERS_FILE, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, dict) and str(manager_id) in data:
                        del data[str(manager_id)]
                        with open(SIMULATED_TRANSFERS_FILE, "w", encoding="utf-8") as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                        return
                except Exception:
                    pass
            SIMULATED_TRANSFERS_FILE.unlink(missing_ok=True)
    except Exception:
        pass

def get_active_simulated_transfers(base_squad: List[Dict[str, Any]], all_players_df, next_gw: int, manager_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Laster og vedlikeholder aktive simulerte bytter for visning på banen og i optimalisatoren.
    - Sjekker om lagrede simulerte bytter finnes på disk for gitt manager.
    - Hvis spilleren allerede er solgt offisielt i FPL (out_id ikke lenger i base_squad), renses byttet automatisk.
    - Dersom filen er tom, sjekkes transfer_tracker.json for eventuelle uavsluttede bytter for neste runde (f.eks. gjort via byttekalkulatoren).
    """
    base_ids = {p.get("element_id") or p.get("id") for p in base_squad}
    saved_sims = load_simulated_transfers(manager_id=manager_id)
    
    if saved_sims:
        valid_sims = []
        for tr in saved_sims:
            out_p = tr.get("out", {})
            out_id = out_p.get("element_id") or out_p.get("id")
            if out_id in base_ids:
                valid_sims.append(tr)
        if len(valid_sims) != len(saved_sims):
            save_simulated_transfers(valid_sims, manager_id=manager_id)
        if valid_sims:
            return valid_sims

    # Fallback: Sjekk om det finnes uavsluttede bytter i transfer_tracker.json for neste GW
    tracked = load_tracked_transfers(manager_id=manager_id)
    reconstructed = []
    for t in tracked:
        if t.get("gw") == next_gw:
            out_id = t.get("out_id")
            in_id = t.get("in_id")
            if out_id in base_ids:
                out_p = next((p for p in base_squad if (p.get("element_id") == out_id or p.get("id") == out_id)), None)
                in_rows = all_players_df[all_players_df["id"] == in_id]
                if out_p and not in_rows.empty:
                    in_p = in_rows.iloc[0].to_dict()
                    reconstructed.append({"out": out_p, "in": in_p})
    
    if reconstructed:
        save_simulated_transfers(reconstructed, manager_id=manager_id)
        return reconstructed

    return []

# ==============================================================================
# LAGRING & PERSISTENS
# ==============================================================================
def load_tracked_transfers(manager_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Laster lagrede overganger fra transfer_tracker.json (støtter filtrering på manager_id)."""
    try:
        if TRACKER_FILE.exists():
            with open(TRACKER_FILE, "r", encoding="utf-8") as f:
                all_tx = json.load(f)
                if manager_id:
                    return [t for t in all_tx if t.get("manager_id") in (None, int(manager_id))]
                return all_tx
    except Exception:
        pass
    return []

def save_tracked_transfers(transfers: List[Dict[str, Any]]) -> None:
    """Lagrer overganger til transfer_tracker.json."""
    try:
        with open(TRACKER_FILE, "w", encoding="utf-8") as f:
            json.dump(transfers, f, indent=2, ensure_ascii=False)
    except Exception:
        pass

def add_tracked_transfer(gw: int, out_id: int, out_name: str, out_team: str,
                         in_id: int, in_name: str, in_team: str,
                         exp_gain: float, hit_cost: int = 0,
                         manager_id: Optional[int] = None) -> bool:
    """
    Kalles når brukeren gjennomfører eller bekrefter et bytte med optimizeren.
    Returnerer True dersom byttet ble lagt til, False dersom det allerede var registrert.
    """
    transfers = load_tracked_transfers()
    rec = {
        "id": f"tx_{int(time.time())}_{out_id}_{in_id}",
        "gw": int(gw),
        "date": datetime.now().strftime("%d.%m.%Y"),
        "manager_id": int(manager_id) if manager_id else 117526,
        "out_id": int(out_id),
        "out_name": str(out_name),
        "out_team": str(out_team),
        "in_id": int(in_id),
        "in_name": str(in_name),
        "in_team": str(in_team),
        "exp_gain": round(float(exp_gain), 2),
        "hit_cost": int(hit_cost)
    }
    
    # Unngå duplikate registreringer for samme runde og spillerpar
    if not any(t.get("gw") == rec["gw"] and t.get("out_id") == rec["out_id"] and t.get("in_id") == rec["in_id"] for t in transfers):
        transfers.append(rec)
        save_tracked_transfers(transfers)
        return True
    return False

def delete_tracked_transfer(tx_id: str) -> None:
    """Fjerner en overgang fra loggen og rydder også i aktive simulerte bytter dersom den er aktiv."""
    transfers = load_tracked_transfers()
    target = next((t for t in transfers if t.get("id") == tx_id), None)
    transfers = [t for t in transfers if t.get("id") != tx_id]
    save_tracked_transfers(transfers)

    if target:
        saved_sims = load_simulated_transfers()
        if saved_sims:
            out_id = target.get("out_id")
            in_id = target.get("in_id")
            updated_sims = [
                tr for tr in saved_sims
                if not (
                    (tr.get("out", {}).get("element_id") == out_id or tr.get("out", {}).get("id") == out_id) and
                    (tr.get("in", {}).get("element_id") == in_id or tr.get("in", {}).get("id") == in_id)
                )
            ]
            save_simulated_transfers(updated_sims)

def get_player_transfer_history(player_id: int, manager_id: Optional[int] = None) -> Dict[str, List[int]]:
    """
    Returnerer hvilke runder en spiller ble kjøpt (grønn) eller solgt (rød),
    både fra offisielle API-overganger og den lokale overgangsloggen.
    """
    bought_gws = set()
    sold_gws = set()

    # 1. Offisielle overganger fra API
    if manager_id and manager_id > 0:
        try:
            api_txs = fpl_api.get_manager_transfers(manager_id) or []
            for tx in api_txs:
                gw = tx.get("event")
                if gw:
                    if tx.get("element_in") == player_id:
                        bought_gws.add(int(gw))
                    if tx.get("element_out") == player_id:
                        sold_gws.add(int(gw))
        except Exception:
            pass

    # 2. Lokale overganger fra overgangslogg
    local_txs = load_tracked_transfers()
    for tx in local_txs:
        gw = tx.get("gw")
        if gw:
            if tx.get("in_id") == player_id:
                bought_gws.add(int(gw))
            if tx.get("out_id") == player_id:
                sold_gws.add(int(gw))

    return {
        "bought": sorted(list(bought_gws)),
        "sold": sorted(list(sold_gws))
    }

# ==============================================================================
# AUTOMATISK POENG-EVALUERING ETTER RUNDEN
# ==============================================================================
def evaluate_transfer_record(rec: Dict[str, Any], static_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Evaluerer et lagret bytte mot faktiske oppnådde FPL-poeng.
    Formel: Faktisk gevinst = INN - UT - Hit
    """
    if static_data is None:
        static_data = fpl_api.get_bootstrap_static()

    events = static_data.get("events", [])
    gw = int(rec.get("gw", 1))
    ev_obj = next((e for e in events if e.get("id") == gw), None)
    is_finished = (ev_obj.get("finished", False) or ev_obj.get("finished_provisional", False)) if ev_obj else False

    # Hent element-summary (full kamphistorikk) for begge spillere
    in_sum = fpl_api.get_element_summary(rec["in_id"]) or {}
    out_sum = fpl_api.get_element_summary(rec["out_id"]) or {}

    in_matches = [h for h in in_sum.get("history", []) if h.get("round") == gw]
    out_matches = [h for h in out_sum.get("history", []) if h.get("round") == gw]

    # Støtt dobbel gameweek (summerer poeng dersom spilleren hadde 2 kamper)
    in_pts = sum(m.get("total_points", 0) for m in in_matches) if in_matches else (0 if is_finished else None)
    out_pts = sum(m.get("total_points", 0) for m in out_matches) if out_matches else (0 if is_finished else None)

    hit = rec.get("hit_cost", 0)
    res = dict(rec)
    res["in_pts"] = in_pts
    res["out_pts"] = out_pts

    if in_pts is not None and out_pts is not None:
        actual_gain = in_pts - out_pts - hit
        res["actual_gain"] = actual_gain
        res["played"] = True
        if actual_gain > 0:
            res["status"] = f"✅ Suksess (+{actual_gain} pts)"
        elif actual_gain == 0:
            res["status"] = "⚖️ Uavgjort (0 pts)"
        else:
            res["status"] = f"❌ Tap ({actual_gain} pts)"
    else:
        res["actual_gain"] = None
        res["played"] = False
        res["status"] = f"⏳ Venter på GW {gw}"

    return res

def get_tracker_scorecard(evaluated_records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Beregner nøkkeltall og suksessrate for alle evaluerte overganger."""
    finished = [t for t in evaluated_records if t.get("played")]
    total_net_gain = sum(t["actual_gain"] for t in finished) if finished else 0
    wins = sum(1 for t in finished if t["actual_gain"] > 0)
    draws = sum(1 for t in finished if t["actual_gain"] == 0)
    losses = sum(1 for t in finished if t["actual_gain"] < 0)
    win_rate = (wins / len(finished) * 100) if finished else 0.0
    avg_gain = (total_net_gain / len(finished)) if finished else 0.0
    avg_exp = (sum(t.get("exp_gain", 0.0) for t in finished) / len(finished)) if finished else 0.0

    return {
        "total_logged": len(evaluated_records),
        "finished_count": len(finished),
        "total_net_gain": total_net_gain,
        "avg_gain": avg_gain,
        "wins": wins,
        "draws": draws,
        "losses": losses,
        "win_rate": win_rate,
        "avg_exp": avg_exp,
        "finished": finished
    }
