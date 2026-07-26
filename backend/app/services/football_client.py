import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("FOOTBALL_DATA_API_KEY")
BASE_URL = "https://api.football-data.org/v4"

def fetch_pl_ratings() -> dict:
    if not API_KEY:
        raise ValueError("API Key is missing. Check your .env file.")

    headers = {"X-Auth-Token": API_KEY}
    url = f"{BASE_URL}/competitions/PL/standings"
    
    response = requests.get(url, headers=headers)
    response.raise_for_status() 
    
    raw_data = response.json()
    table = raw_data['standings'][0]['table']
    
    # 1. Calculate League Averages
    total_goals = 0
    total_matches = 0
    
    for row in table:
        total_goals += row['goalsFor']  # FIXED KEY
        total_matches += row['playedGames']
        
    league_avg_goals_per_match = total_goals / total_matches if total_matches > 0 else 1.35
    
    # 2. Calculate Team Multipliers
    team_ratings = {}
    
    for row in table:
        team_name = row['team']['name']
        matches_played = row['playedGames']
        
        if matches_played == 0:
            team_ratings[team_name] = {"att": 1.0, "def": 1.0}
            continue
            
        team_goals_for_per_match = row['goalsFor'] / matches_played  # FIXED KEY
        team_goals_against_per_match = row['goalsAgainst'] / matches_played
        
        att_strength = team_goals_for_per_match / league_avg_goals_per_match
        def_strength = team_goals_against_per_match / league_avg_goals_per_match
        
        team_ratings[team_name] = {
            "att": round(att_strength, 3),
            "def": round(def_strength, 3)
        }
        
    return team_ratings