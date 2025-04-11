from firebase import db
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from firebase import epics_ref, req_ref, projects_ref
from models.epic_models import Epic, EpicResponse

router = APIRouter()

@router.post("/projects/{project_id}/epics/batch", response_model=List[EpicResponse])
def create_epics_batch(project_id: str, epics: List[Epic]):
    project_ref = projects_ref.document(project_id)
    project = project_ref.get()
    
    if not project.exists:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found"
        )

    # Primer batch para crear épicas
    epics_batch = db.batch()
    created_epics = []
    requirements_to_update = []
    
    # 1. Preparar todas las operaciones de creación de épicas
    for epic in epics:
        if epic.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in epic {epic.idTitle}")
        
        # Verificar si la épica ya existe
        existing_query = epics_ref.where("idTitle", "==", epic.idTitle)\
                                .where("projectRef", "==", project_id)\
                                .limit(1).stream()
        
        if list(existing_query):
            continue
        
        # Crear nueva épica (sin los relatedRequirements)
        new_doc = epics_ref.document()
        epic_dict = epic.dict(exclude={"relatedRequirements"})
        epics_batch.set(new_doc, epic_dict)
        
        # Guardar información para actualizar requerimientos
        if epic.relatedRequirements:
            for req in epic.relatedRequirements:
                requirements_to_update.append({
                    "epic_id": epic.idTitle,
                    "req_id": req.idTitle,
                    "description": req.description
                })
        
        created_epics.append(EpicResponse(id=new_doc.id, **epic_dict))
    
    # Ejecutar batch de épicas
    epics_batch.commit()
    
    # 2. Actualizar los requerimientos con sus epicRef
    if requirements_to_update:
        req_batch = db.batch()
        
        for item in requirements_to_update:
            # Buscar el requerimiento
            req_query = req_ref.where("idTitle", "==", item["req_id"])\
                             .where("projectRef", "==", project_id)\
                             .limit(1).stream()
            
            req_list = list(req_query)
            
            if req_list:
                # Si existe, actualizar su epicRef
                req_doc = req_ref.document(req_list[0].id)
                req_batch.update(req_doc, {"epicRef": item["epic_id"]})
            else:
                # Si no existe, podrías crearlo aquí
                pass
        
        # Ejecutar batch de requerimientos
        req_batch.commit()
    
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