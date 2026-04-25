from sqlalchemy import Column, Integer, String, Text
from database import Base

class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, unique=True, index=True)
    
    # Store preferences like "Standard meeting length is 30 mins"
    standard_meeting_duration = Column(Integer, default=30) 
    preferred_time_of_day = Column(String, default="Any") # Morning, Afternoon, Evening, Any
    
    # Can store raw notes the agent remembers
    memory_context = Column(Text, default="")
