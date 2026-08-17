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
from app.services.news_scraper import scrape_latest_news
from app.services.football_client import fetch_pl_ratings 
from app.services.fpl_client import fetch_injured_players
from app.ai.rag_adjuster import query_team_news, batch_calculate_team_deltas, evaluate_custom_scenario
from app.engine.simulator import run_season_simulation

# Create database tables
Base.metadata.create_all(bind=engine)

# --- Pydantic Models ---
class TeamOverride(BaseModel):
    att_delta: float = 0.0
    def_delta: float = 0.0

class CustomSimulationRequest(BaseModel):
    overrides: Dict[str, TeamOverride]

class NLPSimulationRequest(BaseModel):
    team: str
    scenario: str


# --- ETL & Background Processing ---
def execute_full_refresh(db: Session):
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Running Background ETL Pipeline...")
    
    scrape_latest_news()
    raw_ratings = fetch_pl_ratings()
    all_injuries = fetch_injured_players()
    
    team_contexts = {}
    for team in raw_ratings:
        news_context = query_team_news(team)
        team_injuries = all_injuries.get(team, [])
        if news_context or team_injuries:
            team_contexts[team] = {
                "news": news_context if news_context else "No recent news.",
                "injuries": team_injuries if team_injuries else ["No injuries."]
            }

    ai_adjustments = batch_calculate_team_deltas(team_contexts)
    if not isinstance(ai_adjustments, dict):
        ai_adjustments = {}
    
    # Wipe old cache rows
    db.query(TeamRating).delete()
    
    for team, stats in raw_ratings.items():
        deltas = ai_adjustments.get(team, {})
        if not isinstance(deltas, dict):
            deltas = {}
        
        raw_att_delta = deltas.get("att_delta", 0.0) if isinstance(deltas.get("att_delta"), (int, float)) else 0.0
        raw_def_delta = deltas.get("def_delta", 0.0) if isinstance(deltas.get("def_delta"), (int, float)) else 0.0
        insight = deltas.get("reasoning", None) if isinstance(deltas.get("reasoning"), str) else None
        
        # Strictly clamp AI deltas between -0.15 and +0.15 to preserve squad baseline integrity
        att_delta = max(-0.15, min(0.15, raw_att_delta))
        def_delta = max(-0.15, min(0.15, raw_def_delta))
        
        # Apply clamped adjustments with a stable 0.5 floor
        final_att = max(0.5, stats["att"] + att_delta)
        final_def = max(0.5, stats["def"] + def_delta)
        
        new_rating = TeamRating(
            team_name=team,
            att_strength=final_att,
            def_strength=final_def,
            ai_insight=insight
        )
        db.add(new_rating)
        
    db.commit()
    print("Background ETL Pipeline complete. Database updated.")

def scheduled_etl_task():
    """Wrapper to handle the DB session for the background worker."""
    db = SessionLocal()
    try:
        execute_full_refresh(db)
    finally:
        db.close()


# --- Lifespan Setup ---
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


# --- Helper Functions ---
def _build_ratings_dict(db_ratings, overrides=None):
    """Builds ratings dict and AI insights mapping from database rows."""
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
    """Sorts simulation metrics by expected points and goal difference."""
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


# --- API Endpoints ---
@app.get("/api/simulate")
def get_simulation_results(force: bool = False, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        
        if force or not db_ratings:
            execute_full_refresh(db)
            db_ratings = db.query(TeamRating).all()
            data_source = "live refresh"
        else:
            data_source = "database cache"

        ratings, ai_insights = _build_ratings_dict(db_ratings)
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        return {
            "status": "success",
            "source": data_source,
            "iterations": 1000, 
            "standings": _format_standings(sim_data, ai_insights)
        }
        
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate/custom")
def run_custom_simulation(request: CustomSimulationRequest, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        if not db_ratings:
            raise HTTPException(status_code=400, detail="Database is empty. Please run a standard simulation first.")

        override_dict = {
            team: {"att_delta": data.att_delta, "def_delta": data.def_delta}
            for team, data in request.overrides.items()
        }

        ratings, ai_insights = _build_ratings_dict(db_ratings, override_dict)
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        return {
            "status": "success",
            "source": "custom simulation",
            "iterations": 1000, 
            "standings": _format_standings(sim_data, ai_insights)
        }
        
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simulate/nlp-scenario")
def run_nlp_scenario(request: NLPSimulationRequest, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        if not db_ratings:
            raise HTTPException(status_code=400, detail="Database empty. Run standard simulation first.")

        # Translate scenario prompt into numerical delta adjustments
        ai_evaluation = evaluate_custom_scenario(request.team, request.scenario)
        
        override_dict = {request.team: ai_evaluation}
        ratings, ai_insights = _build_ratings_dict(db_ratings, override_dict)

        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        return {
            "status": "success",
            "source": "AI scenario simulation",
            "iterations": 1000, 
            "ai_deltas": ai_evaluation,
            "standings": _format_standings(sim_data, ai_insights)
        }
        
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
from app.engine.simulator import generate_all_fixture_odds

@app.get("/api/fixtures")
def get_fixture_odds(team: Optional[str] = None, db: Session = Depends(get_db)):
    """Returns simulated odds and projected scores for all 380 Premier League matches."""
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