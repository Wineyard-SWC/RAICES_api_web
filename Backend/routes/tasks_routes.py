from fastapi import APIRouter, HTTPException
from typing import List, Optional,Dict,Set,Any,Tuple
from firebase import db, projects_ref, userstories_ref, sprints_ref, tasks_ref
from firebase_admin import firestore
from models.task_model import TaskFormData, TaskResponse,StatusUpdate,TaskPartialKhabanResponse
from datetime import datetime

router = APIRouter()

def safe_iso(dt):
    if isinstance(dt, datetime):
        return dt.isoformat()
    if hasattr(dt, "isoformat"):
        return dt.isoformat()
    if isinstance(dt, str):
        return dt
    return ""

def convert_assignee_format(data: Dict[str, Any]) -> List[Tuple[str, str]]:
    """Convierte el campo assignee de Firestore al formato de lista de tuplas"""
    assigned_users = []
    
    if "assignee" in data and data["assignee"]:
        # Si es una lista de objetos (nuevo formato)
        if isinstance(data["assignee"], list):
            for user in data["assignee"]:
                if isinstance(user, dict) and "id" in user and "name" in user:
                    assigned_users.append((user["id"], user["name"]))
        # Si es un string (formato antiguo)
        elif isinstance(data["assignee"], str) and data["assignee"]:
            user_name = data.get("assignee_name", "")
            assigned_users.append((data["assignee"], user_name))
            
    return assigned_users


