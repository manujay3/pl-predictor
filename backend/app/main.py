import numpy as np
from fastapi import FastAPI, HTTPException
from app.services.football_client import fetch_pl_ratings
from app.engine.simulator import run_season_simulation

app = FastAPI(title="PL Predictor API")

@app.get("/api/simulate")
def get_simulation_results():
    try:
        # 1. Fetch live current-season ratings directly
        ratings = fetch_pl_ratings()
        
        # 2. Run simulation engine 
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        # 3. Process and structure JSON
        avg_points = {
            team: round(float(np.mean(pts)), 1) 
            for team, pts in sim_data.items()
        }
        
        standings = [
            {"team": team, "expected_points": points} 
            for team, points in sorted(avg_points.items(), key=lambda x: x[1], reverse=True)
        ]
        
        return {
            "status": "success",
            "source": "football-data.org",
            "iterations": 1000, 
            "standings": standings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))