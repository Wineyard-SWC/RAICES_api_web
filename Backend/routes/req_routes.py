from fastapi import APIRouter, HTTPException
from typing import List
from firebase import req_ref
from models.req_models import Requirements, RequirementsResponse

router = APIRouter()

# Obtener requerimientos por ID de proyecto
@router.get("/projects/{project_id}/requirements", response_model=List[RequirementsResponse])
def get_requirements_for_project(project_id: str):
    requirements = req_ref.where("projectRef", "==", project_id).stream()
    return [RequirementsResponse(id=req.id, **req.to_dict()) for req in requirements]

# Obtener requerimientos por ID de épicas
@router.get("/epics/{epic_id}/requirements", response_model=List[RequirementsResponse])
def get_requirements_for_epic(epic_id: str):
    requirements = req_ref.where("epicRef", "==", epic_id).stream()
    return [RequirementsResponse(id=req.id, **req.to_dict()) for req in requirements]

# Obtener requerimiento por ID
@router.get("/requirements/{req_id}", response_model=RequirementsResponse)
def get_requirement(req_id: str):
    req_doc = req_ref.document(req_id).get()
    if not req_doc.exists:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return RequirementsResponse(id=req_doc.id, **req_doc.to_dict())

# Crear un nuevo requerimiento
@router.post("/requirements", response_model=RequirementsResponse)
def create_requirement(requirement: Requirements):
    new_doc = req_ref.document()
    new_doc.set(requirement.dict())
    return RequirementsResponse(id=new_doc.id, **requirement.dict())

# Actualizar requerimiento
@router.put("/requirements/{req_id}", response_model=RequirementsResponse)
def update_requirement(req_id: str, requirement: Requirements):
    req_doc = req_ref.document(req_id)
    if not req_doc.get().exists:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    req_doc.update(requirement.dict())
    return RequirementsResponse(id=req_id, **requirement.dict())

# Eliminar requerimiento
@router.delete("/requirements/{req_id}")
def delete_requirement(req_id: str):
    req_doc = req_ref.document(req_id)
    if not req_doc.get().exists:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    req_doc.delete()
    return {"message": "Requirement deleted successfully"}
