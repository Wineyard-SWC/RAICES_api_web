from .users_model import Users
from .projects_model import Projects

from pydantic import BaseModel

# Proyectos con sus respectivos Usuarios 
class Project_Users(BaseModel):
    userRef: Users 
    projectRef: Projects

class Project_UsersResponse(Project_Users):
    id: str  

class Project_UsersRef(BaseModel):
    userRef: str 
    projectRef: str