from fastapi import APIRouter, HTTPException
from typing import List
from firebase import users_ref, project_users_ref
from models.users_model import Users, UsersResponse
from fastapi import Query


# Inicializar FastAPI
router = APIRouter(tags=["Users"])

# Obtener todos los usuarios
@router.get("/users", response_model=List[UsersResponse])
def get_users():
    users = users_ref.stream()
    return [UsersResponse(id=user.id, **user.to_dict()) for user in users]

# Obtener un usuario por ID
@router.get("/users/{uid}", response_model=UsersResponse)
def get_user(uid: str):
    user_doc = users_ref.document(uid).get()
    if not user_doc.exists:
        raise HTTPException(status_code=404, detail="User not found")
    return UsersResponse(id=user_doc.id, **user_doc.to_dict())

# Crear un usuario
@router.post("/users", response_model=UsersResponse)
def create_user(user: Users):
    user_doc = users_ref.document(user.uid)
    if user_doc.get().exists:
        raise HTTPException(status_code=400, detail="User already exists")

    user_doc.set(user.dict())
    return UsersResponse(id=user.uid, **user.dict())

# Actualizar un usuario
@router.put("/users/{user_id}", response_model=UsersResponse)
def update_user(user_id: str, user: Users):
    user_doc = users_ref.document(user_id)
    if not user_doc.get().exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_doc.update(user.dict())
    return UsersResponse(id=user_id, **user.dict())

# Eliminar un usuario y sus referencias en project_users
@router.delete("/users/{user_id}")
def delete_user(uid: str):
    user_doc = users_ref.document(uid)
    if not user_doc.get().exists:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Eliminar referencias del usuario en project_users
    project_users_query = project_users_ref.where("userRef", "==", user_doc).stream()
    for project_user in project_users_query:
        project_users_ref.document(project_user.id).delete()

    # Eliminar usuario
    user_doc.delete()
    return {"message": "User deleted successfully"}

