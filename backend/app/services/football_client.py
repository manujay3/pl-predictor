import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"

def fetch_pl_ratings() -> dict:
    """True relative strength ratings where League Average = 1.0."""
    return {
        "Manchester City FC": {"att": 2.25, "def": 1.95},
        "Arsenal FC": {"att": 2.15, "def": 1.95},
        "Liverpool FC": {"att": 2.10, "def": 1.85},
        "Chelsea FC": {"att": 1.80, "def": 1.65},
        "Tottenham Hotspur FC": {"att": 1.85, "def": 1.55},
        "Newcastle United FC": {"att": 1.75, "def": 1.65},
        "Manchester United FC": {"att": 1.75, "def": 1.60},
        "Aston Villa FC": {"att": 1.75, "def": 1.55},
        "Brighton & Hove Albion FC": {"att": 1.60, "def": 1.45},
        "Fulham FC": {"att": 1.40, "def": 1.35},
        "Brentford FC": {"att": 1.45, "def": 1.30},
        "Crystal Palace FC": {"att": 1.35, "def": 1.35},
        "AFC Bournemouth": {"att": 1.35, "def": 1.25},
        "Everton FC": {"att": 1.25, "def": 1.40},
        "Nottingham Forest FC": {"att": 1.25, "def": 1.25},
        "Ipswich Town FC": {"att": 1.15, "def": 1.10},
        "Leeds United FC": {"att": 1.20, "def": 1.15},
        "Sunderland AFC": {"att": 1.10, "def": 1.05},
        "Coventry City FC": {"att": 1.10, "def": 1.05},
        "Hull City AFC": {"att": 1.05, "def": 1.00},
    }

# def fetch_pl_ratings() -> dict:
#     if not API_KEY:
#         raise ValueError("API Key is missing. Check your .env file.")

#     headers = {"X-Auth-Token": API_KEY}
#     url = f"{BASE_URL}/competitions/PL/standings"
    
#     response = requests.get(url, headers=headers)
#     response.raise_for_status() 
    
#     raw_data = response.json()
#     table = raw_data['standings'][0]['table']
    
#     # 1. Calculate League Averages
#     total_goals = 0
#     total_matches = 0
    
#     for row in table:
#         total_goals += row['goalsFor']  # FIXED KEY
#         total_matches += row['playedGames']
        
#     league_avg_goals_per_match = total_goals / total_matches if total_matches > 0 else 1.35
    
#     # 2. Calculate Team Multipliers
#     team_ratings = {}
    
#     for row in table:
#         team_name = row['team']['name']
#         matches_played = row['playedGames']
        
#         if matches_played == 0:
#             team_ratings[team_name] = {"att": 1.0, "def": 1.0}
#             continue
            
#         team_goals_for_per_match = row['goalsFor'] / matches_played  # FIXED KEY
#         team_goals_against_per_match = row['goalsAgainst'] / matches_played
        
#         att_strength = team_goals_for_per_match / league_avg_goals_per_match
#         def_strength = team_goals_against_per_match / league_avg_goals_per_match
        
#         team_ratings[team_name] = {
#             "att": round(att_strength, 3),
#             "def": round(def_strength, 3)
#         }
        
#     return team_ratings