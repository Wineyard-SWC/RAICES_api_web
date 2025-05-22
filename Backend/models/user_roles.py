from pydantic import BaseModel, Field
from typing import Optional, List

class RoleDefinition(BaseModel):
    idRole: str
    name: str
    description: Optional[str] = None
    bitmask: int
    is_default: bool = False

class UserRolesDocument(BaseModel):
    id: Optional[str] = None
    userRef: str
    roles: List[RoleDefinition]

class UserRolesCreate(BaseModel):
    userRef: str
    roles: Optional[List[RoleDefinition]] = None

class UserRolesUpdate(BaseModel):
    roles: Optional[List[RoleDefinition]] = None
    
class UserRolesResponse(BaseModel):
    id: str
    userRef: str
    roles: List[RoleDefinition]
