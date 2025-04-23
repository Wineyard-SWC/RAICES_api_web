from pydantic import BaseModel
from enum import Enum
from typing import List, Optional

class PriorityEnum(str, Enum):
    high = 'High'
    medium = 'Medium'
    low = 'Low'

class UserStory(BaseModel):
    uuid: str 
    idTitle: str  # Ejemplo: US-001
    title: str
    comments: Optional[List[str]]
    description: str
    priority: PriorityEnum
    points: int
    acceptanceCriteria: List[str]
    epicRef: Optional[str] = None  # idTitle de la épica (ej. EPIC-001)
    projectRef: str  # ID del proyecto

class UserStoryResponse(UserStory):
    id: str  # ID de Firestore (se mantiene por compatibilidad)