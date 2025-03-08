from .users_model import Users
from .projects_model import Projects

from pydantic import BaseModel

# Proyectos con sus respectivos Usuarios 
class ProjectUsers(BaseModel):
    userRef: Users 
    projectRef: Projects
    role: str 

class ProjectUsersResponse(ProjectUsers):
    id: str  
