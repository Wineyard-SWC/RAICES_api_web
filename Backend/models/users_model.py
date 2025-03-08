from pydantic import BaseModel

# Usuarios
class Users(BaseModel):
    name: str 
    email: str 
    role: str 
    
class UsersResponse(Users):
    id: str  
