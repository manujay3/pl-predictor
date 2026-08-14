from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime, timezone
from app.db.database import Base

class TeamRating(Base):
    __tablename__ = "team_ratings"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, unique=True, index=True)
    att_strength = Column(Float)
    def_strength = Column(Float)
    ai_insight = Column(String, nullable=True)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))