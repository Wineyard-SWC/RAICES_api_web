from fastapi import APIRouter, HTTPException,Body
from typing import List
from datetime import datetime
from firebase import projects_ref, sprints_ref, db
from models.sprint_model import SprintFormData, SprintResponse

router = APIRouter(
    prefix="/projects/{project_id}/sprints",
    tags=["Sprints"],
)

@router.post(
    "",
    response_model=SprintResponse,
)
def create_sprint(
    project_id: str,
    sprint: SprintFormData,
):
    # 1) Asegurarnos de que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    now = datetime.utcnow()

    # 2) Preparamos el dict para Firestore
    data = sprint.dict()
    data.update({
        "project_id": project_id,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    })

    # 3) Creamos el documento en batch o directo
    new_ref = sprints_ref.document()
    new_ref.set(data)

    # 4) Recuperamos lo que acabamos de escribir
    raw = new_ref.get().to_dict() or {}

    # 5) Extraemos los campos que vamos a pasar por separado
    proj_id    = raw.pop("project_id")
    created_at = raw.pop("created_at")
    updated_at = raw.pop("updated_at")

    # 6) Devolvemos la respuesta sin duplicar keywords
    return SprintResponse(
        id=new_ref.id,
        project_id=proj_id,
        created_at=created_at,
        updated_at=updated_at,
        **raw
    )

# Buscar un sprint por ID
@router.get(
    "/{sprint_id}",
    response_model=SprintResponse,
)
def get_sprint(
    project_id: str,
    sprint_id: str,
):
    # 1) Buscar el documento
    doc = sprints_ref.document(sprint_id).get()
    if not doc.exists or doc.get("project_id") != project_id:
        raise HTTPException(404, "Sprint not found")

    raw = doc.to_dict() or {}

    # 2) Extraemos los campos especiales
    proj_id    = raw.pop("project_id")
    created_at = raw.pop("created_at")
    updated_at = raw.pop("updated_at")

    return SprintResponse(
        id=sprint_id,
        project_id=proj_id,
        created_at=created_at,
        updated_at=updated_at,
        **raw
    )

# Listar todos los sprints de un proyecto
@router.get(
    "",
    response_model=List[SprintResponse],
)
def list_sprints(project_id: str):
    try:
        query = sprints_ref.where("project_id", "==", project_id).stream()
        results = []

        for doc in query:
            raw = doc.to_dict() or {}
            results.append(SprintResponse(
                id=doc.id,
                project_id=raw.get("project_id"),
                created_at=raw.get("created_at"),
                updated_at=raw.get("updated_at"),
                **{k: v for k, v in raw.items() if k not in {"project_id", "created_at", "updated_at"}}
            ))

        return results

    except Exception as e:
        raise HTTPException(500, f"Failed to fetch sprints: {e}")
    

# Actualizar un sprint por ID
@router.patch(
    "/{sprint_id}",
    response_model=SprintResponse,
)
def update_sprint(
    project_id: str,
    sprint_id: str,
    updates: SprintFormData = Body(...),
):
    # 1) Verificar que el sprint y proyecto existan
    doc_ref = sprints_ref.document(sprint_id)
    doc = doc_ref.get()

    if not doc.exists or doc.get("project_id") != project_id:
        raise HTTPException(404, "Sprint not found")

    now = datetime.utcnow()

    # 2) Actualizar los campos permitidos
    data = updates.dict()
    data["updated_at"] = now.isoformat()

    doc_ref.update(data)

    # 3) Obtener el documento actualizado
    updated = doc_ref.get().to_dict() or {}
    proj_id = updated.pop("project_id")
    created_at = updated.pop("created_at")
    updated_at = updated.pop("updated_at")

    return SprintResponse(
        id=sprint_id,
        project_id=proj_id,
        created_at=created_at,
        updated_at=updated_at,
        **updated
    )

# Eliminar un sprint por ID
@router.delete(
    "/{sprint_id}",
    status_code=204
)
def delete_sprint(
    project_id: str,
    sprint_id: str,
):
    doc_ref = sprints_ref.document(sprint_id)
    doc = doc_ref.get()

    if not doc.exists or doc.get("project_id") != project_id:
        raise HTTPException(404, "Sprint not found")

    doc_ref.delete()
