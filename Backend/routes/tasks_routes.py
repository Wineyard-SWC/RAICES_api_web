from fastapi import APIRouter, HTTPException
from typing import List, Optional,Dict,Set
from firebase import db, projects_ref, userstories_ref, sprints_ref, tasks_ref
from firebase_admin import firestore
from models.task_model import TaskFormData, TaskResponse,StatusUpdate
from datetime import datetime

router = APIRouter()

@router.post("/projects/{project_id}/tasks/batch",
             response_model=List[TaskResponse])
def batch_upsert_tasks(
    project_id: str,
    tasks: List[TaskFormData],
    archive_missing: bool = False
):
    # 1️⃣  verificar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    story_map: Dict[str, str] = {          # uuid --> title
        d.get("uuid"): d.get("title")
        for d in userstories_ref
              .where("projectRef", "==", project_id)
              .where("status",     "==", "active")   # ← opcional
              .stream()
    }

    print(story_map)

    # 3️⃣  para archivar: tasks existentes en Firestore
    existing = {
        d.id: d.reference
        for d in tasks_ref.where("project_id", "==", project_id).stream()
    }

    batch     = db.batch()
    seen_ids: Set[str] = set()
    now_iso   = datetime.utcnow().isoformat()
    output:   List[TaskResponse] = []

    for t in tasks:
        # 4️⃣  validar con el diccionario precargado
        story_title = story_map.get(t.user_story_id)
        if story_title is None:
            raise HTTPException(
                404,
                f"User story {t.user_story_id} not found in project {project_id}"
            )

        data = t.dict(exclude_unset=True) | {
            "project_id":       project_id,
            "created_at":       now_iso,
            "updated_at":       now_iso,
            "comments":         [],
            "user_story_title": story_title,
        }
        data.pop("id", None)
        
        ref = tasks_ref.document()
        batch.set(ref, data)
        seen_ids.add(ref.id)

        output.append(TaskResponse(
            **data,
            id=ref.id,
            assignee_id=None,
            sprint_name=None
        ))

    # 5️⃣  archivar faltantes
    if archive_missing:
        for tid, ref in existing.items():
            if tid not in seen_ids:
                batch.update(ref, {
                    "status_khanban": "Done",
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

# 9) Agregar un comentario a una task
@router.post("/projects/{project_id}/tasks/{task_id}/comments")
def add_comment(project_id: str, task_id: str, comment: dict):
    ref = tasks_ref.document(task_id)
    snap = ref.get()
    if not snap.exists or snap.get("project_id") != project_id:
        raise HTTPException(404, "Task not found")

    comment["timestamp"] = datetime.utcnow().isoformat()
    ref.update({ "comments": firestore.ArrayUnion([comment]) })

    return { "message": "Comment added successfully" }


@router.delete("/projects/{project_id}/tasks/{task_id}/comments/{comment_id}")
def delete_comment(project_id: str, task_id: str, comment_id: str):
    doc_ref = tasks_ref.document(task_id)
    doc = doc_ref.get()
    if not doc.exists or doc.get("project_id") != project_id:
        raise HTTPException(404, "Task not found")
    
    data = doc.to_dict()
    updated_comments = [c for c in data.get("comments", []) if c["id"] != comment_id]
    doc_ref.update({"comments": updated_comments})
    return {"message": "Comment deleted"}


@router.patch("/projects/{project_id}/tasks/{task_id}/status")
def update_task_status(project_id: str, task_id: str, payload: StatusUpdate):
    # Validar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    task_doc = tasks_ref.document(task_id).get()
    if not task_doc.exists or task_doc.get("project_id") != project_id:
        raise HTTPException(404, "Task not found")

    tasks_ref.document(task_id).update({
        "status_khanban": payload.status_khanban
    })

    return {"message": f"Task {task_id} status updated to {payload.status_khanban}"}