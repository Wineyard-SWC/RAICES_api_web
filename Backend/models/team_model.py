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
