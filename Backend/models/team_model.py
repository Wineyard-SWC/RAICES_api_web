from pydantic import BaseModel
from typing import List, Optional

class TeamMember(BaseModel):
    id: str
    name: str
    role: str
    tasksCompleted: int
    currentTasks: int
    availability: int

class TeamBase(BaseModel):
    name: str
    description: str
    projectId: str

class TeamCreate(TeamBase):
    members: List[str]  # List of user IDs

class TeamResponse(TeamBase):
    id: str
    createdAt: str
    updatedAt: str
    members: List[TeamMember]

class TeamUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    members: Optional[List[str]] = None

class TeamMetricsResponse(BaseModel):
    velocity: float
    mood: int  # Lo dejamos hardcodeado por ahora
    tasks_completed: int
    tasks_in_progress: int
    avg_story_time: float
    sprint_progress: float