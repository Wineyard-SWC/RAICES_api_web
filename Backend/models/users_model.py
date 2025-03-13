from pydantic import BaseModel
from typing import Optional

# Modelo de Usuarios
class Users(BaseModel):
    name: Optional[str]
    email: str
    role: str = "user"  # User por defecto
    picture: Optional[str]

class UsersResponse(Users):
    id: str
