from pydantic import BaseModel
from typing import Optional,List

class SprintMemberData(BaseModel):
    id: str
    name: str
    role: str
    avatar: Optional[str]
    capacity: int
    allocated: int

class Projects(BaseModel):
    title: str
    description: str
    status: str             # Ejemplo: "Active", "Completed", "On Hold"
    priority: str           # Ejemplo: "High", "Medium", "Low"
    progress: int           # Porcentaje de progreso
    startDate: str          # Ejemplo: "2024-01-15T00:00:00Z"
    endDate: str            # Ejemplo: "2024-06-30T00:00:00Z"
    invitationCode: str     # Código de invitación
    tasksCompleted: int
    totalTasks: int
    team: str               # Nombre del equipo
    teamSize: int
    currentSprint: Optional[str]=None
    sprints: Optional[List[str]]=None
    teamMembers:Optional[List[SprintMemberData]]=None
    created_at:Optional[str]=None
    updated_at:Optional[str]=None
    createdBy:Optional[SprintMemberData]=None

class ProjectsResponse(Projects):
    id: str
