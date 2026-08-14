import requests

FPL_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

# Map the official FPL team names directly to your formal database strings
FPL_NAME_MAP = {
    "Arsenal": "Arsenal FC",
    "Aston Villa": "Aston Villa FC",
    "Bournemouth": "Bournemouth",
    "Brentford": "Brentford FC",
    "Brighton": "Brighton & Hove Albion FC",
    "Chelsea": "Chelsea FC",
    "Crystal Palace": "Crystal Palace FC",
    "Everton": "Everton FC",
    "Fulham": "Fulham FC",
    "Ipswich": "Ipswich Town FC",
    "Leicester": "Leicester City FC",
    "Liverpool": "Liverpool FC",
    "Man City": "Manchester City FC",
    "Man Utd": "Manchester United FC",
    "Newcastle": "Newcastle United FC",
    "Nott'm Forest": "Nottingham Forest FC",
    "Southampton": "Southampton FC",
    "Spurs": "Tottenham Hotspur FC",
    "West Ham": "West Ham United FC",
    "Wolves": "Wolverhampton Wanderers FC"
}

def fetch_injured_players() -> dict:
    try:
        response = requests.get(FPL_URL, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        # Create a dictionary to map FPL Team ID -> FPL Team Name
        fpl_teams = {t["id"]: t["name"] for t in data.get("teams", [])}
        
        # Initialize an empty dictionary for the injuries
        injuries_by_team = {db_name: [] for db_name in FPL_NAME_MAP.values()}
        
        for player in data.get("elements", []):
            chance_of_playing = player.get("chance_of_playing_next_round")
            
            if chance_of_playing == 0:
                fpl_team_id = player.get("team")
                fpl_team_name = fpl_teams.get(fpl_team_id)
                
                # If the team maps to one in our system, record the injury
                db_team_name = FPL_NAME_MAP.get(fpl_team_name)
                
                if db_team_name:
                    full_name = f"{player.get('first_name')} {player.get('second_name')}"
                    news = player.get("news", "Unknown injury")
                    injuries_by_team[db_team_name].append(f"{full_name} ({news})")
                    
        return injuries_by_team

    except Exception as e:
        print(f"Error fetching FPL data: {e}")
        return {}

if __name__ == "__main__":
    injuries = fetch_injured_players()
    for team, player_list in injuries.items():
        if player_list:
            print(f"\n{team} Injuries:")
            for p in player_list:
                print(f"  - {p}")

def fetch_current_standings():
    """Fetches the live Premier League table to anchor the simulation."""
    
    try:
        response = requests.get(FPL_URL)
        response.raise_for_status()
        data = response.json()
        
        standings = {}
        for team in data.get("teams", []):
            name = team["name"]
            standings[name] = {
                "current_points": team["points"],
                "matches_played": team["played"],
                "current_gd": team["goal_difference"]
            }
            
        return standings
    except Exception as e:
        print(f"Error fetching live standings: {e}")
        return {}