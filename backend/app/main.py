from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel
from typing import Dict, Optional

from app.db.database import engine, Base, get_db, SessionLocal
from app.db.models import TeamRating
from app.services.news_scraper import scrape_latest_news
from app.services.football_client import fetch_pl_ratings 
from app.services.fpl_client import fetch_injured_players, fetch_current_standings
from app.ai.rag_adjuster import query_team_news, batch_calculate_team_deltas, evaluate_custom_scenario
from app.engine.simulator import run_season_simulation


# Create database tables
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
    print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Running Background ETL Pipeline...")
    
    scrape_latest_news()
    raw_ratings = fetch_pl_ratings()
    all_injuries = fetch_injured_players()
    
    # NEW: Grab the live table
    live_standings = fetch_current_standings()
    
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
    
    db.query(TeamRating).delete()
    
    for team, stats in raw_ratings.items():
        deltas = ai_adjustments.get(team, {})
        if not isinstance(deltas, dict):
            deltas = {}
        
        att_delta = deltas.get("att_delta", 0.0) if isinstance(deltas.get("att_delta"), (int, float)) else 0.0
        def_delta = deltas.get("def_delta", 0.0) if isinstance(deltas.get("def_delta"), (int, float)) else 0.0
        insight = deltas.get("reasoning", None) if isinstance(deltas.get("reasoning"), str) else None
        
        final_att = max(0.1, stats["att"] + att_delta)
        final_def = max(0.1, stats["def"] + def_delta)
        
        new_rating = TeamRating(
            team_name=team,
            att_strength=final_att,
            def_strength=final_def
        )
        new_rating.ai_insight = insight
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

# --- LIFESPAN SCHEDULER SETUP ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler()
    # Run the ETL pipeline every 6 hours
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

@app.get("/api/simulate")
def get_simulation_results(force: bool = False, db: Session = Depends(get_db)):
    try:
        db_ratings = db.query(TeamRating).all()
        
        # If forced OR if database is completely empty, run it right now
        if force or not db_ratings:
            execute_full_refresh(db)
            db_ratings = db.query(TeamRating).all()
            data_source = "live refresh"
        else:
            data_source = "database cache"

        # Construct the ratings dictionary for the Monte Carlo engine
        ratings = {
            r.team_name: {"att": r.att_strength, "def": r.def_strength}
            for r in db_ratings
        }
        
        ai_insights = {
            r.team_name: getattr(r, "ai_insight", None)
            for r in db_ratings 
            if getattr(r, "ai_insight", None)
        }

        # The math engine runs instantly based on the DB values
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        standings = [
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
        
        return {
            "status": "success",
            "source": data_source,
            "iterations": 1000, 
            "standings": standings
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

        ratings = {}
        ai_insights = {}
        
        for r in db_ratings:
            # Start with the cached SQLite baseline
            base_att = r.att_strength
            base_def = r.def_strength
            
            # If the user adjusted this team's sliders, apply the delta
            if r.team_name in request.overrides:
                override = request.overrides[r.team_name]
                base_att = max(0.1, base_att + override.att_delta)
                base_def = max(0.1, base_def + override.def_delta)
                
            ratings[r.team_name] = {"att": base_att, "def": base_def}
            
            # Keep the original AI insight for context
            ai_insights[r.team_name] = getattr(r, "ai_insight", None)

        # Run the Monte Carlo engine instantly in-memory
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        standings = [
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
        
        return {
            "status": "success",
            "source": "custom simulation",
            "iterations": 1000, 
            "standings": standings
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

        # 1. Ask Gemini to translate the text into numerical deltas
        ai_evaluation = evaluate_custom_scenario(request.team, request.scenario)
        
        ratings = {}
        ai_insights = {}
        
        # 2. Apply the AI's math to the base SQLite stats
        for r in db_ratings:
            base_att = r.att_strength
            base_def = r.def_strength
            
            if r.team_name == request.team:
                base_att = max(0.1, base_att + ai_evaluation["att_delta"])
                base_def = max(0.1, base_def + ai_evaluation["def_delta"])
                # Overwrite the base insight with the specific scenario reasoning
                ai_insights[r.team_name] = f"SCENARIO: {ai_evaluation['reasoning']}"
            else:
                ai_insights[r.team_name] = getattr(r, "ai_insight", None)
                
            ratings[r.team_name] = {"att": base_att, "def": base_def}

        # 3. Run the instant math engine
        sim_data = run_season_simulation(ratings, num_simulations=1000)
        
        standings = [
            {"team": team, "ai_insight": ai_insights.get(team, None), **metrics} 
            for team, metrics in sorted(
                sim_data.items(), 
                key=lambda x: (x[1]["expected_points"], x[1]["expected_gd"]), 
                reverse=True
            )
        ]
        
        return {
            "status": "success",
            "source": "AI scenario simulation",
            "iterations": 1000, 
            "ai_deltas": ai_evaluation, # Send the math back to the frontend so the sliders update!
            "standings": standings
        }
        
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))