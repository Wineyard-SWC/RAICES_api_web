from .users_model import Users
from .projects_model import Projects

from pydantic import BaseModel

from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# Modelo para las peticiones (entrada)
class Project_UsersRef(BaseModel):
    userRef: str            # ID o referencia del usuario (por ejemplo, "/users/<id>")
    projectRef: str         # ID o referencia del proyecto (por ejemplo, "/projects/<id>")
    role: str               # Rol del usuario en el proyecto, ej. "Owner", "Member", etc.
    joinedAt: str           # Marca temporal de la unión, ej. "9 de abril de 2025, 4:32:41 p.m. UTC-6"

# Modelo interno (si lo deseas, puede ser igual al de entrada)
class Project_Users(BaseModel):
    userRef: str
    projectRef: str
    role: str
    joinedAt: str

class Project_UsersResponse(BaseModel):
    id: str
    userRef: str
    projectRef: str
    role: Optional[str] = None
    joinedAt: Optional[datetime] = None
