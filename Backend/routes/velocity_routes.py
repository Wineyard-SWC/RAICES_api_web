from fastapi import APIRouter
from firebase_admin import firestore
from datetime import datetime
from models.task_model import GraphicsRequest

router = APIRouter(tags=["VelocityTrend"])
db = firestore.client()

def to_date(date_time):
    return date_time.date() if date_time else None

@router.post("/api/velocitytrend")
async def get_velocity_trend(payload:GraphicsRequest):
    projectId=payload.projectId,
    tasks=payload.tasks or []

    now = datetime.now().date()

    # Obtener todos los sprints del proyecto
    sprints_snapshots = db.collection("sprints").where("project_id", "==", projectId).stream()
    sprints_data = []
    active_sprint = None

    for snap in sprints_snapshots:
        data = snap.to_dict()
        start = to_date(data.get("start_date"))
        end = to_date(data.get("end_date"))

        sprints_data.append((snap.id, data))

        if start and end and start <= now <= end:
            active_sprint = data

    if not active_sprint:
        return {"error": "No active sprint found for this project"}

    num_sprints = len(sprints_data)

    # Obtener solo story_points y status de tareas del proyecto
    if not tasks:
        tasks_snapshots = db.collection("tasks")\
            .where("project_id", "==", projectId)\
            .select("story_points", "status_khanban")\
            .stream()
    else:
        tasks_snapshots = tasks

    total_sp = 0
    done_sp = 0

    if tasks_snapshots:
        for task in tasks_snapshots:
            data = task.to_dict()
            sp = data.get("story_points", 0)
            if isinstance(sp, int):
                total_sp += sp
                if data.get("status_khanban", "").lower() == "done":
                    done_sp += sp

    planned = round(total_sp / num_sprints, 2) if num_sprints else 0

    return [
        {
            "sprint": s.get("name") or f"Sprint {s.get('number', sid[:6])}",
            "Planned": planned,
            "Actual": done_sp
        } for sid, s in sprints_data
    ]