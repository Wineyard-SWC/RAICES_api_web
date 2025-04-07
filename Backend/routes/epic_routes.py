from fastapi import APIRouter, HTTPException
from typing import List
from firebase import epics_ref
from models.epic_models import Epics, EpicsResponse


# Inicializar FastAPI
router = APIRouter()


# Obtener todas las épicas
@router.get("/epics", response_model=List[EpicsResponse])
def get_epics():
    epics = epics_ref.stream()
    return [EpicsResponse(id=epic.id, **epic.to_dict()) for epic in epics]

# Obtener una épica por ID
@router.get("/epics/{epic_id}", response_model=EpicsResponse)
def get_epic(epic_id: str):
    epic_doc = epics_ref.document(epic_id).get()
    if not epic_doc.exists:
        raise HTTPException(status_code=404, detail="Epic not found")
    return EpicsResponse(id=epic_doc.id, **epic_doc.to_dict())

# Crear una épica
@router.post("/epics", response_model=EpicsResponse)
def create_epic(epic: Epics):
    epic_doc = epics_ref.document()  # Genera un ID único
    epic_doc.set(epic.dict())
    return EpicsResponse(id=epic_doc.id, **epic.dict())

# Actualizar una épica
@router.put("/epics/{epic_id}", response_model=EpicsResponse)
def update_epic(epic_id: str, epic: Epics):
    epic_doc = epics_ref.document(epic_id)
    if not epic_doc.get().exists:
        raise HTTPException(status_code=404, detail="Epic not found")
    epic_doc.update(epic.dict())
    return EpicsResponse(id=epic_id, **epic.dict())

# Eliminar una épica
@router.delete("/epics/{epic_id}")
def delete_epic(epic_id: str):
    epic_doc = epics_ref.document(epic_id)
    if not epic_doc.get().exists:
        raise HTTPException(status_code=404, detail="Epic not found")
    epic_doc.delete()
    return {"message": "Epic deleted successfully"}