@router.post("/projects/{project_id}/tasks/batch", response_model=List[TaskResponse])
def batch_upsert_tasks(
    project_id: str,
    tasks: List[TaskFormData],
    archive_missing: bool = False
):
    # 1️⃣ Verificar que el proyecto exista
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(status_code=404, detail="Project not found") 

    # 2️⃣ Cargar títulos de user stories
    story_map: Dict[str, str] = {
        doc.get("uuid"): doc.get("title")
        for doc in userstories_ref
            .where("projectRef", "==", project_id)
            .where("status", "==", "active")
            .stream()
    }

    # 3️⃣ Buscar las tareas que ya están en Firestore
    existing: Dict[str, any] = {
        doc.id: doc.reference
        for doc in tasks_ref.where("project_id", "==", project_id).stream()
    }

    batch     = db.batch()
    seen_ids: Set[str] = set()
    now_iso   = datetime.utcnow().isoformat()
    output:   List[TaskResponse] = []

    for t in tasks:
        # 4️⃣ Validar que la user story pertenezca al proyecto
        story_title = story_map.get(t.user_story_id)
        if story_title is None:
            raise HTTPException(
                status_code=404,
                detail=f"User story {t.user_story_id} not found in project {project_id}"
            )

        # 5️⃣ Preparar datos comunes
        # exclude id para no sobrescribirlo, y toma solo campos enviados
        data = t.dict(exclude_unset=True, exclude={"id"})
        if "assignee" in data and data["assignee"]:
            data["assignee"] = [{"id": user_id, "name": user_name} 
                               for user_id, user_name in data["assignee"]]
        else:
            data["assignee"] = []
        data.update({
            "project_id":       project_id,
            "updated_at":       now_iso,
            "user_story_title": story_title,
        })

        # 6️⃣ Decide si ACTUALIZA o CREA
        if t.id in existing:
            # actualizar campos en doc existente
            ref = existing[t.id]
            batch.update(ref, data)
        else:
            # crea uno nuevo con el mismo ID
            data["created_at"] = now_iso
            ref = tasks_ref.document(t.id)
            batch.set(ref, data)

        seen_ids.add(t.id)

        assigned_users = []
        if data.get("assignee"):
            assigned_users = [(user["id"], user["name"]) for user in data["assignee"]]

        # 7️⃣ Armar la respuesta
        output.append(TaskResponse(
            id               = t.id,
            title            = data["title"],
            description      = data["description"],
            user_story_id    = t.user_story_id,
            assignee         = assigned_users,
            sprint_id        = data.get("sprint_id"),
            status_khanban   = data["status_khanban"],
            priority         = data["priority"],
            story_points     = data["story_points"],
            deadline         = data.get("deadline"),
            comments         = data.get("comments", []),
            user_story_title = story_title,
            assignee_id      = data.get("assignee"),   # ajusta si usas un campo distinto
            sprint_name      = None,                   # si quieres el nombre, haz fetch adicional
            created_at       = safe_iso(data.get("created_at", now_iso)),
            updated_at       = safe_iso(data.get("updated_at")),
            created_by       = tuple(data.get("created_by", ["", ""])),
            modified_by      = tuple(data.get("modified_by", ["", ""])),
            finished_by      = tuple(data.get("finished_by", ["", ""])),
            date_created     = safe_iso(data.get("date_created")),
            date_modified    = safe_iso(data.get("date_modified")),
            date_completed   = safe_iso(data.get("date_completed")),
        ))

    # 8️⃣ Archivar las que ya no vienen en el payload
    if archive_missing:
        for tid, ref in existing.items():
            if tid not in seen_ids:
                batch.update(ref, {
                    "status_khanban": "Done",
                    "updated_at":     datetime.utcnow().isoformat()
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
        
        # Convertir el formato de assignee
        assigned_users = convert_assignee_format(raw)
        
        output.append(TaskResponse(
            id=d.id,
            title=raw.get("title", ""),
            description=raw.get("description", ""),
            user_story_id=raw.get("user_story_id", ""),
            user_story_title=raw.get("user_story_title"),
            assignee=assigned_users,
            sprint_id=raw.get("sprint_id"),
            sprint_name=raw.get("sprint_name"),
            status_khanban=raw.get("status_khanban", "Backlog"),
            priority=raw.get("priority", "Medium"),
            story_points=raw.get("story_points", 0),
            deadline=raw.get("deadline"),
            comments=raw.get("comments", []),
            created_at= safe_iso(raw.get("created_at")),
            updated_at= safe_iso(raw.get("updated_at")),
            created_by= tuple(raw.get("created_by", ["", ""])),
            modified_by= tuple(raw.get("modified_by", ["", ""])),
            finished_by= tuple(raw.get("finished_by", ["", ""])),
            date_created= safe_iso(raw.get("date_created")),
            date_modified= safe_iso(raw.get("date_modified")),
            date_completed= safe_iso(raw.get("date_completed")),
        ))

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
    "/projects/{project_id}/tasks_partial",
    response_model=List[TaskPartialKhabanResponse]
)
def get_tasks_partialdata(project_id: str):
    if not projects_ref.document(project_id).get().exists:
        raise HTTPException(404, "Project not found")

    docs = tasks_ref.where("project_id", "==", project_id).stream()

    result = []

    for d in docs:
        doc = d.to_dict() or {}

        result.append(TaskPartialKhabanResponse(
            id=d.id,
            user_story_title=doc.get("user_story_title"),
            assignee_id=doc.get("assignee_id", []),
            sprint_name=doc.get("sprint_name"),
            created_at= safe_iso(doc.get("created_at")),
            updated_at= safe_iso(doc.get("updated_at")),
        ))

    return result 

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
    
    # Convertir la lista de tuplas a formato adecuado para Firestore
    if data["assignee"]:
        data["assignee"] = [{"id": user_id, "name": user_name} 
                           for user_id, user_name in data["assignee"]]
    
    data.update({
        "project_id": project_id,
        "updated_at": firestore.SERVER_TIMESTAMP,
        "comments": []  # siempre empieza vacío
    })
    data.setdefault("created_at", firestore.SERVER_TIMESTAMP)

    # Si viene id en el form, lo podrías usar para upsert; aquí asumimos POST → create
    new_ref = tasks_ref.document()
    new_ref.set(data)
    
    # Obtener el documento recién creado
    doc = new_ref.get().to_dict() or {}
    
    # Convertir assignee para la respuesta
    assigned_users = convert_assignee_format(doc)
    
    return TaskResponse(
        id=new_ref.id,
        title=doc.get("title", ""),
        description=doc.get("description", ""),
        user_story_id=doc.get("user_story_id", ""),
        user_story_title=doc.get("user_story_title"),
        assignee=assigned_users,
        sprint_id=doc.get("sprint_id"),
        sprint_name=doc.get("sprint_name"),
        status_khanban=doc.get("status_khanban", "Backlog"),
        priority=doc.get("priority", "Medium"),
        story_points=doc.get("story_points", 0),
        deadline=doc.get("deadline"),
        comments=doc.get("comments", []),
        created_at=doc.get("created_at", ""),
        updated_at=doc.get("updated_at", ""), 
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

    data = t.dict(exclude_unset=True, exclude_none=True)
    data["updated_at"] = firestore.SERVER_TIMESTAMP
    ref.update(data)

    updated = ref.get().to_dict() or {}

    # Convertir updated_at a string si es necesario
    if 'updated_at' in updated and hasattr(updated['updated_at'], 'isoformat'):
        updated['updated_at'] = updated['updated_at'].isoformat()
    
    # Convertir created_at si existe y es necesario
    if 'created_at' in updated and hasattr(updated['created_at'], 'isoformat'):
        updated['created_at'] = updated['created_at'].isoformat()
    

    updated_copy = {k: v for k, v in updated.items() 
                    if k not in ['id', 'comments', 'user_story_title', 
                                'assignee_id', 'sprint_name', 'created_at', 'updated_at']}
   
    return TaskResponse(
        id=task_id,
        user_story_title=updated.get("user_story_title"),
        assignee_id=updated.get("assignee_id", []),
        sprint_name=updated.get("sprint_name"),
        comments=updated.get("comments", []),
        created_at=updated.get("created_at", ""),
        updated_at=updated.get("updated_at", ""),
        **updated_copy
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