from fastapi import APIRouter, HTTPException, Query
from typing import List
from firebase import users_ref  # Asegúrate de importar la referencia correcta a la colección "users"
from models.users_model import Users, UsersResponse

router = APIRouter()

@router.get("/users/search", response_model=List[UsersResponse])
def search_users(
    search: str = Query(..., min_length=2, description="Término de búsqueda (mínimo 2 caracteres)")
):
    try:
        # Define los límites para realizar una búsqueda "startsWith"
        lower_bound = search
        upper_bound = search + "\uf8ff"

        users_query = users_ref.where("name", ">=", lower_bound).where("name", "<=", upper_bound).stream()
        results = [UsersResponse(id=user.id, **user.to_dict()) for user in users_query]
        return results
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Error al buscar usuarios: {err}")
