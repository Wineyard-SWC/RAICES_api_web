from fastapi import APIRouter, HTTPException, Query
from typing import List
from firebase import db, users_ref  # Asegúrate de importar la referencia correcta a la colección "users"
from models.users_model import Users, UsersResponse

router = APIRouter(tags=["User Search"])

@router.get("/users/search", response_model=List[UsersResponse])
def search_users(
    search: str = Query(..., min_length=2, description="Término de búsqueda")
):
    try:
        name_query = (
            users_ref
            .where("name", ">=", search)
            .where("name", "<=", search + "\uf8ff")
            .limit(10)
            .stream()
        )
        email_query = (
            users_ref
            .where("email", ">=", search)
            .where("email", "<=", search + "\uf8ff")
            .limit(10)
            .stream()
        )

        name_docs = list(name_query)
        email_docs = list(email_query)

        combined = name_docs + email_docs
        unique_docs = {doc.id: doc for doc in combined}

        # Si no hay coincidencias, retornas []
        if not unique_docs:
            return []

        results = [
            UsersResponse(id=doc_id, **doc.to_dict())
            for doc_id, doc in unique_docs.items()
        ]
        return results

    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error al buscar usuarios: {err}")

@router.get("/projects/{project_id}/users/search", response_model=List[UsersResponse])
def search_project_users(
    project_id: str,
    search: str = Query(..., min_length=2, description="Término de búsqueda")
):
    try:
        project_doc = db.collection("projects").document(project_id).get()
        if not project_doc.exists:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_users_query = db.collection("project_users").where("projectRef", "==", project_doc.reference)
        project_users_docs = list(project_users_query.stream())
        
        if not project_users_docs:
            return []

        search_lower = search.lower()
        filtered_users = []
        
        for pu_doc in project_users_docs:
            pu_data = pu_doc.to_dict()
            user_ref = pu_data["userRef"]  
            
            user_doc = db.collection("users").document(user_ref.id).get()
            if not user_doc.exists:
                continue
                
            user_data = user_doc.to_dict()
            name = user_data.get("name", "").lower()
            email = user_data.get("email", "").lower()
            
            if (search_lower in name) or (search_lower in email):
                user_response = UsersResponse(
                    id=user_ref.id,
                    name=user_data.get("name"),
                    email=user_data.get("email"),
                    picture=user_data.get("picture"),
                    role=pu_data.get("role", "user")
                )
                filtered_users.append(user_response)

        return filtered_users

    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error al buscar usuarios del proyecto: {err}")