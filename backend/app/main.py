from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from typing import Dict, Optional

from app.db.database import engine, Base, get_db, SessionLocal
from app.db.models import TeamRating
from app.services.fpl_client import fetch_pl_ratings, fetch_team_details
from app.ai.rag_adjuster import evaluate_custom_scenario
from app.engine.simulator import run_season_simulation, generate_all_fixture_odds

Base.metadata.create_all(bind=engine)

class TeamOverride(BaseModel):
    att_delta: float = 0.0
    def_delta: float = 0.0

class CustomSimulationRequest(BaseModel):
    overrides: Dict[str, TeamOverride]

class NLPSimulationRequest(BaseModel):
    team: str
    scenario: str

def execute_full_refresh(db: Session):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Refreshing baseline from FPL API...")
    raw_ratings = fetch_pl_ratings()
    
    db.query(TeamRating).delete()
    for team, stats in raw_ratings.items():
        new_rating = TeamRating(
            team_name=team,
            att_strength=stats["att"],
            def_strength=stats["def"],
            ai_insight=None
        )
        db.add(new_rating)
    db.commit()
    print("ETL complete. Official FPL data loaded.")

def scheduled_etl_task():
    db = SessionLocal()
    try:
        execute_full_refresh(db)
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    scheduler.add_job(scheduled_etl_task, 'interval', hours=6)
    scheduler.start()
    yield
    scheduler.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _build_ratings_dict(db_ratings, overrides=None):
    ratings = {}
    ai_insights = {}
    for r in db_ratings:
        base_att = r.att_strength
        base_def = r.def_strength
        insight = getattr(r, "ai_insight", None)
        
        if overrides and r.team_name in overrides:
            override_data = overrides[r.team_name]
            base_att = max(0.5, base_att + override_data.get("att_delta", 0.0))
            base_def = max(0.5, base_def + override_data.get("def_delta", 0.0))
            if "reasoning" in override_data:
                insight = f"SCENARIO: {override_data['reasoning']}"

        ratings[r.team_name] = {"att": base_att, "def": base_def}
        ai_insights[r.team_name] = insight
    return ratings, ai_insights

def _format_standings(sim_data, ai_insights):
    return [
        {
            "team": team, 
            "ai_insight": ai_insights.get(team, None),
            **metrics
        } 
        for team, metrics in sorted(
            sim_data.items(), 
            key=lambda x: (x[1]["expected_points"], x[1]["expected_gd"]), 
            reverse=True
        )
    ]

@app.get("/api/simulate")
def get_simulation_results(force: bool = False, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        if force or not db_ratings:
            execute_full_refresh(db)
            db_ratings = db.query(TeamRating).all()
            data_source = "FPL Live API Refresh"
        else:
            data_source = "Database Cache (FPL)"

        ratings, ai_insights = _build_ratings_dict(db_ratings)
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        return {
            "status": "success",
            "source": data_source,
            "iterations": 1000, 
            "standings": _format_standings(sim_data, ai_insights)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/fixtures")
def get_fixture_odds(team: Optional[str] = None, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        if not db_ratings:
            execute_full_refresh(db)
            db_ratings = db.query(TeamRating).all()
            
        ratings = {r.team_name: {"att": r.att_strength, "def": r.def_strength} for r in db_ratings}
        all_fixtures = generate_all_fixture_odds(ratings, num_sims=1000)
        
        if team:
            filtered = [f for f in all_fixtures if f["home_team"] == team or f["away_team"] == team]
            return {"status": "success", "count": len(filtered), "fixtures": filtered}
        return {"status": "success", "count": len(all_fixtures), "fixtures": all_fixtures}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/team/{team_name}")
def get_team_squad_and_stats(team_name: str):
    """Returns official badge, full roster, top scorers, and factual injury notes."""
    team_data = fetch_team_details()
    matched = team_data.get(team_name)
    if not matched:
        for name, data in team_data.items():
            if name.lower() in team_name.lower() or team_name.lower() in name.lower():
                matched = data
                break
    if not matched:
        raise HTTPException(status_code=404, detail="Team not found in FPL data")

    sorted_players = sorted(matched["players"], key=lambda x: x["minutes"], reverse=True)
    return {
        "status": "success",
        "name": matched["name"],
        "badge_url": matched["badge_url"],
        "official_injuries": matched["injuries"],
        "top_scorers": sorted(matched["players"], key=lambda x: x["goals"], reverse=True)[:5],
        "squad": sorted_players
    }

@app.post("/api/simulate/custom")
def run_custom_simulation(request: CustomSimulationRequest, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        if not db_ratings:
            raise HTTPException(status_code=400, detail="Database empty.")

        override_dict = {
            team: {"att_delta": data.att_delta, "def_delta": data.def_delta}
            for team, data in request.overrides.items()
        }
        ratings, ai_insights = _build_ratings_dict(db_ratings, override_dict)
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        return {
            "status": "success",
            "source": "Custom Manual Simulation",
            "iterations": 1000, 
            "standings": _format_standings(sim_data, ai_insights)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate/nlp-scenario")
def run_nlp_scenario(request: NLPSimulationRequest, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        if not db_ratings:
            raise HTTPException(status_code=400, detail="Database empty.")

        ai_evaluation = evaluate_custom_scenario(request.team, request.scenario)
        override_dict = {request.team: ai_evaluation}
        ratings, ai_insights = _build_ratings_dict(db_ratings, override_dict)
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        return {
            "status": "success",
            "source": "AI Scenario Simulation",
            "iterations": 1000, 
            "ai_deltas": ai_evaluation,
            "standings": _format_standings(sim_data, ai_insights)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))