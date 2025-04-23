from pydantic import BaseModel, Field
from typing import List, Optional

class RelatedRequirement(BaseModel):
    idTitle: str  # REQ-001 
    title: str 
    description: str
    uuid: str


class Epic(BaseModel):
    uuid: str 
    idTitle: str  # EPIC-001
    title: str
    description: str
    projectRef: str  # ID del proyecto
    relatedRequirements: Optional[List[RelatedRequirement]] = Field(
        default=None,
    )


class EpicResponse(Epic):
    id: str  # ID de Firestore (se mantiene por compatibilidad)

