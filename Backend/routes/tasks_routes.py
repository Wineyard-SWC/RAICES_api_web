from fastapi import APIRouter, HTTPException
from typing import List, Optional
from firebase import db, projects_ref, userstories_ref, sprints_ref, tasks_ref
from firebase_admin import firestore
from models.task_model import TaskFormData, TaskResponse
from datetime import datetime

router = APIRouter()

@router.post(
    "/projects/{project_id}/tasks/batch",
    response_model=List[TaskResponse]
)
def batch_upsert_tasks(
    project_id: str,
    tasks: List[TaskFormData],
    archive_missing: bool = False
):
    # 1. Validar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    # 2. Cargar tasks existentes
    existing = {
        doc.id: doc.reference
        for doc in tasks_ref.where("project_id", "==", project_id).stream()
    }

    batch = db.batch()
    seen_ids = set()
    output: List[TaskResponse] = []

    for t in tasks:
        # 3. Validar que la user story exista por su campo 'uuid'
        story_q = (
            userstories_ref
            .where("uuid", "==", t.user_story_id)
            .where("projectRef", "==", project_id)
            .limit(1)
            .stream()
        )
        story_docs = list(story_q)
        if not story_docs:
            raise HTTPException(404, f"User story {t.user_story_id} not found")
        story_doc = story_docs[0]

        # 4. Preparar datos con timestamp como string
        now = datetime.utcnow().isoformat()
        data = t.dict()
        data.update({
            "project_id": project_id,
            "created_at": now,
            "updated_at": now,
            "comments": [],
            # <-- aquí inyectas el título de la historia
            "user_story_title": story_doc.to_dict().get("title"),
        })

        # 5. Crear la nueva tarea
        new_ref = tasks_ref.document()
        batch.set(new_ref, data)
        seen_ids.add(new_ref.id)

        # 6. Construir la respuesta sin duplicar 'comments'
        response_kwargs = data.copy()
        comments = response_kwargs.pop("comments", [])
        # Quita también la clave que inyectaste en `data`
        story_title = response_kwargs.pop("user_story_title", None)

        output.append(
            TaskResponse(
                id=new_ref.id,
                user_story_title=story_title,
                assignee_id=None,
                sprint_name=None,
                comments=comments,
                **response_kwargs
            )
        )

    # 7. Opcional: archivar las que no vinieron en el batch
    if archive_missing:
        for task_id, ref in existing.items():
            if task_id not in seen_ids:
                batch.update(ref, {
                    "status": "Done",
                    "updated_at": datetime.utcnow().isoformat()
                })

    batch.commit()
    return output

# 2) Listar todas las tasks de un proyecto
@router.get(
    "/projects/{project_id}/tasks",
    response_model=List[TaskResponse]
)

@router.get(
    "/projects/{project_id}/tasks/khanban",
    response_model=List[TaskFormData]
)

def get_project_tasks(project_id: str):
    # 1) Validar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    # 2) Recuperar los documentos de Firestore
    docs = tasks_ref.where("project_id", "==", project_id).stream()
    output: List[TaskResponse] = []

    for d in docs:
        raw = d.to_dict() or {}

        # 3) Extraemos y eliminamos del dict los campos “especiales”
        comments          = raw.pop("comments", [])
        user_story_title  = raw.pop("user_story_title", None)
        assignee_id       = raw.pop("assignee_id", None)
        sprint_name       = raw.pop("sprint_name", None)

        # 4) Construimos la respuesta, pasando cada campo solo UNA vez
        output.append(
            TaskResponse(
                id=d.id,
                user_story_title=user_story_title,
                assignee_id=assignee_id,
                sprint_name=sprint_name,
                comments=comments,
                **raw
            )
        )

    return output


# 3) Obtener una task por su ID
@router.get(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=TaskResponse
)
def get_task(project_id: str, task_id: str):
    doc = tasks_ref.document(task_id).get()
    if not doc.exists or doc.get("project_id") != project_id:
        raise HTTPException(404, "Task not found")
    data = doc.to_dict()
    return TaskResponse(
        id=doc.id,
        user_story_title=data.get("user_story_title"),
        assignee_id=data.get("assignee_id"),
        sprint_name=data.get("sprint_name"),
        comments=data.get("comments", []),
        **data  # type: ignore
    )


