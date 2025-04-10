from pydantic import BaseModel, Field
from typing import List, Optional

class RelatedRequirement(BaseModel):
    idTitle: str  # REQ-001
    description: str


class Epic(BaseModel):
    idTitle: str  # EPIC-001
    title: str
    description: str
    projectRef: str  # ID del proyecto
    relatedRequirements: Optional[List[RelatedRequirement]] = Field(
        default=None,
        exclude=True  # Esto hace que no se incluya al crear el documento en Firestore
    )


class EpicResponse(Epic):
    id: str  # ID de Firestore (se mantiene por compatibilidad)

