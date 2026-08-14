import numpy as np
from typing import Dict, Tuple

# Standard baseline metrics
HOME_ADVANTAGE = 1.12       
LEAGUE_AVG_GOALS = 1.35     

def calculate_expected_goals(
    h_att: float, h_def: float, a_att: float, a_def: float
) -> Tuple[float, float]:
    lambda_home = h_att * a_def * LEAGUE_AVG_GOALS * HOME_ADVANTAGE
    lambda_away = a_att * h_def * LEAGUE_AVG_GOALS
    return lambda_home, lambda_away

def simulate_match(lambda_home: float, lambda_away: float) -> Tuple[int, int]:
    home_goals = np.random.poisson(lambda_home)
    away_goals = np.random.poisson(lambda_away)
    return int(home_goals), int(away_goals)

def run_season_simulation(
    team_ratings: Dict[str, Dict[str, float]], 
    num_simulations: int = 1000
) -> Dict[str, Dict]:
    teams = list(team_ratings.keys())
    
    total_points = {team: 0 for team in teams}
    total_gd = {team: 0 for team in teams}  # New: Track GD across all runs
    position_counts = {team: {i: 0 for i in range(1, 21)} for team in teams}
    
    fixtures = [(home, away) for home in teams for away in teams if home != away]
    
    for _ in range(num_simulations):
        season_points = {team: 0 for team in teams}
        season_gd = {team: 0 for team in teams} # New: Track GD for this single season
        
        for home_team, away_team in fixtures:
            h_att, h_def = team_ratings[home_team]["att"], team_ratings[home_team]["def"]
            a_att, a_def = team_ratings[away_team]["att"], team_ratings[away_team]["def"]
            
            lambda_h, lambda_a = calculate_expected_goals(h_att, h_def, a_att, a_def)
            h_goals, a_goals = simulate_match(lambda_h, lambda_a)
            
            # Calculate match goal difference
            match_gd = h_goals - a_goals
            season_gd[home_team] += match_gd
            season_gd[away_team] -= match_gd
            
            if h_goals > a_goals:
                season_points[home_team] += 3
            elif a_goals > h_goals:
                season_points[away_team] += 3
            else:
                season_points[home_team] += 1
                season_points[away_team] += 1
                
        # Updated Sort: Primary key is points, secondary key is Goal Difference
        sorted_run = sorted(teams, key=lambda t: (season_points[t], season_gd[t]), reverse=True)
        
        for rank, team in enumerate(sorted_run, 1):
            total_points[team] += season_points[team]
            total_gd[team] += season_gd[team]
            position_counts[team][rank] += 1
            
    results = {}
    for team in teams:
        avg_pts = total_points[team] / num_simulations
        avg_gd = total_gd[team] / num_simulations
        
        title_prob = (position_counts[team][1] / num_simulations) * 100
        ucl_prob = (sum(position_counts[team][i] for i in range(1, 5)) / num_simulations) * 100
        relegation_prob = (sum(position_counts[team][i] for i in range(18, 21)) / num_simulations) * 100
        
        # NEW: Calculate the exact probability for every single rank (1-20)
        pos_percentages = {
            str(pos): round((count / num_simulations) * 100, 1) 
            for pos, count in position_counts[team].items()
        }
        
        results[team] = {
            "expected_points": round(avg_pts, 1),
            "expected_gd": round(avg_gd, 1),
            "title_prob": round(title_prob, 1),
            "ucl_prob": round(ucl_prob, 1),
            "relegation_prob": round(relegation_prob, 1),
            "positions": pos_percentages # <-- Add this to the payload
        }
        
    return results