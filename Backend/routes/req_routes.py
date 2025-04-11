from firebase import db
from fastapi import APIRouter, HTTPException
from typing import List
from firebase import req_ref, epics_ref, projects_ref
from models.req_models import Requirement, RequirementResponse
from typing import Optional

router = APIRouter()

@router.post("/projects/{project_id}/requirements/batch", response_model=List[RequirementResponse])
def create_requirements_batch(
    project_id: str,
    requirements: List[Requirement],
    epic_id: Optional[str] = None  # Opcional: si se quiere asignar todos a la misma épica
):
    project_ref = projects_ref.document(project_id)
    project = project_ref.get()
    
    if not project.exists:
        raise HTTPException(
            status_code=404,
            detail=f"Project with ID {project_id} not found"
        )
    
    batch = db.batch()  
    created_reqs = []
    
    # Verificar épica si se especificó
    if epic_id:
        epic_query = epics_ref.where("idTitle", "==", epic_id)\
                             .where("projectRef", "==", project_id)\
                             .limit(1).stream()
        if not list(epic_query):
            raise HTTPException(status_code=404, detail="Epic not found")

    for req in requirements:
        if req.projectRef != project_id:
            raise HTTPException(status_code=400, detail=f"ProjectRef mismatch in requirement {req.idTitle}")
        
        # Si se especificó epic_id, sobreescribimos la referencia
        if epic_id:
            req.epicRef = epic_id
        
        # Verificar si ya existe
        existing_query = req_ref.where("idTitle", "==", req.idTitle)\
                              .where("projectRef", "==", project_id)\
                              .limit(1).stream()
        
        existing = list(existing_query)
        
        if existing:
            # Actualizar existente
            req_doc = req_ref.document(existing[0].id)
            batch.update(req_doc, req.dict())
            created_reqs.append({"id": req_doc.id, **req.dict()})
        else:
            # Crear nuevo
            new_doc = req_ref.document()
            batch.set(new_doc, req.dict())
            created_reqs.append({"id": new_doc.id, **req.dict()})
    
    batch.commit()
    return created_reqs


# Obtener todos los requerimientos de un proyecto
@router.get("/projects/{project_id}/requirements", response_model=List[RequirementResponse])
def get_project_requirements(project_id: str):
    requirements = req_ref.where("projectRef", "==", project_id).stream()
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