from typing import List

from fastapi import APIRouter, HTTPException, status

from models.permission_model import PermissionCreate, PermissionResponse
from firebase import permissions_ref

router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
)

@router.post(
    "",
    response_model=List[PermissionResponse],
    status_code=status.HTTP_201_CREATED
)
def create_permissions(permissions: List[PermissionCreate]):
    """
    Recibe un array de permisos (sin id), los inserta en Firestore 
    usando ID auto‐generado y devuelve la lista con los IDs asignados.
    """
    created: List[PermissionResponse] = []
    try:
        for perm in permissions:
            data = perm.dict()
            # ⬇️  Intercambiamos el orden
            _, doc_ref = permissions_ref.add(data)
            created.append(PermissionResponse(id=doc_ref.id, **data))
        return created

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not create permissions: {e}"
        )
