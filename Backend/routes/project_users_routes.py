from models.users_model import Users, UsersResponse
from models.projects_model import Projects, ProjectsResponse
from models.project_users_model import Project_Users, Project_UsersResponse, Project_UsersRef, ProjectUserFullResponse
from firebase import project_users_ref, users_ref, projects_ref
from fastapi import APIRouter, HTTPException
from typing import List

router = APIRouter(tags=["ProjectUsers"])

@router.get("/project_users", response_model=List[Project_UsersResponse])
def get_all_project_users():
    project_users = project_users_ref.stream()
    return [
        Project_UsersResponse(
            id=pu.id,
            userRef=users_ref.document(pu.to_dict()["userRef"].id).get().to_dict(),
            projectRef=projects_ref.document(pu.to_dict()["projectRef"].id).get().to_dict(),
            joinedAt=pu.to_dict().get("joinedAt"),
            role=pu.to_dict().get("role")
        )
        for pu in project_users
    ]

@router.get("/project_users/user/{user_id}", response_model=List[ProjectsResponse])
def get_projects_by_user(user_id: str):
    user_doc = users_ref.document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    project_users = project_users_ref.where("userRef", "==", user_doc.reference).stream()
    projects = [
        projects_ref.document(pu.to_dict()["projectRef"].id).get()
        for pu in project_users
    ]
    return [
        {"id": proj.id, **proj.to_dict()}
        for proj in projects if proj.exists
    ]

@router.get(
    "/project_users/project/{project_id}",
    response_model=List[ProjectUserFullResponse]
)
def get_users_by_project(project_id: str):
    project_doc = projects_ref.document(project_id).get()
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")

    out = []
    for pu in project_users_ref.where("projectRef", "==", project_doc.reference).stream():
        pu_data = pu.to_dict()
        user_ref = pu_data["userRef"]            # DocumentReference
        user_doc = users_ref.document(user_ref.id).get()
        if not user_doc.exists:
            continue
        user = user_doc.to_dict()

        out.append({
            # datos de la relación
            "id":         pu.id,
            "userRef":    user_ref.id,
            "projectRef": project_doc.id,
            "role":       pu_data.get("role"),
            "joinedAt":   pu_data.get("joinedAt"),
            # ahora añadimos los datos del usuario
            "name":    user.get("name"),
            "email":   user.get("email"),
            "picture": user.get("picture"),
        })

    return out


@router.post("/project_users", response_model=Project_UsersResponse)
def create_project_user_relation(project_user: Project_UsersRef):
    # Get the user and project documents using their IDs or references:
    user_doc = users_ref.document(project_user.userRef).get()
    project_doc = projects_ref.document(project_user.projectRef).get()

    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create the relation in Firestore
    project_user_doc = project_users_ref.document()
    project_users_ref.document(project_user_doc.id).set({
        "userRef": users_ref.document(project_user.userRef),
        "projectRef": projects_ref.document(project_user.projectRef),
        "role": project_user.role,
        "joinedAt": project_user.joinedAt
    })

    # Instead of returning the entire document's data, return just the IDs
    return Project_UsersResponse(
        id=project_user_doc.id,
        userRef=user_doc.id,
        projectRef=project_doc.id,
        role=project_user.role,
        joinedAt=project_user.joinedAt
    )


@router.delete("/project_users/{project_user_id}")
def delete_project_user_relation(project_user_id: str):
    project_user_doc = project_users_ref.document(project_user_id).get()
    if not project_user_doc.exists:
        raise HTTPException(status_code=404, detail="Project-user relation not found")
    project_users_ref.document(project_user_id).delete()
    return {"message": "Project-user relation deleted successfully"}

@router.get("/project_users/relation", response_model=Project_UsersResponse)
def get_project_user_relation(user_id: str, project_id: str):
    """
    Retorna la relación (Project_Users) entre un user_id y un project_id específicos,
    incluyendo 'role', 'joinedAt', etc.
    """
    # 1. Verificar que el user exista
    user_doc = users_ref.document(user_id).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. Verificar que el proyecto exista
    project_doc = projects_ref.document(project_id).get()
    if not project_doc.exists:
        raise HTTPException(status_code=404, detail="Project not found")

    # 3. Buscar la relación en project_users que cumpla con ambos
    query = (
        project_users_ref
        .where("userRef", "==", user_doc.reference)
        .where("projectRef", "==", project_doc.reference)
        .limit(1)  # Solo esperamos 1 doc
        .stream()
    )
    docs = list(query)

    if not docs:
        raise HTTPException(status_code=404, detail="No project-user relation found")

    # 4. Retornar la relación
    doc = docs[0]
    data = doc.to_dict()

    return Project_UsersResponse(
        id=doc.id,
        userRef=data["userRef"].id,
        projectRef=data["projectRef"].id,
        role=data.get("role"),
        joinedAt=data.get("joinedAt"),
    )
