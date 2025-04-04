from pydantic import BaseModel

class Projects(BaseModel):
    title: str
    description: str
    status: str  # 'Active', 'Completed', 'On Hold'
    priority: str  # 'High', 'Medium', 'Low'
    progress: int  # Porcentaje de progreso
    startDate: str
    endDate: str
    team: str
    teamSize: int
    tasksCompleted: int
    totalTasks: int

class ProjectsResponse(Projects):
    id: str
