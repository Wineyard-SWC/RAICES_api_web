from pydantic import BaseModel

# Modelo de Usuarios
class Users(BaseModel):
    name: str
    email: str
    role: str = "user"  # User por defecto
    picture: str 

class UsersResponse(Users):
    id: str
