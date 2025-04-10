from firebase import db
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from firebase import epics_ref, req_ref
from models.epic_models import Epic, EpicResponse

router = APIRouter()

@router.post("/projects/{project_id}/epics/batch", response_model=List[EpicResponse])
def create_epics_batch(project_id: str, epics: List[Epic]):
    batch = db.batch()  # Usa db directamente para crear el batch
    created_epics = []
    
    for epic in epics:
        if epic.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in epic {epic.idTitle}")
        
        # Verificar si ya existe
        existing_query = epics_ref.where("idTitle", "==", epic.idTitle)\
                                .where("projectRef", "==", project_id)\
                                .limit(1).stream()
        
        if list(existing_query):
            raise HTTPException(status_code=400, detail=f"Epic {epic.idTitle} already exists")
        
        new_doc = epics_ref.document()
        batch.set(new_doc, epic.dict())
        created_epics.append({"id": new_doc.id, **epic.dict()})
    
    batch.commit()
    return created_epics


# Obtener todas las épicas de un proyecto
@router.get("/projects/{project_id}/epics", response_model=List[EpicResponse])
def get_project_epics(project_id: str):
    epics = epics_ref.where("projectRef", "==", project_id).stream()
    return [EpicResponse(id=epic.id, **epic.to_dict()) for epic in epics]


# Obtener una épica específica por idTitle
@router.get("/projects/{project_id}/epics/{epic_id}", response_model=EpicResponse)
def get_epic(
    project_id: str,
    epic_id: str  # idTitle de la épica (ej. EPIC-001)
):
    epic_query = epics_ref.where("idTitle", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .limit(1).stream()
    epic_list = list(epic_query)
    if not epic_list:
        raise HTTPException(status_code=404, detail="Epic not found")
    epic = epic_list[0]
    return EpicResponse(id=epic.id, **epic.to_dict())


# Crear o actualizar épica (upsert basado en idTitle + projectRef)
@router.post("/projects/{project_id}/epics", response_model=EpicResponse)
def upsert_epic(project_id: str, epic: Epic):
    # Aseguramos que el projectRef coincida con la URL
    if epic.projectRef != project_id:
        raise HTTPException(status_code=400, detail="ProjectRef mismatch")
    
    existing_query = epics_ref.where("idTitle", "==", epic.idTitle)\
                            .where("projectRef", "==", project_id)\
                            .limit(1).stream()
    
    existing = list(existing_query)
    
    if existing:
        # Actualizar
        epic_doc = epics_ref.document(existing[0].id)
        epic_doc.update(epic.dict())
        return EpicResponse(id=epic_doc.id, **epic.dict())
    else:
        # Crear nuevo
        new_doc = epics_ref.document()
        new_doc.set(epic.dict())
        return EpicResponse(id=new_doc.id, **epic.dict())


# Eliminar épica
@router.delete("/projects/{project_id}/epics/{epic_id}")
def delete_epic(
    project_id: str,
    epic_id: str  # idTitle de la épica
):
    epic_query = epics_ref.where("idTitle", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .limit(1).stream()
    epic_list = list(epic_query)
    
    if not epic_list:
        raise HTTPException(status_code=404, detail="Epic not found")
    
    # Desvincular requerimientos asociados
    requirements = req_ref.where("epicRef", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .stream()
    
    batch = req_ref.firestore.batch()
    for req in requirements:
        req_doc = req_ref.document(req.id)
        batch.update(req_doc, {"epicRef": None})
    
    batch.commit()
    
    # Eliminar la épica
    epics_ref.document(epic_list[0].id).delete()
    return {"message": "Epic deleted successfully and requirements unassigned"}