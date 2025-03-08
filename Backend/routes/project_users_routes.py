from models.users_model import Users, UsersResponse
from models.projects_model import Projects, ProjectsResponse
from models.project_users_model import Project_Users, Project_UsersResponse, Project_UsersRef
from firebase import project_users_ref, users_ref, projects_ref
from fastapi import APIRouter, HTTPException
from typing import List

# Inicializar FastAPI
router = APIRouter()

# Obtener todas las relaciones usuario-proyecto
@router.get("/project_users", response_model=List[Project_UsersResponse])
def get_all_project_users():
    project_users = project_users_ref.stream()
    # Modificar para obtener los datos completos de usuario y proyecto
    return [
        Project_UsersResponse(
            id=pu.id,
            userRef=users_ref.document(pu.to_dict()["userRef"].id).get().to_dict(),
            projectRef=projects_ref.document(pu.to_dict()["projectRef"].id).get().to_dict()
        ) 
        for pu in project_users
    ]

# Obtener todos los proyectos de un usuario específico
@router.get("/project_users/user/{user_id}", response_model=List[ProjectsResponse])
def get_projects_by_user(user_id: str):
    user_doc = users_ref.document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    project_users = project_users_ref.where("userRef", "==", user_doc.reference).stream()
    
    projects = [
        projects_ref.document(pu.to_dict()["projectRef"].id).get()  # Obtener documento de Firestore
        for pu in project_users
    ]

    # Usar el ID de Firestore directamente
    return [
        {"id": proj.id, **proj.to_dict()}  # Usar el ID de Firestore del proyecto
        for proj in projects if proj.exists
    ]


# Obtener todos los usuarios de un proyecto específico
@router.get("/project_users/project/{project_id}", response_model=List[UsersResponse])
def get_users_by_project(project_id: str):
    project_doc = projects_ref.document(project_id).get()
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")

    project_users = project_users_ref.where("projectRef", "==", project_doc.reference).stream()
    users = [
        users_ref.document(pu.to_dict()["userRef"].id).get().to_dict() 
        for pu in project_users
    ]

    return [{"id": str(user_id), **user} for user_id, user in enumerate(users) if user]

# Crear una relación usuario-proyecto
@router.post("/project_users", response_model=Project_UsersResponse)
def create_project_user_relation(project_user: Project_UsersRef):
    # Usamos los IDs directamente para obtener los documentos de usuario y proyecto
    user_doc = users_ref.document(project_user.userRef).get()
    project_doc = projects_ref.document(project_user.projectRef).get()

    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")

    # Crear la relación en la colección project_users usando las referencias
    project_user_doc = project_users_ref.document()
    project_user_doc.set({
        "userRef": users_ref.document(project_user.userRef),  # Pasamos la referencia directamente
        "projectRef": projects_ref.document(project_user.projectRef)  # Igual para el proyecto
    })

    # Crear instancias de los modelos Users y Projects
    user_instance = Users(**user_doc.to_dict())  # Crear la instancia de User
    project_instance = Projects(**project_doc.to_dict())  # Crear la instancia de Project

    # Devolver la respuesta con el ID generado por Firestore para la relación
    return Project_UsersResponse(
        id=project_user_doc.id,  # El ID del documento creado en Firestore
        userRef=user_instance,  # Instancia del usuario
        projectRef=project_instance  # Instancia del proyecto
    )


# Eliminar una relación usuario-proyecto
@router.delete("/project_users/{project_user_id}")
def delete_project_user_relation(project_user_id: str):
    project_user_doc = project_users_ref.document(project_user_id).get()

    if not project_user_doc.exists:
        raise HTTPException(status_code=404, detail="Project-user relation not found")

    # Eliminar el documento de la relación usando la referencia
    project_users_ref.document(project_user_id).delete()

    return {"message": "Project-user relation deleted successfully"}

