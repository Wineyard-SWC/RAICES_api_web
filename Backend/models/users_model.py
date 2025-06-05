from pydantic import BaseModel
from typing import Optional

# Modelo de Usuarios
class Users(BaseModel):
    name: Optional[str] = None
    email: str
    role: str = "user"  # User por defecto
    picture: Optional[str] = None

class UsersResponse(Users):
    id: str
