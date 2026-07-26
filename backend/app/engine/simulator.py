import numpy as np
from typing import Dict, List, Tuple
from app.services.football_client import fetch_pl_ratings

# Standard baseline metrics
HOME_ADVANTAGE = 1.12       # ~12% boost for home fixtures
LEAGUE_AVG_GOALS = 1.35     # Average goals per team per match

def calculate_expected_goals(
    h_att: float, h_def: float, a_att: float, a_def: float
) -> Tuple[float, float]:
    """Calculates lambda (expected goals) for home and away teams."""
    lambda_home = h_att * a_def * LEAGUE_AVG_GOALS * HOME_ADVANTAGE
    lambda_away = a_att * h_def * LEAGUE_AVG_GOALS
    return lambda_home, lambda_away

def simulate_match(lambda_home: float, lambda_away: float) -> Tuple[int, int]:
    """Simulates a match scoreline using Poisson distribution sampling."""
    home_goals = np.random.poisson(lambda_home)
    away_goals = np.random.poisson(lambda_away)
    return int(home_goals), int(away_goals)

def run_season_simulation(
    team_ratings: Dict[str, Dict[str, float]], 
    num_simulations: int = 1000
) -> Dict[str, List[int]]:
    """
    Executes a Monte Carlo simulation over a double round-robin season (380 matches).
    Returns total points accumulated by each team across all simulation runs.
    """
    teams = list(team_ratings.keys())
    results = {team: [] for team in teams}
    
    # Construct standard 380 double round-robin fixture list
    fixtures = [
        (home, away) 
        for home in teams 
        for away in teams 
        if home != away
    ]
    
    for _ in range(num_simulations):
        season_points = {team: 0 for team in teams}
        
        for home_team, away_team in fixtures:
            h_att, h_def = team_ratings[home_team]["att"], team_ratings[home_team]["def"]
            a_att, a_def = team_ratings[away_team]["att"], team_ratings[away_team]["def"]
            
            lambda_h, lambda_a = calculate_expected_goals(h_att, h_def, a_att, a_def)
            h_goals, a_goals = simulate_match(lambda_h, lambda_a)
            
            if h_goals > a_goals:
                season_points[home_team] += 3
            elif a_goals > h_goals:
                season_points[away_team] += 3
            else:
                season_points[home_team] += 1
                season_points[away_team] += 1
                
        for team in teams:
            results[team].append(season_points[team])
            
    return results

if __name__ == "__main__":
    print("Fetching live ETL ratings...")
    ratings = fetch_pl_ratings(season=2024)
    
    print("\nRunning 1,000 Monte Carlo season simulations...")
    sim_data = run_season_simulation(ratings, num_simulations=1000)
    
    # Calculate average points per team across 1,000 iterations
    avg_points = {team: round(float(np.mean(pts)), 1) for team, pts in sim_data.items()}
    sorted_standings = sorted(avg_points.items(), key=lambda x: x[1], reverse=True)
    
    print("\n" + "="*45)
    print(f"{'Rank':<5} | {'Team':<25} | {'Avg Pts':<7}")
    print("="*45)
    for rank, (team, pts) in enumerate(sorted_standings, 1):
        print(f"{rank:<5} | {team:<25} | {pts:<7}")