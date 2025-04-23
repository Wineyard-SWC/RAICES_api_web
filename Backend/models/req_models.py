from pydantic import BaseModel
from enum import Enum
from typing import Optional

class PriorityEnum(str, Enum):
    high = 'High'
    medium = 'Medium'
    low = 'Low'

class Requirement(BaseModel):
    idTitle: str  # REQ-001
    title: str
    description: str
    priority: PriorityEnum
    projectRef: str  # ID del proyecto
    epicRef: Optional[str] = None  # EPIC-001 (referencia al idTitle de la épica)
    uuid:str

class RequirementResponse(Requirement):
    id: str  # ID de Firestore (se mantiene por compatibilidad)