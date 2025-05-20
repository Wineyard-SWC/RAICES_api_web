from firebase import db
from fastapi import APIRouter, HTTPException
from typing import List
from firebase import req_ref, epics_ref, projects_ref
from firebase_admin import firestore
from models.req_models import Requirement, RequirementResponse
from typing import Optional

router = APIRouter(tags=["Requirements"])

@router.post("/projects/{project_id}/requirements/batch", response_model=List[RequirementResponse])
def create_requirements_batch(
    project_id: str,
    requirements: List[Requirement],
    epic_id: Optional[str] = None,
    archive_missing: bool = True
):
    project_ref = projects_ref.document(project_id)
    project = project_ref.get()
    
    if not project.exists:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Validar si epic_id se especificó
    if epic_id:
        epic_query = epics_ref.where("idTitle", "==", epic_id)\
                              .where("projectRef", "==", project_id)\
                              .limit(1).stream()
        if not list(epic_query):
            raise HTTPException(status_code=404, detail="Epic not found")
    
    # Obtener requerimientos existentes
    existing_reqs = {
        doc.to_dict()["idTitle"]: doc.reference
        for doc in req_ref.where("projectRef", "==", project_id).stream()
    }

    updated_req_ids = set()
    batch = db.batch()
    created_reqs = []

    for req in requirements:
        if req.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in requirement {req.idTitle}")
        
        # Solo asignar epic_id si no hay uno definido
        if epic_id and not req.epicRef:
            req.epicRef = epic_id

        # Preparar objeto a guardar
        req_dict = req.model_dump(exclude_unset=True, exclude_none=True)
        req_dict["status"] = "active"
        req_dict["lastUpdated"] = firestore.SERVER_TIMESTAMP

        if req.idTitle in existing_reqs:
            ref = existing_reqs[req.idTitle]
            batch.update(ref, req_dict)
            created_reqs.append(RequirementResponse(id=ref.id, **req_dict))
        else:
            new_doc = req_ref.document()
            batch.set(new_doc, req_dict)
            created_reqs.append(RequirementResponse(id=new_doc.id, **req_dict))

        updated_req_ids.add(req.idTitle)

    # Archivar los requerimientos que ya no están
    if archive_missing:
        for req_id, ref in existing_reqs.items():
            if req_id not in updated_req_ids:
                batch.update(ref, {
                    "status": "archived",
                    "lastUpdated": firestore.SERVER_TIMESTAMP
                })

    batch.commit()
    return created_reqs

@router.get("/projects/{project_id}/requirements", response_model=List[RequirementResponse])
def get_project_requirements(
    project_id: str,
    include_archived: bool = False  
):
    query = req_ref.where("projectRef", "==", project_id)
    
    if not include_archived:
        query = query.where("status", "==", "active")
    
    requirements = query.stream()
    return [RequirementResponse(id=req.id, **req.to_dict()) for req in requirements]

# Obtener un requerimiento específico
@router.get("/projects/{project_id}/requirements/{requirement_id}", response_model=RequirementResponse)
def get_requirement(
    project_id: str,
    requirement_id: str  # idTitle del requerimiento (ej. REQ-001)
):
    req_query = req_ref.where("idTitle", "==", requirement_id)\
                      .where("projectRef", "==", project_id)\
                      .limit(1).stream()
    req_list = list(req_query)
    if not req_list:
        raise HTTPException(status_code=404, detail="Requirement not found")
    req = req_list[0]
    return RequirementResponse(id=req.id, **req.to_dict())


# Obtener requerimientos asociados a una épica
@router.get("/projects/{project_id}/epics/{epic_id}/requirements", response_model=List[RequirementResponse])
def get_epic_requirements(
    project_id: str,
    epic_id: str  # idTitle de la épica
):
    requirements = req_ref.where("epicRef", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .stream()
    return [RequirementResponse(id=req.id, **req.to_dict()) for req in requirements]


# Asignar requerimiento a épica
@router.put("/projects/{project_id}/requirements/{requirement_id}/assign-to-epic/{epic_id}", response_model=RequirementResponse)
def assign_requirement_to_epic(
    project_id: str,
    requirement_id: str,  # idTitle del requerimiento
    epic_id: str  # idTitle de la épica
):
    # Buscar requerimiento
    req_query = req_ref.where("idTitle", "==", requirement_id)\
                      .where("projectRef", "==", project_id)\
                      .limit(1).stream()
    req_list = list(req_query)
    
    if not req_list:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    # Verificar que la épica existe
    epic_query = epics_ref.where("idTitle", "==", epic_id)\
                         .where("projectRef", "==", project_id)\
                         .limit(1).stream()
    if not list(epic_query):
        raise HTTPException(status_code=404, detail="Epic not found")
    
    # Actualizar
    req_doc = req_ref.document(req_list[0].id)
    req_doc.update({"epicRef": epic_id})
    
    updated_req = req_doc.get().to_dict()
    return RequirementResponse(id=req_doc.id, **updated_req)


# Crear o actualizar requerimiento
@router.post("/projects/{project_id}/requirements", response_model=RequirementResponse)
def upsert_requirement(project_id: str, requirement: Requirement):
    # Validar coherencia del projectRef
    if requirement.projectRef != project_id:
        raise HTTPException(status_code=400, detail="ProjectRef mismatch")
    
    existing_query = req_ref.where("idTitle", "==", requirement.idTitle)\
                          .where("projectRef", "==", project_id)\
                          .limit(1).stream()
    
    existing = list(existing_query)
    
    if existing:
        # Actualizar
        req_doc = req_ref.document(existing[0].id)
        req_doc.update(requirement.dict())
        return RequirementResponse(id=req_doc.id, **requirement.dict())
    else:
        # Crear nuevo
        new_doc = req_ref.document()
        new_doc.set(requirement.dict())
        return RequirementResponse(id=new_doc.id, **requirement.dict())


# Eliminar requerimiento
@router.delete("/projects/{project_id}/requirements/{requirement_id}")
def delete_requirement(
    project_id: str,
    requirement_id: str  # idTitle del requerimiento
):
    req_query = req_ref.where("idTitle", "==", requirement_id)\
                      .where("projectRef", "==", project_id)\
                      .limit(1).stream()
    req_list = list(req_query)
    
    if not req_list:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    req_ref.document(req_list[0].id).delete()
    return {"message": "Requirement deleted successfully"}