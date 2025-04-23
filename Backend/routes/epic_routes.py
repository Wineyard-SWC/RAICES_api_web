from firebase import db
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from firebase import epics_ref, req_ref, projects_ref
from firebase_admin import firestore
from models.epic_models import Epic, EpicResponse

router = APIRouter()

@router.post("/projects/{project_id}/epics/batch", response_model=List[EpicResponse])
def create_epics_batch(project_id: str, epics: List[Epic], archive_missing: bool = True):
    project_ref = projects_ref.document(project_id)
    project = project_ref.get()
    
    if not project.exists:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Get existing epics for this project
    existing_epics = {doc.to_dict()["idTitle"]: doc.reference 
                     for doc in epics_ref.where("projectRef", "==", project_id).stream()}
    
    # Track which epics we're updating
    updated_epic_ids = set()
    batch = db.batch()
    created_epics = []
    requirements_to_update = []
    
    for epic in epics:
        if epic.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in epic {epic.idTitle}")
        
        epic_dict = epic.model_dump(exclude_unset=True, exclude_none=True)
        epic_dict["status"] = "active"  
        epic_dict["lastUpdated"] = firestore.SERVER_TIMESTAMP
        
        if epic.idTitle in existing_epics:
            # Update existing
            epic_ref = existing_epics[epic.idTitle]
            batch.update(epic_ref, epic_dict)
            created_epics.append(EpicResponse(id=epic_ref.id, **epic_dict))
        else:
            new_doc = epics_ref.document()
            batch.set(new_doc, epic_dict)
            created_epics.append(EpicResponse(id=new_doc.id, **epic_dict))
        
        updated_epic_ids.add(epic.idTitle)
        
        # Handle requirements
        if epic.relatedRequirements:
            for req in epic.relatedRequirements:
                requirements_to_update.append({
                    "epic_id": epic.idTitle,
                    "req_id": req.idTitle,
                    "description": req.description,
                    "uuid": req.uuid
                })
    
    if archive_missing:
        for epic_id, epic_ref in existing_epics.items():
            if epic_id not in updated_epic_ids:
                batch.update(epic_ref, {
                    "status": "archived",
                    "lastUpdated": firestore.SERVER_TIMESTAMP
                })
    
    # Commit all changes
    batch.commit()
    
    # Update requirements
    if requirements_to_update:
        req_batch = db.batch()
        for item in requirements_to_update:
            req_query = req_ref.where("idTitle", "==", item["req_id"])\
                               .where("projectRef", "==", project_id)\
                               .limit(1).stream()
            req_list = list(req_query)
            
            if req_list:
                req_doc = req_ref.document(req_list[0].id)
                req_batch.update(req_doc, {"epicRef": item["epic_id"]})
        req_batch.commit()
    
    return created_epics


# Obtener todas las épicas de un proyecto
@router.get("/projects/{project_id}/epics", response_model=List[EpicResponse])
def get_project_epics(
    project_id: str,
    include_archived: bool = False  # Parámetro opcional para incluir archivados
):
    query = epics_ref.where("projectRef", "==", project_id)
    
    # Si no se solicitan archivados, filtrar por status=active
    if not include_archived:
        query = query.where("status", "==", "active")
    
    epics = query.stream()
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