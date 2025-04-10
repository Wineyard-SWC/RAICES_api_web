from fastapi import APIRouter, HTTPException
from typing import List
from firebase import projects_ref, project_users_ref
from models.projects_model import Projects, ProjectsResponse

router = APIRouter()

@router.get("/projects", response_model=List[ProjectsResponse])
def get_projects():
    projects = projects_ref.stream()
    return [ProjectsResponse(id=project.id, **project.to_dict()) for project in projects]

@router.get("/projects/{project_id}", response_model=ProjectsResponse)
def get_project(project_id: str):
    project_doc = projects_ref.document(project_id).get()
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectsResponse(id=project_doc.id, **project_doc.to_dict())

@router.post("/projects", response_model=ProjectsResponse)
def create_project(project: Projects):
    project_doc = projects_ref.document()  # Genera un ID único automáticamente
    project_doc.set(project.dict())
    return ProjectsResponse(id=project_doc.id, **project.dict())

@router.put("/projects/{project_id}", response_model=ProjectsResponse)
def update_project(project_id: str, project: Projects):
    project_doc = projects_ref.document(project_id)
    if not project_doc.get().exists:
        raise HTTPException(status_code=404, detail="Project not found")
    project_doc.update(project.dict())
    return ProjectsResponse(id=project_id, **project.dict())

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    project_doc = projects_ref.document(project_id)
    if not project_doc.get().exists:
        raise HTTPException(status_code=404, detail="Project not found")
    # Eliminar las relaciones en project_users relacionadas al proyecto
    project_users_query = project_users_ref.where("projectRef", "==", project_doc).stream()
    for pu in project_users_query:
        project_users_ref.document(pu.id).delete()
    project_doc.delete()
    return {"message": "Project deleted successfully"}
