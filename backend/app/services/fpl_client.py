import requests
from typing import Dict, List, Any

FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# Updated for the 2026/27 Premier League Season
DEFAULT_BASELINES = {
    "Man City": {"att": 2.25, "def": 1.95},
    "Arsenal": {"att": 2.15, "def": 1.95},
    "Liverpool": {"att": 2.10, "def": 1.85},
    "Chelsea": {"att": 1.80, "def": 1.65},
    "Spurs": {"att": 1.85, "def": 1.55},
    "Newcastle": {"att": 1.75, "def": 1.65},
    "Man Utd": {"att": 1.75, "def": 1.60},
    "Aston Villa": {"att": 1.75, "def": 1.55},
    "Brighton": {"att": 1.60, "def": 1.45},
    "Fulham": {"att": 1.40, "def": 1.35},
    "Brentford": {"att": 1.45, "def": 1.30},
    "Crystal Palace": {"att": 1.35, "def": 1.35},
    "Bournemouth": {"att": 1.35, "def": 1.25},
    "Everton": {"att": 1.25, "def": 1.40},
    "Nott'm Forest": {"att": 1.25, "def": 1.25},
    "Leeds": {"att": 1.20, "def": 1.15},
    "Sunderland": {"att": 1.15, "def": 1.10},
    "Ipswich Town": {"att": 1.15, "def": 1.10},
    "Coventry City": {"att": 1.10, "def": 1.05},
    "Hull City": {"att": 1.05, "def": 1.00},
}

def fetch_pl_ratings() -> Dict[str, Dict[str, float]]:
    """Calculates relative attack/defense multipliers safely."""
    data = fetch_fpl_bootstrap()
    teams_raw = data.get("teams", [])
    
    if not teams_raw:
        return DEFAULT_BASELINES

    # PRESEASON CHECK: If max == min, FPL has flattened the stats. Use baselines.
    att_strengths = [t.get("strength_attack_home", 1000) for t in teams_raw]
    if not att_strengths or max(att_strengths) == min(att_strengths):
        print("[Info] FPL strengths are flat (preseason). Using dynamic baselines.")
        return DEFAULT_BASELINES

    raw_scores = {}
    total_att = 0.0
    total_def = 0.0

    for t in teams_raw:
        name = t["name"]
        att_score = (t.get("strength_attack_home", 1000) + t.get("strength_attack_away", 1000)) / 2.0
        def_score = (t.get("strength_defence_home", 1000) + t.get("strength_defence_away", 1000)) / 2.0
        
        raw_scores[name] = {"att": max(500.0, float(att_score)), "def": max(500.0, float(def_score))}
        total_att += raw_scores[name]["att"]
        total_def += raw_scores[name]["def"]

    n = max(1, len(teams_raw))
    avg_att = max(1.0, total_att / n)
    avg_def = max(1.0, total_def / n)

    normalized_ratings = {}
    for name, scores in raw_scores.items():
        att_mult = ((scores["att"] / avg_att) ** 2.2) * 1.45
        def_mult = ((scores["def"] / avg_def) ** 2.0) * 1.40
        
        normalized_ratings[name] = {
            "att": round(max(0.5, float(att_mult)), 2),
            "def": round(max(0.5, float(def_mult)), 2)
        }

    return normalized_ratings

def fetch_fpl_bootstrap() -> Dict[str, Any]:
    """Fetches the raw bootstrap-static payload with browser headers."""
    try:
        response = requests.get(FPL_BOOTSTRAP_URL, headers=HEADERS, timeout=8)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[Warning] FPL API Fetch failed: {e}. Utilizing fallback baselines.")
        return {}

def fetch_pl_ratings() -> Dict[str, Dict[str, float]]:
    """Calculates relative attack/defense multipliers safely."""
    data = fetch_fpl_bootstrap()
    teams_raw = data.get("teams", [])
    
    if not teams_raw:
        return DEFAULT_BASELINES

    raw_scores = {}
    total_att = 0.0
    total_def = 0.0

    for t in teams_raw:
        name = t["name"]
        att_score = (t.get("strength_attack_home", 1000) + t.get("strength_attack_away", 1000)) / 2.0
        def_score = (t.get("strength_defence_home", 1000) + t.get("strength_defence_away", 1000)) / 2.0
        
        raw_scores[name] = {"att": max(500.0, float(att_score)), "def": max(500.0, float(def_score))}
        total_att += raw_scores[name]["att"]
        total_def += raw_scores[name]["def"]

    n = max(1, len(teams_raw))
    avg_att = max(1.0, total_att / n)
    avg_def = max(1.0, total_def / n)

    normalized_ratings = {}
    for name, scores in raw_scores.items():
        att_mult = ((scores["att"] / avg_att) ** 2.2) * 1.45
        def_mult = ((scores["def"] / avg_def) ** 2.0) * 1.40
        
        normalized_ratings[name] = {
            "att": round(max(0.5, float(att_mult)), 2),
            "def": round(max(0.5, float(def_mult)), 2)
        }

    return normalized_ratings

def fetch_team_details() -> Dict[str, Dict[str, Any]]:
    """Extracts squad rosters, badges, top scorers, and injury reports."""
    data = fetch_fpl_bootstrap()
    if not data:
        return {}

    teams_raw = data.get("teams", [])
    elements_raw = data.get("elements", [])
    element_types = {et["id"]: et["singular_name_short"] for et in data.get("element_types", [])}

    teams = {}
    for t in teams_raw:
        team_id = t["id"]
        code = t.get("code", 0)
        teams[team_id] = {
            "id": team_id,
            "name": t["name"],
            "short_name": t["short_name"],
            "badge_url": f"https://resources.premierleague.com/premierleague/badges/70/t{code}.png",
            "players": [],
            "injuries": []
        }

    for p in elements_raw:
        t_id = p.get("team")
        if t_id not in teams:
            continue

        player_info = {
            "name": f"{p.get('first_name', '')} {p.get('second_name', '')}".strip(),
            "web_name": p.get("web_name", "Player"),
            "position": element_types.get(p.get("element_type"), "MID"),
            "goals": p.get("goals_scored", 0),
            "assists": p.get("assists", 0),
            "xg": float(p.get("expected_goals") or 0.0),
            "xa": float(p.get("expected_assists") or 0.0),
            "minutes": p.get("minutes", 0),
            "chance_of_playing": p.get("chance_of_playing_next_round"),
            "news": p.get("news", "")
        }

        teams[t_id]["players"].append(player_info)
        if p.get("news"):
            teams[t_id]["injuries"].append({
                "player": player_info["web_name"],
                "status": p.get("news"),
                "chance": p.get("chance_of_playing_next_round")
            })

    return {team_data["name"]: team_data for team_data in teams.values()}