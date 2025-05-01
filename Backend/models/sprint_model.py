from pydantic import BaseModel
from typing import List, Literal, Optional
from datetime import datetime

class SprintMemberData(BaseModel):
    id: str
    name: str
    role: str
    avatar: Optional[str]
    capacity: int
    allocated: int

class SprintUserStoryData(BaseModel):
    id: str
    title: str
    description: str
    acceptance_criteria: List[str]
    tasks: List[str]  # o bien el tipo de Task si quieres embebed
    selected: bool

class SprintFormData(BaseModel):
    name: str
    start_date: datetime
    end_date: datetime
    duration_weeks: int
    status: Literal["planning", "active", "completed"]
    # NO incluyas project_id aquí, lo tomamos de la URL

    team_members: List[SprintMemberData]
    user_stories: List[SprintUserStoryData]

class SprintResponse(SprintFormData):
    id: str
    project_id: str
    created_at: datetime
    updated_at: datetime
