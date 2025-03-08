from models.projects_model import Projects, ProjectsResponse
from firebase import projects_ref, project_users_ref
from fastapi import APIRouter, HTTPException
from typing import List

# Inicializar FastAPI
router = APIRouter()

# Obtener todos los proyectos
@router.get("/projects", response_model=List[ProjectsResponse])
def get_projects():
    projects = projects_ref.stream()
    return [ProjectsResponse(id=project.id, **project.to_dict()) for project in projects]

# Obtener un proyecto por ID
@router.get("/projects/{project_id}", response_model=ProjectsResponse)
def get_project(project_id: str):
    project_doc = projects_ref.document(project_id).get()
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")
    return ProjectsResponse(id=project_doc.id, **project_doc.to_dict())

# Crear un proyecto
@router.post("/projects", response_model=ProjectsResponse)
def create_project(project: Projects):
    project_doc = projects_ref.document()  # Genera un ID único
    project_doc.set(project.dict())
    return ProjectsResponse(id=project_doc.id, **project.dict())

# Actualizar un proyecto
@router.put("/projects/{project_id}", response_model=ProjectsResponse)
def update_project(project_id: str, project: Projects):
    project_doc = projects_ref.document(project_id)
    if not project_doc.get().exists:
        raise HTTPException(status_code=404, detail="Project not found")

    project_doc.update(project.dict())
    return ProjectsResponse(id=project_id, **project.dict())

# Eliminar un proyecto y sus referencias en project_users
@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    project_doc = projects_ref.document(project_id)
    if not project_doc.get().exists:
        raise HTTPException(status_code=404, detail="Project not found")

    # Eliminar referencias del proyecto en project_users
    project_users_query = project_users_ref.where("projectRef", "==", project_doc).stream()
    for project_user in project_users_query:
        project_users_ref.document(project_user.id).delete()

    # Eliminar proyecto
    project_doc.delete()
    return {"message": "Project deleted successfully"}
