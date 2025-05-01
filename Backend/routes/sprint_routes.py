from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime
from firebase import projects_ref, sprints_ref, db
from models.sprint_model import SprintFormData, SprintResponse

router = APIRouter(
    prefix="/projects/{project_id}/sprints",
    tags=["sprints"],
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
