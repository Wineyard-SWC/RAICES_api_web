from pydantic import BaseModel

class Epic(BaseModel):
    idTitle: str  # EPIC-001
    title: str
    description: str
    projectRef: str  # ID del proyecto

class EpicResponse(Epic):
    id: str  # ID de Firestore (se mantiene por compatibilidad)