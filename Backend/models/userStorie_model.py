from pydantic import BaseModel
from enum import Enum
from typing import List, Optional,Literal

class PriorityEnum(str, Enum):
    high = 'High'
    medium = 'Medium'
    low = 'Low'

class Comment(BaseModel):
    id: str
    user_id: str
    user_name: str
    text: str
    timestamp: str

class UserStory(BaseModel):
    uuid: str 
    idTitle: str  # Ejemplo: US-001
    title: str
    comments: List[Comment]
    status_khanban:Literal["Backlog","To Do","In Progress","In Review","Done"]
    description: str
    priority: PriorityEnum
    points: int
    acceptanceCriteria: List[str]
    epicRef: Optional[str] = None  # idTitle de la épica (ej. EPIC-001)
    projectRef: str  # ID del proyecto

class UserStoryResponse(UserStory):
    id: str  # ID de Firestore (se mantiene por compatibilidad)