import math
import random
from collections import defaultdict

# ---------------------------------------------------------
# 1. Mock Data & Configuration
# ---------------------------------------------------------
# Team Attack and Defense ratings relative to league average (1.0 = average)
TEAM_RATINGS = {
    "Arsenal":     {"att": 1.35, "def": 0.65},
    "Man City":    {"att": 1.45, "def": 0.70},
    "Liverpool":   {"att": 1.30, "def": 0.75},
    "Chelsea":     {"att": 1.05, "def": 0.95},
    "Tottenham":   {"att": 1.00, "def": 1.05},
    "Aston Villa": {"att": 0.95, "def": 1.10},
}

LEAGUE_AVG_GOALS = 1.50  # Average goals scored per team per match
HOME_ADVANTAGE   = 1.15  # 15% multiplier for playing at home


# ---------------------------------------------------------
# 2. Match Probability & Goal Generation
# ---------------------------------------------------------
def calculate_match_xg(home_team: str, away_team: str) -> tuple[float, float]:
    """
    Calculates expected goals (λ) for home and away teams based on ratings.
    """
    home_att = TEAM_RATINGS[home_team]["att"]
    away_def = TEAM_RATINGS[away_team]["def"]
    
    away_att = TEAM_RATINGS[away_team]["att"]
    home_def = TEAM_RATINGS[home_team]["def"]

    # λ = Attacking Strength * Opponent Defensive Weakness * Baseline * Home/Away Factor
    home_xg = home_att * away_def * LEAGUE_AVG_GOALS * HOME_ADVANTAGE
    away_xg = away_att * home_def * LEAGUE_AVG_GOALS

    return home_xg, away_xg


def simulate_goals(lmbda: float) -> int:
    """
    Samples goals scored from a Poisson distribution given rate parameter λ.
    """
    L = math.exp(-lmbda)
    k = 0
    p = 1.0
    while p > L:
        k += 1
        p *= random.random()
    return k - 1


# ---------------------------------------------------------
# 3. Monte Carlo League Simulation Engine
# ---------------------------------------------------------
def run_league_simulation(simulations: int = 10_000):
    teams = list(TEAM_RATINGS.keys())
    
    # Track finishing positions across all simulations
    # finish_counts[team][position] = count
    finish_counts = {team: defaultdict(int) for team in teams}

    # Generate full double round-robin fixture list
    fixtures = [
        (home, away) 
        for home in teams 
        for away in teams 
        if home != away
    ]

    print(f"Running {simulations:,} Monte Carlo season simulations...")

    for _ in range(simulations):
        # Reset league table for this season
        points = {team: 0 for team in teams}
        goal_diff = {team: 0 for team in teams}

        # Simulate every fixture in the season
        for home, away in fixtures:
            home_xg, away_xg = calculate_match_xg(home, away)
            
            home_goals = simulate_goals(home_xg)
            away_goals = simulate_goals(away_xg)

            # Update goal difference
            goal_diff[home] += (home_goals - away_goals)
            goal_diff[away] += (away_goals - home_goals)

            # Assign match points
            if home_goals > away_goals:
                points[home] += 3
            elif away_goals > home_goals:
                points[away] += 3
            else:
                points[home] += 1
                points[away] += 1

        # Rank teams by points, then goal difference
        ranked_teams = sorted(
            teams, 
            key=lambda t: (points[t], goal_diff[t]), 
            reverse=True
        )

        # Record final positions (1-indexed)
        for pos, team in enumerate(ranked_teams, start=1):
            finish_counts[team][pos] += 1

    # ---------------------------------------------------------
    # 4. Display Results as a Probability Matrix
    # ---------------------------------------------------------
    print("\n" + "=" * 65)
    print(f"{'Team':<15} | " + " | ".join([f"Pos {i}" for i in range(1, len(teams) + 1)]))
    print("=" * 65)

    for team in teams:
        probs = [
            f"{(finish_counts[team][pos] / simulations):>5.1%}" 
            for pos in range(1, len(teams) + 1)
        ]
        print(f"{team:<15} | " + " | ".join(probs))
    print("=" * 65)


if __name__ == "__main__":
    run_league_simulation(simulations=10_000)