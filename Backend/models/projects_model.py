from pydantic import BaseModel

# Proyectos
class Projects(BaseModel):
    name: str 
    description: str 

class ProjectsResponse(Projects):
    id: str  