# 4) Listar tasks de una user story
@router.get(
    "/projects/{project_id}/userstories/{user_story_id}/tasks",
    response_model=List[TaskResponse]
)
def get_tasks_by_story(project_id: str, user_story_id: str):
    # valida existencia user story
    story_q = (
        userstories_ref
        .where("idTitle", "==", user_story_id)
        .where("projectRef", "==", project_id)
        .limit(1)
        .stream()
    )
    if not list(story_q):
        raise HTTPException(404, "User story not found")

    docs = (
        tasks_ref
        .where("project_id", "==", project_id)
        .where("user_story_id", "==", user_story_id)
        .stream()
    )
    return [
        TaskResponse(
            id=d.id,
            user_story_title=d.get("user_story_title"),
            assignee_id=d.get("assignee_id"),
            sprint_name=d.get("sprint_name"),
            comments=d.get("comments", []),
            **d.to_dict()  # type: ignore
        )
        for d in docs
    ]


# 5) Listar tasks de un sprint
@router.get(
    "/projects/{project_id}/sprints/{sprint_id}/tasks",
    response_model=List[TaskResponse]
)
def get_tasks_by_sprint(project_id: str, sprint_id: str):
    # valida existencia sprint
    sprint_q = (
        sprints_ref
        .where("idTitle", "==", sprint_id)
        .where("projectRef", "==", project_id)
        .limit(1)
        .stream()
    )
    if not list(sprint_q):
        raise HTTPException(404, "Sprint not found")

    docs = (
        tasks_ref
        .where("project_id", "==", project_id)
        .where("sprint_id", "==", sprint_id)
        .stream()
    )
    return [
        TaskResponse(
            id=d.id,
            user_story_title=d.get("user_story_title"),
            assignee_id=d.get("assignee_id"),
            sprint_name=d.get("sprint_name"),
            comments=d.get("comments", []),
            **d.to_dict()  # type: ignore
        )
        for d in docs
    ]


# 6) Crear o actualizar (upsert) una sola task
@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskResponse
)
def upsert_task(project_id: str, t: TaskFormData):
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    data = t.dict()
    data.update({
        "project_id": project_id,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "comments": []  # siempre empieza vacío
    })
    data.setdefault("created_at", firestore.SERVER_TIMESTAMP)

    # Si viene id en el form, lo podrías usar para upsert; aquí asumimos POST → create
    new_ref = tasks_ref.document()
    new_ref.set(data)
    doc = new_ref.get().to_dict() or {}
    return TaskResponse(
        id=new_ref.id,
        user_story_title=doc.get("user_story_title"),
        assignee_id=doc.get("assignee_id"),
        sprint_name=doc.get("sprint_name"),
        comments=doc.get("comments", []),
        **doc  # type: ignore
    )


# 7) Actualizar una task existente
@router.put(
    "/projects/{project_id}/tasks/{task_id}",
    response_model=TaskResponse
)
def update_task(project_id: str, task_id: str, t: TaskFormData):
    ref = tasks_ref.document(task_id)
    snap = ref.get()
    if not snap.exists or snap.get("project_id") != project_id:
        raise HTTPException(404, "Task not found")

    data = t.dict(exclude_unset=True)
    data["updated_at"] = firestore.SERVER_TIMESTAMP
    ref.update(data)

    updated = ref.get().to_dict() or {}
    return TaskResponse(
        id=task_id,
        user_story_title=updated.get("user_story_title"),
        assignee_id=updated.get("assignee_id"),
        sprint_name=updated.get("sprint_name"),
        comments=updated.get("comments", []),
        **updated  # type: ignore
    )


# 8) Eliminar una task
@router.delete("/projects/{project_id}/tasks/{task_id}")
def delete_task(project_id: str, task_id: str):
    ref = tasks_ref.document(task_id)
    snap = ref.get()
    if not snap.exists or snap.get("project_id") != project_id:
        raise HTTPException(404, "Task not found")
    ref.delete()
    return {"message": "Task deleted successfully"}
