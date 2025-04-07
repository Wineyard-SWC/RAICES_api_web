from pydantic import BaseModel
from enum import Enum

class PriorityEnum(str, Enum):
    high = 'High'
    medium = 'Medium'
    low = 'Low'

class Requirements(BaseModel):
    idTitle: str
    title: str
    description: str
    priority: PriorityEnum
    projectRef: str  # ID del proyecto al que pertenece
    epicRef: str = None  # ID de la épica a la que pertenece, puede ser opcional

class ReqResponse(Requirements):
    id: str
