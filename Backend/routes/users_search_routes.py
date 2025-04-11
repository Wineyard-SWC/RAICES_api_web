from fastapi import APIRouter, HTTPException, Query
from typing import List
from firebase import users_ref  # Asegúrate de importar la referencia correcta a la colección "users"
from models.users_model import Users, UsersResponse

router = APIRouter()

@router.get("/users/search", response_model=List[UsersResponse])
def search_users(
    search: str = Query(..., min_length=3, description="Término de búsqueda")
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
