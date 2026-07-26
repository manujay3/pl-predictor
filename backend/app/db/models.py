from sqlalchemy import Column, Integer, String, Float, DateTime
from app.db.database import Base
from datetime import datetime, timezone

class TeamRating(Base):
    __tablename__ = "team_ratings"

    id = Column(Integer, primary_key=True, index=True)
    team_name = Column(String, unique=True, index=True)
    att_strength = Column(Float, nullable=False)
    def_strength = Column(Float, nullable=False)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))